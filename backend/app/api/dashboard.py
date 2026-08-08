from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_user
from app.core.levels import SKILL_LABELS, LevelSource, Skill, level_payload
from app.services.placement_engine import confidence_label
from app.core.curriculum import CurriculumStatus, DayStatus, block_skill_label, BlockStatus
from app.models import (
    Curriculum,
    CurriculumBlock,
    CurriculumDay,
    CurriculumWeek,
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


def _curriculum_path(db: Session, user_language_id: str) -> dict | None:
    """Próximo passo do cronograma ativo — path pedagógico do dia."""
    curriculum = db.scalar(
        select(Curriculum)
        .where(
            Curriculum.user_language_id == user_language_id,
            Curriculum.status == CurriculumStatus.ACTIVE,
        )
        .order_by(Curriculum.created_at.desc())
    )
    if not curriculum:
        return None
    day = db.scalar(
        select(CurriculumDay)
        .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
        .where(
            CurriculumWeek.curriculum_id == curriculum.id,
            CurriculumDay.status.notin_([DayStatus.COMPLETED, DayStatus.SKIPPED]),
        )
        .order_by(CurriculumDay.day_number)
    )
    if not day:
        return {
            "day_id": None,
            "day_number": None,
            "blocks": [],
            "next_block": None,
            "href": "/cronograma",
        }
    blocks = list(
        db.scalars(
            select(CurriculumBlock)
            .where(CurriculumBlock.day_id == day.id)
            .order_by(CurriculumBlock.position)
        )
    )
    next_block = next((b for b in blocks if b.status != BlockStatus.COMPLETED), None)
    return {
        "day_id": day.id,
        "day_number": day.day_number,
        "blocks": blocks,
        "next_block": next_block,
        "href": f"/cronograma/dia/{day.id}",
    }


def _next_activity(
    has_plan: bool,
    reviews_count: int,
    skills: list[str],
    *,
    curriculum_path: dict | None = None,
    needs_placement: bool = False,
) -> dict:
    """Porta única: caminho do dia > nivelamento > cronograma > revisão.

    Prática livre fica fora da CTA principal (está em /learn).
    """
    del skills  # mantido na assinatura por compatibilidade com chamadores
    if not has_plan:
        return {
            "title": "Configurar seu plano",
            "description": "Defina idioma, nível e objetivo para começar.",
            "href": "/onboarding",
            "cta": "Começar onboarding",
            "kind": "onboarding",
        }
    if curriculum_path and curriculum_path.get("next_block"):
        block = curriculum_path["next_block"]
        label = block_skill_label(block.skill)
        return {
            "title": f"Dia {curriculum_path['day_number']} · {label}",
            "description": "Continue a sequência do dia: ativar → estruturar → compreender → produzir → consolidar.",
            "href": curriculum_path["href"],
            "cta": "Continuar caminho",
            "kind": "curriculum",
        }
    if curriculum_path and curriculum_path.get("day_id") is None:
        return {
            "title": "Cronograma concluído",
            "description": "Você terminou o caminho atual. Revise ou gere um novo cronograma.",
            "href": "/cronograma",
            "cta": "Ver cronograma",
            "kind": "curriculum",
        }
    if needs_placement:
        return {
            "title": "Descubra seu nível",
            "description": "Faça o teste para gerar seu caminho diário por competência.",
            "href": "/placement-test",
            "cta": "Fazer teste de nível",
            "kind": "placement",
        }
    if curriculum_path is None:
        return {
            "title": "Montar seu cronograma",
            "description": "Gere um caminho diário em sequência lógica a partir do seu nível.",
            "href": "/cronograma",
            "cta": "Ver cronograma",
            "kind": "curriculum",
        }
    if reviews_count > 0:
        return {
            "title": "Revisões pendentes",
            "description": f"{reviews_count} item(ns) aguardando revisão.",
            "href": "/learn/review",
            "cta": "Revisar agora",
            "kind": "review",
        }
    return {
        "title": "Continuar seu caminho",
        "description": "Abra o dia de hoje e siga a sequência do cronograma.",
        "href": curriculum_path.get("href") or "/cronograma",
        "cta": "Abrir caminho",
        "kind": "curriculum",
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
    curriculum_path = (
        _curriculum_path(db, active_language["user_language_id"]) if active_language else None
    )
    needs_placement = bool(
        active_language
        and active_language.get("level", {}).get("needs_placement_test")
    )
    next_activity = _next_activity(
        has_plan,
        len(reviews_due),
        skills,
        curriculum_path=curriculum_path,
        needs_placement=needs_placement,
    )
    studied_today = (stats.get("minutes_today") or 0) > 0
    minutes_done = bool(minutes) and (stats.get("minutes_today") or 0) >= int(minutes)

    if has_plan and curriculum_path and curriculum_path.get("blocks"):
        day_items = [
            {
                "label": f"Dia {curriculum_path['day_number']} do cronograma",
                "done": curriculum_path.get("next_block") is None,
            }
        ]
        day_items.extend(
            {
                "label": f"{block_skill_label(block.skill)} · {block.topic}",
                "done": block.status == BlockStatus.COMPLETED,
            }
            for block in curriculum_path["blocks"]
        )
    elif has_plan:
        day_items = [
            {
                "label": f"{minutes} min de estudo" if minutes else "Definir meta diária",
                "done": minutes_done if minutes else False,
            },
            {
                "label": primary_goal or "Definir objetivo",
                "done": bool(primary_goal),
            },
            {
                "label": "Montar cronograma estruturado",
                "done": False,
            },
        ]
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
        "source": "curriculum" if curriculum_path and curriculum_path.get("blocks") else "prefs",
        "curriculum_day_href": curriculum_path["href"] if curriculum_path else None,
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
