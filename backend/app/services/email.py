import logging

import httpx

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


class EmailSendError(RuntimeError):
    """A API do Resend recusou ou não respondeu ao envio."""


def send_email(*, to: str, subject: str, html: str) -> None:
    from app.core.config import get_settings

    s = get_settings()
    if not s.resend_api_key:
        logger.warning("RESEND_API_KEY ausente — e-mail para %s não enviado.", to)
        raise EmailSendError("Serviço de e-mail não configurado.")

    try:
        response = httpx.post(
            RESEND_API_URL,
            json={"from": s.resend_from_email, "to": [to], "subject": subject, "html": html},
            headers={"Authorization": f"Bearer {s.resend_api_key}"},
            timeout=10,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Falha ao enviar e-mail via Resend para %s: %s", to, exc)
        raise EmailSendError("Não foi possível enviar o e-mail.") from exc


def password_reset_email_html(*, name: str, reset_url: str, expire_minutes: int) -> str:
    return f"""
<div style="font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px 24px; color: #1a1a2e;">
  <p style="font-size: 13px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; color: #2563eb; margin: 0 0 20px;">BeFluent</p>
  <h1 style="font-size: 20px; font-weight: 600; margin: 0 0 16px;">Redefinição de senha</h1>
  <p style="font-size: 15px; line-height: 1.6; margin: 0 0 16px;">Olá, {name}.</p>
  <p style="font-size: 15px; line-height: 1.6; margin: 0 0 24px;">
    Recebemos um pedido para redefinir a senha da sua conta BeFluent. Clique no botão abaixo para
    escolher uma nova senha. Este link expira em {expire_minutes} minutos.
  </p>
  <p style="margin: 0 0 24px;">
    <a href="{reset_url}" style="display: inline-block; background: #2563eb; color: #ffffff; text-decoration: none; font-size: 15px; font-weight: 600; padding: 12px 24px; border-radius: 8px;">
      Redefinir senha
    </a>
  </p>
  <p style="font-size: 13px; line-height: 1.6; color: #6b7280; margin: 0 0 8px;">
    Se você não pediu essa redefinição, pode ignorar este e-mail com segurança — sua senha continua a mesma.
  </p>
  <p style="font-size: 13px; line-height: 1.6; color: #6b7280; margin: 0;">
    Se o botão não funcionar, copie e cole este link no navegador:<br />
    <a href="{reset_url}" style="color: #2563eb; word-break: break-all;">{reset_url}</a>
  </p>
</div>
""".strip()
