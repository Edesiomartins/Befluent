"""Disparo do e-mail de correção, chamado por tarefa agendada (cron do Coolify).

Mesma autenticação da rota do e-mail diário (`daily_email.py`): chave
compartilhada em `X-Dispatch-Key`, sem cookie de sessão, porque o cron não tem
sessão. As duas rotas usam a mesma variável `DAILY_EMAIL_KEY` — é a mesma
tarefa operacional ("o BeFluent pode mandar e-mail automático"), e duas chaves
para o mesmo dono seriam duas coisas para esquecer de configurar.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import APIError
from app.services.correction_email import dispatch_correction_emails

router = APIRouter(prefix="/correction-email", tags=["correction-email"])


@router.post("/dispatch")
def dispatch(
    x_dispatch_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    expected = get_settings().daily_email_key
    if not expected:
        raise APIError(
            503,
            "dispatch_not_configured",
            "Disparo de e-mail automático não está configurado neste ambiente.",
        )
    if x_dispatch_key != expected:
        raise APIError(401, "dispatch_key_invalid", "Chave de disparo inválida.")

    result = dispatch_correction_emails(db)
    db.commit()
    return result
