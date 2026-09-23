"""Teaching Flow V2 — máquina de estados pedagógica.

Backend é a fonte da verdade. O frontend só solicita transições; transições
inválidas são rejeitadas. Ortogonal a `MasteryState` (domínio) e a
`CurriculumBlock.status` (conclusão administrativa).
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import deque
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.teaching import (
    MAX_REMEDIATION_CYCLES,
    VALID_FLOW_TRANSITIONS,
    FlowPhase,
    MasteryState,
    MemorySubjectType,
    is_valid_flow_transition,
)
from app.models import (
    LearningObjective,
    MemorySchedule,
    TeachingFlowSession,
    UserObjectiveProgress,
    VocabularyExample,
    VocabularyItem,
)
from app.services import activity_generator

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_objective(db: Session, objective_id: str) -> LearningObjective:
    objective = db.get(LearningObjective, objective_id)
    if not objective or not objective.is_active:
        raise APIError(404, "objective_not_found", "Objetivo de aprendizagem não encontrado.")
    return objective


def _vocabulary_context_key(
    *,
    vocabulary_item_ids: list[str],
    lesson_id: str | None,
    curriculum_block_id: str | None,
) -> str:
    canonical = json.dumps(
        {
            "curriculum_block_id": curriculum_block_id,
            "lesson_id": lesson_id,
            "vocabulary_item_ids": sorted(set(vocabulary_item_ids)),
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _flow_for_update_statement(flow_id: str):
    return (
        select(TeachingFlowSession)
        .where(TeachingFlowSession.id == flow_id)
        .with_for_update()
    )


def lock_flow_for_answer(db: Session, flow_id: str) -> TeachingFlowSession:
    session = db.scalar(
        _flow_for_update_statement(flow_id).execution_options(populate_existing=True)
    )
    if session is None:
        raise APIError(404, "flow_not_found", "Sessão de ensino não encontrada.")
    return session


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


def start_vocabulary_flow(
    db: Session,
    *,
    user_language_id: str,
    vocabulary_item_ids: list[str],
    lesson_id: str | None = None,
    curriculum_block_id: str | None = None,
) -> TeachingFlowSession:
    """Inicia uma sessão lexical usando os itens persistidos como identidade."""
    unique_ids = list(dict.fromkeys(vocabulary_item_ids))
    context_key = _vocabulary_context_key(
        vocabulary_item_ids=unique_ids,
        lesson_id=lesson_id,
        curriculum_block_id=curriculum_block_id,
    )
    active_sessions = db.scalars(
        select(TeachingFlowSession).where(
            TeachingFlowSession.user_language_id == user_language_id,
            TeachingFlowSession.objective_id.is_(None),
            TeachingFlowSession.status == "active",
        )
    )
    for existing in active_sessions:
        if (existing.payload_json or {}).get("context_key") == context_key:
            return existing

    found = list(
        db.scalars(
            select(VocabularyItem).where(
                VocabularyItem.id.in_(unique_ids),
                VocabularyItem.user_language_id == user_language_id,
            )
        )
    )
    by_id = {item.id: item for item in found}
    if len(by_id) != len(unique_ids):
        raise APIError(
            404,
            "vocabulary_item_not_found",
            "Um ou mais itens de vocabulário não foram encontrados.",
        )
    items = [by_id[item_id] for item_id in unique_ids]
    examples_by_item: dict[str, list[VocabularyExample]] = {
        item_id: [] for item_id in unique_ids
    }
    if unique_ids:
        for example in db.scalars(
            select(VocabularyExample)
            .where(VocabularyExample.vocabulary_item_id.in_(unique_ids))
            .order_by(VocabularyExample.id.asc())
        ):
            examples_by_item[example.vocabulary_item_id].append(example)
    schedules = list(
        db.scalars(
            select(MemorySchedule).where(
                MemorySchedule.user_language_id == user_language_id,
                MemorySchedule.subject_type == MemorySubjectType.VOCABULARY,
                MemorySchedule.subject_key.in_(unique_ids),
            )
        )
    )
    activities = activity_generator.generate_vocabulary_activities(
        items,
        examples_by_item=examples_by_item,
        memory_by_item={schedule.subject_key: schedule for schedule in schedules},
    )
    if not activities:
        raise APIError(
            409,
            "no_vocabulary_due",
            "Não há itens de vocabulário disponíveis para esta sessão.",
        )
    session = TeachingFlowSession(
        user_language_id=user_language_id,
        objective_id=None,
        lesson_id=lesson_id,
        curriculum_block_id=curriculum_block_id,
        phase=FlowPhase.ACTIVATING,
        activity_cursor=0,
        remediation_cycles=0,
        payload_json={
            "activities": activities,
            "lexical_cycle": True,
            "vocabulary_item_ids": unique_ids,
            "context_key": context_key,
            "history": [{"phase": FlowPhase.ACTIVATING, "at": _now().isoformat()}],
        },
        status="active",
    )
    db.add(session)
    db.flush()
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


def _lexical_target_phase(activity: dict | None) -> str:
    if activity is None:
        return FlowPhase.NEEDS_REVIEW
    return {
        "input": FlowPhase.INPUT,
        "practicing": FlowPhase.PRACTICING,
        "producing": FlowPhase.PRODUCING,
    }.get(activity.get("phase_hint"), FlowPhase.PRACTICING)


def _align_lexical_phase(
    db: Session, session: TeachingFlowSession, target_phase: str
) -> None:
    if session.phase == target_phase:
        return
    allowed = {
        FlowPhase.ACTIVATING,
        FlowPhase.INPUT,
        FlowPhase.NOTICING,
        FlowPhase.PRACTICING,
        FlowPhase.PRODUCING,
        FlowPhase.EVALUATING,
        FlowPhase.NEEDS_REVIEW,
    }
    queue = deque([(session.phase, [])])
    visited = {session.phase}
    path: list[str] | None = None
    while queue:
        phase, current_path = queue.popleft()
        for candidate in VALID_FLOW_TRANSITIONS.get(phase, frozenset()):
            if candidate not in allowed or candidate in visited:
                continue
            next_path = [*current_path, candidate]
            if candidate == target_phase:
                path = next_path
                queue.clear()
                break
            visited.add(candidate)
            queue.append((candidate, next_path))
    if path is None:
        raise APIError(
            409,
            "invalid_lexical_flow_transition",
            f"Não foi possível alinhar o fluxo lexical: {session.phase} → {target_phase}.",
        )
    for phase in path:
        transition(db, session, target_phase=phase, reason="lexical_advance")


def advance_lexical_activity(
    db: Session, session: TeachingFlowSession
) -> TeachingFlowSession:
    advance_activity_cursor(db, session)
    _align_lexical_phase(db, session, _lexical_target_phase(current_activity(session)))
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


def public_activity(session: TeachingFlowSession) -> dict | None:
    """Retorna a atividade atual sem material privado de avaliação lexical."""
    activity = current_activity(session)
    if not isinstance(activity, dict):
        return activity
    public = dict(activity)
    if public.get("vocabulary_item_id") and public.get("type") in {
        "recognition",
        "reverse_recognition",
        "listening_recognition",
        "lexical_production",
    }:
        for private_key in {
            "accepted_variants",
            "answer",
            "canonical_answer",
            "correct_explanation",
            "correct_option",
            "correct_option_id",
            "expected_answer",
            "option_rationales",
            "rationale",
            "required_features",
            "required_patterns",
        }:
            public.pop(private_key, None)
    return public


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
