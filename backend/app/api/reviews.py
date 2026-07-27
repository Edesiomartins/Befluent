from datetime import datetime,timezone
from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.models import ReviewItem,User,UserLanguage
from app.schemas import ReviewAnswer
from app.services.srs import SimpleScheduler
router=APIRouter(prefix="/reviews",tags=["reviews"])
@router.get("/due")
def due(db:Session=Depends(get_db),user:User=Depends(current_user)):
    q=select(ReviewItem).join(UserLanguage).where(UserLanguage.user_id==user.id,ReviewItem.suspended.is_(False),ReviewItem.next_review_at<=datetime.now(timezone.utc))
    return [{"id":x.id,"item_type":x.item_type,"reference_id":x.reference_id,"payload":x.payload_json,"next_review_at":x.next_review_at} for x in db.scalars(q)]
@router.post("/{item_id}/answer")
def answer(item_id:str,data:ReviewAnswer,db:Session=Depends(get_db),user:User=Depends(current_user)):
    item=db.scalar(select(ReviewItem).join(UserLanguage).where(ReviewItem.id==item_id,UserLanguage.user_id==user.id))
    if not item: raise APIError(404,"review_not_found","Item de revisão não encontrado.")
    try: next_at,interval=SimpleScheduler().schedule(data.rating,item.interval_days)
    except ValueError as exc: raise APIError(422,"invalid_rating","Avaliação deve ser again, hard, good, easy, suspend ou mastered.") from exc
    if data.rating=="suspend": item.suspended=True
    elif data.rating=="mastered": item.mastery_state="mastered"
    else: item.next_review_at=next_at; item.interval_days=interval
    db.commit(); return {"id":item.id,"rating":data.rating,"next_review_at":item.next_review_at,"interval_days":item.interval_days,"suspended":item.suspended,"mastery_state":item.mastery_state}
