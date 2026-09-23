from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.helpers import user_language
from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.models import ReviewItem, User, UserLanguage
from app.schemas import ReviewAnswer
from app.services import memory_engine, vocabulary_review

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/due")
def due(
    language_code: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Fila de revisão vencida — escopada a um único idioma.

    Com `language_code`, usa esse idioma. Sem parâmetro, usa o idioma ativo.
    Sem idioma ativo, devolve lista vazia (não mistura idiomas).
    """
    if language_code:
        ul = user_language(db, user.id, code=language_code)
    else:
        ul = db.scalar(
            select(UserLanguage).where(
                UserLanguage.user_id == user.id,
                UserLanguage.is_active.is_(True),
            )
        )
        if not ul:
            return []

    return vocabulary_review.select_due_reviews(db, ul.id)


@router.post("/{item_id}/answer")
def answer(
    item_id: str,
    data: ReviewAnswer,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Compatibilidade legada. Se houver MemorySchedule, ele é a fonte da verdade."""
    item = db.scalar(
        select(ReviewItem)
        .join(UserLanguage)
        .where(ReviewItem.id == item_id, UserLanguage.user_id == user.id)
    )
    if not item:
        raise APIError(404, "review_not_found", "Item de revisão não encontrado.")
    out = memory_engine.answer_review_item(db, item, rating=data.rating)
    db.commit()
    return {
        "id": out["id"],
        "rating": out["rating"],
        "next_review_at": out["next_review_at"],
        "interval_days": out["interval_days"],
        "suspended": out["suspended"],
        "mastery_state": out["mastery_state"],
    }
