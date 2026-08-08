"""Teaching Engine: o núcleo pedagógico entre currículo e atividades.

Formaliza a diferença entre **atividade concluída** (`CurriculumBlock.status`,
inalterado por este módulo) e **aprendizagem demonstrada**
(`UserObjectiveProgress.state`, um `MasteryState`).

Princípio central: erro não termina a atividade. `record_error` sempre abre
um ciclo diagnóstico → remediação → nova tentativa → reavaliação — nunca
apenas marca a tentativa como falha e para por aí.

`evaluate_mastery` é a única função que pode levar um objetivo a `MASTERED`,
e ela só olha para evidência e erro registrados — nunca para quem chamou.
Um `provider="openrouter"` em `evaluate_attempt` é rastreabilidade, não
autoridade: a IA nunca marca domínio sozinha.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.teaching import (
    SEVERITY_RANK,
    AttemptResult,
    MasteryState,
    default_remediation_action,
    escalated_remediation_action,
    mastery_policy,
)
from app.models import (
    LearningAttempt,
    LearningError,
    LearningEvidence,
    LearningObjective,
    Remediation,
    UserObjectiveProgress,
)
from app.services import memory_engine


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_objective(db: Session, objective_id: str) -> LearningObjective:
    objective = db.get(LearningObjective, objective_id)
    if not objective or not objective.is_active:
        raise APIError(404, "objective_not_found", "Objetivo de aprendizagem não encontrado.")
    return objective


def get_or_create_progress(
    db: Session, *, user_language_id: str, objective_id: str
) -> UserObjectiveProgress:
    progress = db.scalar(
        select(UserObjectiveProgress).where(
            UserObjectiveProgress.user_language_id == user_language_id,
            UserObjectiveProgress.objective_id == objective_id,
        )
    )
    if progress is None:
        progress = UserObjectiveProgress(
            user_language_id=user_language_id,
            objective_id=objective_id,
            state=MasteryState.NOT_STARTED,
        )
        db.add(progress)
        db.flush()
    return progress


# --------------------------------------------------------------------- start


def start_objective(db: Session, *, user_language_id: str, objective_id: str) -> UserObjectiveProgress:
    """Engaja o aluno com o objetivo. Idempotente: reabrir não reinicia o histórico."""
    _get_objective(db, objective_id)
    progress = get_or_create_progress(db, user_language_id=user_language_id, objective_id=objective_id)
    if progress.state == MasteryState.NOT_STARTED:
        progress.state = MasteryState.LEARNING
        progress.started_at = _now()
        db.flush()
    return progress


# ------------------------------------------------------------------ attempts


def _next_attempt_number(db: Session, *, user_language_id: str, objective_id: str) -> int:
    count = db.scalar(
        select(func.count(LearningAttempt.id)).where(
            LearningAttempt.user_language_id == user_language_id,
            LearningAttempt.objective_id == objective_id,
        )
    )
    return (count or 0) + 1


def record_attempt(
    db: Session,
    *,
    user_language_id: str,
    objective_id: str,
    activity_type: str,
    student_response: str | None = None,
    curriculum_block_id: str | None = None,
    lesson_id: str | None = None,
) -> LearningAttempt:
    """Registra uma produção do aluno. Não avalia — ver `evaluate_attempt`.

    Não recebe nem guarda áudio bruto: `student_response` é sempre texto
    (transcrição, resposta, redação).
    """
    _get_objective(db, objective_id)
    progress = get_or_create_progress(db, user_language_id=user_language_id, objective_id=objective_id)
    if progress.state == MasteryState.NOT_STARTED:
        progress.state = MasteryState.LEARNING
        progress.started_at = _now()

    attempt = LearningAttempt(
        user_language_id=user_language_id,
        objective_id=objective_id,
        curriculum_block_id=curriculum_block_id,
        lesson_id=lesson_id,
        activity_type=activity_type,
        attempt_number=_next_attempt_number(db, user_language_id=user_language_id, objective_id=objective_id),
        student_response=student_response,
        result=AttemptResult.PENDING,
    )
    db.add(attempt)
    db.flush()
    return attempt


def evaluate_attempt(
    db: Session,
    attempt: LearningAttempt,
    *,
    result: str,
    score: float | None = None,
    provider: str | None = None,
    evidence_type: str | None = None,
    is_transfer: bool = False,
) -> dict:
    """Avalia uma tentativa já registrada.

    Se `evidence_type` for informado e o resultado não for incorreto, cria
    `LearningEvidence` — "clicou em concluir" nunca gera evidência, só uma
    avaliação real (heurística, IA ou o próprio aluno via `provider`) gera.

    Se esta tentativa é o retry de uma `Remediation` e o resultado é
    `correct`, resolve o erro que originou a remediação: é o "retry correto
    resolve erro" do ciclo pedagógico.

    Termina recomputando `evaluate_mastery` — nunca marca `mastered`
    diretamente aqui.
    """
    if result not in (AttemptResult.CORRECT, AttemptResult.PARTIAL, AttemptResult.INCORRECT):
        raise APIError(422, "invalid_result", "Resultado da tentativa inválido.")

    attempt.result = result
    attempt.score = score
    attempt.provider = provider
    attempt.evaluated_at = _now()

    evidence: LearningEvidence | None = None
    if evidence_type and result in (AttemptResult.CORRECT, AttemptResult.PARTIAL):
        evidence = LearningEvidence(
            user_language_id=attempt.user_language_id,
            objective_id=attempt.objective_id,
            attempt_id=attempt.id,
            evidence_type=evidence_type,
            is_transfer=is_transfer,
        )
        db.add(evidence)

    repaired_error: LearningError | None = None
    if result == AttemptResult.CORRECT:
        remediation = db.scalar(
            select(Remediation).where(Remediation.next_attempt_id == attempt.id)
        )
        if remediation is not None:
            error = db.get(LearningError, remediation.error_id)
            if error is not None and not error.resolved:
                error.resolved = True
                error.last_seen = _now()
                repaired_error = error
                if evidence is None:
                    evidence = LearningEvidence(
                        user_language_id=attempt.user_language_id,
                        objective_id=attempt.objective_id,
                        attempt_id=attempt.id,
                        evidence_type="error_repaired",
                    )
                    db.add(evidence)

    db.flush()
    if repaired_error is not None:
        memory_engine.schedule_learner_error(db, error=repaired_error)

    mastery = evaluate_mastery(
        db, user_language_id=attempt.user_language_id, objective_id=attempt.objective_id
    )
    return {"attempt": attempt, "evidence": evidence, "mastery": mastery}


# -------------------------------------------------------------------- errors


def record_error(
    db: Session,
    attempt: LearningAttempt,
    *,
    category: str,
    original: str,
    expected: str | None = None,
    explanation: str | None = None,
    severity: str = "moderate",
    language_feature: str | None = None,
) -> LearningError:
    """Registra um erro real. Erro não termina a atividade: sempre move o
    objetivo para `NEEDS_REMEDIATION`, abrindo o ciclo diagnóstico → remediação
    → retry, independentemente da gravidade (a gravidade só decide depois se o
    erro *bloqueia* domínio — ver `evaluate_mastery`).

    Deduplica por feature linguística (quando houver) ou por texto original:
    reincidência não exige string idêntica se `language_feature` coincidir.
    """
    existing = None
    if language_feature:
        existing = db.scalar(
            select(LearningError).where(
                LearningError.user_language_id == attempt.user_language_id,
                LearningError.objective_id == attempt.objective_id,
                LearningError.language_feature == language_feature,
                LearningError.resolved.is_(False),
            )
        )
    if existing is None:
        existing = db.scalar(
            select(LearningError).where(
                LearningError.user_language_id == attempt.user_language_id,
                LearningError.objective_id == attempt.objective_id,
                LearningError.category == category,
                LearningError.original == original,
                LearningError.resolved.is_(False),
            )
        )
    if existing is not None:
        existing.occurrences += 1
        existing.recurring = True
        existing.last_seen = _now()
        existing.attempt_id = attempt.id
        if expected and not existing.expected:
            existing.expected = expected
        error = existing
    else:
        error = LearningError(
            user_language_id=attempt.user_language_id,
            objective_id=attempt.objective_id,
            attempt_id=attempt.id,
            category=category,
            original=original,
            expected=expected,
            explanation=explanation,
            severity=severity,
            language_feature=language_feature,
        )
        db.add(error)

    db.flush()
    progress = get_or_create_progress(
        db, user_language_id=attempt.user_language_id, objective_id=attempt.objective_id
    )
    progress.state = MasteryState.NEEDS_REMEDIATION
    db.flush()
    return error


# --------------------------------------------------------------- remediation


def choose_remediation(
    db: Session,
    error: LearningError,
    *,
    action: str | None = None,
    reason: str | None = None,
    escalate: bool = False,
) -> Remediation:
    """Escolhe (ou recebe) a ação de remediação para um erro.

    Sem `action` explícito: tabela por categoria. Com `escalate=True`:
    1ª ocorrência → hint; 2ª → explain; recorrente → contraste/controlado.
    """
    if action:
        chosen = action
    elif escalate:
        chosen = escalated_remediation_action(error.occurrences, error.category)
    else:
        chosen = default_remediation_action(error.category)
    remediation = Remediation(error_id=error.id, action=chosen, reason=reason)
    db.add(remediation)
    db.flush()
    return remediation


def record_retry(
    db: Session,
    remediation: Remediation,
    *,
    student_response: str | None = None,
    activity_type: str | None = None,
    curriculum_block_id: str | None = None,
    lesson_id: str | None = None,
) -> LearningAttempt:
    """Registra a nova tentativa pedida pela remediação.

    Estado vai direto para `RETRYING` — um sinal de processo (avaliação
    pendente), não algo que `evaluate_mastery` derivaria sozinho, já que o
    erro que originou a remediação ainda está `resolved=False` neste ponto.

    Idempotente: se `next_attempt_id` já existe, devolve a tentativa ligada
    (não cria segunda tentativa no double-click).
    """
    if remediation.next_attempt_id:
        existing = db.get(LearningAttempt, remediation.next_attempt_id)
        if existing is not None:
            if existing.result != AttemptResult.PENDING:
                raise APIError(
                    409,
                    "retry_already_evaluated",
                    "Esta remediação já possui retry avaliado.",
                )
            if student_response is not None:
                existing.student_response = student_response
            return existing

    error = db.get(LearningError, remediation.error_id)
    if error is None:
        raise APIError(404, "error_not_found", "Erro associado à remediação não encontrado.")
    prior_attempt = db.get(LearningAttempt, error.attempt_id) if error.attempt_id else None
    objective_id = error.objective_id or (prior_attempt.objective_id if prior_attempt else None)
    if not objective_id:
        raise APIError(
            409,
            "objective_unresolved",
            "Não foi possível determinar o objetivo desta remediação.",
        )

    attempt = record_attempt(
        db,
        user_language_id=error.user_language_id,
        objective_id=objective_id,
        activity_type=activity_type or (prior_attempt.activity_type if prior_attempt else "retry"),
        student_response=student_response,
        curriculum_block_id=curriculum_block_id
        or (prior_attempt.curriculum_block_id if prior_attempt else None),
        lesson_id=lesson_id or (prior_attempt.lesson_id if prior_attempt else None),
    )
    remediation.next_attempt_id = attempt.id

    progress = get_or_create_progress(db, user_language_id=error.user_language_id, objective_id=objective_id)
    progress.state = MasteryState.RETRYING
    db.flush()
    return attempt


# --------------------------------------------------------------------- mastery


def _blocking_errors(errors: list[LearningError], policy: dict) -> list[LearningError]:
    threshold = SEVERITY_RANK.get(policy.get("block_on_unresolved_severity"), SEVERITY_RANK["critical"])
    return [
        error
        for error in errors
        if not error.resolved and SEVERITY_RANK.get(error.severity, SEVERITY_RANK["moderate"]) >= threshold
    ]


def _meets_evidence_bar(evidences: list[LearningEvidence], policy: dict) -> bool:
    if len(evidences) < policy.get("min_evidence_count", 1):
        return False
    required = set(policy.get("required_evidence_types") or [])
    present = {evidence.evidence_type for evidence in evidences}
    if not required.issubset(present):
        return False
    if policy.get("require_transfer_success") and not any(evidence.is_transfer for evidence in evidences):
        return False
    return True


def evaluate_mastery(
    db: Session, *, user_language_id: str, objective_id: str, activity_completed: bool = False
) -> dict:
    """Recomputa o estado de domínio a partir de evidência e erro registrados.

    Política simples e transparente (`app.core.teaching.DEFAULT_MASTERY_POLICY`,
    com overrides por objetivo), não um único percentual mágico. `reasons`
    explica a decisão — nunca "confiança 87%" sem explicação por trás.

    `activity_completed=True` é o que distingue block completed de objective
    mastered: se a atividade foi marcada concluída mas a evidência não
    sustenta domínio, o objetivo vai para `NEEDS_REVIEW`, não para `MASTERED`.
    """
    objective = _get_objective(db, objective_id)
    progress = get_or_create_progress(db, user_language_id=user_language_id, objective_id=objective_id)
    policy = mastery_policy(objective.mastery_policy_json)

    evidences = list(
        db.scalars(
            select(LearningEvidence).where(
                LearningEvidence.user_language_id == user_language_id,
                LearningEvidence.objective_id == objective_id,
            )
        )
    )
    errors = list(
        db.scalars(
            select(LearningError).where(
                LearningError.user_language_id == user_language_id,
                LearningError.objective_id == objective_id,
            )
        )
    )
    attempts_exist = bool(
        db.scalar(
            select(func.count(LearningAttempt.id)).where(
                LearningAttempt.user_language_id == user_language_id,
                LearningAttempt.objective_id == objective_id,
            )
        )
    )

    reasons: list[str] = []
    blocking = _blocking_errors(errors, policy)
    open_errors = [error for error in errors if not error.resolved]
    if not attempts_exist:
        state = MasteryState.NOT_STARTED
        reasons.append("Nenhuma tentativa registrada.")
    elif _meets_evidence_bar(evidences, policy) and not blocking:
        # Evidência já sustenta domínio e nenhum erro pendente tem gravidade
        # suficiente para bloquear — um erro leve não resolvido não impede
        # mastery, mas também não é apagado: ele continua visível em `errors`.
        state = MasteryState.MASTERED
        reasons.append("Evidência exigida pela política presente, sem erro bloqueador pendente.")
    elif open_errors:
        # Erro não termina a atividade: enquanto não resolvido, o objetivo
        # sempre volta para o ciclo de remediação — mesmo que a gravidade não
        # seja suficiente para, por si só, bloquear um domínio já alcançado.
        state = MasteryState.NEEDS_REMEDIATION
        if blocking:
            reasons.append(
                f"{len(blocking)} erro(s) não resolvido(s) com gravidade igual ou acima de "
                f"'{policy.get('block_on_unresolved_severity')}' impedem o domínio."
            )
        else:
            reasons.append(f"{len(open_errors)} erro(s) não resolvido(s) aguardando remediação.")
    elif activity_completed:
        state = MasteryState.NEEDS_REVIEW
        reasons.append(
            "Atividade marcada como concluída, mas a evidência registrada ainda não "
            "sustenta domínio — concluir não é o mesmo que dominar."
        )
    elif evidences:
        state = MasteryState.PRACTICING
        reasons.append("Há evidência registrada, mas abaixo do critério de domínio da política.")
    else:
        state = MasteryState.LEARNING
        reasons.append("Tentativas em andamento, sem evidência de domínio ainda.")

    progress.state = state
    progress.last_evaluated_at = _now()
    progress.last_reasons_json = reasons
    memory_schedule_id = None
    if state == MasteryState.MASTERED and progress.mastered_at is None:
        progress.mastered_at = _now()
        schedule = memory_engine.schedule_objective_review(
            db, user_language_id=user_language_id, objective=objective
        )
        memory_schedule_id = schedule.id
        reasons.append("Objetivo agendado na memória universal para revisão futura.")
    db.flush()

    return {
        "state": state,
        "reasons": reasons,
        "progress_id": progress.id,
        "memory_schedule_id": memory_schedule_id,
    }


# ------------------------------------------------------------ recommendation

_STATE_ACTION: dict[str, str] = {
    MasteryState.NOT_STARTED: "start_objective",
    MasteryState.LEARNING: "record_attempt",
    MasteryState.PRACTICING: "record_attempt",
    MasteryState.RETRYING: "evaluate_attempt",
    MasteryState.MASTERED: "srs_review",
    MasteryState.NEEDS_REVIEW: "manual_review",
}

_STATE_MESSAGE: dict[str, str] = {
    MasteryState.NOT_STARTED: "Objetivo ainda não iniciado.",
    MasteryState.LEARNING: "Registre uma tentativa para começar a construir evidência.",
    MasteryState.PRACTICING: "Continue praticando: ainda não há evidência suficiente para domínio.",
    MasteryState.RETRYING: "Há uma nova tentativa pendente de avaliação.",
    MasteryState.MASTERED: "Domínio demonstrado; o item segue para revisão espaçada (SRS).",
    MasteryState.NEEDS_REVIEW: (
        "Atividade concluída, mas sem evidência suficiente — revisão manual recomendada."
    ),
}


def recommend_next_action(db: Session, *, user_language_id: str, objective_id: str) -> dict:
    """Sugere o próximo passo com base no estado atual. Só leitura — não muda
    estado. Serve tanto o frontend quanto uma IA que vá conduzir a interação:
    a IA lê a recomendação, não decide o estado."""
    progress = get_or_create_progress(db, user_language_id=user_language_id, objective_id=objective_id)
    state = progress.state

    if state == MasteryState.NEEDS_REMEDIATION:
        open_error = db.scalar(
            select(LearningError)
            .where(
                LearningError.user_language_id == user_language_id,
                LearningError.objective_id == objective_id,
                LearningError.resolved.is_(False),
            )
            .order_by(LearningError.last_seen.desc())
        )
        if open_error is None:
            return {
                "state": state,
                "action": "record_attempt",
                "message": "Sem erro pendente registrado; continue com uma nova tentativa.",
            }
        pending_remediation = db.scalar(
            select(Remediation)
            .where(Remediation.error_id == open_error.id, Remediation.next_attempt_id.is_(None))
            .order_by(Remediation.created_at.desc())
        )
        if pending_remediation is None:
            return {
                "state": state,
                "action": "choose_remediation",
                "error_id": open_error.id,
                "message": "Erro registrado sem remediação escolhida ainda.",
            }
        return {
            "state": state,
            "action": "record_retry",
            "remediation_id": pending_remediation.id,
            "message": f"Remediação '{pending_remediation.action}' pronta para nova tentativa.",
        }

    return {
        "state": state,
        "action": _STATE_ACTION.get(state, "record_attempt"),
        "message": _STATE_MESSAGE.get(state, ""),
    }
