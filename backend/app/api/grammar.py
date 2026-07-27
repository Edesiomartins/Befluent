from fastapi import APIRouter,Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import current_user
from app.models import GrammarTopic,Language,User
class Practice(BaseModel): topic_id:str; response:str
router=APIRouter(prefix="/grammar",tags=["grammar"])
@router.get("/topics")
def topics(language_code:str,db:Session=Depends(get_db),user:User=Depends(current_user)): return [{"id":x.id,"code":x.code,"title_pt":x.title_pt,"description":x.description} for x in db.scalars(select(GrammarTopic).join(Language).where(Language.code==language_code))]
@router.post("/practice")
def practice(data:Practice,user:User=Depends(current_user)): return {"correct":True,"score":1.0,"feedback":"Resposta registrada em modo simulado."}
