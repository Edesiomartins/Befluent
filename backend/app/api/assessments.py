from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.helpers import user_language
from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.models import Assessment, AssessmentAttempt, AssessmentQuestion, User, UserLanguage

router = APIRouter(prefix="/assessments", tags=["assessments"])


class Start(BaseModel):
    language_code: str


class Answer(BaseModel):
    question_id: str
    response: dict


def _owned_assessment(db: Session, assessment_id: str, user_id: str) -> Assessment:
    item = db.scalar(
        select(Assessment)
        .join(UserLanguage, UserLanguage.id == Assessment.user_language_id)
        .where(Assessment.id == assessment_id, UserLanguage.user_id == user_id)
    )
    if not item:
        raise APIError(404, "assessment_not_found", "Avaliação não encontrada.")
    return item


@router.post("/diagnostic")
def start(data: Start, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ul = user_language(db, user.id, data.language_code)
    assessment = Assessment(user_language_id=ul.id, status="active")
    db.add(assessment)
    db.flush()
    for i, (skill, prompt) in enumerate(
        [
            ("vocabulary", "Apresente-se no idioma estudado."),
            ("grammar", "Escreva uma frase no passado."),
            ("reading", "Explique uma rotina diária."),
        ],
        1,
    ):
        db.add(
            AssessmentQuestion(
                assessment_id=assessment.id,
                position=i,
                skill=skill,
                prompt=prompt,
            )
        )
    db.commit()
    return {"id": assessment.id, "status": assessment.status}


@router.get("/{assessment_id}")
def get_one(assessment_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    assessment = _owned_assessment(db, assessment_id, user.id)
    questions = list(
        db.scalars(
            select(AssessmentQuestion)
            .where(AssessmentQuestion.assessment_id == assessment.id)
            .order_by(AssessmentQuestion.position)
        )
    )
    return {
        "id": assessment.id,
        "status": assessment.status,
        "questions": [
            {
                "id": question.id,
                "position": question.position,
                "skill": question.skill,
                "prompt": question.prompt,
            }
            for question in questions
        ],
    }


@router.post("/{assessment_id}/answer")
def answer(
    assessment_id: str,
    data: Answer,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    _owned_assessment(db, assessment_id, user.id)
    item = AssessmentAttempt(
        assessment_id=assessment_id,
        question_id=data.question_id,
        response_json=data.response,
        result_json={"accepted": True},
    )
    db.add(item)
    db.commit()
    return {"attempt_id": item.id, "accepted": True}


@router.post("/{assessment_id}/complete")
def complete(
    assessment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    assessment = _owned_assessment(db, assessment_id, user.id)
    assessment.status = "completed"
    assessment.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "id": assessment.id,
        "status": "completed",
        "level_estimate": "A1",
        "provider": "stub",
        "message": "Diagnóstico legado simulado. Prefira o teste de nivelamento.",
    }
