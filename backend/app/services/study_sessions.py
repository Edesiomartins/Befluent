"""Validação e ciclo de vida de sessões de estudo."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import APIError
from app.models import StudySession, User, UserLanguage


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def session_duration_seconds(session: StudySession, *, ended_at: datetime | None = None) -> int:
    """Duração bruta em segundos entre início e fim (ou agora se ainda ativa)."""
    if not session.started_at:
        return 0
    start = _as_utc(session.started_at)
    end = _as_utc(ended_at or session.ended_at or _now())
    return max(0, int((end - start).total_seconds()))


def clamped_session_seconds(session: StudySession, *, ended_at: datetime | None = None) -> int:
    """Duração aplicando limites mínimo/máximo das configurações."""
    settings = get_settings()
    raw = session_duration_seconds(session, ended_at=ended_at)
    if raw <= 0:
        return 0
    capped = min(raw, settings.max_completed_session_hours * 3600)
    if capped < settings.min_completed_session_seconds:
        return 0
    return capped


def session_minutes_for_progress(session: StudySession) -> int:
    """Minutos que contam para progresso — só sessões concluídas com fim registrado."""
    if session.status != "completed" or session.ended_at is None:
        return 0
    seconds = clamped_session_seconds(session)
    if seconds <= 0:
        return 0
    return max(1, (seconds + 59) // 60)


def validate_study_session_for_user(
    db: Session,
    user: User,
    session_id: str,
    user_language_id: str,
    *,
    require_active: bool = True,
) -> StudySession:
    """Garante que a sessão pertence ao usuário/idioma e está utilizável."""
    session = db.get(StudySession, session_id)
    if not session:
        raise APIError(404, "session_not_found", "Sessão de estudo não encontrada.")

    profile = db.get(UserLanguage, session.user_language_id)
    if not profile or profile.user_id != user.id:
        raise APIError(404, "session_not_found", "Sessão de estudo não encontrada.")
    if session.user_language_id != user_language_id:
        raise APIError(
            409,
            "session_language_mismatch",
            "A sessão não pertence ao idioma ativo.",
        )
    if require_active and session.status != "active":
        raise APIError(
            409,
            "session_not_active",
            "Esta sessão já foi encerrada.",
        )
    return session


def complete_session(
    db: Session,
    session: StudySession,
    *,
    summary: str | None = None,
) -> StudySession:
    """Marca sessão como concluída (idempotente se já concluída)."""
    if session.status == "completed" and session.ended_at is not None:
        return session
    if session.status == "abandoned":
        raise APIError(
            409,
            "session_already_abandoned",
            "Esta sessão foi abandonada e não pode ser concluída.",
        )
    session.status = "completed"
    session.ended_at = _now()
    if summary:
        session.summary_short = summary
    elif not session.summary_short:
        session.summary_short = "Sessão concluída."
    db.flush()
    return session


def abandon_session(
    db: Session,
    session: StudySession,
    *,
    summary: str | None = None,
) -> StudySession:
    """Marca sessão como abandonada (idempotente se já abandonada)."""
    if session.status == "abandoned":
        return session
    if session.status == "completed":
        raise APIError(
            409,
            "session_already_completed",
            "Esta sessão já foi concluída.",
        )
    session.status = "abandoned"
    session.ended_at = _now()
    if summary:
        session.summary_short = summary
    elif not session.summary_short:
        session.summary_short = "Sessão abandonada."
    db.flush()
    return session


def abandon_stale_sessions(db: Session, timeout_hours: int | None = None) -> int:
    """Abandona sessões ativas sem atividade além do limite configurado."""
    hours = timeout_hours if timeout_hours is not None else get_settings().active_session_timeout_hours
    cutoff = _now() - timedelta(hours=hours)
    stale = list(
        db.scalars(
            select(StudySession).where(
                StudySession.status == "active",
                StudySession.started_at < cutoff,
            )
        )
    )
    for session in stale:
        abandon_session(db, session, summary="Encerrada automaticamente por inatividade.")
    if stale:
        db.flush()
    return len(stale)
