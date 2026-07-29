from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_user
from app.models import Language, LearningGoal, User, UserLanguage
from app.services.progress import aggregate_progress

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("")
def progress(db: Session = Depends(get_db), user: User = Depends(current_user)):
    active = db.execute(
        select(UserLanguage, Language)
        .join(Language)
        .where(UserLanguage.user_id == user.id, UserLanguage.is_active.is_(True))
    ).first()
    if not active:
        active = db.execute(
            select(UserLanguage, Language)
            .join(Language)
            .where(UserLanguage.user_id == user.id, UserLanguage.onboarding_completed.is_(True))
            .order_by(UserLanguage.updated_at.desc())
        ).first()

    ul = active[0] if active else None
    lang = active[1] if active else None
    stats = aggregate_progress(db, user.id, user_language_id=ul.id if ul else None)

    skills: list[str] = []
    goal = None
    if ul:
        skills = list(
            db.scalars(
                select(LearningGoal.description).where(
                    LearningGoal.user_language_id == ul.id,
                    LearningGoal.goal_type == "skill",
                    LearningGoal.status == "active",
                ).order_by(LearningGoal.priority)
            )
        )
        goal = db.scalar(
            select(LearningGoal.description).where(
                LearningGoal.user_language_id == ul.id,
                LearningGoal.goal_type == "personal",
                LearningGoal.status == "active",
            ).order_by(LearningGoal.priority)
        )

    return {
        **stats,
        "active_language": (
            {
                "code": lang.code,
                "name_pt": lang.name_pt,
                "native_name": lang.native_name,
                "level_estimate": ul.level_estimate,
                "current_level": ul.current_level,
                "goal": goal,
                "skills": skills,
            }
            if ul and lang
            else None
        ),
    }
