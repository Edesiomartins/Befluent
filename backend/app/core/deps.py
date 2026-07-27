from datetime import datetime, timezone
from fastapi import Cookie, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session as DB
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import APIError
from app.core.security import token_hash
from app.models import Session, User
def current_user(db:DB=Depends(get_db), token:str|None=Cookie(None, alias=get_settings().session_cookie_name)):
    if not token: raise APIError(401,"not_authenticated","Autenticação necessária.")
    session=db.scalar(select(Session).where(Session.token_hash==token_hash(token),Session.revoked_at.is_(None)))
    if not session or session.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        raise APIError(401,"invalid_session","Sessão inválida ou expirada.")
    user=db.get(User,session.user_id)
    if not user or not user.is_active: raise APIError(401,"inactive_user","Usuário inativo.")
    return user
