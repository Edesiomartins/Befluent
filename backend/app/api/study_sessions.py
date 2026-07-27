from datetime import datetime,timezone
from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.api.helpers import user_language
from app.core.database import get_db
from app.core.deps import current_user
from app.models import StudySession,User
class StartIn(BaseModel): language_code:str
router=APIRouter(prefix="/study-sessions",tags=["study-sessions"])
@router.post("")
def start(data:StartIn,db:Session=Depends(get_db),user:User=Depends(current_user)):
    ul=user_language(db,user.id,data.language_code); item=StudySession(user_language_id=ul.id); db.add(item); db.commit(); return {"id":item.id,"status":item.status}
@router.post("/{session_id}/report")
def report(session_id:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    item=db.scalar(select(StudySession).join(__import__("app.models",fromlist=["UserLanguage"]).UserLanguage).where(StudySession.id==session_id,__import__("app.models",fromlist=["UserLanguage"]).UserLanguage.user_id==user.id))
    if not item: from app.core.errors import APIError; raise APIError(404,"session_not_found","Sessão de estudo não encontrada.")
    item.status="completed"; item.ended_at=datetime.now(timezone.utc); item.summary_short="Sessão concluída."; db.commit(); return {"id":item.id,"status":item.status,"summary":item.summary_short}
