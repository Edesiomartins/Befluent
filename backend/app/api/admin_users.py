"""Administração de contas. Cobrança fica de fora."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DB

from app.core.deps import current_user
from app.core.errors import APIError
from app.models import User
from app.services.admin_access import is_admin
from app.services import admin_users as service
from app.core.database import get_db

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


def require_admin(user: User = Depends(current_user)) -> User:
    if not is_admin(user):
        raise APIError(403, "admin_forbidden", "Acesso não autorizado.")
    return user


class ActiveIn(BaseModel):
    is_active: bool


class LanguageIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)


class DeleteIn(BaseModel):
    confirm_email: str = Field(min_length=1, max_length=320)


@router.get("")
def list_users(db: DB = Depends(get_db), actor: User = Depends(require_admin)):
    return {"users": service.list_users(db)}


@router.patch("/{user_id}")
def set_active(
    user_id: str,
    data: ActiveIn,
    db: DB = Depends(get_db),
    actor: User = Depends(require_admin),
):
    return service.set_user_active(db, actor, user_id, data.is_active)


@router.post("/{user_id}/languages")
def grant_language(
    user_id: str,
    data: LanguageIn,
    db: DB = Depends(get_db),
    actor: User = Depends(require_admin),
):
    return service.grant_language(db, user_id, data.code)


@router.post("/{user_id}/languages/{code}/revoke")
def revoke_language(
    user_id: str,
    code: str,
    db: DB = Depends(get_db),
    actor: User = Depends(require_admin),
):
    return service.revoke_language(db, user_id, code)


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    data: DeleteIn,
    db: DB = Depends(get_db),
    actor: User = Depends(require_admin),
):
    return service.delete_user(db, actor, user_id, data.confirm_email)
