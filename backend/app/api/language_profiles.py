"""Perfil linguístico do usuário por idioma (nível CEFR + competências)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.core.levels import SKILL_LABELS, LevelSource, Skill, level_payload
from app.models import Language, LearningGoal, User, UserLanguage, UserPreference
from app.schemas import LanguageProfileUpdate

router = APIRouter(prefix="/language-profiles", tags=["language-profiles"])

SKILL_COLUMNS = {
    Skill.VOCABULARY_GRAMMAR: "vocabulary_grammar_level",
    Skill.READING: "reading_level",
    Skill.LISTENING: "listening_level",
    Skill.WRITING: "writing_level",
    Skill.SPEAKING: "speaking_level",
}


def _profile_payload(profile: UserLanguage, language: Language, ui_prefs: dict) -> dict:
    skills = []
    for skill, column in SKILL_COLUMNS.items():
        level = getattr(profile, column)
        skills.append(
            {
                "skill": skill,
                "label": SKILL_LABELS[skill],
                "estimated_level": level,
                "level": level_payload(level) if level else None,
            }
        )

    current = profile.current_level
    return {
        "language_code": language.code,
        "language_name_pt": language.name_pt,
        "language_native_name": language.native_name,
        "current_level": current,
        "level": level_payload(current) if current else None,
        "level_source": profile.level_source or LevelSource.PENDING,
        "level_assessed_at": (
            profile.level_assessed_at.isoformat() if profile.level_assessed_at else None
        ),
        "placement_test_id": profile.placement_test_id,
        "confidence_score": profile.confidence_score,
        "skills": skills,
        "recommendations": profile.recommendations_json or [],
        "onboarding_completed": profile.onboarding_completed,
        "is_active": profile.is_active,
        "goal": ui_prefs.get("primary_goal"),
        "minutes_per_day": ui_prefs.get("minutes_per_day"),
        "priority_skills": ui_prefs.get("skills") or [],
    }


def _ui_prefs(db: Session, user: User) -> tuple[UserPreference | None, dict]:
    pref = db.scalar(select(UserPreference).where(UserPreference.user_id == user.id))
    return pref, dict(pref.ui_prefs_json or {}) if pref else {}


@router.get("")
def list_profiles(db: Session = Depends(get_db), user: User = Depends(current_user)):
    _, ui_prefs = _ui_prefs(db, user)
    rows = db.execute(
        select(UserLanguage, Language)
        .join(Language, Language.id == UserLanguage.language_id)
        .where(UserLanguage.user_id == user.id)
        .order_by(UserLanguage.is_active.desc(), UserLanguage.updated_at.desc())
    ).all()
    return {"profiles": [_profile_payload(profile, language, ui_prefs) for profile, language in rows]}


def _owned_profile(db: Session, user: User, language_code: str) -> tuple[UserLanguage, Language]:
    row = db.execute(
        select(UserLanguage, Language)
        .join(Language, Language.id == UserLanguage.language_id)
        .where(UserLanguage.user_id == user.id, Language.code == language_code)
    ).first()
    if not row:
        raise APIError(404, "language_profile_not_found", "Perfil linguístico não encontrado.")
    return row


@router.get("/{language_code}")
def get_profile(
    language_code: str, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    profile, language = _owned_profile(db, user, language_code)
    _, ui_prefs = _ui_prefs(db, user)
    return _profile_payload(profile, language, ui_prefs)


@router.patch("/{language_code}")
def update_profile(
    language_code: str,
    data: LanguageProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Ajustes manuais. Alterar o nível marca a origem como declarada.

    Níveis por competência não são editáveis: eles só têm significado quando
    vêm de uma avaliação.
    """
    profile, language = _owned_profile(db, user, language_code)
    pref, ui_prefs = _ui_prefs(db, user)

    if data.current_level is not None:
        profile.current_level = data.current_level
        profile.level_estimate = data.current_level
        profile.level_source = LevelSource.SELF_DECLARED
        profile.level_assessed_at = datetime.now(timezone.utc)
        profile.placement_test_id = None
        profile.confidence_score = None

    if data.minutes_per_day is not None:
        ui_prefs["minutes_per_day"] = data.minutes_per_day
    if data.goal is not None:
        ui_prefs["primary_goal"] = data.goal
    if data.priority_skills is not None:
        cleaned = [skill.strip() for skill in data.priority_skills if skill and skill.strip()]
        ui_prefs["skills"] = cleaned
        for old in db.scalars(
            select(LearningGoal).where(
                LearningGoal.user_language_id == profile.id,
                LearningGoal.goal_type == "skill",
            )
        ):
            db.delete(old)
        for index, skill in enumerate(cleaned):
            db.add(
                LearningGoal(
                    user_language_id=profile.id,
                    goal_type="skill",
                    description=skill,
                    priority=index + 1,
                )
            )

    if pref is None:
        pref = UserPreference(user_id=user.id, ui_prefs_json=ui_prefs)
        db.add(pref)
    else:
        pref.ui_prefs_json = ui_prefs

    db.commit()
    db.refresh(profile)
    return _profile_payload(profile, language, ui_prefs)
