"""Memória universal — abstração substituível sobre SRS.

Arquitetura V2:

- `MemorySchedule` = **fonte da verdade** da memória universal
- `ReviewItem` = projeção de compatibilidade (fila legada `/reviews`)

Convive com `ReviewItem` + `SimpleScheduler`. Não implementa FSRS.
Erros do aluno e objetivos dominados podem entrar na fila.

Atualização de revisão (legado ou V2) deve passar por `record_review` /
`answer_review_item` para evitar divergência de `due_at` e double-write.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.teaching import MemorySubjectType
from app.models import LearningError, LearningObjective, MemoryReviewEvent, MemorySchedule, ReviewItem
from app.services.srs.simple_scheduler import SimpleScheduler

logger = logging.getLogger(__name__)
_scheduler = SimpleScheduler()
#: Janela de idempotência razoável contra double-submit.
_IDEMPOTENCY_WINDOW = timedelta(seconds=2)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def get_or_create_schedule(
    db: Session,
    *,
    user_language_id: str,
    subject_type: str,
    subject_key: str,
    payload: dict | None = None,
) -> MemorySchedule:
    if subject_type not in set(MemorySubjectType):
        raise APIError(422, "invalid_memory_subject", "Tipo de memória inválido.")
    row = db.scalar(
        select(MemorySchedule).where(
            MemorySchedule.user_language_id == user_language_id,
            MemorySchedule.subject_type == subject_type,
            MemorySchedule.subject_key == subject_key,
        )
    )
    if row is not None:
        return row
    row = MemorySchedule(
        user_language_id=user_language_id,
        subject_type=subject_type,
        subject_key=subject_key,
        state="learning",
        due_at=_now(),
        payload_json=payload or {},
    )
    db.add(row)
    db.flush()
    return row


def schedule_objective_review(
    db: Session, *, user_language_id: str, objective: LearningObjective
) -> MemorySchedule:
    schedule = get_or_create_schedule(
        db,
        user_language_id=user_language_id,
        subject_type=MemorySubjectType.LEARNING_OBJECTIVE,
        subject_key=objective.code,
        payload={"objective_id": objective.id, "can_do": objective.can_do},
    )
    # Espelha no ReviewItem legado para a fila `/reviews/due` continuar útil.
    if schedule.review_item_id is None:
        review = ReviewItem(
            user_language_id=user_language_id,
            item_type="learning_objective",
            reference_id=objective.id,
            priority=2,
            interval_days=1,
            next_review_at=schedule.due_at,
            mastery_state="learning",
            payload_json={"code": objective.code, "can_do": objective.can_do},
        )
        db.add(review)
        db.flush()
        schedule.review_item_id = review.id
        db.flush()
    logger.info("memory_schedule_objective code=%s", objective.code)
    return schedule


def schedule_learner_error(
    db: Session, *, error: LearningError
) -> MemorySchedule:
    """Erro reparado (ou recorrente) entra na memória pedagógica contextual."""
    key = error.language_feature or f"{error.category}:{normalize_key(error.original)}"
    schedule = get_or_create_schedule(
        db,
        user_language_id=error.user_language_id,
        subject_type=MemorySubjectType.LEARNER_ERROR,
        subject_key=key[:160],
        payload={
            "error_id": error.id,
            "category": error.category,
            "original": error.original,
            "expected": error.expected,
            "language_feature": error.language_feature,
            "review_prompt": _error_review_prompt(error),
        },
    )
    if schedule.review_item_id is None:
        review = ReviewItem(
            user_language_id=error.user_language_id,
            item_type="learner_error",
            reference_id=error.id,
            priority=3,
            interval_days=1,
            next_review_at=schedule.due_at,
            mastery_state="learning",
            payload_json=schedule.payload_json,
        )
        db.add(review)
        db.flush()
        schedule.review_item_id = review.id
        db.flush()
    logger.info("memory_schedule_learner_error feature=%s", key)
    return schedule


def normalize_key(text: str) -> str:
    return " ".join((text or "").strip().lower().split())[:80]


def _error_review_prompt(error: LearningError) -> dict:
    """Revisa a competência, não só a tradução da palavra."""
    expected = error.expected or "…"
    return {
        "prompt_pt": "Complete ou reformule usando a forma correta.",
        "prompt": expected,
        "contrast": {"incorrect": error.original, "correct": expected},
    }


def list_due(
    db: Session, *, user_language_id: str, limit: int = 20
) -> list[MemorySchedule]:
    return list(
        db.scalars(
            select(MemorySchedule)
            .where(
                MemorySchedule.user_language_id == user_language_id,
                MemorySchedule.due_at <= _now(),
            )
            .order_by(MemorySchedule.due_at.asc())
            .limit(limit)
        )
    )


def _latest_event(db: Session, schedule_id: str) -> MemoryReviewEvent | None:
    return db.scalar(
        select(MemoryReviewEvent)
        .where(MemoryReviewEvent.memory_schedule_id == schedule_id)
        .order_by(MemoryReviewEvent.reviewed_at.desc())
        .limit(1)
    )


def _project_review_item(db: Session, schedule: MemorySchedule) -> None:
    """Espelha MemorySchedule → ReviewItem (projeção de compatibilidade)."""
    if not schedule.review_item_id:
        return
    review = db.get(ReviewItem, schedule.review_item_id)
    if review is None:
        return
    review.next_review_at = schedule.due_at
    review.interval_days = schedule.interval_days
    review.mastery_state = schedule.state
    if schedule.state == "mastered":
        review.mastery_state = "mastered"
    review.suspended = schedule.state == "suspended" or bool(review.suspended)
    review.updated_at = _now()


def record_review(
    db: Session,
    schedule: MemorySchedule,
    *,
    rating: str,
    result: str | None = None,
    response_time_ms: int | None = None,
) -> MemoryReviewEvent:
    """Autoridade única: atualiza MemorySchedule, projeta ReviewItem, emite evento."""
    recent = _latest_event(db, schedule.id)
    if (
        recent is not None
        and recent.rating == rating
        and recent.reviewed_at is not None
        and (_now() - _aware(recent.reviewed_at)) <= _IDEMPOTENCY_WINDOW
    ):
        return recent

    due_before = schedule.due_at
    try:
        due_after, interval = _scheduler.schedule(rating, schedule.interval_days)
    except ValueError as exc:
        raise APIError(422, "invalid_rating", str(exc)) from exc

    if rating == "suspend":
        schedule.state = "suspended"
        if schedule.review_item_id:
            review = db.get(ReviewItem, schedule.review_item_id)
            if review is not None:
                review.suspended = True
                review.updated_at = _now()
    else:
        schedule.due_at = due_after
        schedule.interval_days = interval
        schedule.last_reviewed_at = _now()
        schedule.review_count += 1
        if rating == "again":
            schedule.lapse_count += 1
            schedule.state = "learning"
        elif rating in {"good", "easy", "mastered"}:
            schedule.state = "reviewing" if rating != "mastered" else "mastered"
            schedule.strength = min(1.0, schedule.strength + 0.15)
        elif rating == "hard":
            schedule.state = "reviewing"
        else:
            schedule.state = "reviewing"
        _project_review_item(db, schedule)

    event = MemoryReviewEvent(
        memory_schedule_id=schedule.id,
        rating=rating,
        result=result,
        due_before=due_before,
        due_after=schedule.due_at,
        response_time_ms=response_time_ms,
    )
    db.add(event)
    db.flush()
    return event


def schedule_for_review_item(db: Session, item: ReviewItem) -> MemorySchedule | None:
    return db.scalar(
        select(MemorySchedule).where(MemorySchedule.review_item_id == item.id)
    )


def answer_review_item(
    db: Session,
    item: ReviewItem,
    *,
    rating: str,
    result: str | None = None,
    response_time_ms: int | None = None,
) -> dict:
    """Endpoint legado `/reviews/{id}/answer`.

    Se existir MemorySchedule ligado, ele é a SoT (um evento, due_at único).
    Caso contrário (vocabulário legado sem schedule), atualiza só o ReviewItem.
    """
    schedule = schedule_for_review_item(db, item)
    if schedule is not None:
        event = record_review(
            db,
            schedule,
            rating=rating,
            result=result,
            response_time_ms=response_time_ms,
        )
        # Recarrega projeção
        db.refresh(item)
        return {
            "id": item.id,
            "rating": rating,
            "next_review_at": item.next_review_at,
            "interval_days": item.interval_days,
            "suspended": item.suspended,
            "mastery_state": item.mastery_state,
            "memory_schedule_id": schedule.id,
            "memory_event_id": event.id,
            "source_of_truth": "memory_schedule",
        }

    try:
        next_at, interval = _scheduler.schedule(rating, item.interval_days)
    except ValueError as exc:
        raise APIError(
            422,
            "invalid_rating",
            "Avaliação deve ser again, hard, good, easy, suspend ou mastered.",
        ) from exc
    if rating == "suspend":
        item.suspended = True
    elif rating == "mastered":
        item.mastery_state = "mastered"
        item.next_review_at = next_at
        item.interval_days = interval
    else:
        item.next_review_at = next_at
        item.interval_days = interval
    item.updated_at = _now()
    db.flush()
    return {
        "id": item.id,
        "rating": rating,
        "next_review_at": item.next_review_at,
        "interval_days": item.interval_days,
        "suspended": item.suspended,
        "mastery_state": item.mastery_state,
        "memory_schedule_id": None,
        "memory_event_id": None,
        "source_of_truth": "review_item",
    }
