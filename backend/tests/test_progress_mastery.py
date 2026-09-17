"""Contrato de domínio demonstrado para a aba Progresso."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.teaching import MasteryState
from app.models import (
    Language,
    LearningAttempt,
    LearningError,
    LearningEvidence,
    LearningObjective,
    User,
    UserLanguage,
    UserObjectiveProgress,
)
from app.services.progress import aggregate_mastery_progress, mastery_percent_for_state


def _user_language(db_session) -> UserLanguage:
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    profile = UserLanguage(user_id=user.id, language_id=language.id, is_active=True)
    db_session.add(profile)
    db_session.commit()
    return profile


def _objective(db_session, *, skill: str = "reading", level: str = "A2") -> LearningObjective:
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    objective = LearningObjective(
        language_id=language.id,
        level=level,
        code=f"EN-{level}-PROGRESS-{uuid.uuid4().hex[:8]}",
        title="Objetivo de progresso",
        can_do="Demonstra a habilidade em contexto.",
        skill_focus=skill,
    )
    db_session.add(objective)
    db_session.commit()
    return objective


def test_mastery_e_erro_aberto_tem_contribuicao_honesta():
    """Pegaria uma regressão que ignorasse erro aberto ou inflasse remediação."""
    assert mastery_percent_for_state(MasteryState.MASTERED, has_open_error=False) == 100
    assert mastery_percent_for_state(MasteryState.NEEDS_REMEDIATION, has_open_error=True) == 35
    assert mastery_percent_for_state(MasteryState.MASTERED, has_open_error=True) == 35


def test_atividade_legada_sem_objetivo_nao_gera_dominio(db_session):
    """Pegaria uma implementação que derive domínio de sessões ou conclusão legada."""
    profile = _user_language(db_session)

    result = aggregate_mastery_progress(
        db_session, profile.id, days=7, tz=ZoneInfo("America/Sao_Paulo")
    )

    assert result["status"] == "calibrating"
    assert result["overall_percent"] is None
    assert result["timeline"][-1]["percent"] is None
    assert result["cefr"] is None


def test_mastery_usa_estado_por_habilidade_e_timeline_somente_por_eventos_datados(db_session):
    """Pegaria projeção retroativa do estado atual para dias anteriores."""
    profile = _user_language(db_session)
    profile.current_level = "B1"
    objective = _objective(db_session, skill="reading", level="A2")
    now = datetime.now(timezone.utc).replace(hour=15, minute=0, second=0, microsecond=0)
    attempt = LearningAttempt(
        user_language_id=profile.id,
        objective_id=objective.id,
        activity_type="practice",
        result="correct",
        created_at=now - timedelta(days=1),
        evaluated_at=now - timedelta(days=1),
    )
    db_session.add(attempt)
    db_session.flush()
    db_session.add(
        LearningEvidence(
            user_language_id=profile.id,
            objective_id=objective.id,
            attempt_id=attempt.id,
            evidence_type="correct_response",
            created_at=now - timedelta(days=1),
        )
    )
    db_session.add(
        UserObjectiveProgress(
            user_language_id=profile.id,
            objective_id=objective.id,
            state=MasteryState.MASTERED,
            started_at=now - timedelta(days=1),
            mastered_at=now,
        )
    )
    db_session.add(
        LearningError(
            user_language_id=profile.id,
            objective_id=objective.id,
            attempt_id=attempt.id,
            category="grammar",
            original="wrong",
            resolved=False,
            first_seen=now,
            last_seen=now,
        )
    )
    db_session.commit()

    result = aggregate_mastery_progress(
        db_session, profile.id, days=7, tz=ZoneInfo("America/Sao_Paulo")
    )

    assert result["status"] == "ready"
    assert result["overall_percent"] == 35
    assert result["by_skill"] == [{"skill": "reading", "percent": 35}]
    assert result["timeline"][-2]["percent"] == 100
    assert result["timeline"][-1]["percent"] == 35
    assert result["cefr"] == {"current": "B1", "next": "B2", "readiness_percent": 35}


def test_mastery_sem_nivel_atual_nao_infere_cefr_do_objetivo(db_session):
    """Pegaria a inferência indevida de CEFR pelo nível do objetivo."""
    profile = _user_language(db_session)
    objective = _objective(db_session, level="C1")
    attempt = LearningAttempt(
        user_language_id=profile.id,
        objective_id=objective.id,
        activity_type="practice",
        result="correct",
    )
    db_session.add(attempt)
    db_session.flush()
    db_session.add(
        LearningEvidence(
            user_language_id=profile.id,
            objective_id=objective.id,
            attempt_id=attempt.id,
            evidence_type="correct_response",
        )
    )
    db_session.add(
        UserObjectiveProgress(
            user_language_id=profile.id,
            objective_id=objective.id,
            state=MasteryState.MASTERED,
        )
    )
    db_session.commit()

    result = aggregate_mastery_progress(
        db_session, profile.id, days=7, tz=ZoneInfo("America/Sao_Paulo")
    )

    assert result["cefr"] is None


def test_mastery_ignora_objetivo_inativo_mesmo_com_evidencia(db_session):
    """Pegaria domínio inflado por objetivos removidos do catálogo ativo."""
    profile = _user_language(db_session)
    objective = _objective(db_session)
    objective.is_active = False
    attempt = LearningAttempt(
        user_language_id=profile.id,
        objective_id=objective.id,
        activity_type="practice",
        result="correct",
    )
    db_session.add(attempt)
    db_session.flush()
    db_session.add(
        LearningEvidence(
            user_language_id=profile.id,
            objective_id=objective.id,
            attempt_id=attempt.id,
            evidence_type="correct_response",
        )
    )
    db_session.add(
        UserObjectiveProgress(
            user_language_id=profile.id,
            objective_id=objective.id,
            state=MasteryState.MASTERED,
        )
    )
    db_session.commit()

    result = aggregate_mastery_progress(
        db_session, profile.id, days=7, tz=ZoneInfo("America/Sao_Paulo")
    )

    assert result["status"] == "calibrating"
    assert result["overall_percent"] is None
    assert result["by_skill"] == []
    assert all(point["percent"] is None for point in result["timeline"])
