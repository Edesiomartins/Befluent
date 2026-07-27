from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.errors import APIError
from app.models import Language, UserLanguage
def user_language(db:Session,user_id:str,code:str|None=None,active=False):
    query=select(UserLanguage).join(Language).where(UserLanguage.user_id==user_id)
    if code: query=query.where(Language.code==code)
    if active: query=query.where(UserLanguage.is_active.is_(True))
    item=db.scalar(query)
    if not item: raise APIError(404,"language_not_configured","Idioma não configurado para o usuário.")
    return item
def as_dict(obj,*fields): return {field:getattr(obj,field) for field in fields}
