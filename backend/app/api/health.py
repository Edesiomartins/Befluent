from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "service": "befluent-backend", "database": "ok"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "service": "befluent-backend",
                "database": "unavailable",
            },
        )


@router.get("/health/ai")
def health_ai():
    """Torna visível de fora se a IA está de fato ativa — sem isto, um
    OPENROUTER_API_KEY inválido ou um modelo mal configurado falha em
    silêncio: o app continua funcionando no MockAIProvider e nada no ar
    denuncia isso. Nunca expõe a chave, só se ela e o modelo estão presentes.
    """
    s = get_settings()
    models = [m for m in (s.openrouter_model, s.openrouter_fallback_model) if m]
    openrouter_configured = bool(s.openrouter_api_key and models)
    active_provider = "mock" if s.ai_mock_mode else "openrouter"
    return {
        "ai_mock_mode": s.ai_mock_mode,
        "active_provider": active_provider,
        "openrouter_configured": openrouter_configured,
        "openrouter_model": s.openrouter_model or None,
        "openrouter_fallback_model": s.openrouter_fallback_model or None,
    }
