from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy import select

from app.core.config import get_settings
from app.models import Language, LanguageEntitlement, User
from app.services.language_access import (
    ensure_legacy_language_entitlement,
    user_can_access_language,
)


def _user_id(db_session) -> str:
    return db_session.scalar(select(User.id).where(User.email == "admin@befluent.local"))


def _language_id(db_session, code: str = "en") -> str:
    return db_session.scalar(select(Language.id).where(Language.code == code))


def _set_entitlements_enabled(monkeypatch, enabled: bool) -> None:
    monkeypatch.setattr(get_settings(), "language_entitlements_enabled", enabled)


def _add_entitlement(
    db_session,
    *,
    user_id: str,
    language_id: str,
    source: str = "subscription",
    status: str = "active",
    starts_at: datetime | None = None,
    expires_at: datetime | None = None,
    cancelled_at: datetime | None = None,
) -> LanguageEntitlement:
    entitlement = LanguageEntitlement(
        user_id=user_id,
        language_id=language_id,
        source=source,
        status=status,
        starts_at=starts_at or datetime.now(timezone.utc) - timedelta(days=1),
        expires_at=expires_at,
        cancelled_at=cancelled_at,
        metadata_json={},
    )
    db_session.add(entitlement)
    db_session.commit()
    return entitlement


def test_flag_desligada_preserva_acesso_sem_concessao(db_session, monkeypatch):
    """Quebra se a fundação bloquear usuários antes da flag ser ligada."""
    _set_entitlements_enabled(monkeypatch, False)

    assert user_can_access_language(db_session, _user_id(db_session), "en") is True


def test_flag_ligada_permite_concessao_vigente(db_session, monkeypatch):
    """Quebra se uma concessão ativa e dentro do período for ignorada."""
    _set_entitlements_enabled(monkeypatch, True)
    user_id = _user_id(db_session)
    _add_entitlement(
        db_session,
        user_id=user_id,
        language_id=_language_id(db_session),
        starts_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    assert user_can_access_language(db_session, user_id, "en") is True


def test_flag_ligada_nega_concessao_expirada(db_session, monkeypatch):
    """Quebra se uma concessão vencida continuar autorizando estudo."""
    _set_entitlements_enabled(monkeypatch, True)
    user_id = _user_id(db_session)
    _add_entitlement(
        db_session,
        user_id=user_id,
        language_id=_language_id(db_session),
        starts_at=datetime.now(timezone.utc) - timedelta(days=10),
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    assert user_can_access_language(db_session, user_id, "en") is False


def test_flag_ligada_nega_concessao_cancelada(db_session, monkeypatch):
    """Quebra se uma concessão cancelada continuar autorizando estudo."""
    _set_entitlements_enabled(monkeypatch, True)
    user_id = _user_id(db_session)
    _add_entitlement(
        db_session,
        user_id=user_id,
        language_id=_language_id(db_session),
        cancelled_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    assert user_can_access_language(db_session, user_id, "en") is False


def test_admin_e_trial_autorizam_sem_pagamento(db_session, monkeypatch):
    """Quebra se fontes explícitas sem billing forem tratadas como inválidas."""
    _set_entitlements_enabled(monkeypatch, True)
    language_id = _language_id(db_session)
    for source in ("admin", "trial"):
        user_id = _user_id(db_session)
        _add_entitlement(
            db_session,
            user_id=user_id,
            language_id=language_id,
            source=source,
        )

        assert user_can_access_language(db_session, user_id, "en") is True

        db_session.query(LanguageEntitlement).delete()
        db_session.commit()


def test_flag_ligada_nega_ausencia_de_concessao(db_session, monkeypatch):
    """Quebra se a flag ligada mantiver acesso aberto sem grant."""
    _set_entitlements_enabled(monkeypatch, True)

    assert user_can_access_language(db_session, _user_id(db_session), "en") is False


def test_helper_legacy_cria_concessao_idempotente(db_session):
    """Quebra se novas ativações legadas puderem duplicar grants."""
    user_id = _user_id(db_session)
    language_id = _language_id(db_session)

    first = ensure_legacy_language_entitlement(db_session, user_id, language_id)
    second = ensure_legacy_language_entitlement(db_session, user_id, language_id)

    grants = db_session.scalars(
        select(LanguageEntitlement).where(
            LanguageEntitlement.user_id == user_id,
            LanguageEntitlement.language_id == language_id,
            LanguageEntitlement.source == "legacy",
        )
    ).all()
    assert first.id == second.id
    assert len(grants) == 1
    assert grants[0].status == "active"
    assert grants[0].expires_at is None


def test_migration_cria_entitlements_legacy_para_user_languages_existentes(tmp_path):
    """Quebra se o backfill não preservar acessos existentes antes da flag."""
    user_language_id = "11111111-1111-4111-8111-111111111111"
    db_path = tmp_path / "language_entitlements.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    config.set_main_option("script_location", str(root / "alembic"))
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()

    command.upgrade(config, "0011_widen_language_codes")
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO languages (id, code, name_pt, native_name, description, "
                "strategy_summary, is_active) "
                "VALUES ('lang-en', 'en', 'Inglês', 'English', '', '', 1)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, name, is_active, created_at, updated_at) "
                "VALUES ('user-1', 'legado@befluent.local', 'hash', 'Legado', 1, "
                "'2026-01-01', '2026-01-01')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO user_languages "
                "(id, user_id, language_id, level_estimate, onboarding_completed, "
                " diagnostic_completed, is_active, started_at, updated_at) "
                "VALUES (:id, 'user-1', 'lang-en', 'A1', 1, 0, 1, "
                "'2026-01-01', '2026-01-01')",
            ),
            {"id": user_language_id},
        )

    command.upgrade(config, "head")

    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT id, user_id, language_id, source, status, expires_at, cancelled_at "
                "FROM language_entitlements"
            )
        ).one()
    assert row == (user_language_id, "user-1", "lang-en", "legacy", "active", None, None)
