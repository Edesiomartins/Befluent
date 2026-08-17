"""TTS Lab — endpoints isolados para comparar modelos de TTS da OpenRouter.

Não é usado por nenhuma tela de aluno. Acesso restrito por allow-list de
e-mail (`TTS_LAB_ALLOWED_EMAILS`) porque o projeto ainda não tem papel de
admin — ver `docs/TTS_LAB.md` para a limitação e como desativar a
ferramenta (basta limpar a variável de ambiente).
"""

from __future__ import annotations

import base64

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.deps import current_user
from app.core.errors import APIError
from app.models import User
from app.services import tts_lab as service

router = APIRouter(prefix="/tts-lab", tags=["tts-lab"])


def require_tts_lab_access(user: User = Depends(current_user)) -> User:
    settings = get_settings()
    allowed = {
        email.strip().lower()
        for email in settings.tts_lab_allowed_emails.split(",")
        if email.strip()
    }
    if user.email.lower() not in allowed:
        raise APIError(403, "tts_lab_forbidden", "Acesso não autorizado ao TTS Lab.")
    return user


@router.get("/models")
def get_models(user: User = Depends(require_tts_lab_access)):
    return {"models": service.list_models()}


class TTSLabGenerateIn(BaseModel):
    model: str
    text: str = Field(min_length=1, max_length=2000)
    speed: float | None = Field(default=None, ge=0.5, le=2.0)
    voice: str | None = None


@router.post("/generate")
def generate(data: TTSLabGenerateIn, user: User = Depends(require_tts_lab_access)):
    try:
        result = service.generate(data.model, data.text, data.speed, data.voice)
    except service.TTSLabError as exc:
        raise APIError(exc.status_code, exc.code, exc.message, exc.retryable) from exc

    return {
        "model": result.model,
        "audio_base64": base64.b64encode(result.audio_bytes).decode("ascii"),
        "content_type": result.content_type,
        "latency_ms": result.latency_ms,
        "audio_size_bytes": result.audio_size_bytes,
        "free_model": result.free_model,
        "cost_available": result.cost_available,
        "estimated_cost": result.estimated_cost,
    }
