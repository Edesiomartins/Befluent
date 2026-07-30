"""Lições de estudo, geradas a partir do nível estimado pelo teste de nivelamento."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
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
from app.services.content_repository import fetch_approved_unit, record_lesson_usage
from app.services.learner_context import build_context, recommended_modes
from app.services.progress import aggregate_progress
from app.services.study_sessions import abandon_session, complete_session


class Create(BaseModel):
    language_code: str
    title: str = "Aula guiada"
    objective: str = "Praticar comunicação"


class SessionActionIn(BaseModel):
    summary: str | None = Field(default=None, max_length=500)


router = APIRouter(prefix="/lessons", tags=["lessons"])


def _owned_lesson(db: Session, user: User, lesson_id: str) -> tuple[Lesson, UserLanguage]:
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise APIError(404, "lesson_not_found", "Lição não encontrada.")
    owner = db.get(UserLanguage, lesson.user_language_id)
    if not owner or owner.user_id != user.id:
        raise APIError(404, "lesson_not_found", "Lição não encontrada.")
    return lesson, owner


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
    """Modos disponíveis, com os recomendados primeiro."""
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

    skill = MODE_SKILL.get(data.mode)
    curated_unit = None
    try:
        ul_preview = user_language(db, user.id, data.language_code)
    except APIError:
        ul_preview = None
    if ul_preview is not None and skill:
        curated_unit = fetch_approved_unit(
            db,
            language_id=ul_preview.language_id,
            level=context.level_for_skill(skill),
            skill=skill,
            mode=data.mode,
        )

    if curated_unit is not None:
        unit_payload = dict(curated_unit.payload_json or {})
        payload = {
            **unit_payload,
            "mode": data.mode,
            "title": curated_unit.title or unit_payload.get("title", data.mode),
            "objective": unit_payload.get("objective", curated_unit.topic or ""),
            "language_code": data.language_code,
            "level": curated_unit.cefr_level,
            "content_origin": "curated_library",
            "provider": "curated_library",
        }
        if curated_unit.attribution_text:
            payload["attribution_text"] = curated_unit.attribution_text
    else:
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
                status="active",
                ended_at=None,
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
            if curated_unit is not None:
                record_lesson_usage(
                    db,
                    lesson_id=lesson.id,
                    content_unit_id=curated_unit.id,
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
    lesson, _ = _owned_lesson(db, user, lesson_id)
    return {
        "id": lesson.id,
        "title": lesson.title,
        "objective": lesson.objective,
        "content": lesson.content_json,
    }


@router.post("/{lesson_id}/complete")
def complete_lesson(
    lesson_id: str,
    data: SessionActionIn | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    lesson, owner = _owned_lesson(db, user, lesson_id)
    if lesson.status == "completed":
        raise APIError(409, "lesson_already_completed", "Esta lição já foi concluída.")

    summary = data.summary if data else None
    if lesson.study_session_id:
        session = db.get(StudySession, lesson.study_session_id)
        if session:
            complete_session(db, session, summary=summary)

    lesson.status = "completed"
    db.commit()

    progress = aggregate_progress(db, user.id, user_language_id=owner.id)
    return {"lesson_id": lesson.id, "status": lesson.status, "progress": progress}


@router.post("/{lesson_id}/abandon")
def abandon_lesson(
    lesson_id: str,
    data: SessionActionIn | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    lesson, owner = _owned_lesson(db, user, lesson_id)
    if lesson.status == "completed":
        raise APIError(409, "lesson_already_completed", "Esta lição já foi concluída.")
    if lesson.status == "abandoned":
        return {"lesson_id": lesson.id, "status": lesson.status}

    summary = data.summary if data else None
    if lesson.study_session_id:
        session = db.get(StudySession, lesson.study_session_id)
        if session and session.status == "active":
            abandon_session(db, session, summary=summary)

    lesson.status = "abandoned"
    db.commit()

    progress = aggregate_progress(db, user.id, user_language_id=owner.id)
    return {"lesson_id": lesson.id, "status": lesson.status, "progress": progress}
