from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_user
from app.core.levels import SKILL_LABELS, LevelSource, Skill, level_payload
from app.services.placement_engine import confidence_label
from app.models import (
    Language,
    LearningGoal,
    ReviewItem,
    StudySession,
    User,
    UserLanguage,
    UserPreference,
)
from app.services.progress import aggregate_progress

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

SKILL_TO_MODE = {
    "Conversação": ("conversation", "Conversação"),
    "Compreensão auditiva": ("listening", "Compreensão auditiva"),
    "Vocabulário": ("vocabulary", "Vocabulário"),
    "Gramática": ("grammar", "Gramática"),
    "Leitura": ("reading", "Leitura"),
    "Escrita": ("writing", "Escrita"),
}


def _level_block(ul: UserLanguage) -> dict:
    """Bloco de nível do dashboard. Nunca inventa nível: pendente fica None."""
    source = ul.level_source or LevelSource.PENDING
    current = ul.current_level
    skills = [
        {
            "skill": skill,
            "label": SKILL_LABELS[skill],
            "estimated_level": getattr(ul, column),
        }
        for skill, column in (
            (Skill.VOCABULARY_GRAMMAR, "vocabulary_grammar_level"),
            (Skill.READING, "reading_level"),
            (Skill.LISTENING, "listening_level"),
            (Skill.WRITING, "writing_level"),
            (Skill.SPEAKING, "speaking_level"),
        )
    ]
    return {
        "current_level": current,
        "details": level_payload(current) if current else None,
        "source": source,
        "from_test": source == LevelSource.PLACEMENT_TEST,
        "assessed_at": ul.level_assessed_at.isoformat() if ul.level_assessed_at else None,
        "confidence_score": ul.confidence_score,
        "confidence_label": (
            confidence_label(ul.confidence_score) if ul.confidence_score is not None else None
        ),
        "placement_test_id": ul.placement_test_id,
        "skills": skills,
        "recommendations": ul.recommendations_json or [],
        "needs_placement_test": current is None or source == LevelSource.PENDING,
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
    onboarding_completed = False
    skills: list[str] = []
    minutes = None
    primary_goal = None
    stats = aggregate_progress(db, user.id)

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
        stats = aggregate_progress(db, user.id, user_language_id=ul.id)

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
            "level": _level_block(ul),
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
    studied_today = (stats.get("minutes_today") or 0) > 0
    minutes_done = bool(minutes) and (stats.get("minutes_today") or 0) >= int(minutes)

    if has_plan:
        day_items = [
            {
                "label": f"{minutes} min de estudo" if minutes else "Definir meta diária",
                "done": minutes_done if minutes else False,
            },
            {
                "label": primary_goal or "Definir objetivo",
                "done": bool(primary_goal),
            },
        ]
        # Marca foco como feito se houve qualquer estudo hoje (proxy simples e honesto).
        day_items.extend(
            {"label": f"Foco: {skill}", "done": studied_today} for skill in skills[:3]
        )
    else:
        day_items = [{"label": "Concluir onboarding para montar o plano do dia", "done": False}]

    day_plan = {
        "minutes_per_day": minutes,
        "goal": primary_goal,
        "skills": skills,
        "items": day_items,
        "minutes_today": stats.get("minutes_today") or 0,
    }

    return {
        "onboarding_completed": onboarding_completed,
        "active_language": active_language,
        "next_activity": next_activity,
        "day_plan": day_plan,
        "progress": {
            "vocabulary_items": stats["vocabulary_items"],
            "study_sessions": stats["study_sessions"],
            "reviews_due_count": len(reviews_due),
            "streak_days": stats["streak_days"],
            "total_minutes": stats["total_minutes"],
            "minutes_today": stats["minutes_today"],
            "total_minutes_label": stats["total_minutes_label"],
        },
        "reviews_due_count": len(reviews_due),
        "reviews_due": reviews_due,
        "recent_activity": stats["recent_activity"][:5],
    }
