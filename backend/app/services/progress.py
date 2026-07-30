"""Agregações de progresso a partir de sessões concluídas e vocabulário."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import StudySession, UserLanguage, UserPreference, VocabularyItem

DEFAULT_TIMEZONE = "America/Sao_Paulo"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def resolve_timezone(db: Session, user_id: str, *, strict: bool = False) -> ZoneInfo:
    """Resolve fuso do usuário; inválido cai em America/Sao_Paulo ou erro em strict."""
    pref = db.scalar(select(UserPreference).where(UserPreference.user_id == user_id))
    tz_name = (pref.timezone if pref and pref.timezone else DEFAULT_TIMEZONE).strip()
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        if strict:
            from app.core.errors import APIError

            raise APIError(422, "invalid_timezone", "Fuso horário inválido.")
        return ZoneInfo(DEFAULT_TIMEZONE)


def format_minutes(total: int) -> str:
    hours, minutes = divmod(max(0, total), 60)
    if hours and minutes:
        return f"{hours}h {minutes}min"
    if hours:
        return f"{hours}h"
    return f"{minutes}min"


def compute_streak(session_dates: set[date], *, today: date | None = None) -> int:
    """Sequência de dias consecutivos com estudo, terminando hoje ou ontem."""
    if not session_dates:
        return 0
    if today is None:
        today = datetime.now(timezone.utc).date()
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


def _completed_sessions(sessions: list[StudySession]) -> list[StudySession]:
    return [
        s
        for s in sessions
        if s.status == "completed" and s.ended_at is not None and s.started_at is not None
    ]


def study_dates_local(sessions: list[StudySession], tz: ZoneInfo) -> set[date]:
    """Datas locais em que houve sessão concluída (usa ended_at)."""
    dates: set[date] = set()
    for session in _completed_sessions(sessions):
        ended = _as_utc(session.ended_at)  # type: ignore[arg-type]
        dates.add(ended.astimezone(tz).date())
    return dates


def minutes_on_local_day(
    sessions: list[StudySession],
    day: date,
    tz: ZoneInfo,
) -> int:
    from app.services.study_sessions import session_minutes_for_progress

    total = 0
    for session in _completed_sessions(sessions):
        ended = _as_utc(session.ended_at)  # type: ignore[arg-type]
        if ended.astimezone(tz).date() != day:
            continue
        total += session_minutes_for_progress(session)
    return total


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
    tz = resolve_timezone(db, user_id)
    now_utc = datetime.now(timezone.utc)
    today_local = now_utc.astimezone(tz).date()

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

    all_sessions = list(
        db.scalars(
            select(StudySession)
            .where(StudySession.user_language_id.in_(ul_ids))
            .order_by(StudySession.started_at.desc())
        )
    )
    completed = _completed_sessions(all_sessions)

    from app.services.study_sessions import session_minutes_for_progress

    vocab = (
        db.scalar(
            select(func.count(VocabularyItem.id)).where(VocabularyItem.user_language_id.in_(ul_ids))
        )
        or 0
    )
    total_minutes = sum(session_minutes_for_progress(s) for s in completed)
    minutes_today = minutes_on_local_day(completed, today_local, tz)
    streak = compute_streak(study_dates_local(completed, tz), today=today_local)

    recent = []
    for session in completed[:10]:
        mins = session_minutes_for_progress(session)
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
        "study_sessions": len(completed),
        "streak_days": streak,
        "total_minutes": total_minutes,
        "minutes_today": minutes_today,
        "total_minutes_label": format_minutes(total_minutes),
        "recent_activity": recent,
    }
