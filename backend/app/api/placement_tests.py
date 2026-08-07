"""Endpoints do teste de nivelamento.

Regras invioláveis:
- o score é sempre calculado no backend (nunca aceito do cliente);
- gabarito, rubrica e explicação nunca são expostos antes da submissão;
- um usuário só acessa os próprios testes.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.core.levels import (
    SKILL_LABELS,
    CEFRLevel,
    LevelSource,
    ReviewStatus,
    Skill,
    TestStatus,
    level_payload,
)
from app.models import (
    Language,
    PlacementItem,
    PlacementTest,
    PlacementTestAnswer,
    PlacementTestSection,
    User,
    UserLanguage,
)
from app.schemas import PlacementAnswerIn, PlacementTestCreate, PlacementWritingIn
from app.services import placement_engine as engine
from app.services.progression import CHECKPOINT_SOURCE, apply_checkpoint_outcome
from app.services.placement_delivery import (
    approved_active_filter,
    consume_delivery_for_answer,
    deliver_item,
    get_open_delivery,
)
from app.services.writing_evaluation import evaluate_writing

router = APIRouter(prefix="/placement-tests", tags=["placement"])

#: Intervalo mínimo entre dois testes concluídos do mesmo idioma.
RETAKE_INTERVAL_DAYS = 30

#: STT disponível apenas em modo mock: a avaliação oral não é realizada.
SPEAKING_AVAILABLE = False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _owned_test(db: Session, test_id: str, user: User) -> PlacementTest:
    test = db.get(PlacementTest, test_id)
    if not test or test.user_id != user.id:
        # Mesma resposta para inexistente e alheio: não revela IDs de terceiros.
        raise APIError(404, "placement_test_not_found", "Teste não encontrado.")
    return test


def _answers_of(db: Session, test_id: str) -> list[PlacementTestAnswer]:
    return list(
        db.scalars(
            select(PlacementTestAnswer)
            .where(PlacementTestAnswer.test_id == test_id)
            .order_by(PlacementTestAnswer.created_at)
        )
    )


def _state_from(answers: list[PlacementTestAnswer], declared_beginner: bool) -> engine.TestState:
    """Reconstrói o estado adaptativo a partir das respostas persistidas."""
    state = engine.TestState(current_band=engine.initial_band(declared_beginner))
    for answer in answers:
        if answer.skill == Skill.WRITING:
            continue
        engine.register_answer(
            state,
            engine.AnswerRecord(
                skill=answer.skill,
                cefr_level=answer.cefr_level,
                normalized_score=answer.normalized_score or 0.0,
                response_time_ms=answer.response_time_ms,
            ),
        )
    return state


def _records(answers: list[PlacementTestAnswer]) -> list[engine.AnswerRecord]:
    return [
        engine.AnswerRecord(
            skill=a.skill,
            cefr_level=a.cefr_level,
            normalized_score=a.normalized_score or 0.0,
            response_time_ms=a.response_time_ms,
        )
        for a in answers
        if a.normalized_score is not None
    ]


def _public_item(item: PlacementItem) -> dict:
    """Payload do item SEM gabarito, rubrica ou explicação."""
    return {
        "id": item.id,
        "skill": item.skill,
        "skill_label": SKILL_LABELS.get(item.skill, item.skill),
        "item_type": item.item_type,
        "prompt": item.prompt,
        "instructions": item.instructions,
        "passage": item.passage,
        "options": item.options_json or [],
        "audio_url": item.audio_url,
        "audio_script": item.audio_script,
    }


def _grade(item: PlacementItem, answer: str | None) -> tuple[bool, float]:
    """Correção objetiva no backend. Retorna (correto, score normalizado)."""
    if answer is None:
        return False, 0.0
    expected = item.correct_answer_json or {}
    given = answer.strip()

    if "value" in expected:
        correct = given.casefold() == str(expected["value"]).strip().casefold()
        return correct, 1.0 if correct else 0.0

    accepted = expected.get("accepted") or []
    correct = any(given.casefold() == str(option).strip().casefold() for option in accepted)
    return correct, 1.0 if correct else 0.0


def _progress(answers: list[PlacementTestAnswer]) -> dict:
    objective = [a for a in answers if a.skill != Skill.WRITING]
    return {
        "answered": len(objective),
        "minimum": engine.MIN_OBJECTIVE_ITEMS,
        "target": engine.RECOMMENDED_OBJECTIVE_ITEMS,
        "maximum": engine.MAX_OBJECTIVE_ITEMS,
        "writing_submitted": any(a.skill == Skill.WRITING for a in answers),
    }


def _test_payload(test: PlacementTest, answers: list[PlacementTestAnswer]) -> dict:
    return {
        "id": test.id,
        "language_code": test.language_code,
        "status": test.status,
        "version": test.version,
        "source": test.source,
        "started_at": test.started_at.isoformat() if test.started_at else None,
        "completed_at": test.completed_at.isoformat() if test.completed_at else None,
        "progress": _progress(answers),
        "speaking_available": SPEAKING_AVAILABLE,
    }


# ------------------------------------------------------------------ endpoints


@router.post("")
def create_test(
    data: PlacementTestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    language = db.scalar(select(Language).where(Language.code == data.language_code))
    if not language:
        raise APIError(404, "language_not_found", "Idioma não encontrado.")

    existing = db.scalar(
        select(PlacementTest).where(
            PlacementTest.user_id == user.id,
            PlacementTest.language_code == data.language_code,
            PlacementTest.status.in_([TestStatus.PENDING, TestStatus.IN_PROGRESS]),
            # Checkpoint do cronograma é outro fluxo: não é retomado aqui nem
            # bloqueia a abertura de um teste de nivelamento completo.
            PlacementTest.source != CHECKPOINT_SOURCE,
        )
    )
    if existing:
        # Teste abandonado/incompleto é retomado, não duplicado.
        return _test_payload(existing, _answers_of(db, existing.id))

    last_completed = db.scalar(
        select(PlacementTest)
        .where(
            PlacementTest.user_id == user.id,
            PlacementTest.language_code == data.language_code,
            PlacementTest.status == TestStatus.COMPLETED,
            # O intervalo de 30 dias vale entre nivelamentos completos. Um
            # checkpoint quinzenal não pode travar o teste de verdade.
            PlacementTest.source != CHECKPOINT_SOURCE,
        )
        .order_by(PlacementTest.completed_at.desc())
    )
    if last_completed and last_completed.completed_at:
        completed_at = last_completed.completed_at
        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)
        available_at = completed_at + timedelta(days=RETAKE_INTERVAL_DAYS)
        if _now() < available_at:
            raise APIError(
                409,
                "placement_retake_too_soon",
                f"Você poderá refazer o teste a partir de {available_at.date().isoformat()}.",
            )

    test = PlacementTest(
        user_id=user.id,
        language_code=data.language_code,
        status=TestStatus.IN_PROGRESS,
        source=LevelSource.PLACEMENT_TEST,
        current_level_band=engine.initial_band(data.declared_beginner),
        result_json={"declared_beginner": data.declared_beginner},
    )
    db.add(test)
    db.commit()
    return _test_payload(test, [])


@router.get("/current")
def current_test(
    language_code: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    query = select(PlacementTest).where(
        PlacementTest.user_id == user.id,
        PlacementTest.status.in_([TestStatus.PENDING, TestStatus.IN_PROGRESS]),
        PlacementTest.source != CHECKPOINT_SOURCE,
    )
    if language_code:
        query = query.where(PlacementTest.language_code == language_code)
    test = db.scalar(query.order_by(PlacementTest.started_at.desc()))
    if not test:
        return {"test": None}
    return {"test": _test_payload(test, _answers_of(db, test.id))}


@router.get("/{test_id}")
def get_test(test_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    test = _owned_test(db, test_id, user)
    return _test_payload(test, _answers_of(db, test.id))


@router.post("/{test_id}/next-item")
def next_item(test_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    test = _owned_test(db, test_id, user)
    if test.status == TestStatus.COMPLETED:
        raise APIError(409, "placement_test_completed", "Este teste já foi concluído.")

    answers = _answers_of(db, test.id)
    answered_ids = {a.item_id for a in answers}
    declared_beginner = bool((test.result_json or {}).get("declared_beginner"))
    state = _state_from(answers, declared_beginner)

    # Retoma entrega aberta (mesmo item) se o aluno pedir next-item de novo.
    open_delivery = get_open_delivery(db, test.id)
    if open_delivery and open_delivery.item_id not in answered_ids:
        item = db.get(PlacementItem, open_delivery.item_id)
        if item and item.review_status == ReviewStatus.APPROVED and item.is_active:
            stage = "writing" if item.skill == Skill.WRITING else "objective"
            return {"item": _public_item(item), "stage": stage, "progress": _progress(answers)}

    if engine.should_stop(state):
        writing_item = _pick_writing_item(db, test, state, answered_ids)
        if writing_item:
            deliver_item(db, test, writing_item)
            db.commit()
            return {"item": _public_item(writing_item), "stage": "writing", "progress": _progress(answers)}
        return {"item": None, "stage": "ready_to_complete", "progress": _progress(answers)}

    item = _pick_objective_item(db, test.language_code, state, answered_ids)
    if item is None:
        writing_item = _pick_writing_item(db, test, state, answered_ids)
        if writing_item:
            deliver_item(db, test, writing_item)
            db.commit()
            return {"item": _public_item(writing_item), "stage": "writing", "progress": _progress(answers)}
        return {"item": None, "stage": "ready_to_complete", "progress": _progress(answers)}

    deliver_item(db, test, item)
    test.current_level_band = state.current_band
    db.commit()
    return {"item": _public_item(item), "stage": "objective", "progress": _progress(answers)}


def _pick_objective_item(
    db: Session,
    language_code: str,
    state: engine.TestState,
    answered_ids: set[str],
) -> PlacementItem | None:
    """Item da faixa atual na competência menos usada; relaxa se faltar item."""
    preferred_skill = engine.next_skill(state)
    skill_order = [preferred_skill] + [s for s in engine.OBJECTIVE_SKILLS if s != preferred_skill]

    base = [
        PlacementItem.language_code == language_code,
        *approved_active_filter(),
    ]
    if answered_ids:
        base.append(PlacementItem.id.not_in(answered_ids))

    for skill in skill_order:
        item = db.scalar(
            select(PlacementItem).where(
                *base,
                PlacementItem.cefr_level == state.current_band,
                PlacementItem.skill == skill,
            )
        )
        if item:
            return item

    for band in engine.TESTABLE_LEVELS:
        item = db.scalar(
            select(PlacementItem).where(
                *base,
                PlacementItem.cefr_level == band,
                PlacementItem.skill.in_(list(engine.OBJECTIVE_SKILLS)),
            )
        )
        if item:
            return item
    return None


def _pick_writing_item(
    db: Session,
    test: PlacementTest,
    state: engine.TestState,
    answered_ids: set[str],
) -> PlacementItem | None:
    already = db.scalar(
        select(PlacementTestAnswer).where(
            PlacementTestAnswer.test_id == test.id,
            PlacementTestAnswer.skill == Skill.WRITING,
        )
    )
    if already:
        return None

    base = [
        PlacementItem.language_code == test.language_code,
        *approved_active_filter(),
        PlacementItem.skill == Skill.WRITING,
    ]
    if answered_ids:
        base.append(PlacementItem.id.not_in(answered_ids))

    for band in [state.current_band, CEFRLevel.A2, CEFRLevel.A1]:
        item = db.scalar(select(PlacementItem).where(*base, PlacementItem.cefr_level == band))
        if item:
            return item
    return None


@router.post("/{test_id}/answers")
def submit_answer(
    test_id: str,
    data: PlacementAnswerIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    test = _owned_test(db, test_id, user)
    if test.status == TestStatus.COMPLETED:
        raise APIError(409, "placement_test_completed", "Este teste já foi concluído.")

    item = consume_delivery_for_answer(db, test=test, item_id=data.item_id)
    if item.skill == Skill.WRITING:
        raise APIError(400, "wrong_endpoint", "Use o endpoint de escrita para esta atividade.")

    duplicate = db.scalar(
        select(PlacementTestAnswer).where(
            PlacementTestAnswer.test_id == test.id,
            PlacementTestAnswer.item_id == item.id,
        )
    )
    if duplicate:
        raise APIError(409, "answer_already_submitted", "Este item já foi respondido.")

    is_correct, score = _grade(item, data.answer)
    record = PlacementTestAnswer(
        test_id=test.id,
        item_id=item.id,
        skill=item.skill,
        cefr_level=item.cefr_level,
        answer_json={"value": data.answer},
        is_correct=is_correct,
        raw_score=score,
        normalized_score=score,
        response_time_ms=data.response_time_ms,
        evaluated_by="auto",
    )
    db.add(record)

    answers = _answers_of(db, test.id) + [record]
    declared_beginner = bool((test.result_json or {}).get("declared_beginner"))
    state = _state_from(answers, declared_beginner)
    test.current_level_band = state.current_band
    db.commit()

    return {"accepted": True, "progress": _progress(answers)}


@router.post("/{test_id}/writing")
def submit_writing(
    test_id: str,
    data: PlacementWritingIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    test = _owned_test(db, test_id, user)
    if test.status == TestStatus.COMPLETED:
        raise APIError(409, "placement_test_completed", "Este teste já foi concluído.")

    item = consume_delivery_for_answer(db, test=test, item_id=data.item_id)
    if item.skill != Skill.WRITING:
        raise APIError(404, "placement_item_not_found", "Atividade de escrita não encontrada.")

    duplicate = db.scalar(
        select(PlacementTestAnswer).where(
            PlacementTestAnswer.test_id == test.id,
            PlacementTestAnswer.item_id == item.id,
        )
    )
    if duplicate:
        raise APIError(409, "answer_already_submitted", "Esta atividade já foi enviada.")

    rubric = item.rubric_json or {}
    evaluation = evaluate_writing(
        text=data.text,
        language_code=test.language_code,
        target_level=item.cefr_level,
        min_chars=int(rubric.get("min_chars", 20)),
    )

    assessed = evaluation.get("status") == "assessed"
    record = PlacementTestAnswer(
        test_id=test.id,
        item_id=item.id,
        skill=Skill.WRITING,
        cefr_level=item.cefr_level,
        answer_json={"text": data.text},
        is_correct=None,
        raw_score=evaluation.get("normalized_score"),
        normalized_score=evaluation.get("normalized_score") if assessed else None,
        response_time_ms=data.response_time_ms,
        evaluated_by=evaluation.get("evaluated_by", "heuristic"),
        feedback_json=evaluation,
    )
    db.add(record)
    db.commit()

    return {
        "accepted": True,
        "status": evaluation.get("status"),
        "evaluated_by": evaluation.get("evaluated_by"),
    }


@router.post("/{test_id}/speaking")
def submit_speaking(test_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Avaliação oral indisponível: só existe provedor STT mock.

    Responde 501 em vez de fabricar um resultado. O teste conclui normalmente
    com `speaking` registrado como não avaliada.
    """
    _owned_test(db, test_id, user)
    raise APIError(
        501,
        "speaking_not_available",
        "Avaliação oral ainda não disponível. Sua fala não será avaliada neste teste.",
    )


@router.post("/{test_id}/complete")
def complete_test(test_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    test = _owned_test(db, test_id, user)
    if test.status == TestStatus.COMPLETED:
        return _result_payload(db, test)

    answers = _answers_of(db, test.id)
    scored = _records(answers)
    if len(scored) < engine.MIN_OBJECTIVE_ITEMS:
        raise APIError(
            400,
            "placement_insufficient_items",
            f"Responda ao menos {engine.MIN_OBJECTIVE_ITEMS} itens para concluir o teste.",
        )

    started = test.started_at
    if started and started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    duration = int((_now() - started).total_seconds()) if started else None

    result = engine.build_result(scored, duration_seconds=duration)

    test.status = TestStatus.COMPLETED
    test.completed_at = _now()
    test.overall_level = result["overall_level"]
    test.confidence_score = result["confidence_score"]
    test.total_score = result["total_score"]
    test.duration_seconds = duration
    test.result_json = {**(test.result_json or {}), **result}

    for skill, data in result["skills"].items():
        section = db.scalar(
            select(PlacementTestSection).where(
                PlacementTestSection.test_id == test.id,
                PlacementTestSection.skill == skill,
            )
        )
        if section is None:
            section = PlacementTestSection(test_id=test.id, skill=skill)
            db.add(section)
        section.score = data["score"]
        section.max_score = data["max_score"]
        section.estimated_level = data["estimated_level"]
        section.status = "assessed"
        section.completed_at = _now()

    for skill in result["not_assessed_skills"]:
        section = db.scalar(
            select(PlacementTestSection).where(
                PlacementTestSection.test_id == test.id,
                PlacementTestSection.skill == skill,
            )
        )
        if section is None:
            section = PlacementTestSection(test_id=test.id, skill=skill)
            db.add(section)
        section.status = "not_assessed" if skill != Skill.SPEAKING else "not_available"
        section.estimated_level = None

    _apply_to_profile(db, test, result, user)
    # Checkpoint do cronograma: corrige a origem do nível e avalia a promoção
    # das semanas ainda pendentes. Teste comum não passa por aqui.
    if test.source == CHECKPOINT_SOURCE:
        apply_checkpoint_outcome(db, test)
    db.commit()
    return _result_payload(db, test)


def _apply_to_profile(db: Session, test: PlacementTest, result: dict, user: User) -> None:
    """Grava o resultado no perfil linguístico (user_languages)."""
    language = db.scalar(select(Language).where(Language.code == test.language_code))
    if not language:
        return

    profile = db.scalar(
        select(UserLanguage).where(
            UserLanguage.user_id == user.id,
            UserLanguage.language_id == language.id,
        )
    )
    if profile is None:
        profile = UserLanguage(user_id=user.id, language_id=language.id)
        db.add(profile)
        db.flush()

    skills = result["skills"]
    profile.current_level = result["overall_level"]
    profile.level_source = LevelSource.PLACEMENT_TEST
    profile.level_assessed_at = test.completed_at
    profile.placement_test_id = test.id
    profile.confidence_score = result["confidence_score"]
    profile.vocabulary_grammar_level = skills.get(Skill.VOCABULARY_GRAMMAR, {}).get("estimated_level")
    profile.reading_level = skills.get(Skill.READING, {}).get("estimated_level")
    profile.listening_level = skills.get(Skill.LISTENING, {}).get("estimated_level")
    profile.writing_level = skills.get(Skill.WRITING, {}).get("estimated_level")
    profile.speaking_level = skills.get(Skill.SPEAKING, {}).get("estimated_level")
    profile.recommendations_json = result["recommendations"]
    profile.diagnostic_completed = True
    if result["overall_level"]:
        profile.level_estimate = result["overall_level"]


@router.get("/{test_id}/result")
def get_result(test_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    test = _owned_test(db, test_id, user)
    if test.status != TestStatus.COMPLETED:
        raise APIError(409, "placement_test_incomplete", "Este teste ainda não foi concluído.")
    return _result_payload(db, test)


def _result_payload(db: Session, test: PlacementTest) -> dict:
    result = dict(test.result_json or {})
    result.pop("declared_beginner", None)

    sections = list(
        db.scalars(select(PlacementTestSection).where(PlacementTestSection.test_id == test.id))
    )
    skills = [
        {
            "skill": section.skill,
            "label": SKILL_LABELS.get(section.skill, section.skill),
            "estimated_level": section.estimated_level,
            "level": level_payload(section.estimated_level) if section.estimated_level else None,
            "score": section.score,
            "max_score": section.max_score,
            "status": section.status,
        }
        for section in sorted(sections, key=lambda s: s.skill)
    ]

    overall = test.overall_level
    return {
        "id": test.id,
        "language_code": test.language_code,
        "status": test.status,
        "completed_at": test.completed_at.isoformat() if test.completed_at else None,
        "duration_seconds": test.duration_seconds,
        "overall_level": overall,
        "overall": level_payload(overall) if overall else None,
        "confidence_score": test.confidence_score,
        "confidence_label": result.get("confidence_label"),
        "items_answered": result.get("items_answered"),
        "weights_used": result.get("weights_used", {}),
        "recommendations": result.get("recommendations", []),
        "skills": skills,
        "speaking_available": SPEAKING_AVAILABLE,
        "disclaimer": "Nível estimado. Não é uma certificação oficial.",
    }
