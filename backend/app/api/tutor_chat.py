"""Chat de apoio livre — tira dúvidas a qualquer momento, fora de uma lição.

Sem persistência em banco: o histórico vive só no cliente enquanto o widget
está aberto. Diferente de `conversations.py` (conversa roteirizada, ligada a
uma `StudySession` e ao progresso), este endpoint não afeta streak nem
sessões de estudo — é apoio, não prática avaliada.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.models import User
from app.services.ai import get_ai_provider
from app.services.learner_context import build_context

HISTORY_LIMIT = 10


class HistoryMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class TutorChatIn(BaseModel):
    language_code: str
    text: str = Field(min_length=1, max_length=2000)
    history: list[HistoryMessageIn] = Field(default_factory=list, max_length=30)


router = APIRouter(prefix="/tutor-chat", tags=["tutor-chat"])


@router.post("")
def tutor_chat(
    data: TutorChatIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    try:
        context = build_context(db, user, data.language_code)
    except LookupError:
        raise APIError(404, "language_not_found", "Idioma não encontrado.")

    history = [
        {"role": message.role, "content": message.content}
        for message in data.history[-HISTORY_LIMIT:]
    ]
    from app.services.language_roles import checked_tutor_turn

    result, rejected = checked_tutor_turn(
        get_ai_provider(),
        data.text,
        context,
        history,
        target_language=data.language_code,
        native_language=user.native_language,
    )
    if rejected:
        raise APIError(
            422,
            "assistant_language_rejected",
            "A resposta do tutor não estava no par de idiomas desta conversa.",
        )
    return result
