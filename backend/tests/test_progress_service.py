from datetime import date, datetime, timedelta, timezone

from app.services.progress import compute_streak, format_minutes, session_minutes
from app.models import StudySession


def test_compute_streak_consecutive_including_today():
    today = date(2026, 7, 29)
    days = {today, today - timedelta(days=1), today - timedelta(days=2)}
    assert compute_streak(days, today=today) == 3


def test_compute_streak_allows_missing_today_if_yesterday():
    today = date(2026, 7, 29)
    days = {today - timedelta(days=1), today - timedelta(days=2)}
    assert compute_streak(days, today=today) == 2


def test_compute_streak_breaks_on_gap():
    today = date(2026, 7, 29)
    days = {today, today - timedelta(days=2)}
    assert compute_streak(days, today=today) == 1


def test_format_minutes():
    assert format_minutes(0) == "0min"
    assert format_minutes(45) == "45min"
    assert format_minutes(60) == "1h"
    assert format_minutes(125) == "2h 5min"


def test_session_minutes_uses_ended_at():
    start = datetime(2026, 7, 29, 10, 0, tzinfo=timezone.utc)
    end = datetime(2026, 7, 29, 10, 17, tzinfo=timezone.utc)
    session = StudySession(user_language_id="ul", started_at=start, ended_at=end, status="completed")
    assert session_minutes(session) == 17
