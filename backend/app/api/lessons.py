"""Lições de estudo, geradas a partir do nível estimado pelo teste de nivelamento."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.helpers import user_language
from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.core.levels import SKILL_LABELS
from app.models import Lesson, LessonActivity, StudySession, User, UserLanguage
from app.prompts.library import MODE_SKILL, SUPPORTED_MODES
from app.schemas import LessonGenerateIn
from app.services.ai import get_ai_provider
from app.services.learner_context import build_context, recommended_modes


class Create(BaseModel):
    language_code: str
    title: str = "Aula guiada"
    objective: str = "Praticar comunicação"


router = APIRouter(prefix="/lessons", tags=["lessons"])


@router.get("")
def list_all(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [
        {"id": x.id, "title": x.title, "status": x.status}
        for x in db.scalars(
            select(Lesson).join(UserLanguage).where(UserLanguage.user_id == user.id)
        )
    ]


@router.get("/modes")
def modes(
    language_code: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Modos disponíveis, com os recomendados primeiro.

    A recomendação vem das competências mais fracas do teste de nivelamento;
    sem avaliação, devolve uma ordem neutra em vez de fingir personalização.
    """
    try:
        context = build_context(db, user, language_code)
    except LookupError:
        raise APIError(404, "language_not_found", "Idioma não encontrado.")

    recommended = recommended_modes(context)
    return {
        "language_code": context.language_code,
        "level": context.level,
        "level_source": context.level_source,
        "level_is_estimated": context.level_is_estimated,
        "weakest_skills": [
            {"skill": code, "label": SKILL_LABELS[code]} for code in context.weakest_skills
        ],
        "recommended_modes": recommended,
        "modes": [
            {
                "mode": mode,
                "skill": MODE_SKILL.get(mode),
                "skill_label": SKILL_LABELS.get(MODE_SKILL.get(mode, "")),
                "level": context.level_for_skill(MODE_SKILL.get(mode)),
                "recommended": mode in recommended,
            }
            for mode in SUPPORTED_MODES
        ],
    }


@router.post("/generate")
def generate(
    data: LessonGenerateIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Gera uma lição calibrada pelo nível do aluno naquela competência."""
    try:
        context = build_context(db, user, data.language_code)
    except LookupError:
        raise APIError(404, "language_not_found", "Idioma não encontrado.")

    try:
        payload = get_ai_provider().generate_lesson(data.mode, context)
    except ValueError:
        raise APIError(400, "unsupported_mode", "Modo de estudo não suportado.")

    if data.persist:
        try:
            ul = user_language(db, user.id, data.language_code)
        except APIError:
            ul = None
        if ul is not None:
            session = StudySession(
                user_language_id=ul.id,
                status="completed",
                ended_at=datetime.now(timezone.utc),
                summary_short=f"Prática: {payload.get('title', data.mode)}",
            )
            db.add(session)
            db.flush()
            lesson = Lesson(
                user_language_id=ul.id,
                study_session_id=session.id,
                title=payload.get("title", data.mode),
                objective=payload.get("objective", ""),
                content_json=payload,
                status="active",
            )
            db.add(lesson)
            db.flush()
            db.add(
                LessonActivity(
                    lesson_id=lesson.id,
                    position=1,
                    activity_type=data.mode,
                    prompt=payload.get("objective", ""),
                    payload_json=payload,
                )
            )
            db.commit()
            payload = {**payload, "lesson_id": lesson.id, "study_session_id": session.id}

    return payload


@router.post("")
def create(
    data: Create, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    ul = user_language(db, user.id, data.language_code)
    x = Lesson(
        user_language_id=ul.id,
        title=data.title,
        objective=data.objective,
        status="active",
        content_json={"reading": "Texto curto de prática."},
    )
    db.add(x)
    db.flush()
    db.add(
        LessonActivity(
            lesson_id=x.id,
            position=1,
            activity_type="reading",
            prompt="Leia e resuma o texto.",
        )
    )
    db.commit()
    return {"id": x.id, "title": x.title, "status": x.status}


@router.get("/{lesson_id}")
def one(lesson_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise APIError(404, "lesson_not_found", "Lição não encontrada.")
    owner = db.get(UserLanguage, lesson.user_language_id)
    if not owner or owner.user_id != user.id:
        raise APIError(404, "lesson_not_found", "Lição não encontrada.")
    return {
        "id": lesson.id,
        "title": lesson.title,
        "objective": lesson.objective,
        "content": lesson.content_json,
    }
