"""Fila adaptativa de revisão lexical.

`MemorySchedule` continua sendo a fonte da verdade. Esta camada só escolhe
quais itens vencidos entrar na sessão e em que ordem: fracos primeiro,
dominados com frequência reduzida. Itens legados sem schedule permanecem
válidos e não recebem explicação gramatical inventada.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.teaching import MemorySubjectType
from app.models import MemorySchedule, ReviewItem, VocabularyExample, VocabularyItem

#: Com itens fracos vencidos, no máximo um item dominado entra na sessão.
MAX_MASTERED_WHEN_WEAK = 1


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime:
    if value is None:
        return _now()
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _is_vocabulary(item: ReviewItem) -> bool:
    return item.item_type in {MemorySubjectType.VOCABULARY, "vocabulary"}


def _is_mastered(item: ReviewItem, schedule: MemorySchedule | None) -> bool:
    if schedule is not None:
        summary = (schedule.payload_json or {}).get("evidence_summary") or {}
        return schedule.state == "mastered" or bool(summary.get("mastered"))
    return item.mastery_state == "mastered"


def _sort_key(
    item: ReviewItem, schedule: MemorySchedule | None
) -> tuple[int, int, float, datetime, str]:
    mastered = 1 if _is_mastered(item, schedule) else 0
    lapses = schedule.lapse_count if schedule is not None else 0
    strength = schedule.strength if schedule is not None else 0.0
    due = _aware(schedule.due_at if schedule is not None else item.next_review_at)
    return (mastered, -lapses, strength, due, item.id)


def _schedules_for(
    db: Session, items: list[ReviewItem]
) -> dict[str, MemorySchedule]:
    if not items:
        return {}
    by_review_id = {
        schedule.review_item_id: schedule
        for schedule in db.scalars(
            select(MemorySchedule).where(
                MemorySchedule.review_item_id.in_([item.id for item in items])
            )
        )
        if schedule.review_item_id
    }
    missing = [item for item in items if item.id not in by_review_id and _is_vocabulary(item)]
    if missing:
        by_subject = {
            schedule.subject_key: schedule
            for schedule in db.scalars(
                select(MemorySchedule).where(
                    MemorySchedule.user_language_id == missing[0].user_language_id,
                    MemorySchedule.subject_type == MemorySubjectType.VOCABULARY,
                    MemorySchedule.subject_key.in_([item.reference_id for item in missing]),
                )
            )
        }
        for item in missing:
            schedule = by_subject.get(item.reference_id)
            if schedule is not None:
                by_review_id[item.id] = schedule
    return by_review_id


def due_review_items(
    db: Session,
    user_language_id: str,
    *,
    limit: int = 20,
    now: datetime | None = None,
) -> list[ReviewItem]:
    """Itens vencidos, fracos primeiro; item dominado entra no máximo uma vez."""
    reference = now or _now()
    items = list(
        db.scalars(
            select(ReviewItem).where(
                ReviewItem.user_language_id == user_language_id,
                ReviewItem.suspended.is_(False),
                ReviewItem.next_review_at <= reference,
            )
        )
    )
    schedules = _schedules_for(db, items)
    ranked = sorted(items, key=lambda item: _sort_key(item, schedules.get(item.id)))
    weak = [item for item in ranked if not _is_mastered(item, schedules.get(item.id))]
    mastered = [item for item in ranked if _is_mastered(item, schedules.get(item.id))]
    selected = weak + mastered[: MAX_MASTERED_WHEN_WEAK if weak else len(mastered)]
    return selected[:limit]


def _serialize_payload(
    db: Session, item: ReviewItem, schedule: MemorySchedule | None
) -> dict:
    payload = dict(item.payload_json or {})
    if not _is_vocabulary(item):
        payload.setdefault("review_mode", "legacy")
        return payload

    vocabulary = db.get(VocabularyItem, item.reference_id)
    if vocabulary is not None:
        payload.setdefault("term", vocabulary.term)
        payload.setdefault("translation_pt", vocabulary.translation_pt)

    example = None
    if vocabulary is not None and schedule is not None:
        example = db.scalar(
            select(VocabularyExample)
            .where(VocabularyExample.vocabulary_item_id == vocabulary.id)
            .order_by(VocabularyExample.id.asc())
            .limit(1)
        )
        if example is not None:
            payload.setdefault("example", example.example_text)
            if example.translation_pt:
                payload.setdefault("example_translation_pt", example.translation_pt)

    if schedule is not None:
        payload["review_mode"] = "lexical_v2"
        audio_targets: list[dict[str, str]] = []
        term = payload.get("term")
        if isinstance(term, str) and term.strip():
            audio_targets.append(
                {"audio_target_type": "vocabulary_item", "audio_text": term}
            )
        example_text = payload.get("example")
        if isinstance(example_text, str) and example_text.strip():
            audio_targets.append(
                {"audio_target_type": "example_sentence", "audio_text": example_text}
            )
        if audio_targets:
            payload["audio_targets"] = audio_targets
    else:
        payload["review_mode"] = "legacy"

    payload.pop("form_note", None)
    payload.pop("activity_type", None)
    return payload


def serialize_review_item(
    db: Session, item: ReviewItem, schedule: MemorySchedule | None = None
) -> dict:
    if schedule is None:
        schedule = _schedules_for(db, [item]).get(item.id)
    return {
        "id": item.id,
        "item_type": item.item_type,
        "reference_id": item.reference_id,
        "payload": _serialize_payload(db, item, schedule),
        "next_review_at": item.next_review_at,
    }


def select_due_reviews(
    db: Session,
    user_language_id: str,
    *,
    limit: int = 20,
    now: datetime | None = None,
) -> list[dict]:
    items = due_review_items(db, user_language_id, limit=limit, now=now)
    schedules = _schedules_for(db, items)
    return [serialize_review_item(db, item, schedules.get(item.id)) for item in items]
