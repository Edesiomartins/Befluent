from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LearningPlan, LearningPlanItem


def create_simple_plan(db: Session, user_language_id: str) -> LearningPlan:
    """Cria um plano inicial determinístico, fácil de substituir por IA depois."""
    current = db.scalar(
        select(LearningPlan).where(
            LearningPlan.user_language_id == user_language_id,
            LearningPlan.status == "active",
        )
    )
    if current:
        return current

    plan = LearningPlan(user_language_id=user_language_id, generated_from="simple")
    db.add(plan)
    db.flush()
    for position, (activity_type, title) in enumerate(
        [
            ("lesson", "Aula inicial"),
            ("conversation", "Conversa guiada"),
            ("review", "Revisão"),
        ],
        start=1,
    ):
        db.add(
            LearningPlanItem(
                plan_id=plan.id,
                position=position,
                activity_type=activity_type,
                title=title,
            )
        )
    return plan
