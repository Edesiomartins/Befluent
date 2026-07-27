from datetime import datetime,timezone
from fastapi import APIRouter,Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.helpers import user_language
from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.models import Assessment,AssessmentAttempt,AssessmentQuestion,User
class Start(BaseModel): language_code:str
class Answer(BaseModel): question_id:str; response:dict
router=APIRouter(prefix="/assessments",tags=["assessments"])
@router.post("/diagnostic")
def start(data:Start,db:Session=Depends(get_db),user:User=Depends(current_user)):
    ul=user_language(db,user.id,data.language_code); a=Assessment(user_language_id=ul.id,status="active"); db.add(a); db.flush()
    for i,(skill,prompt) in enumerate([("vocabulary","Apresente-se no idioma estudado."),("grammar","Escreva uma frase no passado."),("reading","Explique uma rotina diária.")],1): db.add(AssessmentQuestion(assessment_id=a.id,position=i,skill=skill,prompt=prompt))
    db.commit(); return {"id":a.id,"status":a.status}
@router.get("/{assessment_id}")
def get_one(assessment_id:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    a=db.get(Assessment,assessment_id)
    if not a: raise APIError(404,"assessment_not_found","Avaliação não encontrada.")
    return {"id":a.id,"status":a.status,"questions":[{"id":q.id,"position":q.position,"skill":q.skill,"prompt":q.prompt} for q in db.scalars(select(AssessmentQuestion).where(AssessmentQuestion.assessment_id==a.id).order_by(AssessmentQuestion.position))]}
@router.post("/{assessment_id}/answer")
def answer(assessment_id:str,data:Answer,db:Session=Depends(get_db),user:User=Depends(current_user)):
    if not db.get(Assessment,assessment_id): raise APIError(404,"assessment_not_found","Avaliação não encontrada.")
    item=AssessmentAttempt(assessment_id=assessment_id,question_id=data.question_id,response_json=data.response,result_json={"accepted":True}); db.add(item); db.commit(); return {"attempt_id":item.id,"accepted":True}
@router.post("/{assessment_id}/complete")
def complete(assessment_id:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    a=db.get(Assessment,assessment_id)
    if not a: raise APIError(404,"assessment_not_found","Avaliação não encontrada.")
    a.status="completed"; a.completed_at=datetime.now(timezone.utc); db.commit(); return {"id":a.id,"status":"completed","level_estimate":"A1"}
