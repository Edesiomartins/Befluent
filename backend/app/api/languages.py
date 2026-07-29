from fastapi import APIRouter,Depends
from sqlalchemy import select,update
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.models import Language,User,UserLanguage
from app.schemas import LanguageActivate
router=APIRouter(prefix="/languages",tags=["languages"])
def out(x): return {"id":x.id,"code":x.code,"name_pt":x.name_pt,"native_name":x.native_name,"description":x.description,"strategy_summary":x.strategy_summary}
@router.get("")
def list_languages(db:Session=Depends(get_db),user:User=Depends(current_user)): return [out(x) for x in db.scalars(select(Language).where(Language.is_active.is_(True)).order_by(Language.name_pt))]
@router.get("/mine")
def mine(db:Session=Depends(get_db),user:User=Depends(current_user)):
    rows=db.execute(select(UserLanguage,Language).join(Language).where(UserLanguage.user_id==user.id)).all()
    return [{
        **out(lang),
        "user_language_id":ul.id,
        "active":ul.is_active,
        "level_estimate":ul.level_estimate,
        "current_level":ul.current_level,
        "onboarding_completed":ul.onboarding_completed,
    } for ul,lang in rows]
@router.post("/activate")
def activate(data:LanguageActivate,db:Session=Depends(get_db),user:User=Depends(current_user)):
    lang=db.scalar(select(Language).where(Language.code==data.code,Language.is_active.is_(True)))
    if not lang: raise APIError(404,"language_not_found","Idioma não encontrado.")
    db.execute(update(UserLanguage).where(UserLanguage.user_id==user.id).values(is_active=False))
    ul=db.scalar(select(UserLanguage).where(UserLanguage.user_id==user.id,UserLanguage.language_id==lang.id))
    if not ul: ul=UserLanguage(user_id=user.id,language_id=lang.id,is_active=True); db.add(ul)
    else: ul.is_active=True
    db.commit(); return {"code":lang.code,"active":True,"user_language_id":ul.id}
