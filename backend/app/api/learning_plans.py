"""Planos de estudo — DEPRECATED.

Substituído por `app/api/curriculum.py`: uma lista de três itens sem datas não
sustenta um cronograma que leva o aluno do nível diagnosticado até a meta. As
rotas continuam funcionando para clientes antigos e para os planos já criados;
nenhum código novo deve usá-las.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.helpers import user_language
from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.models import LearningPlan, LearningPlanItem, User, UserLanguage
from app.services.learning import create_simple_plan

router = APIRouter(prefix="/learning-plans", tags=["learning-plans"])


class Create(BaseModel):
    language_code: str


def _owned_plan(db: Session, plan_id: str, user_id: str) -> LearningPlan:
    plan = db.scalar(
        select(LearningPlan)
        .join(UserLanguage, UserLanguage.id == LearningPlan.user_language_id)
        .where(LearningPlan.id == plan_id, UserLanguage.user_id == user_id)
    )
    if not plan:
        raise APIError(404, "plan_not_found", "Plano de estudo não encontrado.")
    return plan


@router.get("")
def list_all(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [
        {"id": item.id, "version": item.version, "status": item.status}
        for item in db.scalars(
            select(LearningPlan)
            .join(UserLanguage)
            .where(UserLanguage.user_id == user.id)
        )
    ]


@router.post("")
def create(data: Create, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ul = user_language(db, user.id, data.language_code)
    plan = create_simple_plan(db, ul.id)
    db.commit()
    return {"id": plan.id, "version": plan.version, "status": plan.status}


@router.get("/{plan_id}")
def one(plan_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    plan = _owned_plan(db, plan_id, user.id)
    items = list(
        db.scalars(
            select(LearningPlanItem)
            .where(LearningPlanItem.plan_id == plan.id)
            .order_by(LearningPlanItem.position)
        )
    )
    return {
        "id": plan.id,
        "status": plan.status,
        "items": [
            {
                "id": item.id,
                "position": item.position,
                "title": item.title,
                "status": item.status,
            }
            for item in items
        ],
    }
