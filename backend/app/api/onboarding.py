from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.models import Language, LearningGoal, User, UserLanguage, UserPreference
from app.schemas import OnboardingIn

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _preference(db: Session, user: User) -> UserPreference:
    item = db.scalar(select(UserPreference).where(UserPreference.user_id == user.id))
    if not item:
        item = UserPreference(user_id=user.id)
        db.add(item)
        db.flush()
    return item


@router.get("/status")
def status(db: Session = Depends(get_db), user: User = Depends(current_user)):
    items = list(db.scalars(select(UserLanguage).where(UserLanguage.user_id == user.id)))
    return {
        "completed": any(x.onboarding_completed for x in items),
        "languages": [{"id": x.id, "completed": x.onboarding_completed} for x in items],
    }


@router.post("/complete")
def complete(data: OnboardingIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    lang = db.scalar(select(Language).where(Language.code == data.language_code))
    if not lang:
        raise APIError(404, "language_not_found", "Idioma não encontrado.")

    level = data.resolved_level
    goals = data.resolved_goals
    minutes = data.minutes_per_day if data.minutes_per_day is not None else 20
    skills = [s.strip() for s in data.skills if s and s.strip()]

    db.execute(update(UserLanguage).where(UserLanguage.user_id == user.id).values(is_active=False))

    ul = db.scalar(
        select(UserLanguage).where(
            UserLanguage.user_id == user.id,
            UserLanguage.language_id == lang.id,
        )
    )
    if not ul:
        ul = UserLanguage(user_id=user.id, language_id=lang.id)
        db.add(ul)
        db.flush()

    ul.level_estimate = level
    ul.onboarding_completed = True
    ul.is_active = True

    # Substitui objetivos pessoais anteriores deste idioma
    for old in list(db.scalars(select(LearningGoal).where(LearningGoal.user_language_id == ul.id))):
        db.delete(old)
    for index, goal in enumerate(goals):
        db.add(
            LearningGoal(
                user_language_id=ul.id,
                goal_type="personal",
                description=goal,
                priority=index + 1,
            )
        )
    for index, skill in enumerate(skills):
        db.add(
            LearningGoal(
                user_language_id=ul.id,
                goal_type="skill",
                description=skill,
                priority=index + 1,
            )
        )

    pref = _preference(db, user)
    pref.default_language_id = lang.id
    ui_prefs = dict(pref.ui_prefs_json or {})
    ui_prefs["minutes_per_day"] = minutes
    ui_prefs["skills"] = skills
    ui_prefs["primary_goal"] = goals[0] if goals else None
    pref.ui_prefs_json = ui_prefs

    db.commit()
    return {
        "completed": True,
        "user_language_id": ul.id,
        "language_code": lang.code,
        "perceived_level": level,
        "goal": goals[0] if goals else None,
        "minutes_per_day": minutes,
        "skills": skills,
    }
