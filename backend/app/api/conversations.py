"""Conversação com o tutor, calibrada pelo nível do aluno."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.helpers import user_language
from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.models import (
    Conversation,
    ConversationMessage,
    Language,
    StudySession,
    User,
    UserLanguage,
)
from app.services.ai import get_ai_provider
from app.services.learner_context import build_context
from app.services.progress import aggregate_progress
from app.services.study_sessions import (
    abandon_session,
    complete_session,
    validate_study_session_for_user,
)

HISTORY_LIMIT = 10


class StartIn(BaseModel):
    language_code: str
    topic: str = "Conversa livre"
    study_session_id: str | None = None
    opening: str | None = Field(default=None, max_length=2000)


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class SessionActionIn(BaseModel):
    summary: str | None = Field(default=None, max_length=500)


router = APIRouter(prefix="/conversations", tags=["conversations"])


def _owned_conversation(db: Session, user: User, conversation_id: str) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise APIError(404, "conversation_not_found", "Conversa não encontrada.")
    profile = db.get(UserLanguage, conversation.user_language_id)
    if not profile or profile.user_id != user.id:
        raise APIError(404, "conversation_not_found", "Conversa não encontrada.")
    return conversation


def _ensure_conversation_active(conversation: Conversation) -> None:
    if conversation.status in ("completed", "abandoned"):
        raise APIError(
            409,
            "conversation_closed",
            "Esta conversa já foi encerrada.",
        )


@router.post("")
def start(data: StartIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ul = user_language(db, user.id, data.language_code)
    session_id = data.study_session_id
    if session_id:
        validate_study_session_for_user(db, user, session_id, ul.id, require_active=True)
    else:
        session = StudySession(user_language_id=ul.id, status="active", ended_at=None)
        db.add(session)
        db.flush()
        session_id = session.id

    item = Conversation(
        study_session_id=session_id,
        user_language_id=ul.id,
        topic=data.topic,
        status="active",
    )
    db.add(item)
    db.flush()
    if data.opening:
        db.add(
            ConversationMessage(
                conversation_id=item.id, role="assistant", content_text=data.opening
            )
        )
    db.commit()

    context = build_context(db, user, data.language_code)
    return {
        "id": item.id,
        "topic": item.topic,
        "study_session_id": session_id,
        "level": context.level_for_skill("speaking"),
        "level_source": context.level_source,
        "level_is_estimated": context.level_is_estimated,
    }


@router.post("/{conversation_id}/messages")
def message(
    conversation_id: str,
    data: MessageIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    conversation = _owned_conversation(db, user, conversation_id)
    _ensure_conversation_active(conversation)

    language = db.scalar(
        select(Language)
        .join(UserLanguage, UserLanguage.language_id == Language.id)
        .where(UserLanguage.id == conversation.user_language_id)
    )
    if not language:
        raise APIError(404, "language_not_found", "Idioma não encontrado.")

    history = [
        {"role": row.role, "content": row.content_text}
        for row in db.scalars(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation.id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(HISTORY_LIMIT)
        )
    ][::-1]

    db.add(
        ConversationMessage(
            conversation_id=conversation.id, role="user", content_text=data.text
        )
    )

    context = build_context(db, user, language.code)
    result = get_ai_provider().conversation_turn(data.text, context, history)

    reply = ConversationMessage(
        conversation_id=conversation.id,
        role="assistant",
        content_text=result["reply"],
        corrections_json=result["corrections"],
    )
    db.add(reply)
    db.commit()
    return {"message_id": reply.id, **result}


@router.post("/{conversation_id}/complete")
def complete_conversation(
    conversation_id: str,
    data: SessionActionIn | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    conversation = _owned_conversation(db, user, conversation_id)
    if conversation.status == "completed":
        progress = aggregate_progress(db, user.id, user_language_id=conversation.user_language_id)
        return {"id": conversation.id, "status": conversation.status, "progress": progress}

    summary = data.summary if data else None
    session = db.get(StudySession, conversation.study_session_id)
    if session and session.status == "active":
        complete_session(db, session, summary=summary or f"Conversa: {conversation.topic}")

    from datetime import datetime, timezone

    conversation.status = "completed"
    conversation.ended_at = datetime.now(timezone.utc)
    db.commit()

    progress = aggregate_progress(db, user.id, user_language_id=conversation.user_language_id)
    return {"id": conversation.id, "status": conversation.status, "progress": progress}


@router.post("/{conversation_id}/abandon")
def abandon_conversation(
    conversation_id: str,
    data: SessionActionIn | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    conversation = _owned_conversation(db, user, conversation_id)
    if conversation.status == "completed":
        raise APIError(409, "conversation_already_completed", "Esta conversa já foi concluída.")
    if conversation.status == "abandoned":
        progress = aggregate_progress(db, user.id, user_language_id=conversation.user_language_id)
        return {"id": conversation.id, "status": conversation.status, "progress": progress}

    summary = data.summary if data else None
    session = db.get(StudySession, conversation.study_session_id)
    if session and session.status == "active":
        abandon_session(db, session, summary=summary)

    from datetime import datetime, timezone

    conversation.status = "abandoned"
    conversation.ended_at = datetime.now(timezone.utc)
    db.commit()

    progress = aggregate_progress(db, user.id, user_language_id=conversation.user_language_id)
    return {"id": conversation.id, "status": conversation.status, "progress": progress}


@router.get("/{conversation_id}/messages")
def messages(
    conversation_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    conversation = _owned_conversation(db, user, conversation_id)
    return [
        {
            "id": row.id,
            "role": row.role,
            "content": row.content_text,
            "corrections": row.corrections_json,
        }
        for row in db.scalars(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation.id)
            .order_by(ConversationMessage.created_at)
        )
    ]
