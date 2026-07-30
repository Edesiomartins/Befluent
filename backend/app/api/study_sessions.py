from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.helpers import user_language
from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.models import StudySession, User, UserLanguage
from app.services.study_sessions import abandon_session, complete_session


class StartIn(BaseModel):
    language_code: str


router = APIRouter(prefix="/study-sessions", tags=["study-sessions"])


@router.post("")
def start(data: StartIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ul = user_language(db, user.id, data.language_code)
    item = StudySession(user_language_id=ul.id, status="active", ended_at=None)
    db.add(item)
    db.commit()
    return {"id": item.id, "status": item.status}


@router.post("/{session_id}/report")
def report(session_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = db.scalar(
        select(StudySession)
        .join(UserLanguage)
        .where(StudySession.id == session_id, UserLanguage.user_id == user.id)
    )
    if not item:
        raise APIError(404, "session_not_found", "Sessão de estudo não encontrada.")
    complete_session(db, item, summary="Sessão concluída.")
    db.commit()
    return {"id": item.id, "status": item.status, "summary": item.summary_short}


@router.post("/{session_id}/complete")
def complete(session_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = db.scalar(
        select(StudySession)
        .join(UserLanguage)
        .where(StudySession.id == session_id, UserLanguage.user_id == user.id)
    )
    if not item:
        raise APIError(404, "session_not_found", "Sessão de estudo não encontrada.")
    complete_session(db, item)
    db.commit()
    return {"id": item.id, "status": item.status}


@router.post("/{session_id}/abandon")
def abandon(session_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = db.scalar(
        select(StudySession)
        .join(UserLanguage)
        .where(StudySession.id == session_id, UserLanguage.user_id == user.id)
    )
    if not item:
        raise APIError(404, "session_not_found", "Sessão de estudo não encontrada.")
    abandon_session(db, item)
    db.commit()
    return {"id": item.id, "status": item.status}
