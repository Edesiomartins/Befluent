"""Progressão do cronograma: execução dos blocos, checkpoints e recuperação.

Três responsabilidades:

1. **Executar um bloco** — gerar/recuperar a lição, medir o tempo real (sessão
   de estudo) e fechar o dia quando o último bloco cai.
2. **Checkpoint** — a cada duas semanas, reavaliar o nível por competência
   reusando o motor do nivelamento em amostra curta e, com evidência
   suficiente, promover o restante do cronograma.
3. **Recuperar atraso** — comprimir ou estender, sem apagar o que foi feito.

Princípio que atravessa o módulo: nada aqui fabrica avaliação. O bloco de
revisão consome a fila real do SRS; o checkpoint usa itens revisados do banco
de nivelamento; a promoção exige dois checkpoints, não um dia bom.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.curriculum import (
    BLOCK_ASSESSED_SKILL,
    BLOCK_LESSON_MODE,
    ESSENTIAL_BLOCKS,
    BlockSkill,
    BlockStatus,
    DayStatus,
)
from app.core.errors import APIError
from app.core.levels import LEVEL_INDEX, LevelSource, TestStatus, level_at
from app.models import (
    Curriculum,
    CurriculumBlock,
    CurriculumDay,
    CurriculumWeek,
    Language,
    Lesson,
    LessonActivity,
    PlacementTest,
    ReviewItem,
    StudySession,
    User,
    UserLanguage,
)
from app.services.ai import get_ai_provider
from app.services.content_repository import fetch_approved_unit, record_lesson_usage
from app.services.learner_context import build_context, for_curriculum_block
from app.services.study_sessions import complete_session

#: A partir de quantos dias vencidos o cronograma oferece reagendamento.
OVERDUE_THRESHOLD = 5

COMPRESS = "compress"
EXTEND = "extend"
RESCHEDULE_STRATEGIES: frozenset[str] = frozenset({COMPRESS, EXTEND})

#: Acerto médio exigido em cada checkpoint para contar como evidência de
#: domínio da faixa atual.
PROMOTION_SCORE = 0.80
#: Checkpoints consecutivos exigidos. Um só não distingue aprendizado de um dia
#: bom; dois seguidos no mesmo nível já são um padrão.
PROMOTION_STREAK = 2

#: Origem gravada nos testes gerados pelo cronograma.
CHECKPOINT_SOURCE = "checkpoint"

#: Teto de itens da fila de revisão consumidos por um bloco de revisão.
REVIEW_QUEUE_LIMIT = 20


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------- execução


def _language_code(db: Session, day_owner: UserLanguage) -> str:
    language = db.get(Language, day_owner.language_id)
    if not language:
        raise APIError(404, "language_not_found", "Idioma não encontrado.")
    return language.code


def _owner_of(db: Session, day: CurriculumDay) -> UserLanguage:
    week = db.get(CurriculumWeek, day.week_id)
    curriculum = db.get(Curriculum, week.curriculum_id) if week else None
    owner = db.get(UserLanguage, curriculum.user_language_id) if curriculum else None
    if not owner:
        raise APIError(404, "curriculum_not_found", "Cronograma não encontrado.")
    return owner


def review_queue(db: Session, user_language_id: str, *, limit: int = REVIEW_QUEUE_LIMIT) -> list[ReviewItem]:
    """Fila real de revisão vencida daquele idioma (mesma de `/reviews/due`)."""
    return list(
        db.scalars(
            select(ReviewItem)
            .where(
                ReviewItem.user_language_id == user_language_id,
                ReviewItem.suspended.is_(False),
                ReviewItem.next_review_at <= _now(),
            )
            .order_by(ReviewItem.next_review_at)
            .limit(limit)
        )
    )


def _review_payload(db: Session, block: CurriculumBlock, owner: UserLanguage) -> dict:
    """Bloco de revisão: consome a fila do SRS, não gera conteúdo novo.

    Com a fila vazia, declara isso em vez de inventar itens — o aluno precisa
    saber que não há nada vencido, não receber uma revisão de mentira.
    """
    items = review_queue(db, owner.id)
    return {
        "mode": BlockSkill.REVIEW,
        "provider": "srs",
        "title": f"Revisão espaçada · {block.cefr_level}",
        "objective": "Recuperar da memória o que está vencido na sua fila de revisão.",
        "topic": block.topic,
        "level": block.cefr_level,
        "source": "srs_queue",
        "queue_empty": not items,
        "items": [
            {
                "review_item_id": item.id,
                "item_type": item.item_type,
                "reference_id": item.reference_id,
                "payload": item.payload_json,
                "next_review_at": item.next_review_at.isoformat() if item.next_review_at else None,
            }
            for item in items
        ],
        "empty_notice": (
            None
            if items
            else "Nenhum item vencido na fila hoje. Salve vocabulário para alimentar a revisão."
        ),
    }


def _generate_payload(
    db: Session,
    *,
    user: User,
    block: CurriculumBlock,
    owner: UserLanguage,
    language_code: str,
) -> tuple[dict, object | None]:
    """Conteúdo do bloco: biblioteca curada quando existir, senão IA/mock."""
    mode = BLOCK_LESSON_MODE[block.skill]
    assessed_skill = BLOCK_ASSESSED_SKILL[block.skill]

    context = build_context(db, user, language_code)
    context = for_curriculum_block(
        context,
        assessed_skill=assessed_skill,
        cefr_level=block.cefr_level,
        topic=block.topic,
    )

    curated = fetch_approved_unit(
        db,
        language_id=owner.language_id,
        level=block.cefr_level,
        skill=assessed_skill,
        mode=mode,
    )
    if curated is not None:
        unit_payload = dict(curated.payload_json or {})
        payload = {
            **unit_payload,
            "mode": mode,
            "title": curated.title or unit_payload.get("title", mode),
            "objective": unit_payload.get("objective", curated.topic or ""),
            "language_code": language_code,
            "level": curated.cefr_level,
            "content_origin": "curated_library",
            "provider": "curated_library",
        }
        if curated.attribution_text:
            payload["attribution_text"] = curated.attribution_text
        return payload, curated

    try:
        payload = get_ai_provider().generate_lesson(mode, context)
    except ValueError:
        raise APIError(400, "unsupported_mode", "Modo de estudo não suportado.")
    return payload, None


def build_block_lesson(db: Session, *, user: User, block: CurriculumBlock, day: CurriculumDay) -> dict:
    """Gera (ou recupera) a lição do bloco e a vincula em `lesson_ref`.

    Idempotente: reabrir um bloco devolve a mesma lição em vez de criar outra.
    Sem isso, cada refresh da página inflaria o histórico do aluno.
    """
    owner = _owner_of(db, day)
    language_code = _language_code(db, owner)

    if block.lesson_ref:
        existing = db.get(Lesson, block.lesson_ref)
        if existing is not None:
            return {**(existing.content_json or {}), "lesson_id": existing.id}

    if block.skill == BlockSkill.REVIEW:
        payload = _review_payload(db, block, owner)
        curated = None
    else:
        payload, curated = _generate_payload(
            db, user=user, block=block, owner=owner, language_code=language_code
        )

    payload = {**payload, "curriculum_block_id": block.id, "topic": block.topic}

    # Uma sessão por bloco: a duração vem do relógio (início → conclusão), o
    # mesmo critério das lições avulsas. `estimated_minutes` é previsão, não
    # medição — não pode virar minuto de progresso.
    session = StudySession(
        user_language_id=owner.id,
        status="active",
        ended_at=None,
        summary_short=f"Cronograma · dia {day.day_number} · {payload.get('title', block.skill)}",
    )
    db.add(session)
    db.flush()

    lesson = Lesson(
        user_language_id=owner.id,
        study_session_id=session.id,
        title=str(payload.get("title", block.topic or block.skill))[:200],
        objective=str(payload.get("objective", "")),
        content_json=payload,
        status="active",
    )
    db.add(lesson)
    db.flush()
    db.add(
        LessonActivity(
            lesson_id=lesson.id,
            position=1,
            activity_type=BLOCK_LESSON_MODE[block.skill],
            prompt=str(payload.get("objective", "")),
            payload_json=payload,
        )
    )
    if curated is not None:
        record_lesson_usage(db, lesson_id=lesson.id, content_unit_id=curated.id)

    block.lesson_ref = lesson.id
    db.flush()
    return {**payload, "lesson_id": lesson.id, "study_session_id": session.id}


def complete_block(
    db: Session,
    *,
    block: CurriculumBlock,
    day: CurriculumDay,
    score: float | None = None,
) -> dict:
    """Marca o bloco e fecha o dia quando todos os blocos estiverem concluídos."""
    if block.status != BlockStatus.COMPLETED:
        block.status = BlockStatus.COMPLETED
    if score is not None:
        block.score = score

    if block.lesson_ref:
        lesson = db.get(Lesson, block.lesson_ref)
        if lesson is not None:
            lesson.status = "completed"
            if lesson.study_session_id:
                session = db.get(StudySession, lesson.study_session_id)
                if session is not None and session.status == "active":
                    complete_session(db, session, summary=lesson.title)

    blocks = list(
        db.scalars(select(CurriculumBlock).where(CurriculumBlock.day_id == day.id))
    )
    day_completed = bool(blocks) and all(b.status == BlockStatus.COMPLETED for b in blocks)
    if day_completed:
        day.status = DayStatus.COMPLETED
        day.completed_at = _now()
    elif day.status == DayStatus.PENDING:
        day.status = DayStatus.IN_PROGRESS

    db.flush()
    return {"day_completed": day_completed}


# ---------------------------------------------------------------- checkpoints


def checkpoint_test(db: Session, curriculum_id: str, week_number: int) -> PlacementTest | None:
    """Teste de checkpoint já criado para aquela semana, se existir."""
    for test in db.scalars(
        select(PlacementTest)
        .where(PlacementTest.source == CHECKPOINT_SOURCE)
        .order_by(PlacementTest.started_at.desc())
    ):
        meta = test.result_json or {}
        if meta.get("curriculum_id") == curriculum_id and meta.get("week_number") == week_number:
            return test
    return None


def start_checkpoint(
    db: Session,
    *,
    user: User,
    curriculum: Curriculum,
    week: CurriculumWeek,
) -> PlacementTest:
    """Abre a mini-avaliação da semana de checkpoint.

    Reusa o motor do nivelamento (`placement_engine` + as rotas de
    `/placement-tests`) em vez de duplicar a entrega de itens: o teste nasce
    ancorado na faixa CEFR da semana e é respondido pelo mesmo fluxo já
    validado, com o mesmo controle anti-IDOR.

    LIMITAÇÃO DECLARADA: a amostra é curta (o mínimo do motor, ~12 a 20 itens
    objetivos, ~3 a 5 por competência, mais uma tarefa de escrita). Serve para
    ajustar o cronograma, não para emitir um nível com o peso do teste completo
    — por isso `level_source` fica `checkpoint`, e não `placement_test`.
    """
    if not week.is_checkpoint:
        raise APIError(409, "not_a_checkpoint_week", "Esta semana não tem checkpoint.")

    existing = checkpoint_test(db, curriculum.id, week.week_number)
    if existing and existing.status != TestStatus.COMPLETED:
        return existing
    if existing:
        raise APIError(
            409,
            "checkpoint_already_completed",
            "O checkpoint desta semana já foi concluído.",
        )

    owner = db.get(UserLanguage, curriculum.user_language_id)
    language = db.get(Language, owner.language_id) if owner else None
    if not owner or not language:
        raise APIError(404, "language_not_found", "Idioma não encontrado.")

    test = PlacementTest(
        user_id=user.id,
        language_code=language.code,
        status=TestStatus.IN_PROGRESS,
        source=CHECKPOINT_SOURCE,
        current_level_band=week.cefr_focus,
        result_json={
            "declared_beginner": False,
            "curriculum_id": curriculum.id,
            "week_number": week.week_number,
            "cefr_focus": week.cefr_focus,
        },
    )
    db.add(test)
    db.flush()
    return test


def completed_checkpoints(db: Session, curriculum: Curriculum) -> list[PlacementTest]:
    """Checkpoints concluídos do currículo, do mais antigo para o mais recente."""
    tests = [
        test
        for test in db.scalars(
            select(PlacementTest).where(
                PlacementTest.source == CHECKPOINT_SOURCE,
                PlacementTest.status == TestStatus.COMPLETED,
            )
        )
        if (test.result_json or {}).get("curriculum_id") == curriculum.id
    ]
    return sorted(tests, key=lambda test: test.completed_at or test.started_at)


def _accuracy(test: PlacementTest) -> float:
    result = test.result_json or {}
    maximum = result.get("max_score") or 0
    if not maximum:
        return 0.0
    return float(result.get("total_score") or 0) / float(maximum)


def evaluate_promotion(db: Session, curriculum: Curriculum) -> dict:
    """Promove o restante do cronograma após dois checkpoints consistentes.

    Regra: os dois últimos checkpoints concluídos precisam ter sido feitos na
    mesma faixa CEFR e com acerto médio ≥ 80%. Só as semanas ainda pendentes
    sobem um subnível — semanas já cumpridas ficam como foram estudadas, e
    blocos já concluídos nunca são reescritos.
    """
    history = completed_checkpoints(db, curriculum)
    if len(history) < PROMOTION_STREAK:
        return {"promoted": False, "reason": "insufficient_checkpoints"}

    recent = history[-PROMOTION_STREAK:]
    bands = {(test.result_json or {}).get("cefr_focus") for test in recent}
    if len(bands) != 1:
        return {"promoted": False, "reason": "different_bands"}
    if any(_accuracy(test) < PROMOTION_SCORE for test in recent):
        return {"promoted": False, "reason": "below_threshold"}

    band = bands.pop()
    if band is None:
        return {"promoted": False, "reason": "unknown_band"}

    last_week_number = (recent[-1].result_json or {}).get("week_number") or 0
    pending_weeks = list(
        db.scalars(
            select(CurriculumWeek)
            .where(
                CurriculumWeek.curriculum_id == curriculum.id,
                CurriculumWeek.week_number > last_week_number,
                CurriculumWeek.cefr_focus == band,
            )
            .order_by(CurriculumWeek.week_number)
        )
    )
    if not pending_weeks:
        return {"promoted": False, "reason": "nothing_to_promote"}

    promoted_level = level_at(LEVEL_INDEX[band] + 1)
    if promoted_level == band:
        return {"promoted": False, "reason": "at_ceiling"}

    changed_weeks = 0
    changed_blocks = 0
    for week in pending_weeks:
        week.cefr_focus = promoted_level
        changed_weeks += 1
        for block in db.scalars(
            select(CurriculumBlock)
            .join(CurriculumDay, CurriculumDay.id == CurriculumBlock.day_id)
            .where(
                CurriculumDay.week_id == week.id,
                CurriculumBlock.status == BlockStatus.PENDING,
            )
        ):
            block.cefr_level = promoted_level
            changed_blocks += 1

    if LEVEL_INDEX[promoted_level] > LEVEL_INDEX[curriculum.target_level]:
        curriculum.target_level = promoted_level

    db.flush()
    return {
        "promoted": True,
        "from_level": band,
        "to_level": promoted_level,
        "weeks_updated": changed_weeks,
        "blocks_updated": changed_blocks,
    }


def apply_checkpoint_outcome(db: Session, test: PlacementTest) -> dict:
    """Pós-processamento de um checkpoint concluído: origem do nível + promoção.

    O nível por competência já foi gravado pelo fluxo do nivelamento; aqui só
    corrigimos a origem (um checkpoint não tem o peso do teste completo) e
    avaliamos a promoção do cronograma.
    """
    meta = test.result_json or {}
    curriculum = db.get(Curriculum, meta.get("curriculum_id") or "")
    if curriculum is None:
        return {"promoted": False, "reason": "curriculum_not_found"}

    owner = db.get(UserLanguage, curriculum.user_language_id)
    if owner is not None:
        owner.level_source = LevelSource.CHECKPOINT

    return evaluate_promotion(db, curriculum)


# ------------------------------------------------------------------- atrasos


def overdue_days(days: list[CurriculumDay], *, reference: date) -> list[CurriculumDay]:
    """Dias vencidos ainda em aberto, do mais antigo para o mais recente."""
    return [
        day
        for day in sorted(days, key=lambda item: item.day_number)
        if day.scheduled_date < reference
        and day.status not in {DayStatus.COMPLETED, DayStatus.SKIPPED}
    ]


def _all_days(db: Session, curriculum: Curriculum) -> list[CurriculumDay]:
    return list(
        db.scalars(
            select(CurriculumDay)
            .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
            .where(CurriculumWeek.curriculum_id == curriculum.id)
            .order_by(CurriculumDay.day_number)
        )
    )


def _extend(db: Session, curriculum: Curriculum, *, reference: date) -> dict:
    """Desloca todos os dias não concluídos para frente.

    Nada é perdido: o cronograma inteiro anda, e a data de término se afasta
    exatamente pelo tanto que o aluno atrasou.
    """
    days = _all_days(db, curriculum)
    pending = [day for day in days if day.status != DayStatus.COMPLETED]
    if not pending:
        return {"shifted_days": 0, "offset_days": 0}

    offset = (reference - pending[0].scheduled_date).days
    if offset <= 0:
        return {"shifted_days": 0, "offset_days": 0}

    for day in pending:
        day.scheduled_date = day.scheduled_date + timedelta(days=offset)
    db.flush()
    return {"shifted_days": len(pending), "offset_days": offset}


def _compress(db: Session, curriculum: Curriculum, *, reference: date) -> dict:
    """Concentra o essencial dos dias vencidos nos dias que ainda restam.

    Vocabulário, gramática e revisão são remanejados; os demais blocos do dia
    vencido são marcados como concluídos-por-compressão? Não: são removidos do
    caminho crítico e o dia vira `skipped`. O aluno precisa ver que aquele dia
    não foi estudado — apagar o atraso seria mentir sobre o progresso.
    """
    days = _all_days(db, curriculum)
    late = overdue_days(days, reference=reference)
    future = [
        day
        for day in days
        if day.scheduled_date >= reference and day.status != DayStatus.COMPLETED
    ]
    if not late:
        return {"skipped_days": 0, "moved_blocks": 0, "dropped_blocks": 0}
    if not future:
        raise APIError(
            409,
            "no_remaining_days",
            "Não há dias restantes para redistribuir. Use a opção de estender o cronograma.",
        )

    next_position: dict[str, int] = {}
    for day in future:
        highest = max(
            (
                block.position
                for block in db.scalars(
                    select(CurriculumBlock).where(CurriculumBlock.day_id == day.id)
                )
            ),
            default=0,
        )
        next_position[day.id] = highest + 1

    moved = 0
    dropped = 0
    cursor = 0
    for day in late:
        pending_blocks = list(
            db.scalars(
                select(CurriculumBlock)
                .where(
                    CurriculumBlock.day_id == day.id,
                    CurriculumBlock.status == BlockStatus.PENDING,
                )
                .order_by(CurriculumBlock.position)
            )
        )
        for block in pending_blocks:
            if block.skill not in ESSENTIAL_BLOCKS:
                db.delete(block)
                dropped += 1
                continue
            target = future[cursor % len(future)]
            cursor += 1
            block.day_id = target.id
            block.position = next_position[target.id]
            next_position[target.id] += 1
            moved += 1
        day.status = DayStatus.SKIPPED

    db.flush()
    return {"skipped_days": len(late), "moved_blocks": moved, "dropped_blocks": dropped}


def reschedule(db: Session, curriculum: Curriculum, *, strategy: str, reference: date) -> dict:
    if strategy == EXTEND:
        return _extend(db, curriculum, reference=reference)
    if strategy == COMPRESS:
        return _compress(db, curriculum, reference=reference)
    raise APIError(422, "invalid_strategy", "Estratégia de reagendamento inválida.")
