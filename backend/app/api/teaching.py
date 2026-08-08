"""Teaching Engine: objetivos de aprendizagem, tentativas, erro, remediação e
domínio. Núcleo pedagógico entre currículo e atividades — ver
`app.services.teaching_engine` para as regras; esta rota só resolve
propriedade (todo acesso passa por `UserLanguage.user_id`, id de outro
usuário responde 404, nunca 403) e serializa.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.helpers import user_language
from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.models import (
    CurriculumBlock,
    Language,
    LearningAttempt,
    LearningError,
    LearningObjective,
    Lesson,
    MemorySchedule,
    Remediation,
    TeachingFlowSession,
    User,
    UserLanguage,
    UserObjectiveProgress,
)
from app.schemas import (
    AttemptCreateIn,
    AttemptEvaluateIn,
    DeterministicEvaluateIn,
    ErrorCreateIn,
    FlowStartIn,
    FlowTransitionIn,
    IntelligibilityIn,
    MemoryReviewIn,
    RemediationCreateIn,
    RetryIn,
    SliceAnswerIn,
    SliceRetryIn,
    SliceStartIn,
)
from app.services import (
    activity_generator,
    deterministic_evaluator,
    memory_engine,
    speech_intelligibility,
    teaching_engine as engine,
    teaching_flow,
    teaching_slice,
)
from app.services.objective_seed import ensure_en_a1_can_001

router = APIRouter(prefix="/teaching", tags=["teaching"])


# ------------------------------------------------------------------- lookups


def _owned_objective_language(db: Session, user: User, objective: LearningObjective) -> UserLanguage:
    language = db.get(Language, objective.language_id)
    if not language:
        raise APIError(404, "objective_not_found", "Objetivo de aprendizagem não encontrado.")
    return user_language(db, user.id, language.code)


def _get_objective_or_404(db: Session, objective_id: str) -> LearningObjective:
    objective = db.get(LearningObjective, objective_id)
    if not objective or not objective.is_active:
        raise APIError(404, "objective_not_found", "Objetivo de aprendizagem não encontrado.")
    return objective


def _owned_attempt(db: Session, attempt_id: str, user: User) -> LearningAttempt:
    row = db.scalar(
        select(LearningAttempt)
        .join(UserLanguage, UserLanguage.id == LearningAttempt.user_language_id)
        .where(LearningAttempt.id == attempt_id, UserLanguage.user_id == user.id)
    )
    if not row:
        raise APIError(404, "attempt_not_found", "Tentativa não encontrada.")
    return row


def _owned_error(db: Session, error_id: str, user: User) -> LearningError:
    row = db.scalar(
        select(LearningError)
        .join(UserLanguage, UserLanguage.id == LearningError.user_language_id)
        .where(LearningError.id == error_id, UserLanguage.user_id == user.id)
    )
    if not row:
        raise APIError(404, "error_not_found", "Erro não encontrado.")
    return row


def _owned_remediation(db: Session, remediation_id: str, user: User) -> Remediation:
    row = db.scalar(
        select(Remediation)
        .join(LearningError, LearningError.id == Remediation.error_id)
        .join(UserLanguage, UserLanguage.id == LearningError.user_language_id)
        .where(Remediation.id == remediation_id, UserLanguage.user_id == user.id)
    )
    if not row:
        raise APIError(404, "remediation_not_found", "Remediação não encontrada.")
    return row


def _validate_reference(
    db: Session, *, curriculum_block_id: str | None, lesson_id: str | None, user_language_id: str
) -> None:
    """IDOR guard: bloco/lição referenciados precisam pertencer ao mesmo perfil."""
    if curriculum_block_id:
        block = db.get(CurriculumBlock, curriculum_block_id)
        owns = block is not None and _block_user_language_id(db, block) == user_language_id
        if not owns:
            raise APIError(404, "curriculum_block_not_found", "Bloco de estudo não encontrado.")
    if lesson_id:
        lesson = db.get(Lesson, lesson_id)
        if not lesson or lesson.user_language_id != user_language_id:
            raise APIError(404, "lesson_not_found", "Lição não encontrada.")


def _block_user_language_id(db: Session, block: CurriculumBlock) -> str | None:
    from app.models import Curriculum, CurriculumDay, CurriculumWeek

    return db.scalar(
        select(Curriculum.user_language_id)
        .join(CurriculumWeek, CurriculumWeek.curriculum_id == Curriculum.id)
        .join(CurriculumDay, CurriculumDay.week_id == CurriculumWeek.id)
        .where(CurriculumDay.id == block.day_id)
    )


# ------------------------------------------------------------------ payloads


def _objective_payload(objective: LearningObjective) -> dict:
    return {
        "id": objective.id,
        "code": objective.code,
        "level": objective.level,
        "title": objective.title,
        "can_do": objective.can_do,
        "description": objective.description,
        "skill_focus": objective.skill_focus,
        "prerequisites": objective.prerequisites_json or [],
        "target_vocabulary": objective.target_vocabulary_json or [],
        "target_expressions": objective.target_expressions_json or [],
        "target_patterns": objective.target_patterns_json or [],
        "pronunciation_focus": objective.pronunciation_focus_json or [],
        "pedagogy": objective.pedagogy_json or {},
        "mastery_policy": objective.mastery_policy_json or {},
        "version": objective.version,
    }


def _owned_flow(db: Session, flow_id: str, user: User) -> TeachingFlowSession:
    row = db.scalar(
        select(TeachingFlowSession)
        .join(UserLanguage, UserLanguage.id == TeachingFlowSession.user_language_id)
        .where(TeachingFlowSession.id == flow_id, UserLanguage.user_id == user.id)
    )
    if not row:
        raise APIError(404, "flow_not_found", "Sessão de ensino não encontrada.")
    return row


def _owned_memory(db: Session, schedule_id: str, user: User) -> MemorySchedule:
    row = db.scalar(
        select(MemorySchedule)
        .join(UserLanguage, UserLanguage.id == MemorySchedule.user_language_id)
        .where(MemorySchedule.id == schedule_id, UserLanguage.user_id == user.id)
    )
    if not row:
        raise APIError(404, "memory_not_found", "Item de memória não encontrado.")
    return row


def _progress_payload(progress: UserObjectiveProgress) -> dict:
    return {
        "state": progress.state,
        "started_at": progress.started_at.isoformat() if progress.started_at else None,
        "mastered_at": progress.mastered_at.isoformat() if progress.mastered_at else None,
        "last_evaluated_at": progress.last_evaluated_at.isoformat() if progress.last_evaluated_at else None,
        "reasons": progress.last_reasons_json,
    }


def _attempt_payload(attempt: LearningAttempt) -> dict:
    return {
        "id": attempt.id,
        "objective_id": attempt.objective_id,
        "curriculum_block_id": attempt.curriculum_block_id,
        "lesson_id": attempt.lesson_id,
        "activity_type": attempt.activity_type,
        "attempt_number": attempt.attempt_number,
        "result": attempt.result,
        "score": attempt.score,
        "provider": attempt.provider,
        "created_at": attempt.created_at.isoformat(),
    }


def _error_payload(error: LearningError) -> dict:
    return {
        "id": error.id,
        "objective_id": error.objective_id,
        "category": error.category,
        "original": error.original,
        "expected": error.expected,
        "explanation": error.explanation,
        "severity": error.severity,
        "language_feature": error.language_feature,
        "recurring": error.recurring,
        "resolved": error.resolved,
        "occurrences": error.occurrences,
    }


def _remediation_payload(remediation: Remediation) -> dict:
    return {
        "id": remediation.id,
        "error_id": remediation.error_id,
        "action": remediation.action,
        "reason": remediation.reason,
        "next_attempt_id": remediation.next_attempt_id,
    }


# ----------------------------------------------------------------- endpoints


@router.get("/objectives")
def list_objectives(
    language_code: str,
    level: str | None = None,
    skill: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Catálogo de objetivos — conteúdo, não pertence ao usuário (como `/grammar/topics`)."""
    query = select(LearningObjective).join(Language).where(
        Language.code == language_code, LearningObjective.is_active.is_(True)
    )
    if level:
        query = query.where(LearningObjective.level == level)
    if skill:
        query = query.where(LearningObjective.skill_focus == skill)
    return [_objective_payload(o) for o in db.scalars(query.order_by(LearningObjective.code))]


@router.get("/objectives/{objective_id}")
def get_objective(
    objective_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Objetivo + progresso do usuário (cria progresso `not_started` se ainda não existir)."""
    objective = _get_objective_or_404(db, objective_id)
    owner = _owned_objective_language(db, user, objective)
    progress = engine.get_or_create_progress(db, user_language_id=owner.id, objective_id=objective.id)
    db.commit()
    return {"objective": _objective_payload(objective), "progress": _progress_payload(progress)}


@router.get("/objectives/{objective_id}/mastery")
def get_mastery(
    objective_id: str,
    activity_completed: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Recomputa e devolve o estado de domínio.

    `activity_completed=true` é o ponto de integração com `CurriculumBlock`: o
    frontend chama isto depois de `POST /curriculum/block/{id}/complete` para
    saber se a conclusão do bloco também significa domínio — não presume que sim.
    """
    objective = _get_objective_or_404(db, objective_id)
    owner = _owned_objective_language(db, user, objective)
    mastery = engine.evaluate_mastery(
        db,
        user_language_id=owner.id,
        objective_id=objective.id,
        activity_completed=activity_completed,
    )
    recommendation = engine.recommend_next_action(db, user_language_id=owner.id, objective_id=objective.id)
    db.commit()
    return {**mastery, "recommended_next_action": recommendation}


@router.post("/attempts")
def create_attempt(
    data: AttemptCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    objective = _get_objective_or_404(db, data.objective_id)
    owner = _owned_objective_language(db, user, objective)
    _validate_reference(
        db,
        curriculum_block_id=data.curriculum_block_id,
        lesson_id=data.lesson_id,
        user_language_id=owner.id,
    )
    attempt = engine.record_attempt(
        db,
        user_language_id=owner.id,
        objective_id=objective.id,
        activity_type=data.activity_type,
        student_response=data.student_response,
        curriculum_block_id=data.curriculum_block_id,
        lesson_id=data.lesson_id,
    )
    db.commit()
    return _attempt_payload(attempt)


@router.post("/attempts/{attempt_id}/evaluate")
def evaluate_attempt_endpoint(
    attempt_id: str,
    data: AttemptEvaluateIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    attempt = _owned_attempt(db, attempt_id, user)
    result = engine.evaluate_attempt(
        db,
        attempt,
        result=data.result,
        score=data.score,
        provider=data.provider,
        evidence_type=data.evidence_type,
        is_transfer=data.is_transfer,
    )
    db.commit()
    return {
        "attempt": _attempt_payload(result["attempt"]),
        "evidence_recorded": result["evidence"] is not None,
        "mastery": result["mastery"],
    }


@router.post("/attempts/{attempt_id}/errors")
def create_error(
    attempt_id: str,
    data: ErrorCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    attempt = _owned_attempt(db, attempt_id, user)
    error = engine.record_error(
        db,
        attempt,
        category=data.category,
        original=data.original,
        expected=data.expected,
        explanation=data.explanation,
        severity=data.severity,
        language_feature=data.language_feature,
    )
    db.commit()
    return _error_payload(error)


@router.post("/errors/{error_id}/remediation")
def create_remediation(
    error_id: str,
    data: RemediationCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    error = _owned_error(db, error_id, user)
    remediation = engine.choose_remediation(db, error, action=data.action, reason=data.reason)
    db.commit()
    return _remediation_payload(remediation)


@router.post("/remediation/{remediation_id}/retry")
def retry_remediation(
    remediation_id: str,
    data: RetryIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    remediation = _owned_remediation(db, remediation_id, user)
    error = db.get(LearningError, remediation.error_id)
    if error is not None:
        _validate_reference(
            db,
            curriculum_block_id=data.curriculum_block_id,
            lesson_id=data.lesson_id,
            user_language_id=error.user_language_id,
        )
    attempt = engine.record_retry(
        db,
        remediation,
        student_response=data.student_response,
        activity_type=data.activity_type,
        curriculum_block_id=data.curriculum_block_id,
        lesson_id=data.lesson_id,
    )
    db.commit()
    return _attempt_payload(attempt)


# ------------------------------------------------------------- Teaching Flow V2


@router.post("/flows")
def start_flow_endpoint(
    data: FlowStartIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    objective = _get_objective_or_404(db, data.objective_id)
    owner = _owned_objective_language(db, user, objective)
    _validate_reference(
        db,
        curriculum_block_id=data.curriculum_block_id,
        lesson_id=None,
        user_language_id=owner.id,
    )
    engine.start_objective(db, user_language_id=owner.id, objective_id=objective.id)
    session = teaching_flow.start_flow(
        db,
        user_language_id=owner.id,
        objective_id=objective.id,
        curriculum_block_id=data.curriculum_block_id,
    )
    db.commit()
    return {
        "id": session.id,
        "phase": session.phase,
        "phase_label_pt": teaching_flow.phase_label_pt(session.phase),
        "status": session.status,
        "activity_cursor": session.activity_cursor,
        "current_activity": teaching_flow.current_activity(session),
        "activities_total": len((session.payload_json or {}).get("activities") or []),
    }


@router.get("/flows/{flow_id}")
def get_flow_endpoint(
    flow_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    session = _owned_flow(db, flow_id, user)
    return {
        "id": session.id,
        "phase": session.phase,
        "phase_label_pt": teaching_flow.phase_label_pt(session.phase),
        "status": session.status,
        "objective_id": session.objective_id,
        "activity_cursor": session.activity_cursor,
        "remediation_cycles": session.remediation_cycles,
        "current_activity": teaching_flow.current_activity(session),
        "activities_total": len((session.payload_json or {}).get("activities") or []),
    }


@router.post("/flows/{flow_id}/transition")
def transition_flow_endpoint(
    flow_id: str,
    data: FlowTransitionIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    session = _owned_flow(db, flow_id, user)
    teaching_flow.transition(
        db, session, target_phase=data.target_phase, reason=data.reason
    )
    db.commit()
    return {
        "id": session.id,
        "phase": session.phase,
        "phase_label_pt": teaching_flow.phase_label_pt(session.phase),
        "status": session.status,
    }


@router.post("/objectives/{objective_id}/activities")
def generate_activities_endpoint(
    objective_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    objective = _get_objective_or_404(db, objective_id)
    _owned_objective_language(db, user, objective)
    activities = activity_generator.generate_activities(objective)
    return {"objective_id": objective.id, "activities": activities, "ai_called": False}


@router.post("/evaluate-deterministic")
def evaluate_deterministic_endpoint(
    data: DeterministicEvaluateIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    _ = (db, user)  # autenticação obrigatória; sem estado
    return deterministic_evaluator.evaluate_response(
        student_response=data.student_response,
        activity=data.activity,
        canonical_answer=data.canonical_answer,
        accepted_variants=data.accepted_variants,
        required_features=data.required_features,
    )


@router.post("/intelligibility")
def intelligibility_endpoint(
    data: IntelligibilityIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    _ = (db, user)
    return speech_intelligibility.assess_intelligibility(
        target_text=data.target_text,
        transcript=data.transcript,
        provider=data.provider,
    )


@router.get("/memory/due")
def memory_due_endpoint(
    language_code: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    owner = user_language(db, user.id, language_code)
    rows = memory_engine.list_due(db, user_language_id=owner.id)
    return [
        {
            "id": row.id,
            "subject_type": row.subject_type,
            "subject_key": row.subject_key,
            "state": row.state,
            "due_at": row.due_at.isoformat(),
            "payload": row.payload_json,
        }
        for row in rows
    ]


@router.post("/memory/{schedule_id}/review")
def memory_review_endpoint(
    schedule_id: str,
    data: MemoryReviewIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    schedule = _owned_memory(db, schedule_id, user)
    event = memory_engine.record_review(
        db,
        schedule,
        rating=data.rating,
        result=data.result,
        response_time_ms=data.response_time_ms,
    )
    db.commit()
    return {
        "schedule_id": schedule.id,
        "event_id": event.id,
        "due_at": schedule.due_at.isoformat(),
        "state": schedule.state,
        "review_count": schedule.review_count,
    }


# ------------------------------------------------------------- vertical slice


@router.get("/slice/en-a1-can-001/active")
def get_active_vertical_slice(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Restaura flow ativo/recente sem criar sessão. 404 se ainda não houver."""
    objective = ensure_en_a1_can_001(db)
    owner = _owned_objective_language(db, user, objective)
    payload = teaching_slice.get_active_slice(db, user_language_id=owner.id)
    if payload is None:
        raise APIError(404, "no_active_flow", "Não há fluxo ativo para este objetivo.")
    return payload


@router.post("/slice/en-a1-can-001/start")
def start_vertical_slice(
    data: SliceStartIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    objective = ensure_en_a1_can_001(db)
    owner = _owned_objective_language(db, user, objective)
    if data.curriculum_block_id:
        _validate_reference(
            db,
            curriculum_block_id=data.curriculum_block_id,
            lesson_id=None,
            user_language_id=owner.id,
        )
    payload = teaching_slice.start_slice(
        db, user_language_id=owner.id, curriculum_block_id=data.curriculum_block_id
    )
    db.commit()
    return payload


@router.post("/slice/flows/{flow_id}/answer")
def slice_answer(
    flow_id: str,
    data: SliceAnswerIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    session = _owned_flow(db, flow_id, user)
    payload = teaching_slice.submit_slice_answer(
        db,
        session,
        student_response=data.student_response,
        activity_index=data.activity_index,
    )
    db.commit()
    return payload


@router.post("/slice/flows/{flow_id}/retry")
def slice_retry(
    flow_id: str,
    data: SliceRetryIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    session = _owned_flow(db, flow_id, user)
    payload = teaching_slice.retry_slice(
        db,
        session,
        remediation_id=data.remediation_id,
        student_response=data.student_response,
    )
    db.commit()
    return payload
