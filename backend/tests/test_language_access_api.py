from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import get_settings
from app.models import Language, LanguageEntitlement, User, UserLanguage


def _set_entitlements_enabled(monkeypatch, enabled: bool) -> None:
    monkeypatch.setattr(get_settings(), "language_entitlements_enabled", enabled)


def _user_id(db_session) -> str:
    return db_session.scalar(select(User.id).where(User.email == "admin@befluent.local"))


def _language(db_session, code: str = "en") -> Language:
    return db_session.scalar(select(Language).where(Language.code == code))


def _grant(db_session, *, user_id: str, language: Language, source: str = "subscription") -> None:
    db_session.add(
        LanguageEntitlement(
            user_id=user_id,
            language_id=language.id,
            source=source,
            status="active",
            starts_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            expires_at=None,
            cancelled_at=None,
            metadata_json={},
        )
    )
    db_session.commit()


def _complete_onboarding(client, auth, language_code: str = "en"):
    return client.post(
        "/api/v1/onboarding/complete",
        json={
            "language_code": language_code,
            "level_choice": "later",
            "goal": "Conversar com confiança",
            "minutes_per_day": 20,
            "skills": [],
        },
        headers=auth,
    )


def test_catalogo_anota_estado_de_acesso_sem_ocultar_idiomas(client, auth, db_session, monkeypatch):
    """Quebra se o catálogo esconder idiomas ou não publicar locked/entitled."""
    _set_entitlements_enabled(monkeypatch, True)
    user_id = _user_id(db_session)
    _grant(db_session, user_id=user_id, language=_language(db_session, "fr"))

    response = client.get("/api/v1/languages", headers=auth)

    assert response.status_code == 200
    by_code = {item["code"]: item for item in response.json()}
    assert {"en", "fr", "la-classical"}.issubset(by_code)
    assert by_code["en"]["access_state"] == "locked"
    assert by_code["fr"]["access_state"] == "entitled"


def test_catalogo_marca_idiomas_como_available_quando_flag_desligada(client, auth, monkeypatch):
    """Quebra se a flag desligada expuser locked/entitled e mudar a UX atual."""
    _set_entitlements_enabled(monkeypatch, False)

    response = client.get("/api/v1/languages", headers=auth)

    assert response.status_code == 200
    assert {item["access_state"] for item in response.json()} == {"available"}


def test_ativacao_com_flag_desligada_preserva_fluxo_e_cria_grant_legacy(
    client, auth, db_session, monkeypatch
):
    """Quebra se ativações legadas deixarem de ganhar entitlement idempotente."""
    _set_entitlements_enabled(monkeypatch, False)

    response = client.post("/api/v1/languages/activate", json={"code": "en"}, headers=auth)

    assert response.status_code == 200
    user_id = _user_id(db_session)
    language = _language(db_session, "en")
    grant = db_session.scalar(
        select(LanguageEntitlement).where(
            LanguageEntitlement.user_id == user_id,
            LanguageEntitlement.language_id == language.id,
            LanguageEntitlement.source == "legacy",
        )
    )
    assert grant is not None
    assert grant.status == "active"
    assert grant.cancelled_at is None


def test_ativacao_com_flag_ligada_nega_idioma_sem_grant(client, auth, monkeypatch):
    """Quebra se a ativação continuar sendo a autoridade de acesso."""
    _set_entitlements_enabled(monkeypatch, True)

    response = client.post("/api/v1/languages/activate", json={"code": "en"}, headers=auth)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "language_locked"


def test_ativacao_com_flag_ligada_permite_idioma_com_grant(
    client, auth, db_session, monkeypatch
):
    """Quebra se um entitlement vigente não liberar a ativação."""
    _set_entitlements_enabled(monkeypatch, True)
    _grant(db_session, user_id=_user_id(db_session), language=_language(db_session, "en"))

    response = client.post("/api/v1/languages/activate", json={"code": "en"}, headers=auth)

    assert response.status_code == 200
    assert response.json()["code"] == "en"


def test_onboarding_com_flag_desligada_cria_grant_legacy(client, auth, db_session, monkeypatch):
    """Quebra se onboarding legado criar perfil sem preservar acesso futuro."""
    _set_entitlements_enabled(monkeypatch, False)

    response = _complete_onboarding(client, auth, "fr")

    assert response.status_code == 200
    grant = db_session.scalar(
        select(LanguageEntitlement)
        .join(Language, Language.id == LanguageEntitlement.language_id)
        .where(
            LanguageEntitlement.user_id == _user_id(db_session),
            Language.code == "fr",
            LanguageEntitlement.source == "legacy",
        )
    )
    assert grant is not None


def test_onboarding_com_flag_ligada_nega_idioma_sem_grant(client, auth, monkeypatch):
    """Quebra se o onboarding puder criar acesso quando o backend nega entitlement."""
    _set_entitlements_enabled(monkeypatch, True)

    response = _complete_onboarding(client, auth, "en")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "language_locked"


def test_lookup_de_perfil_existente_respeita_servico_central(client, auth, db_session, monkeypatch):
    """Quebra se lookups protegidos aceitarem UserLanguage como autorização."""
    _set_entitlements_enabled(monkeypatch, True)
    user_id = _user_id(db_session)
    language = _language(db_session, "en")
    db_session.add(UserLanguage(user_id=user_id, language_id=language.id, is_active=True))
    db_session.commit()

    response = client.get("/api/v1/language-profiles/en", headers=auth)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "language_locked"
