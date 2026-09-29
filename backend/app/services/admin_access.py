"""Acesso da área de administração. A lista vem do ambiente e começa vazia."""

from app.core.config import get_settings
from app.models import User


def admin_email_set() -> set[str]:
    return {
        email.strip().casefold()
        for email in get_settings().admin_emails.split(",")
        if email.strip()
    }


def is_admin(user: User) -> bool:
    allowed = admin_email_set()
    return bool(allowed) and user.email.casefold() in allowed
