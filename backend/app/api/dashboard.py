from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_user
from app.models import (
    Language,
    LearningGoal,
    ReviewItem,
    StudySession,
    User,
    UserLanguage,
    UserPreference,
    VocabularyItem,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

SKILL_TO_MODE = {
    "Conversação": ("conversation", "Conversação"),
    "Compreensão auditiva": ("listening", "Compreensão auditiva"),
    "Vocabulário": ("vocabulary", "Vocabulário"),
    "Gramática": ("grammar", "Gramática"),
    "Leitura": ("reading", "Leitura"),
    "Escrita": ("writing", "Escrita"),
}


def _next_activity(has_plan: bool, reviews_count: int, skills: list[str]) -> dict:
    if not has_plan:
        return {
            "title": "Configurar seu plano",
            "description": "Defina idioma, nível e objetivo para começar.",
            "href": "/onboarding",
            "cta": "Começar onboarding",
            "kind": "onboarding",
        }
    if reviews_count > 0:
        return {
            "title": "Revisões pendentes",
            "description": f"{reviews_count} item(ns) aguardando revisão.",
            "href": "/learn/review",
            "cta": "Revisar agora",
            "kind": "review",
        }
    for skill in skills:
        mapped = SKILL_TO_MODE.get(skill)
        if mapped:
            slug, label = mapped
            return {
                "title": label,
                "description": f"Pratique {label.lower()} com foco no seu plano.",
                "href": f"/learn/{slug}",
                "cta": "Continuar",
                "kind": "practice",
            }
    return {
        "title": "Aula guiada",
        "description": "Uma sequência estruturada para avançar com clareza.",
        "href": "/learn/guided",
        "cta": "Começar",
        "kind": "practice",
    }


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
    skills: list[str] = []
    minutes = None
    primary_goal = None
    vocabulary_items = 0
    study_sessions = 0

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

        vocabulary_items = (
            db.scalar(
                select(func.count(VocabularyItem.id)).where(VocabularyItem.user_language_id == ul.id)
            )
            or 0
        )
        study_sessions = (
            db.scalar(
                select(func.count(StudySession.id)).where(StudySession.user_language_id == ul.id)
            )
            or 0
        )
    else:
        any_completed = db.scalar(
            select(UserLanguage.id).where(
                UserLanguage.user_id == user.id,
                UserLanguage.onboarding_completed.is_(True),
            )
        )
        onboarding_completed = any_completed is not None

    has_plan = bool(active_language and onboarding_completed)
    next_activity = _next_activity(has_plan, len(reviews_due), skills)

    if has_plan:
        day_items = [
            {
                "label": f"{minutes} min de estudo" if minutes else "Definir meta diária",
                "done": False,
            },
            {
                "label": primary_goal or "Definir objetivo",
                "done": bool(primary_goal),
            },
        ]
        day_items.extend({"label": f"Foco: {skill}", "done": False} for skill in skills[:3])
    else:
        day_items = [{"label": "Concluir onboarding para montar o plano do dia", "done": False}]

    day_plan = {
        "minutes_per_day": minutes,
        "goal": primary_goal,
        "skills": skills,
        "items": day_items,
    }

    return {
        "onboarding_completed": onboarding_completed,
        "active_language": active_language,
        "next_activity": next_activity,
        "day_plan": day_plan,
        "progress": {
            "vocabulary_items": vocabulary_items,
            "study_sessions": study_sessions,
            "reviews_due_count": len(reviews_due),
            "streak_days": 0,
        },
        "reviews_due_count": len(reviews_due),
        "reviews_due": reviews_due,
        "recent_activity": recent_activity,
    }
