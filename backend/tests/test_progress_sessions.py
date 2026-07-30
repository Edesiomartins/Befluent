"""Progresso conta apenas sessões concluídas com ended_at."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.models import Language, StudySession, User, UserLanguage, UserPreference
from app.services.progress import aggregate_progress, compute_streak, minutes_on_local_day, study_dates_local


def _activate_language(db, user_id, code="en"):
    lang = db.scalar(select(Language).where(Language.code == code))
    ul = db.scalar(
        select(UserLanguage).where(UserLanguage.user_id == user_id, UserLanguage.language_id == lang.id)
    )
    if not ul:
        ul = UserLanguage(user_id=user_id, language_id=lang.id, onboarding_completed=True, is_active=True)
        db.add(ul)
        db.flush()
    return ul


def test_generate_active_does_not_count(client, auth, db_session):
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    ul = _activate_language(db_session, user.id)
    db_session.commit()

    before = aggregate_progress(db_session, user.id, user_language_id=ul.id)
    assert before["study_sessions"] == 0

    response = client.post(
        "/api/v1/lessons/generate",
        json={"language_code": "en", "mode": "guided", "persist": True},
        headers=auth,
    )
    assert response.status_code == 200
    body = response.json()
    assert body.get("lesson_id")
    assert body.get("study_session_id")

    after = aggregate_progress(db_session, user.id, user_language_id=ul.id)
    assert after["study_sessions"] == 0
    assert after["total_minutes"] == 0


def test_complete_counts(client, auth, db_session):
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    ul = _activate_language(db_session, user.id)
    db_session.commit()

    gen = client.post(
        "/api/v1/lessons/generate",
        json={"language_code": "en", "mode": "guided", "persist": True},
        headers=auth,
    ).json()
    lesson_id = gen["lesson_id"]

    session = db_session.get(StudySession, gen["study_session_id"])
    session.started_at = datetime.now(timezone.utc) - timedelta(seconds=20)
    db_session.commit()

    complete = client.post(f"/api/v1/lessons/{lesson_id}/complete", headers=auth)
    assert complete.status_code == 200
    progress = complete.json()["progress"]
    assert progress["study_sessions"] == 1
    assert progress["total_minutes"] >= 1


def test_abandon_does_not_count(client, auth, db_session):
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    ul = _activate_language(db_session, user.id)
    db_session.commit()

    gen = client.post(
        "/api/v1/lessons/generate",
        json={"language_code": "en", "mode": "vocabulary", "persist": True},
        headers=auth,
    ).json()

    abandon = client.post(f"/api/v1/lessons/{gen['lesson_id']}/abandon", headers=auth)
    assert abandon.status_code == 200
    progress = abandon.json()["progress"]
    assert progress["study_sessions"] == 0


def test_timezone_near_midnight_sao_paulo(db_session):
    """Sessão concluída após meia-noite UTC mas ainda 'ontem' em SP não conta como hoje."""
    user = db_session.scalar(select(User).limit(1))
    pref = db_session.scalar(select(UserPreference).where(UserPreference.user_id == user.id))
    pref.timezone = "America/Sao_Paulo"
    ul = _activate_language(db_session, user.id)

    # 02:30 UTC em 30/jul = 23:30 em 29/jul SP
    ended = datetime(2026, 7, 30, 2, 30, tzinfo=timezone.utc)
    started = ended - timedelta(minutes=20)
    session = StudySession(
        user_language_id=ul.id,
        started_at=started,
        ended_at=ended,
        status="completed",
    )
    db_session.add(session)
    db_session.commit()

    tz = ZoneInfo("America/Sao_Paulo")
    local_day = ended.astimezone(tz).date()
    assert local_day.isoformat() == "2026-07-29"

    minutes = minutes_on_local_day([session], date(2026, 7, 29), tz)
    assert minutes >= 1
    assert minutes_on_local_day([session], date(2026, 7, 30), tz) == 0

    streak_day = study_dates_local([session], tz)
    assert date(2026, 7, 29) in streak_day
    assert compute_streak(streak_day, today=date(2026, 7, 30)) == 1
