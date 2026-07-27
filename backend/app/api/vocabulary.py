from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.helpers import user_language
from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.models import ReviewItem,User,UserLanguage,VocabularyItem
from app.schemas import VocabularyIn,VocabularyUpdate
router=APIRouter(prefix="/vocabulary",tags=["vocabulary"])
def out(x): return {"id":x.id,"term":x.term,"translation_pt":x.translation_pt,"reading_or_pinyin":x.reading_or_pinyin,"notes":x.notes,"status":x.status,"next_review_at":x.next_review_at}
@router.get("")
def list_items(language_code:str|None=None,db:Session=Depends(get_db),user:User=Depends(current_user)):
    q=select(VocabularyItem).join(UserLanguage).where(UserLanguage.user_id==user.id)
    if language_code: q=q.where(UserLanguage.id==user_language(db,user.id,language_code).id)
    return [out(x) for x in db.scalars(q.order_by(VocabularyItem.term))]
@router.post("")
def create(data:VocabularyIn,db:Session=Depends(get_db),user:User=Depends(current_user)):
    ul=user_language(db,user.id,data.language_code); item=VocabularyItem(user_language_id=ul.id,**data.model_dump(exclude={"language_code"})); db.add(item); db.flush()
    db.add(ReviewItem(user_language_id=ul.id,item_type="vocabulary",reference_id=item.id,payload_json={"term":item.term})); db.commit(); return out(item)
def owned(db,user,item_id):
    item=db.scalar(select(VocabularyItem).join(UserLanguage).where(VocabularyItem.id==item_id,UserLanguage.user_id==user.id))
    if not item: raise APIError(404,"vocabulary_not_found","Item de vocabulário não encontrado.")
    return item
@router.patch("/{item_id}")
def update(item_id:str,data:VocabularyUpdate,db:Session=Depends(get_db),user:User=Depends(current_user)):
    item=owned(db,user,item_id)
    for key,value in data.model_dump(exclude_unset=True).items(): setattr(item,key,value)
    db.commit(); return out(item)
@router.delete("/{item_id}")
def delete(item_id:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    item=owned(db,user,item_id); db.delete(item); db.commit(); return {"message":"Item removido com sucesso."}
