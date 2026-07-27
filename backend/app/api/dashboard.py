from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_user
from app.models import Language, LearningGoal, ReviewItem, StudySession, User, UserLanguage, UserPreference

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(db: Session = Depends(get_db), user: User = Depends(current_user)):
    pref = db.scalar(select(UserPreference).where(UserPreference.user_id == user.id))
    ui_prefs = dict(pref.ui_prefs_json or {}) if pref else {}

    active_row = db.execute(
        select(UserLanguage, Language)
        .join(Language)
        .where(UserLanguage.user_id == user.id, UserLanguage.is_active.is_(True))
    ).first()

    if not active_row:
        # Fallback: idioma com onboarding concluído mais recente
        active_row = db.execute(
            select(UserLanguage, Language)
            .join(Language)
            .where(UserLanguage.user_id == user.id, UserLanguage.onboarding_completed.is_(True))
            .order_by(UserLanguage.updated_at.desc())
        ).first()

    active_language = None
    reviews_due: list[dict] = []
    recent_activity: list[dict] = []
    onboarding_completed = False

    if active_row:
        ul, lang = active_row
        onboarding_completed = bool(ul.onboarding_completed)
        goals = list(
            db.scalars(
                select(LearningGoal)
                .where(
                    LearningGoal.user_language_id == ul.id,
                    LearningGoal.goal_type == "personal",
                    LearningGoal.status == "active",
                )
                .order_by(LearningGoal.priority)
            )
        )
        skill_goals = list(
            db.scalars(
                select(LearningGoal)
                .where(
                    LearningGoal.user_language_id == ul.id,
                    LearningGoal.goal_type == "skill",
                    LearningGoal.status == "active",
                )
                .order_by(LearningGoal.priority)
            )
        )
        skills = [g.description for g in skill_goals] or list(ui_prefs.get("skills") or [])
        primary_goal = goals[0].description if goals else ui_prefs.get("primary_goal")
        minutes = ui_prefs.get("minutes_per_day")

        active_language = {
            "code": lang.code,
            "name_pt": lang.name_pt,
            "native_name": lang.native_name,
            "level_estimate": ul.level_estimate,
            "goal": primary_goal,
            "minutes_per_day": minutes,
            "skills": skills,
            "onboarding_completed": ul.onboarding_completed,
            "user_language_id": ul.id,
        }

        now = datetime.now(timezone.utc)
        due_items = list(
            db.scalars(
                select(ReviewItem).where(
                    ReviewItem.user_language_id == ul.id,
                    ReviewItem.suspended.is_(False),
                    ReviewItem.next_review_at <= now,
                )
            )
        )
        reviews_due = [
            {
                "id": item.id,
                "item_type": item.item_type,
                "reference_id": item.reference_id,
                "payload": item.payload_json,
                "next_review_at": item.next_review_at.isoformat() if item.next_review_at else None,
            }
            for item in due_items
        ]

        sessions = list(
            db.scalars(
                select(StudySession)
                .where(StudySession.user_language_id == ul.id)
                .order_by(StudySession.started_at.desc())
                .limit(5)
            )
        )
        recent_activity = [
            {
                "id": session.id,
                "status": session.status,
                "summary": session.summary_short,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            }
            for session in sessions
        ]
    else:
        any_completed = db.scalar(
            select(UserLanguage.id).where(
                UserLanguage.user_id == user.id,
                UserLanguage.onboarding_completed.is_(True),
            )
        )
        onboarding_completed = any_completed is not None

    return {
        "onboarding_completed": onboarding_completed,
        "active_language": active_language,
        "reviews_due_count": len(reviews_due),
        "reviews_due": reviews_due,
        "recent_activity": recent_activity,
    }
