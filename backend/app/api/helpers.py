from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.errors import APIError
from app.models import Language, UserLanguage
from app.services.language_access import user_can_access_language


def ensure_language_access(db: Session, user_id: str, code: str) -> None:
    if not user_can_access_language(db, user_id, code):
        raise APIError(403, "language_locked", "Idioma bloqueado para este usuário.")


def user_language(db:Session,user_id:str,code:str|None=None,active=False):
    query=select(UserLanguage).join(Language).where(UserLanguage.user_id==user_id)
    if code: query=query.where(Language.code==code)
    if active: query=query.where(UserLanguage.is_active.is_(True))
    item=db.scalar(query)
    if not item: raise APIError(404,"language_not_configured","Idioma não configurado para o usuário.")
    if code:
        ensure_language_access(db, user_id, code)
    else:
        language = db.scalar(select(Language).where(Language.id == item.language_id))
        if language:
            ensure_language_access(db, user_id, language.code)
    return item
def as_dict(obj,*fields): return {field:getattr(obj,field) for field in fields}
