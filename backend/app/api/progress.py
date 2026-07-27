from fastapi import APIRouter,Depends
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import current_user
from app.models import StudySession,User,UserLanguage,VocabularyItem
router=APIRouter(prefix="/progress",tags=["progress"])
@router.get("")
def progress(db:Session=Depends(get_db),user:User=Depends(current_user)):
    vocab=db.scalar(select(func.count(VocabularyItem.id)).join(UserLanguage).where(UserLanguage.user_id==user.id)) or 0
    sessions=db.scalar(select(func.count(StudySession.id)).join(UserLanguage).where(UserLanguage.user_id==user.id)) or 0
    return {"vocabulary_items":vocab,"study_sessions":sessions,"streak_days":0}
