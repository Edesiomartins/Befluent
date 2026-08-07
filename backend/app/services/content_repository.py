"""Consulta de unidades pedagógicas aprovadas para uso em lições."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.content_policy import ValidationStatus
from app.core.levels import LEVEL_INDEX, LEVEL_ORDER
from app.models import ContentSource, ContentUnit, LessonContentUsage


def _nearby_levels(level: str) -> list[str]:
    if level not in LEVEL_INDEX:
        return list(LEVEL_ORDER)
    idx = LEVEL_INDEX[level]
    candidates: list[str] = []
    for offset in (0, -1, 1, -2, 2):
        pos = idx + offset
        if 0 <= pos < len(LEVEL_ORDER):
            candidates.append(LEVEL_ORDER[pos])
    return candidates


def _public_payload(unit: ContentUnit) -> dict:
    """Remove metadados internos sensíveis antes de expor ao cliente."""
    payload = dict(unit.payload_json or {})
    for key in (
        "internal_notes",
        "source_excerpt_raw",
        "review_notes",
        "file_hash",
        "similarity_debug",
    ):
        payload.pop(key, None)
    return {
        "id": unit.id,
        "title": unit.title,
        "topic": unit.topic,
        "cefr_level": unit.cefr_level,
        "skill": unit.skill,
        "mode": unit.mode,
        "content_type": unit.content_type,
        "payload": payload,
        "attribution_text": unit.attribution_text,
    }


def _pick_unit(
    db: Session,
    *,
    base_filters: list,
    band: str,
    topic: str | None,
) -> ContentUnit | None:
    """Prefere unidade cujo tópico casa com o bloco; senão a mais recente."""
    source_ok = ContentSource.review_status == ValidationStatus.APPROVED
    if topic and topic.strip():
        needle = topic.strip().lower()
        # Match simples por substring — tópicos do currículo e da biblioteca
        # não compartilham taxonomia rígida ainda.
        candidates = list(
            db.scalars(
                select(ContentUnit)
                .join(ContentSource, ContentSource.id == ContentUnit.source_id)
                .where(
                    *base_filters,
                    ContentUnit.cefr_level == band,
                    source_ok,
                    ContentUnit.topic.is_not(None),
                )
                .order_by(ContentUnit.updated_at.desc())
                .limit(24)
            )
        )
        for unit in candidates:
            hay = (unit.topic or "").lower()
            if needle in hay or hay in needle:
                return unit
    return db.scalar(
        select(ContentUnit)
        .join(ContentSource, ContentSource.id == ContentUnit.source_id)
        .where(
            *base_filters,
            ContentUnit.cefr_level == band,
            source_ok,
        )
        .order_by(ContentUnit.updated_at.desc())
    )


def fetch_approved_unit(
    db: Session,
    *,
    language_id: str,
    level: str,
    skill: str,
    mode: str,
    exclude_ids: set[str] | None = None,
    topic: str | None = None,
) -> ContentUnit | None:
    """Busca unidade aprovada mais próxima do nível pedido; None se indisponível."""
    exclude_ids = exclude_ids or set()
    base_filters = [
        ContentUnit.language_id == language_id,
        ContentUnit.skill == skill,
        ContentUnit.mode == mode,
        ContentUnit.validation_status == ValidationStatus.APPROVED,
        ContentUnit.is_active.is_(True),
    ]
    if exclude_ids:
        base_filters.append(ContentUnit.id.not_in(exclude_ids))

    for band in _nearby_levels(level):
        unit = _pick_unit(db, base_filters=base_filters, band=band, topic=topic)
        if unit:
            return unit
    return None


def record_lesson_usage(
    db: Session,
    *,
    lesson_id: str,
    content_unit_id: str,
    usage_type: str = "primary",
) -> LessonContentUsage:
    usage = LessonContentUsage(
        lesson_id=lesson_id,
        content_unit_id=content_unit_id,
        usage_type=usage_type,
    )
    db.add(usage)
    db.flush()
    return usage


def public_unit_or_none(unit: ContentUnit | None) -> dict | None:
    return _public_payload(unit) if unit else None
