from fastapi import APIRouter,Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.helpers import user_language
from app.core.database import get_db
from app.core.deps import current_user
from app.models import ListeningActivity,User
class Create(BaseModel): language_code:str; prompt:str
router=APIRouter(prefix="/listening",tags=["listening"])
@router.post("")
def create(data:Create,db:Session=Depends(get_db),user:User=Depends(current_user)):
    ul=user_language(db,user.id,data.language_code); x=ListeningActivity(user_language_id=ul.id,prompt=data.prompt,questions_json=[{"question":"Qual é a ideia principal?"}]); db.add(x); db.commit(); return {"id":x.id,"prompt":x.prompt,"questions":x.questions_json}
@router.post("/{activity_id}/answer")
def answer(activity_id:str,user:User=Depends(current_user)): return {"score":1.0,"feedback":"Resposta recebida."}
