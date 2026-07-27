from fastapi import APIRouter,Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.helpers import user_language
from app.core.database import get_db
from app.core.deps import current_user
from app.models import LearningPlan,LearningPlanItem,User,UserLanguage
from app.services.learning import create_simple_plan
class Create(BaseModel): language_code:str
router=APIRouter(prefix="/learning-plans",tags=["learning-plans"])
@router.get("")
def list_all(db:Session=Depends(get_db),user:User=Depends(current_user)):
    return [{"id":x.id,"version":x.version,"status":x.status} for x in db.scalars(select(LearningPlan).join(UserLanguage).where(UserLanguage.user_id==user.id))]
@router.post("")
def create(data:Create,db:Session=Depends(get_db),user:User=Depends(current_user)):
    ul=user_language(db,user.id,data.language_code); p=create_simple_plan(db,ul.id)
    db.commit(); return {"id":p.id,"version":p.version,"status":p.status}
@router.get("/{plan_id}")
def one(plan_id:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    p=db.get(LearningPlan,plan_id); return {"id":p.id,"status":p.status,"items":[{"id":x.id,"position":x.position,"title":x.title,"status":x.status} for x in db.scalars(select(LearningPlanItem).where(LearningPlanItem.plan_id==p.id).order_by(LearningPlanItem.position))]}
