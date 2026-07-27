from fastapi import APIRouter,Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.helpers import user_language
from app.core.database import get_db
from app.core.deps import current_user
from app.models import Lesson,LessonActivity,User,UserLanguage
class Create(BaseModel): language_code:str; title:str="Aula guiada"; objective:str="Praticar comunicação"
router=APIRouter(prefix="/lessons",tags=["lessons"])
@router.get("")
def list_all(db:Session=Depends(get_db),user:User=Depends(current_user)): return [{"id":x.id,"title":x.title,"status":x.status} for x in db.scalars(select(Lesson).join(UserLanguage).where(UserLanguage.user_id==user.id))]
@router.post("")
def create(data:Create,db:Session=Depends(get_db),user:User=Depends(current_user)):
    ul=user_language(db,user.id,data.language_code); x=Lesson(user_language_id=ul.id,title=data.title,objective=data.objective,status="active",content_json={"reading":"Texto curto de prática."}); db.add(x); db.flush()
    db.add(LessonActivity(lesson_id=x.id,position=1,activity_type="reading",prompt="Leia e resuma o texto.")); db.commit(); return {"id":x.id,"title":x.title,"status":x.status}
@router.get("/{lesson_id}")
def one(lesson_id:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    x=db.get(Lesson,lesson_id); return {"id":x.id,"title":x.title,"objective":x.objective,"content":x.content_json}
