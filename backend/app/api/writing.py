"""Produção escrita das lições, com correção real (IA ou heurística)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.helpers import user_language
from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.models import User, WritingSubmission
from app.prompts.library import MODE_SKILL
from app.schemas import LessonWritingIn
from app.services.learner_context import build_context
from app.services.writing_evaluation import evaluate_lesson_writing

router = APIRouter(prefix="/writing", tags=["writing"])


@router.post("")
def create(
    data: LessonWritingIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Corrige o texto e guarda a devolutiva.

    O nível-alvo vem do perfil do aluno quando não é informado — a correção
    precisa cobrar o que o nível dele comporta, não um padrão fixo.
    """
    if data.min_words > data.max_words:
        raise APIError(
            400, "invalid_word_range", "A faixa de palavras informada é inválida."
        )

    try:
        context = build_context(db, user, data.language_code)
    except LookupError:
        raise APIError(404, "language_not_found", "Idioma não encontrado.")

    target_level = data.target_level or context.level_for_skill(MODE_SKILL["writing"])

    result = evaluate_lesson_writing(
        data.content_text,
        data.language_code,
        target_level,
        data.min_words,
        data.max_words,
    )

    submission = None
    try:
        ul = user_language(db, user.id, data.language_code)
    except APIError:
        ul = None
    if ul is not None:
        submission = WritingSubmission(
            user_language_id=ul.id,
            prompt=data.prompt,
            content_text=data.content_text,
            score=result.get("normalized_score"),
            feedback_json=result,
        )
        db.add(submission)
        db.commit()

    return {
        **result,
        "id": submission.id if submission else None,
        "score": result.get("normalized_score"),
    }
