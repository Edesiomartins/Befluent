"""Agregações de progresso a partir de sessões concluídas e vocabulário."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.levels import LEVEL_INDEX, LEVEL_ORDER, normalize_level
from app.core.teaching import AttemptResult, MasteryState
from app.models import (
    LearningAttempt,
    LearningError,
    LearningEvidence,
    LearningObjective,
    StudySession,
    UserLanguage,
    UserObjectiveProgress,
    UserPreference,
    VocabularyItem,
)

DEFAULT_TIMEZONE = "America/Sao_Paulo"

MASTERY_PERCENT = {
    MasteryState.NOT_STARTED: 0,
    MasteryState.LEARNING: 25,
    MasteryState.PRACTICING: 50,
    MasteryState.NEEDS_REMEDIATION: 35,
    MasteryState.NEEDS_REVIEW: 35,
    MasteryState.RETRYING: 45,
    MasteryState.MASTERED: 100,
}


def mastery_percent_for_state(state: str, *, has_open_error: bool) -> int:
    """Converte somente o estágio do Teaching Engine em contribuição visível."""
    percent = MASTERY_PERCENT.get(state, 0)
    return min(percent, 35) if has_open_error else percent


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


def daily_activity(
    sessions: list[StudySession],
    *,
    period_end: date,
    tz: ZoneInfo,
    days: int = 7,
) -> dict:
    """Série diária completa, calculada do histórico integral de sessões."""
    period_start = period_end - timedelta(days=days - 1)
    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "timezone": tz.key,
        "days": [
            {
                "date": (period_start + timedelta(days=offset)).isoformat(),
                "minutes": minutes_on_local_day(
                    sessions,
                    period_start + timedelta(days=offset),
                    tz,
                ),
            }
            for offset in range(days)
        ],
        "total_minutes": sum(
            minutes_on_local_day(sessions, period_start + timedelta(days=offset), tz)
            for offset in range(days)
        ),
    }


def load_user_language_ids(db: Session, user_id: str, user_language_id: str | None = None) -> list[str]:
    if user_language_id:
        return [user_language_id]
    return list(db.scalars(select(UserLanguage.id).where(UserLanguage.user_id == user_id)))


def _event_percent(result: str) -> int | None:
    return {
        AttemptResult.CORRECT: 100,
        AttemptResult.PARTIAL: 50,
        AttemptResult.INCORRECT: 35,
    }.get(result)


def _timeline(
    attempts: list[LearningAttempt],
    evidences: list[LearningEvidence],
    errors: list[LearningError],
    *,
    period_end: date,
    days: int,
    tz: ZoneInfo,
) -> list[dict]:
    """Reconstrói apenas os seis últimos dias a partir de eventos datados.

    UserObjectiveProgress não tem histórico de transições. Por isso seu estado
    atual é deliberadamente excluído daqui: usá-lo no passado fabricaria uma
    trajetória que o banco não registrou.
    """
    period_start = period_end - timedelta(days=days - 1)
    events: list[tuple[datetime, str, str, int | None]] = []
    for attempt in attempts:
        event_at = attempt.evaluated_at or attempt.created_at
        percent = _event_percent(attempt.result)
        if percent is not None:
            events.append((_as_utc(event_at), attempt.objective_id, "attempt", percent))
    for evidence in evidences:
        events.append((_as_utc(evidence.created_at), evidence.objective_id, "evidence", 100))
    for error in errors:
        if error.objective_id is None:
            continue
        events.append((_as_utc(error.first_seen), error.objective_id, "error_open", 35))
        if error.resolved:
            events.append((_as_utc(error.last_seen), error.objective_id, "error_resolved", None))
    events.sort(key=lambda item: item[0])

    per_objective: dict[str, int] = {}
    open_errors: set[str] = set()
    cursor = 0
    history: list[dict] = []
    for offset in range(days):
        day = period_start + timedelta(days=offset)
        day_end = datetime.combine(day + timedelta(days=1), datetime.min.time(), tzinfo=tz).astimezone(timezone.utc)
        while cursor < len(events) and events[cursor][0] < day_end:
            _, objective_id, kind, percent = events[cursor]
            if kind == "error_open":
                open_errors.add(objective_id)
                per_objective[objective_id] = 35
            elif kind == "error_resolved":
                open_errors.discard(objective_id)
            elif percent is not None:
                per_objective[objective_id] = min(percent, 35) if objective_id in open_errors else percent
            cursor += 1
        percent = round(sum(per_objective.values()) / len(per_objective)) if per_objective else None
        history.append({"date": day.isoformat(), "percent": percent})
    return history[-6:]


def aggregate_mastery_progress(
    db: Session,
    user_language_id: str,
    *,
    days: int,
    tz: ZoneInfo,
    as_of: datetime | None = None,
) -> dict:
    """Agrega domínio demonstrado, sem usar métricas administrativas legadas."""
    now_local = _as_utc(as_of or datetime.now(timezone.utc)).astimezone(tz).date()
    rows = list(
        db.execute(
            select(UserObjectiveProgress, LearningObjective)
            .join(LearningObjective, LearningObjective.id == UserObjectiveProgress.objective_id)
            .where(
                UserObjectiveProgress.user_language_id == user_language_id,
                LearningObjective.is_active.is_(True),
            )
        )
    )
    attempts = list(
        db.scalars(
            select(LearningAttempt)
            .join(LearningObjective, LearningObjective.id == LearningAttempt.objective_id)
            .where(
                LearningAttempt.user_language_id == user_language_id,
                LearningObjective.is_active.is_(True),
            )
        )
    )
    evidences = list(
        db.scalars(
            select(LearningEvidence)
            .join(LearningObjective, LearningObjective.id == LearningEvidence.objective_id)
            .where(
                LearningEvidence.user_language_id == user_language_id,
                LearningObjective.is_active.is_(True),
            )
        )
    )
    errors = list(
        db.scalars(
            select(LearningError)
            .join(LearningObjective, LearningObjective.id == LearningError.objective_id)
            .where(
                LearningError.user_language_id == user_language_id,
                LearningObjective.is_active.is_(True),
            )
        )
    )
    evidence_objectives = {evidence.objective_id for evidence in evidences}
    open_error_objectives = {
        error.objective_id for error in errors if not error.resolved and error.objective_id is not None
    }

    # Um estágio sem evidência não é um percentual de domínio. Isso também
    # impede que a mera conclusão de bloco/sessão apareça como aprendizagem.
    demonstrated = [
        (progress, objective)
        for progress, objective in rows
        if objective.id in evidence_objectives
    ]
    timeline = _timeline(
        attempts,
        evidences,
        errors,
        period_end=now_local,
        days=days,
        tz=tz,
    )
    if not demonstrated:
        return {
            "status": "calibrating",
            "overall_percent": None,
            "by_skill": [],
            "timeline": timeline,
            "cefr": None,
            "priorities": [],
        }

    contributions = [
        (
            objective.skill_focus,
            objective.level,
            mastery_percent_for_state(
                progress.state,
                has_open_error=objective.id in open_error_objectives,
            ),
        )
        for progress, objective in demonstrated
    ]
    overall_percent = round(sum(percent for _, _, percent in contributions) / len(contributions))
    by_skill: dict[str, list[int]] = {}
    for skill, _, percent in contributions:
        by_skill.setdefault(skill, []).append(percent)
    profile = db.get(UserLanguage, user_language_id)
    current = normalize_level(profile.current_level if profile else None)
    cefr = None
    if current is not None:
        next_index = min(LEVEL_INDEX[current] + 1, len(LEVEL_ORDER) - 1)
        cefr = {
            "current": current,
            "next": LEVEL_ORDER[next_index],
            "readiness_percent": overall_percent,
        }
    priorities = list((profile.recommendations_json if profile else None) or [])[:3]
    return {
        "status": "ready",
        "overall_percent": overall_percent,
        "by_skill": [
            {"skill": skill, "percent": round(sum(values) / len(values))}
            for skill, values in sorted(by_skill.items())
        ],
        "timeline": timeline,
        "cefr": cefr,
        "priorities": priorities,
    }


def aggregate_progress(
    db: Session,
    user_id: str,
    *,
    user_language_id: str | None = None,
    activity_days: int = 7,
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
            "daily_activity": daily_activity([], period_end=today_local, tz=tz, days=activity_days),
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
        "daily_activity": daily_activity(completed, period_end=today_local, tz=tz, days=activity_days),
    }
