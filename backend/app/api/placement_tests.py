"""Endpoints do teste de nivelamento.

Regras invioláveis:
- o score é sempre calculado no backend (nunca aceito do cliente);
- gabarito, rubrica e explicação nunca são expostos antes da submissão;
- um usuário só acessa os próprios testes.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import hashlib

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.curriculum import GeneratedFrom
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
    CurriculumDay,
    CurriculumWeek,
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
from app.services.curriculum_generator import active_curriculum, ensure_active_curriculum
from app.services.progression import CHECKPOINT_SOURCE, apply_checkpoint_outcome
from app.services.placement_delivery import (
    approved_active_filter,
    consume_delivery_for_answer,
    deliver_item,
    get_open_delivery,
)
from app.services.writing_evaluation import evaluate_writing
from app.services.speech import save_temp_audio, transcribe_audio
from app.services.placement_production import production_result, evaluate_speaking
from app.core.config import get_settings
from app.services.placement_coverage import bank_capacity, evidence_fingerprint

router = APIRouter(prefix="/placement-tests", tags=["placement"])

#: Intervalo mínimo entre dois testes concluídos do mesmo idioma.
RETAKE_INTERVAL_DAYS = 30

#: STT disponível apenas em modo mock: a avaliação oral não é realizada.
SPEAKING_AVAILABLE = True


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _owned_test(db: Session, test_id: str, user: User, *, lock: bool = False) -> PlacementTest:
    if lock:
        # All placement writers use the same order. The user lock also fences
        # profile/curriculum creation by different placements for this account.
        # Locks last until commit/rollback; refresh status after waiting so a
        # stale identity-map object cannot run finalization a second time.
        db.scalar(select(User).where(User.id == user.id).with_for_update())
        test = db.scalar(
            select(PlacementTest)
            .where(PlacementTest.id == test_id, PlacementTest.user_id == user.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    else:
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
        if answer.skill in engine.PRODUCTION_SKILLS or answer.normalized_score is None:
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
        if a.normalized_score is not None and a.skill not in engine.PRODUCTION_SKILLS
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


def _progress(answers: list[PlacementTestAnswer], test: PlacementTest | None = None) -> dict:
    objective = [a for a in answers if a.skill in engine.OBJECTIVE_SKILLS]
    return {
        "answered": len(objective),
        "minimum": engine.MIN_OBJECTIVE_ITEMS,
        "target": (test.result_json or {}).get("coverage_plan", {}).get("target", engine.RECOMMENDED_OBJECTIVE_ITEMS) if test else engine.RECOMMENDED_OBJECTIVE_ITEMS,
        "bank_feasibility": (test.result_json or {}).get("coverage_plan", {}).get("bank_feasibility", "unknown") if test else "unknown",
        "maximum": engine.MAX_OBJECTIVE_ITEMS,
        "writing_submitted": any(a.skill == Skill.WRITING for a in answers),
        "speaking_submitted": any(a.skill == Skill.SPEAKING for a in answers),
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
        "progress": _progress(answers, test),
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
    if last_completed and last_completed.completed_at and (last_completed.result_json or {}).get("overall_estimate_status") == "sufficient":
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
        result_json={"declared_beginner": data.declared_beginner, "coverage_plan": bank_capacity(db, data.language_code)},
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
    test = _owned_test(db, test_id, user, lock=True)
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
            stage = item.skill if item.skill in engine.PRODUCTION_SKILLS else "objective"
            return {"item": _public_item(item), "stage": stage, "progress": _progress(answers, test)}

    if engine.should_stop(state):
        test.result_json = {**(test.result_json or {}), "stop_reason": "maximum_reached" if len(state.answers) >= engine.MAX_OBJECTIVE_ITEMS else "objective_coverage_satisfied"}
        writing_item = _pick_production_item(db, test, state, answered_ids)
        if writing_item:
            deliver_item(db, test, writing_item)
            db.commit()
            return {"item": _public_item(writing_item), "stage": writing_item.skill, "progress": _progress(answers, test)}
        db.commit()
        return {"item": None, "stage": "ready_to_complete", "progress": _progress(answers, test)}

    item = _pick_objective_item(db, test.language_code, state, answered_ids)
    if item is None:
        test.result_json = {**(test.result_json or {}), "stop_reason": "bank_exhausted"}
        writing_item = _pick_production_item(db, test, state, answered_ids)
        if writing_item:
            deliver_item(db, test, writing_item)
            db.commit()
            return {"item": _public_item(writing_item), "stage": writing_item.skill, "progress": _progress(answers, test)}
        db.commit()
        return {"item": None, "stage": "ready_to_complete", "progress": _progress(answers, test)}

    deliver_item(db, test, item)
    test.current_level_band = state.current_band
    db.commit()
    return {"item": _public_item(item), "stage": "objective", "progress": _progress(answers, test)}


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
    used_fingerprints = {evidence_fingerprint(item) for item in db.scalars(
        select(PlacementItem).where(PlacementItem.id.in_(answered_ids)))} if answered_ids else set()

    for skill in skill_order:
        current = engine.state_for(state, skill).current_band
        skill_answers = [a for a in state.answers if a.skill == skill]
        buckets = engine._band_accuracy(skill_answers)
        candidates = [band for band, (accuracy, count) in buckets.items()
                      if accuracy >= engine.BAND_MASTERY_THRESHOLD and count < 3]
        confirmation = max(candidates, key=engine.LEVEL_INDEX.__getitem__) if candidates else None
        preferred = confirmation if len(skill_answers) >= engine.MIN_ITEMS_PER_SKILL and engine.estimate_skill_level(skill_answers) is None else current
        bands = sorted(engine.TESTABLE_LEVELS, key=lambda band: (
            band != preferred, abs(engine.LEVEL_INDEX[band] - engine.LEVEL_INDEX[current]), engine.LEVEL_INDEX[band]))
        for band in bands:
            candidates_in_band = db.scalars(select(PlacementItem).where(
                *base, PlacementItem.cefr_level == band, PlacementItem.skill == skill,
                PlacementItem.item_type.in_(["multiple_choice", "fill_blank", "reading_comprehension", "listening_comprehension"]),
            ).order_by(PlacementItem.external_key, PlacementItem.id))
            for item in candidates_in_band:
                if evidence_fingerprint(item) not in used_fingerprints:
                    return item
    return None


def _pick_production_item(db, test, state, answered_ids):
    answered_skills = {a.skill for a in _answers_of(db, test.id)}
    for skill, item_type in ((Skill.WRITING, "short_writing"), (Skill.SPEAKING, "speaking_prompt")):
        if skill in answered_skills:
            continue
        item = db.scalar(select(PlacementItem).where(
            PlacementItem.language_code == test.language_code, *approved_active_filter(),
            PlacementItem.skill == skill, PlacementItem.item_type == item_type,
            PlacementItem.cefr_level.in_(engine.TESTABLE_LEVELS),
        ).order_by((PlacementItem.cefr_level == "B1").desc(), PlacementItem.external_key.desc()))
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
    test = _owned_test(db, test_id, user, lock=True)
    if test.status == TestStatus.COMPLETED:
        raise APIError(409, "placement_test_completed", "Este teste já foi concluído.")

    item = consume_delivery_for_answer(db, test=test, item_id=data.item_id)
    if item.skill in engine.PRODUCTION_SKILLS:
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

    return {"accepted": True, "progress": _progress(answers, test)}


@router.post("/{test_id}/writing")
def submit_writing(
    test_id: str,
    data: PlacementWritingIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    test = _owned_test(db, test_id, user, lock=True)
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
        native_language=user.native_language,
        task=item.prompt,
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
async def submit_speaking(test_id: str, item_id: str = Form(...), file: UploadFile = File(...),
                          db: Session = Depends(get_db), user: User = Depends(current_user)):
    test = _owned_test(db, test_id, user, lock=True)
    if test.status == TestStatus.COMPLETED:
        raise APIError(409, "placement_test_completed", "Este teste já foi concluído.")
    item = consume_delivery_for_answer(db, test=test, item_id=item_id)
    if item.skill != Skill.SPEAKING:
        raise APIError(400, "wrong_endpoint", "Esta atividade não é de fala.")
    mime = (file.content_type or "").split(";")[0]
    if mime not in {"audio/webm", "audio/ogg", "audio/wav", "audio/mp4", "audio/mpeg"}:
        raise APIError(400, "invalid_audio_format", "Envie um arquivo de áudio compatível.")
    data = await file.read(get_settings().max_audio_bytes + 1)
    if not data:
        raise APIError(400, "empty_audio", "A gravação está vazia.")
    try:
        path = save_temp_audio(data)
    except ValueError as exc:
        raise APIError(413, "audio_too_large", str(exc)) from exc
    try:
        transcript = transcribe_audio(path, test.language_code, mime)
        if transcript.get("provider") == "mock":
            raise APIError(503, "stt_unavailable", "Reconhecimento real não está configurado. Tente novamente ou pule a fala.")
        if not str(transcript.get("text", "")).strip():
            raise APIError(422, "speech_not_recognized", "Não foi possível reconhecer fala. Grave novamente.")
        evaluation = evaluate_speaking(transcript, test.language_code, item.cefr_level,
                                       user.native_language, item.prompt)
    finally:
        if os.path.exists(path):
            os.unlink(path)
    db.add(PlacementTestAnswer(test_id=test.id, item_id=item.id, skill=Skill.SPEAKING,
        cefr_level=item.cefr_level, answer_json={"transcript": transcript["text"],
            "audio_metadata": {"received": True, "sha256": hashlib.sha256(data).hexdigest(),
                               "bytes": len(data), "mime_type": mime, "retained": False}},
        normalized_score=evaluation.get("normalized_score"), raw_score=evaluation.get("normalized_score"),
        evaluated_by=evaluation.get("evaluated_by", "unavailable"), feedback_json=evaluation))
    db.commit()
    return {"accepted": True, "status": "provisional", "transcript": transcript["text"],
            "limitations": evaluation["limitations"]}


@router.post("/{test_id}/skip-production")
def skip_production(test_id: str, data: PlacementWritingIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    test = _owned_test(db, test_id, user, lock=True)
    if test.status == TestStatus.COMPLETED:
        raise APIError(409, "placement_test_completed", "Este teste já foi concluído.")
    item = consume_delivery_for_answer(db, test=test, item_id=data.item_id)
    if item.skill not in engine.PRODUCTION_SKILLS:
        raise APIError(400, "wrong_endpoint", "Esta atividade não é de produção.")
    db.add(PlacementTestAnswer(test_id=test.id, item_id=item.id, skill=item.skill,
        cefr_level=item.cefr_level, answer_json={}, evaluated_by="not_evaluated",
        feedback_json={"status": "skipped", "limitations": ["user_skipped"]}))
    db.commit()
    return {"accepted": True, "status": "not_collected"}


@router.post("/{test_id}/complete")
def complete_test(test_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    test = _owned_test(db, test_id, user, lock=True)
    if test.status == TestStatus.COMPLETED:
        return _result_payload(db, test, user=user)

    answers = _answers_of(db, test.id)
    scored = _records(answers)
    if not answers and (test.result_json or {}).get("stop_reason") != "bank_exhausted":
        raise APIError(
            400,
            "placement_insufficient_items",
            f"Responda ao menos {engine.MIN_OBJECTIVE_ITEMS} itens para concluir o teste.",
        )

    started = test.started_at
    if started and started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    duration = int((_now() - started).total_seconds()) if started else None

    production = {a.skill: production_result(a) for a in answers if a.skill in engine.PRODUCTION_SKILLS}
    result = engine.build_result(scored, duration_seconds=duration, production_results=production)
    capacity = (test.result_json or {}).get("coverage_plan") or bank_capacity(db, test.language_code)
    result["assessment_coverage"].update(capacity)
    result["assessment_coverage"]["stop_reason"] = (test.result_json or {}).get("stop_reason", "user_completed")
    result["assessment_coverage"]["supported_skills"] = list(engine.OBJECTIVE_SKILLS) + ["writing", "speaking"]
    result["assessment_coverage"]["supported_scope_status"] = "sufficient" if all(
        result["skills"][s]["status"] == "estimated" for s in engine.OBJECTIVE_SKILLS) else "insufficient"
    result["assessment_coverage"]["supported_scope"] = list(engine.OBJECTIVE_SKILLS)
    result["assessment_coverage"]["speaking_scope"] = "transcript_linguistic_content"
    _add_diagnostic_contract(result, scored)

    test.status = TestStatus.COMPLETED
    test.completed_at = _now()
    test.overall_level = result["overall_level"]
    test.confidence_score = result["confidence_score"]
    test.total_score = result["total_score"]
    test.duration_seconds = duration
    test.result_json = {**(test.result_json or {}), **result}

    # Build the final values before touching ORM sections: writing overrides its
    # not-assessed entry. Never SELECT twice for a pending row (autoflush=False).
    section_values = {
        skill: {
            "score": data["score"] or 0.0, "max_score": data["max_score"] or 0.0,
            "estimated_level": data["estimated_level"],
            "status": {"estimated": "assessed", "not_collected": "not_assessed", "unavailable": "not_available"}.get(data["status"], "calibrating"),
            "completed_at": test.completed_at if data["evidence_counts"]["answered"] else None,
        }
        for skill, data in result["skills"].items()
    }

    # The parent locks above serialize all section writers, protecting the
    # get-or-update against parallel requests as well as preserving row IDs.
    sections = {section.skill: section for section in db.scalars(
        select(PlacementTestSection).where(PlacementTestSection.test_id == test.id)
        .execution_options(populate_existing=True)
    )}
    for skill, values in section_values.items():
        section = sections.get(skill)
        if section is None:
            section = PlacementTestSection(test_id=test.id, skill=skill)
            db.add(section)
            sections[skill] = section
        for field, value in values.items():
            setattr(section, field, value)

    _apply_to_profile(db, test, result, user)
    # Checkpoint do cronograma: corrige a origem do nível e avalia a promoção
    # das semanas ainda pendentes. Teste comum não passa por aqui.
    if test.source == CHECKPOINT_SOURCE:
        apply_checkpoint_outcome(db, test)
    else:
        # Nivelamento inicial: o caminho diário nasce junto com o resultado.
        language = db.scalar(select(Language).where(Language.code == test.language_code))
        if language is not None:
            profile = db.scalar(
                select(UserLanguage).where(
                    UserLanguage.user_id == user.id,
                    UserLanguage.language_id == language.id,
                )
            )
            if profile is not None and result["diagnostic_status"] == "ready":
                # A ready diagnostic has objective skill levels. Failure to
                # consolidate its curriculum must roll back the whole request,
                # rather than commit a completed test that retries cannot repair.
                ensure_active_curriculum(
                    db,
                    profile.id,
                    duration_days=90,
                    generated_from=GeneratedFrom.PLACEMENT,
                )
    db.commit()
    return _result_payload(db, test, user=user)


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
    previous_summary = profile.assessment_summary_json or {}
    previous_global_status = previous_summary.get("global_estimate_status", previous_summary.get("overall_estimate_status"))
    profile.last_assessment_id = test.id
    profile.assessment_summary_json = {
        "overall_estimate_status": result["overall_estimate_status"],
        "global_estimate_status": "sufficient" if result["overall_estimate_status"] == "sufficient" and test.source != CHECKPOINT_SOURCE else previous_global_status,
        "assessment_coverage": result["assessment_coverage"],
        "skills": skills, "policy_version": result["policy_version"],
    }
    objective_levels = [r["estimated_level"] for s, r in skills.items()
                        if s in engine.OBJECTIVE_SKILLS and r["status"] == "estimated"]
    if objective_levels and not profile.planning_level:
        profile.planning_level = min(objective_levels, key=engine.LEVEL_INDEX.__getitem__)
        profile.planning_level_source = "partial_placement"
    sufficient = result["overall_estimate_status"] == "sufficient" and test.source != CHECKPOINT_SOURCE
    if sufficient:
        profile.current_level = result["overall_level"]
        profile.level_estimate = result["overall_level"]
        profile.level_source = LevelSource.PLACEMENT_TEST
        profile.level_assessed_at = test.completed_at
        profile.placement_test_id = test.id
        profile.confidence_score = None
        profile.diagnostic_completed = True
    elif not profile.current_level:
        profile.level_source = LevelSource.PENDING
        profile.diagnostic_completed = False
    for skill, column in ((Skill.VOCABULARY_GRAMMAR, "vocabulary_grammar_level"),
                          (Skill.READING, "reading_level"), (Skill.LISTENING, "listening_level"),
                          (Skill.WRITING, "writing_level"), (Skill.SPEAKING, "speaking_level")):
        value = skills[skill]
        if value["status"] == "estimated" and (sufficient or not getattr(profile, column)):
            setattr(profile, column, value["estimated_level"])
    profile.recommendations_json = result["priority_focus"]



def _add_diagnostic_contract(result: dict, scored: list[engine.AnswerRecord]) -> None:
    """Expõe apenas uma estimativa sustentada por evidência objetiva."""
    ready = result["overall_level"] is not None
    result["diagnostic_status"] = "ready" if ready else "calibrating"
    if not ready:
        result["confidence_score"] = None
        result["confidence_label"] = None

    assessed = set(result["assessed_skills"])
    focus: list[dict] = []
    for skill in engine.OBJECTIVE_SKILLS:
        if skill not in assessed:
            focus.append(
                {
                    "skill": skill,
                    "reason": "insufficient_evidence",
                    "priority": 1,
                    "href": "/learn",
                }
            )

    for item in result["recommendations"]:
        if item["skill"] in engine.OBJECTIVE_SKILLS and item["reason"] == "below_overall":
            focus.append(
                {
                    "skill": item["skill"],
                    "reason": "needs_practice",
                    "priority": 1,
                    "href": "/learn",
                }
            )

    # A menor acurácia objetiva orienta a prática, antes de produção não acionável.
    accuracies: dict[str, float] = {}
    for answer in scored:
        accuracies.setdefault(answer.skill, 0.0)
        accuracies[answer.skill] += answer.normalized_score
    counts = {skill: sum(1 for answer in scored if answer.skill == skill) for skill in accuracies}
    for skill, total in sorted(accuracies.items(), key=lambda item: (item[1] / counts[item[0]], item[0])):
        if not any(item["skill"] == skill for item in focus):
            focus.append(
                {
                    "skill": skill,
                    "reason": "lowest_accuracy",
                    "priority": 2,
                    "href": "/learn",
                }
            )

    result["priority_focus"] = focus[:3]
    result["recommendations"] = result["priority_focus"]


@router.get("/{test_id}/result")
def get_result(test_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    test = _owned_test(db, test_id, user)
    if test.status != TestStatus.COMPLETED:
        raise APIError(409, "placement_test_incomplete", "Este teste ainda não foi concluído.")
    return _result_payload(db, test, user=user)


def _curriculum_summary(db: Session, user: User | None, language_code: str) -> dict | None:
    if user is None:
        return None
    language = db.scalar(select(Language).where(Language.code == language_code))
    if language is None:
        return None
    profile = db.scalar(
        select(UserLanguage).where(
            UserLanguage.user_id == user.id,
            UserLanguage.language_id == language.id,
        )
    )
    if profile is None:
        return None
    curriculum = active_curriculum(db, profile.id)
    if curriculum is None:
        return None
    day = db.scalar(
        select(CurriculumDay)
        .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
        .where(CurriculumWeek.curriculum_id == curriculum.id)
        .order_by(CurriculumDay.day_number)
    )
    return {
        "id": curriculum.id,
        "duration_days": curriculum.duration_days,
        "entry_level": curriculum.entry_level,
        "target_level": curriculum.target_level,
        "day_href": f"/cronograma/dia/{day.id}" if day else "/cronograma",
    }


def _result_payload(db: Session, test: PlacementTest, *, user: User | None = None) -> dict:
    result = dict(test.result_json or {})
    result.pop("declared_beginner", None)

    if result.get("result_schema_version") != 2:
        answers = _answers_of(db, test.id)
        result = engine.build_result(_records(answers), production_results={
            a.skill: production_result(a) for a in answers if a.skill in engine.PRODUCTION_SKILLS})
        result["coverage_origin"] = "legacy_reconstructed" if answers else "legacy_coverage_unknown"
        result["legacy_overall_level"] = test.overall_level
        _add_diagnostic_contract(result, _records(answers))
    skills = [{**data, "label": SKILL_LABELS[skill],
               "level": level_payload(data["estimated_level"]) if data["estimated_level"] else None}
              for skill, data in result["skills"].items()]

    overall = result.get("overall_level")
    return {
        **result,
        "id": test.id,
        "language_code": test.language_code,
        "status": test.status,
        "completed_at": test.completed_at.replace(tzinfo=timezone.utc).isoformat() if test.completed_at else None,
        "duration_seconds": test.duration_seconds,
        "overall_level": overall,
        "overall": level_payload(overall) if overall else None,
        "confidence_score": None,
        "confidence_label": result.get("confidence_label"),
        "items_answered": result.get("items_answered"),
        "weights_used": result.get("weights_used", {}),
        "recommendations": result.get("recommendations", []),
        "priority_focus": result.get("priority_focus", result.get("recommendations", []))[:3],
        "diagnostic_status": result.get(
            "diagnostic_status", "ready" if overall else "calibrating"
        ),
        "skills": skills,
        "speaking_available": SPEAKING_AVAILABLE,
        "disclaimer": "Nível estimado. Não é uma certificação oficial.",
        "curriculum": _curriculum_summary(db, user, test.language_code),
    }
