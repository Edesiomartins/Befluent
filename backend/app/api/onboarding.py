from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.models import Language,LearningGoal,User,UserLanguage
from app.schemas import OnboardingIn
router=APIRouter(prefix="/onboarding",tags=["onboarding"])
@router.get("/status")
def status(db:Session=Depends(get_db),user:User=Depends(current_user)):
    items=list(db.scalars(select(UserLanguage).where(UserLanguage.user_id==user.id)))
    return {"completed":any(x.onboarding_completed for x in items),"languages":[{"id":x.id,"completed":x.onboarding_completed} for x in items]}
@router.post("/complete")
def complete(data:OnboardingIn,db:Session=Depends(get_db),user:User=Depends(current_user)):
    lang=db.scalar(select(Language).where(Language.code==data.language_code))
    if not lang: raise APIError(404,"language_not_found","Idioma não encontrado.")
    ul=db.scalar(select(UserLanguage).where(UserLanguage.user_id==user.id,UserLanguage.language_id==lang.id))
    if not ul: ul=UserLanguage(user_id=user.id,language_id=lang.id); db.add(ul); db.flush()
    ul.level_estimate=data.level_estimate; ul.onboarding_completed=True
    for goal in data.goals: db.add(LearningGoal(user_language_id=ul.id,goal_type="personal",description=goal,priority=1))
    db.commit(); return {"completed":True,"user_language_id":ul.id}
