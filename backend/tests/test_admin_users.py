"""Área de administração de contas: só a allow-list, sem cobrança."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import Language, LanguageEntitlement, Lesson, User, UserLanguage, UserPreference
from app.services.language_access import user_can_access_language


def _allow(monkeypatch, emails: str) -> None:
    monkeypatch.setattr(get_settings(), "admin_emails", emails)


def _login(client, email: str, password: str = "senha-segura") -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


def _student(db_session, email: str = "aluno@befluent.local") -> User:
    user = User(email=email, name="Aluno", password_hash=hash_password("senha-segura"))
    db_session.add(user)
    db_session.flush()
    db_session.add(UserPreference(user_id=user.id))
    db_session.commit()
    return user


def test_admin_routes_reject_empty_allowlist_and_strangers(client, auth, monkeypatch):
    _allow(monkeypatch, "")
    assert TestClient(app()).get("/api/v1/admin/users").status_code == 401
    denied = client.get("/api/v1/admin/users", headers=auth)
    assert denied.status_code == 403
    assert denied.json()["error"]["message"]

    _allow(monkeypatch, "Prof.Edesio@gmail.com")
    assert client.get("/api/v1/admin/users", headers=auth).status_code == 403
    assert client.get("/api/v1/auth/me", headers=auth).json()["is_admin"] is False


def test_admin_allowlist_matches_email_without_case(client, db_session, monkeypatch):
    owner = User(
        email="prof.edesio@gmail.com",
        name="Edesio",
        password_hash=hash_password("senha-segura"),
    )
    db_session.add(owner)
    db_session.flush()
    db_session.add(UserPreference(user_id=owner.id))
    db_session.commit()
    _allow(monkeypatch, "Prof.Edesio@gmail.com")
    headers = _login(client, "prof.edesio@gmail.com")

    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["is_admin"] is True
    listed = client.get("/api/v1/admin/users", headers=headers)
    assert listed.status_code == 200
    payload = listed.json()["users"]
    assert any(item["email"] == "prof.edesio@gmail.com" for item in payload)
    assert "password" not in listed.text
    assert "password_hash" not in listed.text


def test_deactivate_blocks_login_and_spares_the_admin(client, auth, db_session, monkeypatch):
    _allow(monkeypatch, "admin@befluent.local")
    student = _student(db_session)
    student_client = TestClient(app())
    assert student_client.post(
        "/api/v1/auth/login",
        json={"email": student.email, "password": "senha-segura"},
    ).status_code == 200

    self_deny = client.patch(
        f"/api/v1/admin/users/{_admin_id(db_session)}",
        json={"is_active": False},
        headers=auth,
    )
    assert self_deny.status_code == 403
    assert db_session.get(User, _admin_id(db_session)).is_active is True

    turned_off = client.patch(
        f"/api/v1/admin/users/{student.id}",
        json={"is_active": False},
        headers=auth,
    )
    assert turned_off.status_code == 200
    db_session.expire_all()
    assert db_session.get(User, student.id).is_active is False
    assert student_client.get("/api/v1/auth/me").status_code == 401
    assert student_client.post(
        "/api/v1/auth/login",
        json={"email": student.email, "password": "senha-segura"},
    ).status_code == 403


def test_language_grant_and_revoke_are_recorded_without_locking_study(
    client, auth, db_session, monkeypatch
):
    _allow(monkeypatch, "admin@befluent.local")
    student = _student(db_session)
    french = db_session.scalar(select(Language).where(Language.code == "fr"))
    english = db_session.scalar(select(Language).where(Language.code == "en"))
    db_session.add_all(
        [
            LanguageEntitlement(
                user_id=student.id,
                language_id=french.id,
                source="legacy",
                status="active",
            ),
            LanguageEntitlement(
                user_id=student.id,
                language_id=french.id,
                source="admin",
                status="cancelled",
                cancelled_at=datetime.now(timezone.utc),
            ),
            LanguageEntitlement(
                user_id=student.id,
                language_id=english.id,
                source="legacy",
                status="active",
            ),
        ]
    )
    db_session.commit()

    missing = client.post(
        f"/api/v1/admin/users/{student.id}/languages",
        json={"code": "la-classical"},
        headers=auth,
    )
    assert missing.status_code == 404

    granted = client.post(
        f"/api/v1/admin/users/{student.id}/languages",
        json={"code": "fr"},
        headers=auth,
    )
    assert granted.status_code == 200
    db_session.expire_all()
    admin_grant = db_session.scalar(
        select(LanguageEntitlement).where(
            LanguageEntitlement.user_id == student.id,
            LanguageEntitlement.language_id == french.id,
            LanguageEntitlement.source == "admin",
        )
    )
    assert admin_grant.status == "active"
    assert admin_grant.cancelled_at is None
    assert admin_grant.expires_at is None
    assert get_settings().language_entitlements_enabled is False

    revoked = client.post(
        f"/api/v1/admin/users/{student.id}/languages/fr/revoke",
        headers=auth,
    )
    assert revoked.status_code == 200
    db_session.expire_all()
    french_grants = db_session.scalars(
        select(LanguageEntitlement).where(
            LanguageEntitlement.user_id == student.id,
            LanguageEntitlement.language_id == french.id,
        )
    ).all()
    assert french_grants
    assert all(item.status == "cancelled" and item.cancelled_at is not None for item in french_grants)
    english_grant = db_session.scalar(
        select(LanguageEntitlement).where(
            LanguageEntitlement.user_id == student.id,
            LanguageEntitlement.language_id == english.id,
        )
    )
    assert english_grant.status == "active"
    assert user_can_access_language(db_session, student.id, "fr") is True


def test_delete_removes_personal_data_and_refuses_a_bad_confirmation(
    client, auth, db_session, monkeypatch
):
    _allow(monkeypatch, "admin@befluent.local")
    db_session.connection().exec_driver_sql("PRAGMA foreign_keys=ON")
    student = _student(db_session)
    english = db_session.scalar(select(Language).where(Language.code == "en"))
    profile = UserLanguage(user_id=student.id, language_id=english.id, is_active=True)
    db_session.add(profile)
    db_session.flush()
    lesson = Lesson(
        user_language_id=profile.id,
        title="Aula",
        objective="Cumprimentar",
        content_json={},
    )
    db_session.add(lesson)
    db_session.commit()
    student_id = student.id
    profile_id = profile.id
    lesson_id = lesson.id
    english_id = english.id
    admin_id = _admin_id(db_session)

    mismatch = client.request(
        "DELETE",
        f"/api/v1/admin/users/{student.id}",
        json={"confirm_email": "outro@befluent.local"},
        headers=auth,
    )
    assert mismatch.status_code == 400
    assert db_session.get(User, student_id) is not None

    own = client.request(
        "DELETE",
        f"/api/v1/admin/users/{admin_id}",
        json={"confirm_email": "admin@befluent.local"},
        headers=auth,
    )
    assert own.status_code == 403
    assert db_session.get(User, admin_id) is not None

    removed = client.request(
        "DELETE",
        f"/api/v1/admin/users/{student_id}",
        json={"confirm_email": "Aluno@befluent.local"},
        headers=auth,
    )
    assert removed.status_code == 200
    db_session.expire_all()
    db_session.expunge_all()
    assert db_session.get(User, student_id) is None
    assert db_session.get(Lesson, lesson_id) is None
    assert db_session.get(UserLanguage, profile_id) is None
    assert db_session.get(Language, english_id) is not None
    assert db_session.get(User, admin_id) is not None


def _admin_id(db_session) -> str:
    return db_session.scalar(select(User.id).where(User.email == "admin@befluent.local"))


def app():
    from app.main import app as fastapi_app

    return fastapi_app
