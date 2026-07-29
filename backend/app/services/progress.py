"""Agregações de progresso a partir de sessões e vocabulário reais."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import StudySession, UserLanguage, VocabularyItem


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def session_minutes(session: StudySession, *, now: datetime | None = None) -> int:
    """Minutos de uma sessão; sessões ativas contam até agora."""
    start = _as_utc(session.started_at)
    end = _as_utc(session.ended_at) if session.ended_at else _as_utc(now or datetime.now(timezone.utc))
    seconds = max(0, int((end - start).total_seconds()))
    return max(1, (seconds + 59) // 60) if seconds > 0 else 0


def compute_streak(session_dates: set[date], *, today: date | None = None) -> int:
    """Sequência de dias consecutivos com estudo, terminando hoje ou ontem."""
    if not session_dates:
        return 0
    today = today or datetime.now(timezone.utc).date()
    if today in session_dates:
        cursor = today
    elif today - timedelta(days=1) in session_dates:
        cursor = today - timedelta(days=1)
    else:
        return 0
    streak = 0
    while cursor in session_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def study_dates(sessions: list[StudySession]) -> set[date]:
    return {_as_utc(s.started_at).date() for s in sessions if s.started_at}


def minutes_on_day(sessions: list[StudySession], day: date, *, now: datetime | None = None) -> int:
    total = 0
    for session in sessions:
        if not session.started_at:
            continue
        if _as_utc(session.started_at).date() != day:
            continue
        total += session_minutes(session, now=now)
    return total


def format_minutes(total: int) -> str:
    hours, minutes = divmod(max(0, total), 60)
    if hours and minutes:
        return f"{hours}h {minutes}min"
    if hours:
        return f"{hours}h"
    return f"{minutes}min"


def load_user_language_ids(db: Session, user_id: str, user_language_id: str | None = None) -> list[str]:
    if user_language_id:
        return [user_language_id]
    return list(db.scalars(select(UserLanguage.id).where(UserLanguage.user_id == user_id)))


def aggregate_progress(
    db: Session,
    user_id: str,
    *,
    user_language_id: str | None = None,
) -> dict:
    """Retorna contadores reais para dashboard/progresso."""
    now = datetime.now(timezone.utc)
    today = now.date()
    ul_ids = load_user_language_ids(db, user_id, user_language_id)
    if not ul_ids:
        return {
            "vocabulary_items": 0,
            "study_sessions": 0,
            "streak_days": 0,
            "total_minutes": 0,
            "minutes_today": 0,
            "total_minutes_label": format_minutes(0),
            "recent_activity": [],
        }

    sessions = list(
        db.scalars(
            select(StudySession)
            .where(StudySession.user_language_id.in_(ul_ids))
            .order_by(StudySession.started_at.desc())
        )
    )
    vocab = (
        db.scalar(
            select(func.count(VocabularyItem.id)).where(VocabularyItem.user_language_id.in_(ul_ids))
        )
        or 0
    )
    total_minutes = sum(session_minutes(s, now=now) for s in sessions)
    minutes_today = minutes_on_day(sessions, today, now=now)
    streak = compute_streak(study_dates(sessions), today=today)

    recent = []
    for session in sessions[:10]:
        mins = session_minutes(session, now=now)
        recent.append(
            {
                "id": session.id,
                "status": session.status,
                "summary": session.summary_short,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "minutes": mins,
            }
        )

    return {
        "vocabulary_items": vocab,
        "study_sessions": len(sessions),
        "streak_days": streak,
        "total_minutes": total_minutes,
        "minutes_today": minutes_today,
        "total_minutes_label": format_minutes(total_minutes),
        "recent_activity": recent,
    }
