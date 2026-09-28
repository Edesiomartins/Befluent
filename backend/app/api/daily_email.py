"""Disparo do e-mail diário, chamado por tarefa agendada (cron do Coolify).

Esta rota não usa cookie de sessão: o cron não tem sessão. Ela é autenticada
por chave compartilhada no cabeçalho `X-Dispatch-Key`. Chave em query string
vazaria em log de acesso, então não é aceita.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import APIError
from app.services.daily_email import dispatch_daily_emails

router = APIRouter(prefix="/daily-email", tags=["daily-email"])


@router.post("/dispatch")
def dispatch(
    x_dispatch_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    expected = get_settings().daily_email_key
    if not expected:
        # Sem chave no ambiente a porta fica fechada, nunca aberta.
        raise APIError(
            503,
            "dispatch_not_configured",
            "Disparo do e-mail diário não está configurado neste ambiente.",
        )
    if x_dispatch_key != expected:
        raise APIError(401, "dispatch_key_invalid", "Chave de disparo inválida.")

    result = dispatch_daily_emails(db)
    db.commit()
    return result
