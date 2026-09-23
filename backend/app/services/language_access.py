from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Language, LanguageEntitlement


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def entitlement_is_current(entitlement: LanguageEntitlement, *, now: datetime) -> bool:
    """Regra canônica: só `active` sem cancelamento e dentro da janela é vigente."""
    if entitlement.status != "active" or entitlement.cancelled_at is not None:
        return False
    starts_at = _as_aware_utc(entitlement.starts_at)
    expires_at = _as_aware_utc(entitlement.expires_at) if entitlement.expires_at else None
    return starts_at <= now and (expires_at is None or expires_at > now)


def user_can_access_language(db: Session, user_id: str, language_code: str) -> bool:
    if not get_settings().language_entitlements_enabled:
        return True

    language_id = db.scalar(select(Language.id).where(Language.code == language_code))
    if language_id is None:
        return False

    entitlements = db.scalars(
        select(LanguageEntitlement).where(
            LanguageEntitlement.user_id == user_id,
            LanguageEntitlement.language_id == language_id,
        )
    )
    now = _utcnow()
    return any(entitlement_is_current(entitlement, now=now) for entitlement in entitlements)


def ensure_legacy_language_entitlement(
    db: Session, user_id: str, language_id: str
) -> LanguageEntitlement:
    query = select(LanguageEntitlement).where(
        LanguageEntitlement.user_id == user_id,
        LanguageEntitlement.language_id == language_id,
        LanguageEntitlement.source == "legacy",
    )
    existing = db.scalar(
        query
    )
    if existing is not None:
        return existing

    try:
        with db.begin_nested():
            entitlement = LanguageEntitlement(
                user_id=user_id,
                language_id=language_id,
                source="legacy",
                status="active",
                starts_at=_utcnow(),
                expires_at=None,
                cancelled_at=None,
                metadata_json={},
            )
            db.add(entitlement)
            db.flush()
            return entitlement
    except IntegrityError:
        winner = db.scalar(query)
        if winner is None:
            raise
        return winner
