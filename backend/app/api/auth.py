import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session as DB

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.core.security import hash_password, token_hash, verify_password
from app.models import Session, User, UserPreference
from app.schemas import LoginIn, RegisterIn
from app.services.auth import create_session

router = APIRouter(prefix="/auth", tags=["auth"])


def _cookie_kwargs() -> dict:
    s = get_settings()
    kwargs: dict = {
        "secure": s.session_secure,
        "samesite": s.cookie_samesite,
        "max_age": s.session_days * 86400,
        "path": "/",
    }
    if s.cookie_domain:
        kwargs["domain"] = s.cookie_domain
    return kwargs


def _clear_cookie(response: Response, name: str) -> None:
    s = get_settings()
    kwargs: dict = {"path": "/"}
    if s.cookie_domain:
        kwargs["domain"] = s.cookie_domain
    response.delete_cookie(name, **kwargs)


def _issue_session(response: Response, db: DB, user: User) -> dict:
    token = create_session(db, user.id)
    csrf = secrets.token_urlsafe(32)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    s = get_settings()
    cookies = _cookie_kwargs()
    response.set_cookie(
        s.session_cookie_name,
        token,
        httponly=True,
        **cookies,
    )
    response.set_cookie(
        "csrf_token",
        csrf,
        httponly=False,
        **cookies,
    )
    # csrf_token também no body: frontend em outro subdomínio não lê cookie host-only.
    return {
        "user": {"id": user.id, "email": user.email, "name": user.name},
        "csrf_token": csrf,
    }


def _public_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if getattr(user, "created_at", None) else None,
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: DB = Depends(get_db)):
    """Cadastro público. Não inicia sessão — o usuário deve fazer login depois."""
    email = data.email  # já normalizado no schema
    name = data.name.strip()

    if data.password != data.password_confirmation:
        raise APIError(400, "password_mismatch", "As senhas não coincidem.")
    if len(data.password) < 8:
        raise APIError(400, "weak_password", "A senha deve ter pelo menos 8 caracteres.")

    if db.scalar(select(User).where(User.email == email)):
        raise APIError(409, "email_taken", "Já existe uma conta com este e-mail.")

    try:
        user = User(email=email, name=name, password_hash=hash_password(data.password))
        db.add(user)
        db.flush()
        db.add(UserPreference(user_id=user.id))
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise APIError(500, "register_failed", "Não foi possível criar a conta. Tente novamente.")

    payload = _public_user(user)
    # Garantir que campos sensíveis nunca vazem
    assert "password" not in payload
    assert "password_hash" not in payload
    return {"user": payload, "message": "Conta criada com sucesso."}


@router.post("/login")
def login(data: LoginIn, response: Response, db: DB = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise APIError(401, "invalid_credentials", "E-mail ou senha inválidos.")
    if not user.is_active:
        raise APIError(403, "inactive_user", "Usuário inativo.")
    return _issue_session(response, db, user)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: DB = Depends(get_db),
    user: User = Depends(current_user),
):
    token = request.cookies.get(get_settings().session_cookie_name)
    db.execute(
        update(Session)
        .where(Session.token_hash == token_hash(token))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    db.commit()
    _clear_cookie(response, get_settings().session_cookie_name)
    _clear_cookie(response, "csrf_token")
    return {"message": "Sessão encerrada com sucesso."}


@router.get("/csrf")
def get_csrf(request: Request, response: Response):
    """Devolve o token CSRF no body (necessário quando FE e API são subdomínios)."""
    existing = request.cookies.get("csrf_token")
    if existing:
        return {"csrf_token": existing}
    csrf = secrets.token_urlsafe(32)
    response.set_cookie("csrf_token", csrf, httponly=False, **_cookie_kwargs())
    return {"csrf_token": csrf}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email, "name": user.name, "is_active": user.is_active}
