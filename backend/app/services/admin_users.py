"""Operações de conta da área de administração.

Liberar ou tirar um idioma só grava LanguageEntitlement. Não liga
LANGUAGE_ENTITLEMENTS_ENABLED. Apagar a conta remove a pessoa; o banco
leva o que é só dela e conserva o catálogo.
"""

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models import (
    AuditLog,
    ContentReview,
    Language,
    LanguageEntitlement,
    User,
)
from app.services.language_access import entitlement_is_current


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _user_or_404(db: Session, user_id: str) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise APIError(404, "user_not_found", "Usuário não encontrado.")
    return user


def _reject_self(actor: User, target: User) -> None:
    if actor.id == target.id:
        raise APIError(
            403,
            "admin_self",
            "Você não pode desativar ou apagar a sua própria conta.",
        )


def list_users(db: Session) -> list[dict]:
    users = list(db.scalars(select(User).order_by(User.name, User.email)))
    if not users:
        return []
    user_ids = [user.id for user in users]
    entitlements = db.scalars(
        select(LanguageEntitlement).where(LanguageEntitlement.user_id.in_(user_ids))
    ).all()
    languages = {
        language.id: language
        for language in db.scalars(select(Language)).all()
    }
    now = _utcnow()
    grouped: dict[str, list[dict]] = {user.id: [] for user in users}
    for entitlement in entitlements:
        if not entitlement_is_current(entitlement, now=now):
            continue
        language = languages.get(entitlement.language_id)
        if language is None:
            continue
        grouped[entitlement.user_id].append(
            {
                "code": language.code,
                "name_pt": language.name_pt,
                "source": entitlement.source,
                "status": entitlement.status,
            }
        )
    return [
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
            "languages": sorted(grouped[user.id], key=lambda item: item["name_pt"]),
        }
        for user in users
    ]


def set_user_active(db: Session, actor: User, user_id: str, is_active: bool) -> dict:
    target = _user_or_404(db, user_id)
    _reject_self(actor, target)
    target.is_active = is_active
    db.commit()
    return {"id": target.id, "is_active": target.is_active}


def grant_language(db: Session, user_id: str, code: str) -> dict:
    target = _user_or_404(db, user_id)
    language = db.scalar(
        select(Language).where(Language.code == code, Language.is_active.is_(True))
    )
    if language is None:
        raise APIError(404, "language_not_found", "Idioma não encontrado.")
    existing = db.scalar(
        select(LanguageEntitlement).where(
            LanguageEntitlement.user_id == target.id,
            LanguageEntitlement.language_id == language.id,
            LanguageEntitlement.source == "admin",
        )
    )
    if existing is None:
        existing = LanguageEntitlement(
            user_id=target.id,
            language_id=language.id,
            source="admin",
            status="active",
            starts_at=_utcnow(),
            expires_at=None,
            cancelled_at=None,
            metadata_json={},
        )
        db.add(existing)
    else:
        existing.status = "active"
        existing.cancelled_at = None
        existing.expires_at = None
    db.commit()
    return {"user_id": target.id, "code": language.code, "source": "admin", "status": "active"}


def revoke_language(db: Session, user_id: str, code: str) -> dict:
    target = _user_or_404(db, user_id)
    language = db.scalar(select(Language).where(Language.code == code))
    if language is None:
        raise APIError(404, "language_not_found", "Idioma não encontrado.")
    now = _utcnow()
    entitlements = db.scalars(
        select(LanguageEntitlement).where(
            LanguageEntitlement.user_id == target.id,
            LanguageEntitlement.language_id == language.id,
        )
    ).all()
    for entitlement in entitlements:
        if entitlement_is_current(entitlement, now=now):
            entitlement.status = "cancelled"
            entitlement.cancelled_at = now
    db.commit()
    return {"user_id": target.id, "code": language.code, "status": "cancelled"}


def delete_user(db: Session, actor: User, user_id: str, confirm_email: str) -> dict:
    target = _user_or_404(db, user_id)
    _reject_self(actor, target)
    if confirm_email.strip().casefold() != target.email.casefold():
        raise APIError(
            400,
            "confirm_email_mismatch",
            "Digite o e-mail da conta para confirmar.",
        )
    db.execute(update(AuditLog).where(AuditLog.user_id == target.id).values(user_id=None))
    db.execute(
        update(ContentReview)
        .where(ContentReview.reviewer_user_id == target.id)
        .values(reviewer_user_id=None)
    )
    _enable_sqlite_foreign_keys(db)
    db.delete(target)
    db.commit()
    return {"id": user_id, "deleted": True}


def _enable_sqlite_foreign_keys(db: Session) -> None:
    """SQLite só aplica ON DELETE CASCADE com a pragma ligada, fora de transação."""
    bind = db.get_bind()
    if bind.dialect.name != "sqlite":
        return
    db.commit()
    db.connection().exec_driver_sql("PRAGMA foreign_keys=ON")
