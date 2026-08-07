from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.helpers import user_language
from app.core.database import get_db
from app.core.deps import current_user
from app.models import PronunciationAttempt, User
from app.services.speech import assess_pronunciation


class Create(BaseModel):
    language_code: str
    target_text: str
    transcript: str | None = None


router = APIRouter(prefix="/pronunciation", tags=["pronunciation"])


@router.post("/attempts")
def create(data: Create, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Registra tentativa de prática. Sem provedor fonético, score fica nulo."""
    assessment = assess_pronunciation(data.target_text, data.transcript or "")
    ul = user_language(db, user.id, data.language_code)
    attempt = PronunciationAttempt(
        user_language_id=ul.id,
        target_text=data.target_text,
        transcript=data.transcript,
        score=assessment.get("score"),
        feedback_json={
            **(assessment.get("feedback") or {}),
            "status": assessment.get("status"),
            "provider": assessment.get("provider"),
        },
    )
    db.add(attempt)
    db.commit()
    return {
        "id": attempt.id,
        "status": assessment.get("status"),
        "score": attempt.score,
        "feedback": attempt.feedback_json,
        "provider": assessment.get("provider"),
    }
