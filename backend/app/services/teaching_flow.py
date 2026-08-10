"""Teaching Flow V2 — máquina de estados pedagógica.

Backend é a fonte da verdade. O frontend só solicita transições; transições
inválidas são rejeitadas. Ortogonal a `MasteryState` (domínio) e a
`CurriculumBlock.status` (conclusão administrativa).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.teaching import (
    MAX_REMEDIATION_CYCLES,
    FlowPhase,
    MasteryState,
    is_valid_flow_transition,
)
from app.models import LearningObjective, TeachingFlowSession, UserObjectiveProgress
from app.services import activity_generator

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_objective(db: Session, objective_id: str) -> LearningObjective:
    objective = db.get(LearningObjective, objective_id)
    if not objective or not objective.is_active:
        raise APIError(404, "objective_not_found", "Objetivo de aprendizagem não encontrado.")
    return objective


def start_flow(
    db: Session,
    *,
    user_language_id: str,
    objective_id: str,
    curriculum_block_id: str | None = None,
) -> TeachingFlowSession:
    """Inicia (ou reabre) uma sessão ativa para o objetivo."""
    objective = _get_objective(db, objective_id)
    existing = db.scalar(
        select(TeachingFlowSession).where(
            TeachingFlowSession.user_language_id == user_language_id,
            TeachingFlowSession.objective_id == objective_id,
            TeachingFlowSession.status == "active",
        )
    )
    if existing is not None:
        return existing

    activities = activity_generator.generate_activities(objective)
    session = TeachingFlowSession(
        user_language_id=user_language_id,
        objective_id=objective_id,
        curriculum_block_id=curriculum_block_id,
        phase=FlowPhase.ACTIVATING,
        activity_cursor=0,
        remediation_cycles=0,
        payload_json={
            "activities": activities,
            "history": [{"phase": FlowPhase.ACTIVATING, "at": _now().isoformat()}],
        },
        status="active",
    )
    db.add(session)
    db.flush()
    logger.info(
        "teaching_flow_started objective=%s phase=%s",
        objective.code,
        session.phase,
    )
    return session


def get_flow(db: Session, flow_id: str) -> TeachingFlowSession:
    session = db.get(TeachingFlowSession, flow_id)
    if session is None:
        raise APIError(404, "flow_not_found", "Sessão de ensino não encontrada.")
    return session


def transition(
    db: Session,
    session: TeachingFlowSession,
    *,
    target_phase: str,
    reason: str | None = None,
) -> TeachingFlowSession:
    """Aplica transição válida. Rejeita inventadas pelo cliente."""
    if target_phase not in set(FlowPhase):
        raise APIError(422, "invalid_flow_phase", "Fase de ensino inválida.")
    if session.status != "active":
        raise APIError(409, "flow_closed", "Esta sessão de ensino já foi encerrada.")
    if not is_valid_flow_transition(session.phase, target_phase):
        raise APIError(
            409,
            "invalid_flow_transition",
            f"Transição inválida: {session.phase} → {target_phase}.",
        )

    # MASTERED no flow só após domínio real em UserObjectiveProgress.
    # Impede POST /flows/{id}/transition com phase=mastered sem evidência.
    if target_phase == FlowPhase.MASTERED:
        progress = db.scalar(
            select(UserObjectiveProgress).where(
                UserObjectiveProgress.user_language_id == session.user_language_id,
                UserObjectiveProgress.objective_id == session.objective_id,
            )
        )
        if progress is None or progress.state != MasteryState.MASTERED:
            raise APIError(
                409,
                "mastery_not_demonstrated",
                "Não é possível marcar o fluxo como dominado sem evidência de mastery.",
            )

    if target_phase == FlowPhase.RETRYING:
        session.remediation_cycles += 1
        if session.remediation_cycles > MAX_REMEDIATION_CYCLES:
            target_phase = FlowPhase.NEEDS_REVIEW
            reason = reason or "Limite de ciclos de remediação atingido."

    previous = session.phase
    session.phase = target_phase
    payload = dict(session.payload_json or {})
    history = list(payload.get("history") or [])
    history.append(
        {
            "from": previous,
            "phase": target_phase,
            "reason": reason,
            "at": _now().isoformat(),
        }
    )
    payload["history"] = history
    session.payload_json = payload
    session.updated_at = _now()

    if target_phase in (FlowPhase.MASTERED, FlowPhase.NEEDS_REVIEW):
        session.status = "closed"
        session.closed_at = _now()

    db.flush()
    logger.info(
        "teaching_flow_transition from=%s to=%s flow=%s",
        previous,
        target_phase,
        session.id,
    )
    return session


def advance_activity_cursor(db: Session, session: TeachingFlowSession) -> TeachingFlowSession:
    activities = (session.payload_json or {}).get("activities") or []
    if session.activity_cursor < len(activities):
        session.activity_cursor += 1
        db.flush()
    return session


def current_activity(session: TeachingFlowSession) -> dict | None:
    """Atividade atual. Em remediação/retry, preferir variante pós-revelação.

    Se `retry_safe` for False, NÃO reapresenta o item revelado como se fosse novo —
    mantém a atividade original bloqueada e a UI deve oferecer Continuar.
    """
    payload = session.payload_json or {}
    if session.phase in {FlowPhase.NEEDS_REMEDIATION, FlowPhase.RETRYING}:
        retry_activity = payload.get("retry_activity")
        if (
            isinstance(retry_activity, dict)
            and retry_activity.get("type")
            and retry_activity.get("retry_safe", True) is not False
        ):
            return retry_activity
    activities = payload.get("activities") or []
    if 0 <= session.activity_cursor < len(activities):
        return activities[session.activity_cursor]
    return None


def phase_label_pt(phase: str) -> str:
    return {
        FlowPhase.NOT_STARTED: "Ainda não iniciado",
        FlowPhase.ACTIVATING: "Você está aprendendo",
        FlowPhase.INPUT: "Recebendo o modelo",
        FlowPhase.NOTICING: "Observe o padrão",
        FlowPhase.PRACTICING: "Você está praticando",
        FlowPhase.PRODUCING: "Sua produção",
        FlowPhase.EVALUATING: "Avaliando",
        FlowPhase.NEEDS_REMEDIATION: "Vamos corrigir isto",
        FlowPhase.RETRYING: "Tente novamente",
        FlowPhase.TRANSFER_CHECK: "Agora use em outra situação",
        FlowPhase.MASTERED: "Objetivo dominado",
        FlowPhase.NEEDS_REVIEW: "Revisaremos depois",
    }.get(phase, phase)
