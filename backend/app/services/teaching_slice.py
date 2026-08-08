"""Orquestrador do vertical slice Teaching Engine V2.

Liga flow → atividade atual → tentativa → avaliação determinística →
erro/remediação/retry → transfer → mastery → memória.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.teaching import (
    AttemptResult,
    ErrorCategory,
    ErrorSeverity,
    EvidenceType,
    FlowPhase,
    RemediationAction,
)
from app.models import LearningObjective, TeachingFlowSession
from app.services import (
    activity_generator,
    deterministic_evaluator,
    teaching_engine,
    teaching_flow,
)
from app.services.objective_seed import ensure_en_a1_can_001

logger = logging.getLogger(__name__)

#: Fases da atividade → fase do flow (quando a resposta é correta).
_SUCCESS_PHASE: dict[str, str] = {
    "activating": FlowPhase.INPUT,
    "input": FlowPhase.NOTICING,
    "noticing": FlowPhase.PRACTICING,
    "practicing": FlowPhase.PRACTICING,
    "producing": FlowPhase.EVALUATING,
    "transfer_check": FlowPhase.TRANSFER_CHECK,
}


def ensure_slice_objective(db: Session) -> LearningObjective:
    return ensure_en_a1_can_001(db)


def start_slice(
    db: Session,
    *,
    user_language_id: str,
    curriculum_block_id: str | None = None,
) -> dict[str, Any]:
    objective = ensure_slice_objective(db)
    progress = teaching_engine.start_objective(
        db, user_language_id=user_language_id, objective_id=objective.id
    )
    session = teaching_flow.start_flow(
        db,
        user_language_id=user_language_id,
        objective_id=objective.id,
        curriculum_block_id=curriculum_block_id,
    )
    return _restore_payload(db, session, objective, progress.state)


def get_active_slice(
    db: Session,
    *,
    user_language_id: str,
) -> dict[str, Any] | None:
    """Restaura flow ativo (ou o mais recente fechado) sem criar sessão nova.

    Backend é a fonte da verdade — o frontend consulta isto no refresh.
    """
    from sqlalchemy import select

    from app.models import TeachingFlowSession, UserObjectiveProgress

    objective = ensure_slice_objective(db)
    active = db.scalar(
        select(TeachingFlowSession).where(
            TeachingFlowSession.user_language_id == user_language_id,
            TeachingFlowSession.objective_id == objective.id,
            TeachingFlowSession.status == "active",
        )
    )
    session = active
    if session is None:
        session = db.scalar(
            select(TeachingFlowSession)
            .where(
                TeachingFlowSession.user_language_id == user_language_id,
                TeachingFlowSession.objective_id == objective.id,
            )
            .order_by(TeachingFlowSession.updated_at.desc())
            .limit(1)
        )
    if session is None:
        return None
    progress = db.scalar(
        select(UserObjectiveProgress).where(
            UserObjectiveProgress.user_language_id == user_language_id,
            UserObjectiveProgress.objective_id == objective.id,
        )
    )
    progress_state = progress.state if progress else "not_started"
    return _restore_payload(db, session, objective, progress_state)


def _restore_payload(
    db: Session,
    session: TeachingFlowSession,
    objective: LearningObjective,
    progress_state: str,
) -> dict[str, Any]:
    base = _session_payload(db, session, objective, progress_state)
    pending = (session.payload_json or {}).get("pending_remediation")
    if pending and session.phase in {
        FlowPhase.NEEDS_REMEDIATION,
        FlowPhase.RETRYING,
    }:
        base["remediation"] = pending
    else:
        base["remediation"] = None
    if progress_state == "mastered" or session.phase == FlowPhase.MASTERED:
        base["mastery"] = {
            "state": "mastered",
            "reasons": ["Restaurado do servidor — domínio já registrado."],
        }
    return base


def submit_slice_answer(
    db: Session,
    session: TeachingFlowSession,
    *,
    student_response: str,
    activity_index: int | None = None,
) -> dict[str, Any]:
    objective = db.get(LearningObjective, session.objective_id)
    if objective is None:
        raise APIError(404, "objective_not_found", "Objetivo de aprendizagem não encontrado.")

    if session.phase == FlowPhase.NEEDS_REMEDIATION:
        raise APIError(
            409,
            "use_retry_endpoint",
            "Há remediação pendente — use o retry, não uma nova resposta nesta atividade.",
        )
    if session.status != "active":
        raise APIError(409, "flow_closed", "Esta sessão de ensino já foi encerrada.")

    activities = (session.payload_json or {}).get("activities") or []
    index = session.activity_cursor if activity_index is None else activity_index
    if index < 0 or index >= len(activities):
        raise APIError(409, "no_current_activity", "Não há atividade atual nesta sessão.")

    payload = dict(session.payload_json or {})
    completed = set(payload.get("completed_indices") or [])
    if index in completed:
        raise APIError(
            409,
            "activity_already_completed",
            "Esta atividade já foi concluída nesta sessão.",
        )
    activity = activities[index]

    if activity_generator.activity_requires_ai(activity):
        raise APIError(
            501,
            "ai_activity_not_in_slice",
            "Esta atividade exigiria IA; o vertical slice usa só regras determinísticas.",
        )

    # Atividades de input/ativação/noticing/matching: "continuar" sem produção.
    if activity.get("type") in {"listen", "recognition", "matching"} and not student_response.strip():
        student_response = "__ack__"

    evaluation = None
    result = AttemptResult.CORRECT
    evidence_type = EvidenceType.COMPREHENSION
    is_transfer = activity.get("type") == "transfer_question"

    if student_response != "__ack__":
        evaluation = deterministic_evaluator.evaluate_response(
            student_response=student_response, activity=activity
        )
        result = evaluation["result"]
        if activity.get("type") == "guided_production":
            evidence_type = EvidenceType.WRITTEN_PRODUCTION
        elif is_transfer:
            evidence_type = EvidenceType.TRANSFER
        elif activity.get("type") in {"fill_gap", "word_order", "multiple_choice"}:
            evidence_type = EvidenceType.CORRECT_RESPONSE
        else:
            evidence_type = EvidenceType.SUCCESSFUL_RECALL

    attempt = teaching_engine.record_attempt(
        db,
        user_language_id=session.user_language_id,
        objective_id=session.objective_id,
        activity_type=activity.get("type") or "practice",
        student_response=None if student_response == "__ack__" else student_response,
        curriculum_block_id=session.curriculum_block_id,
    )

    eval_out = teaching_engine.evaluate_attempt(
        db,
        attempt,
        result=result,
        score=1.0 if result == AttemptResult.CORRECT else 0.0,
        provider="deterministic",
        evidence_type=evidence_type if result != AttemptResult.INCORRECT else None,
        is_transfer=is_transfer and result == AttemptResult.CORRECT,
    )

    remediation_payload = None
    if result != AttemptResult.INCORRECT:
        # Marca índice concluído só em sucesso/ack — evita double-submit
        # gerar evidência duplicada no mesmo passo.
        completed.add(index)
        payload["completed_indices"] = sorted(completed)
        session.payload_json = payload
        db.flush()

    if result == AttemptResult.INCORRECT:
        error = teaching_engine.record_error(
            db,
            attempt,
            category=ErrorCategory.GRAMMAR
            if activity.get("type") in {"fill_gap", "word_order", "guided_production"}
            else ErrorCategory.COMPREHENSION,
            original=student_response,
            expected=activity.get("canonical_answer")
            or (activity.get("accepted_variants") or [None])[0],
            explanation=_contrast_explanation(activity),
            severity=ErrorSeverity.CRITICAL
            if activity.get("type") in {"guided_production", "transfer_question"}
            else ErrorSeverity.MODERATE,
            language_feature=_feature_key(activity),
        )
        remediation = teaching_engine.choose_remediation(
            db,
            error,
            escalate=True,
            reason="Vertical slice — remediação escalonada sem IA.",
        )
        teaching_flow.transition(
            db, session, target_phase=FlowPhase.NEEDS_REMEDIATION, reason="incorrect_attempt"
        )
        remediation_payload = {
            "id": remediation.id,
            "action": remediation.action,
            "error_id": error.id,
            "explanation": error.explanation,
            "contrast": {
                "incorrect": error.original,
                "correct": error.expected,
            },
            "hint_pt": _hint_for(remediation.action, activity),
        }
        payload = dict(session.payload_json or {})
        payload["pending_remediation"] = remediation_payload
        session.payload_json = payload
        db.flush()
    else:
        _advance_after_success(db, session, activity)

    mastery = eval_out["mastery"]
    if mastery["state"] == "mastered" and session.status == "active":
        _close_as_mastered(db, session)

    progress_state = mastery["state"]
    return {
        **_session_payload(db, session, objective, progress_state),
        "attempt": {
            "id": attempt.id,
            "result": attempt.result,
            "attempt_number": attempt.attempt_number,
        },
        "evaluation": evaluation,
        "remediation": remediation_payload,
        "mastery": mastery,
        "ai_called": False,
    }


def retry_slice(
    db: Session,
    session: TeachingFlowSession,
    *,
    remediation_id: str,
    student_response: str,
) -> dict[str, Any]:
    from app.models import Remediation

    remediation = db.get(Remediation, remediation_id)
    if remediation is None:
        raise APIError(404, "remediation_not_found", "Remediação não encontrada.")

    if session.phase == FlowPhase.NEEDS_REMEDIATION:
        teaching_flow.transition(db, session, target_phase=FlowPhase.RETRYING, reason="retry")
    elif session.phase != FlowPhase.RETRYING:
        raise APIError(
            409,
            "retry_not_available",
            "Retry só é permitido em remediação ou retry pendente.",
        )

    attempt = teaching_engine.record_retry(
        db,
        remediation,
        student_response=student_response,
        curriculum_block_id=session.curriculum_block_id,
    )
    activity = teaching_flow.current_activity(session) or {}
    evaluation = deterministic_evaluator.evaluate_response(
        student_response=student_response, activity=activity
    )
    eval_out = teaching_engine.evaluate_attempt(
        db,
        attempt,
        result=evaluation["result"],
        score=1.0 if evaluation["result"] == AttemptResult.CORRECT else 0.0,
        provider="deterministic",
        evidence_type=EvidenceType.ERROR_REPAIRED
        if evaluation["result"] == AttemptResult.CORRECT
        else None,
    )
    if evaluation["result"] == AttemptResult.CORRECT:
        payload = dict(session.payload_json or {})
        completed = set(payload.get("completed_indices") or [])
        completed.add(session.activity_cursor)
        payload["completed_indices"] = sorted(completed)
        payload.pop("pending_remediation", None)
        session.payload_json = payload
        teaching_flow.transition(
            db, session, target_phase=FlowPhase.EVALUATING, reason="retry_correct"
        )
        teaching_flow.transition(
            db, session, target_phase=FlowPhase.PRACTICING, reason="resume_practice"
        )
        teaching_flow.advance_activity_cursor(db, session)
    else:
        teaching_flow.transition(
            db, session, target_phase=FlowPhase.NEEDS_REMEDIATION, reason="retry_incorrect"
        )

    objective = db.get(LearningObjective, session.objective_id)
    return {
        **_session_payload(db, session, objective, eval_out["mastery"]["state"]),
        "attempt": {
            "id": attempt.id,
            "result": attempt.result,
            "attempt_number": attempt.attempt_number,
        },
        "evaluation": evaluation,
        "mastery": eval_out["mastery"],
        "ai_called": False,
    }


def _close_as_mastered(db: Session, session: TeachingFlowSession) -> None:
    from app.core.teaching import is_valid_flow_transition

    if session.phase == FlowPhase.MASTERED:
        return
    if is_valid_flow_transition(session.phase, FlowPhase.MASTERED):
        teaching_flow.transition(
            db, session, target_phase=FlowPhase.MASTERED, reason="mastery_reached"
        )
        return
    _step_toward(db, session, FlowPhase.EVALUATING)
    if is_valid_flow_transition(session.phase, FlowPhase.MASTERED):
        teaching_flow.transition(
            db, session, target_phase=FlowPhase.MASTERED, reason="mastery_reached"
        )


def _advance_after_success(db: Session, session: TeachingFlowSession, activity: dict) -> None:
    hint = activity.get("phase_hint") or "practicing"
    # Ack de activating → input, etc.
    target_map = {
        "activating": FlowPhase.INPUT,
        "input": FlowPhase.NOTICING,
        "noticing": FlowPhase.PRACTICING,
        "producing": FlowPhase.EVALUATING,
        "transfer_check": FlowPhase.TRANSFER_CHECK,
    }
    desired = target_map.get(hint)
    if desired and session.phase != desired:
        # Caminho curto: avançar uma transição legal por vez.
        _step_toward(db, session, desired)

    if hint == "transfer_check":
        if session.phase != FlowPhase.TRANSFER_CHECK:
            _step_toward(db, session, FlowPhase.TRANSFER_CHECK)
        teaching_flow.transition(
            db, session, target_phase=FlowPhase.EVALUATING, reason="transfer_answered"
        )
    elif hint == "producing":
        teaching_flow.advance_activity_cursor(db, session)
        # Após produção, próxima é transfer se existir.
        nxt = teaching_flow.current_activity(session)
        if nxt and nxt.get("type") == "transfer_question":
            _step_toward(db, session, FlowPhase.TRANSFER_CHECK)
    else:
        teaching_flow.advance_activity_cursor(db, session)
        if session.phase == FlowPhase.NOT_STARTED:
            teaching_flow.transition(db, session, target_phase=FlowPhase.ACTIVATING)


def _step_toward(db: Session, session: TeachingFlowSession, target: str) -> None:
    from app.core.teaching import VALID_FLOW_TRANSITIONS, is_valid_flow_transition

    guard = 0
    while session.phase != target and guard < 12:
        guard += 1
        if is_valid_flow_transition(session.phase, target):
            teaching_flow.transition(db, session, target_phase=target, reason="advance")
            return
        options = list(VALID_FLOW_TRANSITIONS.get(session.phase, frozenset()))
        # Preferir fases "à frente" na ordem pedagógica.
        order = [
            FlowPhase.ACTIVATING,
            FlowPhase.INPUT,
            FlowPhase.NOTICING,
            FlowPhase.PRACTICING,
            FlowPhase.PRODUCING,
            FlowPhase.EVALUATING,
            FlowPhase.TRANSFER_CHECK,
            FlowPhase.MASTERED,
        ]
        nxt = None
        try:
            current_i = order.index(session.phase)  # type: ignore[arg-type]
        except ValueError:
            current_i = -1
        for candidate in order[current_i + 1 :]:
            if candidate in options:
                nxt = candidate
                break
        if nxt is None and options:
            nxt = options[0]
        if nxt is None:
            break
        teaching_flow.transition(db, session, target_phase=nxt, reason="step")


def _feature_key(activity: dict) -> str | None:
    canonical = activity.get("canonical_answer")
    if canonical:
        return f"pattern:{deterministic_evaluator.normalize_text(str(canonical))[:80]}"
    req = activity.get("required_features") or []
    if req:
        return "features:" + "+".join(sorted(str(x) for x in req))
    return None


def _contrast_explanation(activity: dict) -> str:
    correct = activity.get("canonical_answer") or (
        (activity.get("accepted_variants") or ["…"])[0]
    )
    return f"Compare sua resposta com o modelo: {correct}"


def _hint_for(action: str, activity: dict) -> str:
    if action in (RemediationAction.HINT, RemediationAction.GIVE_HINT):
        scaffold = activity.get("scaffold_pt") or activity.get("canonical_answer")
        return f"Dica: {scaffold}" if scaffold else "Tente de novo com a estrutura do modelo."
    if action == RemediationAction.SHOW_CONTRAST:
        return "Veja o contraste entre a forma incorreta e a correta."
    if action in (RemediationAction.EXPLAIN,):
        return "Lembre: em inglês a ordem é sujeito + verbo + complemento."
    return "Vamos tentar de novo com apoio."


def _session_payload(
    db: Session,
    session: TeachingFlowSession,
    objective: LearningObjective | None,
    progress_state: str,
) -> dict[str, Any]:
    activity = teaching_flow.current_activity(session)
    return {
        "flow": {
            "id": session.id,
            "phase": session.phase,
            "phase_label_pt": teaching_flow.phase_label_pt(session.phase),
            "status": session.status,
            "activity_cursor": session.activity_cursor,
            "remediation_cycles": session.remediation_cycles,
        },
        "objective": {
            "id": objective.id if objective else session.objective_id,
            "code": objective.code if objective else None,
            "title": objective.title if objective else None,
            "can_do": objective.can_do if objective else None,
            "level": objective.level if objective else None,
        },
        "progress_state": progress_state,
        "current_activity": activity,
        "activities_total": len((session.payload_json or {}).get("activities") or []),
    }
