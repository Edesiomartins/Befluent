from fastapi import APIRouter,Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.helpers import user_language
from app.core.database import get_db
from app.core.deps import current_user
from app.models import User,WritingSubmission
class Create(BaseModel): language_code:str; prompt:str; content_text:str
router=APIRouter(prefix="/writing",tags=["writing"])
@router.post("")
def create(data:Create,db:Session=Depends(get_db),user:User=Depends(current_user)):
    ul=user_language(db,user.id,data.language_code); x=WritingSubmission(user_language_id=ul.id,prompt=data.prompt,content_text=data.content_text,score=80,feedback_json={"summary":"Texto avaliado em modo simulado.","corrections":[]}); db.add(x); db.commit(); return {"id":x.id,"score":x.score,"feedback":x.feedback_json}
