"""Tentativas autoritativas de atividades objetivas em lições (legado).

Backend é a única autoridade. Não gera LearningEvidence / mastery.
Completion permanece independente (complete_lesson no frontend).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models import Lesson, LessonActivityAttempt, UserLanguage
from app.services.answer_feedback import build_answer_feedback


def make_activity_key(surface: str, kind: str, index: int) -> str:
    """Identidade estável: surface:kind:index (ex.: grammar:exercise:0)."""
    return f"{surface}:{kind}:{int(index)}"


def parse_activity_key(activity_key: str) -> tuple[str, str, int]:
    parts = (activity_key or "").strip().split(":")
    if len(parts) != 3:
        raise APIError(
            422,
            "invalid_activity_key",
            "activity_key deve ser surface:kind:index (ex.: grammar:exercise:0).",
        )
    surface, kind, index_raw = parts
    try:
        index = int(index_raw)
    except ValueError as exc:
        raise APIError(
            422,
            "invalid_activity_key",
            "O índice da activity_key deve ser numérico.",
        ) from exc
    if index < 0 or not surface or not kind:
        raise APIError(422, "invalid_activity_key", "activity_key inválida.")
    return surface, kind, index


def resolve_question_item(content: dict[str, Any], activity_key: str) -> dict[str, Any]:
    """Resolve o item objetivo a partir do content_json da lição (servidor)."""
    surface, kind, index = parse_activity_key(activity_key)
    if kind == "exercise":
        items = list(content.get("exercises") or [])
    elif kind == "question":
        items = list(content.get("questions") or [])
    else:
        raise APIError(
            404,
            "activity_not_found",
            f"Tipo de atividade «{kind}» não suportado nesta lição.",
        )
    if index >= len(items):
        raise APIError(404, "activity_not_found", "Atividade não encontrada na lição.")
    item = items[index]
    if not isinstance(item, dict):
        raise APIError(404, "activity_not_found", "Atividade inválida na lição.")
    if not item.get("options") or not item.get("answer"):
        raise APIError(
            422,
            "activity_not_objective",
            "Esta atividade não é uma questão objetiva avaliável.",
        )
    # surface só documenta a origem; não altera resolução.
    _ = surface
    return item


def list_attempts_for_lesson(
    db: Session, *, lesson_id: str
) -> list[LessonActivityAttempt]:
    return list(
        db.scalars(
            select(LessonActivityAttempt)
            .where(LessonActivityAttempt.lesson_id == lesson_id)
            .order_by(
                LessonActivityAttempt.activity_key,
                LessonActivityAttempt.attempt_number,
            )
        ).all()
    )


def latest_attempt(
    db: Session, *, lesson_id: str, activity_key: str
) -> LessonActivityAttempt | None:
    return db.scalar(
        select(LessonActivityAttempt)
        .where(
            LessonActivityAttempt.lesson_id == lesson_id,
            LessonActivityAttempt.activity_key == activity_key,
        )
        .order_by(LessonActivityAttempt.attempt_number.desc())
        .limit(1)
    )


def attempt_to_dict(attempt: LessonActivityAttempt) -> dict[str, Any]:
    feedback = dict(attempt.feedback_json or {})
    return {
        "attempt_id": attempt.id,
        "activity_key": attempt.activity_key,
        "attempt_number": attempt.attempt_number,
        "submitted": attempt.status == "submitted",
        "correct": attempt.is_correct,
        "selected_answer": (attempt.answer_json or {}).get("selected_answer"),
        "correct_answer": feedback.get("correct_option")
        or (attempt.question_snapshot_json or {}).get("answer"),
        "feedback": feedback.get("answer_feedback") or {
            "is_correct": attempt.is_correct,
            "selected": (attempt.answer_json or {}).get("selected_answer"),
            "correct_option": feedback.get("correct_option"),
            "why_selected": feedback.get("why_selected"),
            "why_correct": feedback.get("why_correct"),
            "remember": feedback.get("remember"),
        },
        "revealed_correct_answer": attempt.revealed_correct_answer,
        "retry": feedback.get("retry")
        or {"available": False, "strategy": "none", "activity": None},
        "retry_of_id": attempt.retry_of_id,
        "pedagogical_effect": attempt.pedagogical_effect,
        "question_snapshot": attempt.question_snapshot_json or {},
        "status": attempt.status,
        "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
    }


def _build_legacy_retry_activity(
    *,
    content: dict[str, Any],
    activity_key: str,
    current: dict[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    """Hierarquia: outro item da lição → banco curado → fallback seguro."""
    from app.services import lesson_bank

    surface, kind, index = parse_activity_key(activity_key)
    pool_key = "exercises" if kind == "exercise" else "questions"
    pool = [x for x in (content.get(pool_key) or []) if isinstance(x, dict)]
    current_prompt = str(current.get("prompt") or "")
    current_answer = str(current.get("answer") or "")

    def _usable(candidate: dict[str, Any]) -> bool:
        return bool(
            candidate.get("prompt") != current_prompt
            and candidate.get("answer")
            and candidate.get("options")
            and str(candidate.get("answer")) != current_answer
        )

    for candidate in pool:
        if _usable(candidate):
            variant = dict(candidate)
            variant["post_reveal"] = True
            variant["is_retry_variant"] = True
            return variant, "lesson_sibling"

    # Banco curado (grammar): outro exercício do mesmo idioma em outra faixa.
    if kind == "exercise":
        language_code = str(content.get("language_code") or "")
        if language_code in lesson_bank.SUPPORTED_LANGUAGES:
            band = str(content.get("band") or content.get("level_band") or "")
            for other_band in lesson_bank.ALL_BANDS:
                if band and other_band == band:
                    continue
                for candidate in lesson_bank.grammar_exercises(language_code, other_band):
                    if isinstance(candidate, dict) and _usable(candidate):
                        variant = dict(candidate)
                        variant["post_reveal"] = True
                        variant["is_retry_variant"] = True
                        return variant, "curated_bank"

    _ = surface, index
    return None, "fallback_continue"


def prepare_retry(
    db: Session,
    *,
    lesson: Lesson,
    activity_key: str,
) -> dict[str, Any]:
    """Prepara variante de retry sem reabrir a tentativa anterior.

    Não cria nova tentativa até o aluno enviar resposta (submit com request_retry).
    """
    latest = latest_attempt(db, lesson_id=lesson.id, activity_key=activity_key)
    if latest is None:
        raise APIError(409, "retry_not_available", "Não há tentativa anterior para retry.")
    if latest.is_correct:
        raise APIError(
            409,
            "retry_not_available",
            "Retry não é necessário após acerto nesta atividade.",
        )
    content = dict(lesson.content_json or {})
    current = resolve_question_item(content, activity_key)
    # Preferir snapshot da última tentativa se for variante.
    snap = latest.question_snapshot_json or {}
    if snap.get("options") and snap.get("answer"):
        current = snap
    variant, strategy = _build_legacy_retry_activity(
        content=content, activity_key=activity_key, current=current
    )
    feedback = dict(latest.feedback_json or {})
    if variant:
        feedback["retry"] = {
            "available": True,
            "strategy": strategy,
            "activity": {
                "prompt": variant.get("prompt"),
                "options": variant.get("options"),
                # NÃO enviar answer ao cliente antes do submit — só metadados UI.
                "post_reveal": True,
                "is_retry_variant": True,
                "rationale": variant.get("rationale"),
                "option_rationales": variant.get("option_rationales"),
                "remember": variant.get("remember"),
            },
        }
        feedback["retry_activity"] = variant  # servidor-only na próxima avaliação
    else:
        feedback["retry"] = {
            "available": False,
            "strategy": strategy,
            "activity": None,
            "message": (
                "Não há variante segura agora. Continue o percurso; "
                "o erro fica marcado para revisão futura."
            ),
        }
        feedback.pop("retry_activity", None)
    latest.feedback_json = feedback
    db.flush()
    return {
        **attempt_to_dict(latest),
        "retry": feedback["retry"],
    }


def submit_objective_answer(
    db: Session,
    *,
    lesson: Lesson,
    owner: UserLanguage,
    activity_key: str,
    selected_answer: str,
    request_retry: bool = False,
) -> dict[str, Any]:
    """Persiste e avalia uma tentativa. Segunda submissão da mesma geração → 409."""
    selected = (selected_answer or "").strip()
    if not selected:
        raise APIError(422, "empty_answer", "Envie uma resposta.")

    content = dict(lesson.content_json or {})
    latest = latest_attempt(db, lesson_id=lesson.id, activity_key=activity_key)

    if latest is not None and latest.status == "submitted" and not request_retry:
        raise APIError(
            409,
            "attempt_already_submitted",
            "Esta tentativa já foi enviada e não pode ser alterada.",
        )

    if request_retry:
        if latest is None:
            raise APIError(409, "retry_not_available", "Não há tentativa anterior.")
        if latest.is_correct:
            raise APIError(409, "retry_not_available", "Retry não disponível após acerto.")
        retry_meta = (latest.feedback_json or {}).get("retry") or {}
        if not retry_meta.get("available"):
            # Auto-preparar se ainda não pediu prepare_retry.
            prepared = prepare_retry(db, lesson=lesson, activity_key=activity_key)
            retry_meta = prepared.get("retry") or {}
            latest = latest_attempt(db, lesson_id=lesson.id, activity_key=activity_key)
        if not retry_meta.get("available"):
            raise APIError(
                409,
                "retry_variant_unavailable",
                "Não há variante segura para retry. Continue sem falso acerto.",
            )
        question = (latest.feedback_json or {}).get("retry_activity")
        if not isinstance(question, dict):
            raise APIError(409, "retry_variant_unavailable", "Variante de retry indisponível.")
        attempt_number = latest.attempt_number + 1
        retry_of_id = latest.id
        post_reveal = True
    else:
        question = resolve_question_item(content, activity_key)
        attempt_number = 1
        retry_of_id = None
        post_reveal = False

    options = [str(o) for o in (question.get("options") or [])]
    if selected not in options:
        raise APIError(
            422,
            "invalid_option",
            "A resposta deve ser uma das alternativas da atividade.",
        )

    correct_answer = str(question.get("answer") or "")
    is_correct = selected == correct_answer
    answer_feedback = build_answer_feedback(
        activity={
            **question,
            "canonical_answer": correct_answer,
            "correct_explanation": question.get("rationale"),
            "remember_pt": question.get("remember"),
        },
        student_response=selected,
        is_correct=is_correct,
    )

    # Após feedback, a resposta correta é revelada (acerto ou erro).
    revealed = True

    # Preparar oferta de retry se errou.
    retry_payload: dict[str, Any] = {
        "available": False,
        "strategy": "none",
        "activity": None,
    }
    retry_activity_full: dict[str, Any] | None = None
    if not is_correct:
        variant, strategy = _build_legacy_retry_activity(
            content=content, activity_key=activity_key, current=question
        )
        if variant:
            retry_activity_full = variant
            retry_payload = {
                "available": True,
                "strategy": strategy,
                "activity": {
                    "prompt": variant.get("prompt"),
                    "options": variant.get("options"),
                    "post_reveal": True,
                    "is_retry_variant": True,
                    "rationale": variant.get("rationale"),
                    "option_rationales": variant.get("option_rationales"),
                },
            }
        else:
            retry_payload = {
                "available": False,
                "strategy": strategy,
                "activity": None,
                "message": (
                    "Não há variante segura agora. Continue o percurso; "
                    "o erro fica marcado para revisão futura."
                ),
            }

    effect = "completion_only"
    if post_reveal and is_correct:
        effect = "repaired_after_feedback"
    elif is_correct and attempt_number == 1:
        effect = "correct_first_try"
    elif not is_correct and attempt_number == 1:
        effect = "incorrect_first_try"
    elif not is_correct:
        effect = "unresolved"

    feedback_store = {
        "answer_feedback": answer_feedback,
        "correct_option": correct_answer,
        "why_selected": answer_feedback.get("why_selected"),
        "why_correct": answer_feedback.get("why_correct"),
        "remember": answer_feedback.get("remember"),
        "retry": retry_payload,
        "post_reveal": post_reveal,
    }
    if retry_activity_full:
        feedback_store["retry_activity"] = retry_activity_full

    attempt = LessonActivityAttempt(
        lesson_id=lesson.id,
        user_language_id=owner.id,
        activity_key=activity_key,
        attempt_number=attempt_number,
        activity_type="multiple_choice",
        answer_json={"selected_answer": selected},
        is_correct=is_correct,
        revealed_correct_answer=revealed,
        feedback_json=feedback_store,
        question_snapshot_json={
            "prompt": question.get("prompt"),
            "options": options,
            "answer": correct_answer,
            "rationale": question.get("rationale"),
            "option_rationales": question.get("option_rationales"),
            "post_reveal": post_reveal,
            "is_retry_variant": bool(question.get("is_retry_variant")),
        },
        status="submitted",
        retry_of_id=retry_of_id,
        pedagogical_effect=effect,
    )
    try:
        with db.begin_nested():
            db.add(attempt)
            db.flush()
    except IntegrityError as exc:
        # Corrida / replay: unique (lesson, key, attempt_number).
        raise APIError(
            409,
            "attempt_already_submitted",
            "Esta tentativa já foi enviada e não pode ser alterada.",
        ) from exc

    db.flush()
    return attempt_to_dict(attempt)
