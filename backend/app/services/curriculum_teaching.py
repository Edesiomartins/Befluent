"""Integração Teaching Engine V2 ↔ cronograma (piloto Semana 1 B2).

Um CurriculumDay resolve **um** LearningObjective; blocos pedagógicos
compartilham o mesmo `objective_id`. Review/SRS fica independente.

Mapa bloco → fase pedagógica (rótulos internos; UI usa phase_label PT):

- vocabulary → ACTIVATING / INPUT
- grammar → NOTICING / PRACTICING
- listening/reading → PRACTICING
- pronunciation → PRACTICING
- writing → PRODUCING
- conversation → PRODUCING / EVALUATING (Dia 7: TRANSFER_CHECK)
- review → MEMORY/SRS (sem objective_id)
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.curriculum import BlockSkill
from app.core.errors import APIError
from app.core.teaching import FlowPhase, MasteryState
from app.models import (
    CurriculumBlock,
    LearningObjective,
    TeachingFlowSession,
    UserObjectiveProgress,
)
from app.services import teaching_engine, teaching_flow, teaching_slice

#: Skills que compartilham o Can-Do do dia. Review fica de fora.
PEDAGOGICAL_SKILLS: frozenset[str] = frozenset(
    {
        BlockSkill.VOCABULARY,
        BlockSkill.GRAMMAR,
        BlockSkill.PRONUNCIATION,
        BlockSkill.LISTENING,
        BlockSkill.READING,
        BlockSkill.CONVERSATION,
        BlockSkill.WRITING,
    }
)

SKILL_FLOW_HINT: dict[str, str] = {
    BlockSkill.VOCABULARY: FlowPhase.ACTIVATING,
    BlockSkill.GRAMMAR: FlowPhase.NOTICING,
    BlockSkill.PRONUNCIATION: FlowPhase.PRACTICING,
    BlockSkill.LISTENING: FlowPhase.PRACTICING,
    BlockSkill.READING: FlowPhase.PRACTICING,
    BlockSkill.WRITING: FlowPhase.PRODUCING,
    BlockSkill.CONVERSATION: FlowPhase.PRODUCING,
}


def day_objective_id(blocks: list[CurriculumBlock]) -> str | None:
    """Objetivo da jornada = objective_id compartilhado pelos blocos pedagógicos."""
    for block in sorted(blocks, key=lambda b: b.position):
        if block.skill in PEDAGOGICAL_SKILLS and block.objective_id:
            return block.objective_id
    return None


def day_learning_objective_payload(
    db: Session,
    *,
    blocks: list[CurriculumBlock],
    user_language_id: str | None,
) -> dict[str, Any] | None:
    objective_id = day_objective_id(blocks)
    if not objective_id:
        return None
    objective = db.get(LearningObjective, objective_id)
    if objective is None:
        return None
    pedagogy = dict(objective.pedagogy_json or {})
    # Âncoras temáticas leves não são Can-Do de jornada.
    if pedagogy.get("source") == "curriculum_theme":
        return None

    state = MasteryState.NOT_STARTED
    reasons: list[str] = []
    if user_language_id:
        progress = db.scalar(
            select(UserObjectiveProgress).where(
                UserObjectiveProgress.user_language_id == user_language_id,
                UserObjectiveProgress.objective_id == objective.id,
            )
        )
        if progress is not None:
            state = progress.state
            reasons = list(progress.last_reasons_json or [])

    # Rótulos para o aluno — sem códigos técnicos como texto principal.
    if state == MasteryState.MASTERED:
        status_label = "Demonstrado"
    elif state in {MasteryState.NOT_STARTED}:
        status_label = "Em desenvolvimento"
    else:
        status_label = "Em desenvolvimento"

    activation = pedagogy.get("activation") or {}
    learner_goal = activation.get("can_do") or objective.can_do

    return {
        "id": objective.id,
        "code": objective.code,
        "title": objective.title,
        "can_do": objective.can_do,
        "learner_goal": learner_goal,
        "level": objective.level,
        "state": state,
        "status_label": status_label,
        "reasons": reasons,
        "is_pilot": bool((pedagogy.get("pilot") or {})),
        "transfer_day": bool((pedagogy.get("pilot") or {}).get("transfer_day")),
    }


def ensure_block_teaching(
    db: Session,
    *,
    user_language_id: str,
    block: CurriculumBlock,
) -> dict[str, Any] | None:
    """Inicia progresso + flow TE quando o bloco tem Can-Do real.

    Idempotente. Review nunca entra. Não altera completion do bloco.
    """
    if not block.objective_id or block.skill == BlockSkill.REVIEW:
        return None
    if block.skill not in PEDAGOGICAL_SKILLS:
        return None

    objective = db.get(LearningObjective, block.objective_id)
    if objective is None:
        return None

    # Objetivos-tema leves (EN-B2-TH-*) não têm pedagogia completa — não abrir flow.
    pedagogy = dict(objective.pedagogy_json or {})
    if pedagogy.get("source") == "curriculum_theme":
        return None

    progress = teaching_engine.start_objective(
        db, user_language_id=user_language_id, objective_id=objective.id
    )
    session = teaching_flow.start_flow(
        db,
        user_language_id=user_language_id,
        objective_id=objective.id,
        curriculum_block_id=block.id,
    )
    # Atualiza bloco de referência se o flow já existia sem vínculo.
    if session.curriculum_block_id is None:
        session.curriculum_block_id = block.id
        db.flush()

    return teaching_slice._restore_payload(db, session, objective, progress.state)


def get_block_teaching(
    db: Session,
    *,
    user_language_id: str,
    block: CurriculumBlock,
) -> dict[str, Any] | None:
    if not block.objective_id or block.skill == BlockSkill.REVIEW:
        return None
    objective = db.get(LearningObjective, block.objective_id)
    if objective is None:
        return None
    pedagogy = dict(objective.pedagogy_json or {})
    if pedagogy.get("source") == "curriculum_theme":
        return None

    session = db.scalar(
        select(TeachingFlowSession).where(
            TeachingFlowSession.user_language_id == user_language_id,
            TeachingFlowSession.objective_id == objective.id,
            TeachingFlowSession.status == "active",
        )
    )
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
    state = progress.state if progress else MasteryState.NOT_STARTED
    return teaching_slice._restore_payload(db, session, objective, state)


def submit_block_answer(
    db: Session,
    *,
    user_language_id: str,
    block: CurriculumBlock,
    student_response: str,
    activity_index: int | None = None,
) -> dict[str, Any]:
    payload = ensure_block_teaching(db, user_language_id=user_language_id, block=block)
    if payload is None:
        raise APIError(
            409,
            "teaching_not_available",
            "Este bloco não está integrado ao Teaching Engine.",
        )
    flow = payload.get("flow") or {}
    session = db.get(TeachingFlowSession, flow.get("id"))
    if session is None:
        raise APIError(404, "flow_not_found", "Sessão de ensino não encontrada.")
    return teaching_slice.submit_slice_answer(
        db,
        session,
        student_response=student_response,
        activity_index=activity_index,
    )


def retry_block_answer(
    db: Session,
    *,
    user_language_id: str,
    block: CurriculumBlock,
    remediation_id: str,
    student_response: str,
) -> dict[str, Any]:
    payload = get_block_teaching(db, user_language_id=user_language_id, block=block)
    if payload is None:
        raise APIError(
            409,
            "teaching_not_available",
            "Este bloco não está integrado ao Teaching Engine.",
        )
    flow = payload.get("flow") or {}
    session = db.get(TeachingFlowSession, flow.get("id"))
    if session is None:
        raise APIError(404, "flow_not_found", "Sessão de ensino não encontrada.")
    return teaching_slice.retry_slice(
        db,
        session,
        remediation_id=remediation_id,
        student_response=student_response,
    )


def skill_flow_hint(skill: str) -> str | None:
    return SKILL_FLOW_HINT.get(skill)
