"""Retomada de prática: recarregar não abre outra lição.

`practiced` continua significando entregue, não concluída. A unidade já
gravada em LessonContentUsage permanece fora da próxima seleção. O que muda
é que uma lição ainda active do mesmo modo é devolvida de novo.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
import threading

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.content_policy import ValidationStatus
from app.core.levels import CEFRLevel, LevelSource
from app.main import app
from app.models import (
    ContentSource,
    ContentUnit,
    Language,
    Lesson,
    LessonContentUsage,
    User,
    UserLanguage,
)


def _profile(db, code: str) -> UserLanguage:
    user = db.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db.scalar(select(Language).where(Language.code == code))
    profile = UserLanguage(
        user_id=user.id,
        language_id=language.id,
        current_level=CEFRLevel.A2,
        level_source=LevelSource.PLACEMENT_TEST,
        assessment_summary_json={"global_estimate_status": "sufficient"},
        is_active=True,
        onboarding_completed=True,
    )
    db.add(profile)
    db.commit()
    return profile


def _guided_units(db) -> tuple[ContentUnit, ContentUnit]:
    language = db.scalar(select(Language).where(Language.code == "en"))
    source = ContentSource(
        title="Fonte da retomada",
        language_id=language.id,
        review_status=ValidationStatus.APPROVED,
        usage_policy="OPEN_LICENSE",
    )
    db.add(source)
    db.flush()
    older = ContentUnit(
        source_id=source.id,
        language_id=language.id,
        cefr_level="A2",
        skill="vocabulary_grammar",
        mode="guided",
        title="Unidade já entregue",
        payload_json={"objective": "Praticar a primeira unidade."},
        validation_status=ValidationStatus.APPROVED,
        is_active=True,
        updated_at=datetime(2026, 11, 1, tzinfo=UTC),
    )
    newer = ContentUnit(
        source_id=source.id,
        language_id=language.id,
        cefr_level="A2",
        skill="vocabulary_grammar",
        mode="guided",
        title="Unidade seguinte",
        payload_json={"objective": "Praticar a segunda unidade."},
        validation_status=ValidationStatus.APPROVED,
        is_active=True,
        updated_at=datetime(2026, 11, 2, tzinfo=UTC),
    )
    db.add_all([older, newer])
    db.commit()
    return older, newer


def _generate(client, auth, code="en", mode="guided"):
    response = client.post(
        "/api/v1/lessons/generate",
        json={"language_code": code, "mode": mode},
        headers=auth,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_reload_resumes_the_active_practice(client, auth, db_session):
    profile = _profile(db_session, "en")
    older, newer = _guided_units(db_session)

    first = _generate(client, auth)
    second = _generate(client, auth)

    assert second["lesson_id"] == first["lesson_id"]
    assert second["study_session_id"] == first["study_session_id"]
    assert second["title"] == first["title"] == "Unidade seguinte"
    assert second["selection_trace"]["reason"] == "resumed_active_practice"
    assert first["selection_trace"]["delivered"]["content_unit_id"] == newer.id
    db_session.expire_all()
    lessons = db_session.scalars(select(Lesson).where(Lesson.user_language_id == profile.id)).all()
    usages = db_session.scalars(select(LessonContentUsage)).all()
    assert [lesson.id for lesson in lessons] == [first["lesson_id"]]
    assert [usage.content_unit_id for usage in usages] == [newer.id]
    assert older.id not in {usage.content_unit_id for usage in usages}


def test_completed_delivery_stays_practiced_and_the_next_practice_is_new(client, auth, db_session):
    _profile(db_session, "en")
    older, newer = _guided_units(db_session)
    first = _generate(client, auth)
    done = client.post(f"/api/v1/lessons/{first['lesson_id']}/complete", json={}, headers=auth)
    assert done.status_code == 200

    second = _generate(client, auth)

    assert second["lesson_id"] != first["lesson_id"]
    assert second["selection_trace"]["reason"] == "curated_lesson"
    assert second["selection_trace"]["delivered"]["content_unit_id"] == older.id
    assert second["title"] == "Unidade já entregue"
    db_session.expire_all()
    assert db_session.scalar(select(func.count()).select_from(Lesson)) == 2
    used = set(db_session.scalars(select(LessonContentUsage.content_unit_id)))
    assert used == {newer.id, older.id}


def test_another_mode_is_not_resumed_as_the_same_practice(client, auth, db_session):
    _profile(db_session, "fr")
    guided = _generate(client, auth, code="fr", mode="guided")
    grammar = _generate(client, auth, code="fr", mode="grammar")
    assert grammar["lesson_id"] != guided["lesson_id"]
    assert grammar["selection_trace"]["reason"] != "resumed_active_practice"
    again = _generate(client, auth, code="fr", mode="grammar")
    assert again["lesson_id"] == grammar["lesson_id"]
    assert again["selection_trace"]["reason"] == "resumed_active_practice"


def test_concurrent_generate_creates_one_practice(client, auth, db_session):
    profile = _profile(db_session, "en")
    _guided_units(db_session)

    def post_once():
        other = TestClient(app)
        other.cookies.update(client.cookies)
        response = other.post(
            "/api/v1/lessons/generate",
            json={"language_code": "en", "mode": "guided"},
            headers=auth,
        )
        body = response.json()
        return response.status_code, body.get("lesson_id")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [future.result(timeout=30) for future in (pool.submit(post_once) for _ in range(2))]

    assert [status for status, _ in results] == [200, 200]
    assert results[0][1] == results[1][1]
    db_session.expire_all()
    count = db_session.scalar(
        select(func.count()).select_from(Lesson).where(Lesson.user_language_id == profile.id)
    )
    assert count == 1


def test_generate_returns_409_when_lock_is_busy(client, auth, db_session, monkeypatch):
    _profile(db_session, "en")
    _guided_units(db_session)
    busy = threading.Lock()
    busy.acquire()

    monkeypatch.setattr("app.api.lessons._PRACTICE_LOCK_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr("app.api.lessons._thread_lock", lambda *_args, **_kwargs: busy)

    response = client.post(
        "/api/v1/lessons/generate",
        json={"language_code": "en", "mode": "guided"},
        headers=auth,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "practice_generation_in_progress"


def test_generate_releases_lock_when_generation_raises(client, auth, db_session, monkeypatch):
    _profile(db_session, "en")
    _guided_units(db_session)

    from app.api import lessons as lessons_api

    calls = {"count": 0}
    original = lessons_api._generate_unlocked

    def fail_once(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("boom")
        return original(*args, **kwargs)

    monkeypatch.setattr(lessons_api, "_generate_unlocked", fail_once)
    with pytest.raises(RuntimeError, match="boom"):
        client.post(
            "/api/v1/lessons/generate",
            json={"language_code": "en", "mode": "guided"},
            headers=auth,
        )

    second = client.post(
        "/api/v1/lessons/generate",
        json={"language_code": "en", "mode": "guided"},
        headers=auth,
    )
    assert second.status_code == 200
