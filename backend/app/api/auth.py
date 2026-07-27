import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session as DB
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.core.security import token_hash, verify_password
from app.models import Session, User
from app.schemas import LoginIn
from app.services.auth import create_session
router=APIRouter(prefix="/auth",tags=["auth"])
@router.post("/login")
def login(data:LoginIn,response:Response,db:DB=Depends(get_db)):
    user=db.scalar(select(User).where(User.email==data.email.lower()))
    if not user or not verify_password(data.password,user.password_hash): raise APIError(401,"invalid_credentials","E-mail ou senha inválidos.")
    if not user.is_active: raise APIError(403,"inactive_user","Usuário inativo.")
    token=create_session(db,user.id); csrf=secrets.token_urlsafe(32); user.last_login_at=datetime.now(timezone.utc); db.commit(); s=get_settings()
    response.set_cookie(s.session_cookie_name,token,httponly=True,secure=s.session_secure,samesite="lax",max_age=s.session_days*86400,path="/")
    response.set_cookie("csrf_token",csrf,httponly=False,secure=s.session_secure,samesite="lax",max_age=s.session_days*86400,path="/")
    return {"user":{"id":user.id,"email":user.email,"name":user.name}}
@router.post("/logout")
def logout(request:Request,response:Response,db:DB=Depends(get_db),user:User=Depends(current_user)):
    token=request.cookies.get(get_settings().session_cookie_name)
    db.execute(update(Session).where(Session.token_hash==token_hash(token)).values(revoked_at=datetime.now(timezone.utc))); db.commit()
    response.delete_cookie(get_settings().session_cookie_name,path="/"); response.delete_cookie("csrf_token",path="/")
    return {"message":"Sessão encerrada com sucesso."}
@router.get("/me")
def me(user:User=Depends(current_user)): return {"id":user.id,"email":user.email,"name":user.name,"is_active":user.is_active}
