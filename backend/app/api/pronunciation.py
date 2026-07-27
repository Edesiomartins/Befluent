from fastapi import APIRouter,Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.helpers import user_language
from app.core.database import get_db
from app.core.deps import current_user
from app.models import PronunciationAttempt,User
class Create(BaseModel): language_code:str; target_text:str; transcript:str|None=None
router=APIRouter(prefix="/pronunciation",tags=["pronunciation"])
@router.post("/attempts")
def create(data:Create,db:Session=Depends(get_db),user:User=Depends(current_user)):
    ul=user_language(db,user.id,data.language_code); x=PronunciationAttempt(user_language_id=ul.id,target_text=data.target_text,transcript=data.transcript,score=85,feedback_json={"message":"Resultado simulado."}); db.add(x); db.commit(); return {"id":x.id,"score":x.score,"feedback":x.feedback_json}
