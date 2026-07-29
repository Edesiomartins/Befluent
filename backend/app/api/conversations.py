"""Conversação com o tutor, calibrada pelo nível do aluno.

Antes, o turno era gerado por um prompt genérico (“responda como tutor de {code}”)
que ignorava o resultado do teste de nivelamento. Agora usa o prompt de
conversação simulada da biblioteca, com o nível de fala do aluno no contexto.
"""

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

#: Turnos anteriores enviados ao modelo. Suficiente para manter o fio da conversa
#: sem inflar o custo de cada requisição.
HISTORY_LIMIT = 10


class StartIn(BaseModel):
    language_code: str
    topic: str = "Conversa livre"
    study_session_id: str | None = None
    #: Fala de abertura já exibida ao aluno pela lição. Persistir aqui evita que
    #: o tutor repita essa mesma fala no primeiro turno e mantém o histórico
    #: salvo igual ao que o aluno viu na tela.
    opening: str | None = Field(default=None, max_length=2000)


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


router = APIRouter(prefix="/conversations", tags=["conversations"])


def _owned_conversation(db: Session, user: User, conversation_id: str) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise APIError(404, "conversation_not_found", "Conversa não encontrada.")
    profile = db.get(UserLanguage, conversation.user_language_id)
    if not profile or profile.user_id != user.id:
        raise APIError(404, "conversation_not_found", "Conversa não encontrada.")
    return conversation


@router.post("")
def start(data: StartIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ul = user_language(db, user.id, data.language_code)
    session_id = data.study_session_id
    if not session_id:
        session = StudySession(user_language_id=ul.id)
        db.add(session)
        db.flush()
        session_id = session.id
    item = Conversation(
        study_session_id=session_id, user_language_id=ul.id, topic=data.topic
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
