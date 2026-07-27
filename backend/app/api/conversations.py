from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.api.helpers import user_language
from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.models import Conversation,ConversationMessage,StudySession,User
from app.services.ai import get_ai_provider
class StartIn(BaseModel): language_code:str; topic:str="Conversa livre"; study_session_id:str|None=None
class MessageIn(BaseModel): text:str
router=APIRouter(prefix="/conversations",tags=["conversations"])
@router.post("")
def start(data:StartIn,db:Session=Depends(get_db),user:User=Depends(current_user)):
    ul=user_language(db,user.id,data.language_code)
    sid=data.study_session_id
    if not sid: s=StudySession(user_language_id=ul.id); db.add(s); db.flush(); sid=s.id
    item=Conversation(study_session_id=sid,user_language_id=ul.id,topic=data.topic); db.add(item); db.commit(); return {"id":item.id,"topic":item.topic}
@router.post("/{conversation_id}/messages")
def message(conversation_id:str,data:MessageIn,db:Session=Depends(get_db),user:User=Depends(current_user)):
    conv=db.get(Conversation,conversation_id)
    if not conv or db.get(__import__("app.models",fromlist=["UserLanguage"]).UserLanguage,conv.user_language_id).user_id!=user.id: raise APIError(404,"conversation_not_found","Conversa não encontrada.")
    lang=db.scalar(select(__import__("app.models",fromlist=["Language"]).Language).join(__import__("app.models",fromlist=["UserLanguage"]).UserLanguage).where(__import__("app.models",fromlist=["UserLanguage"]).UserLanguage.id==conv.user_language_id))
    db.add(ConversationMessage(conversation_id=conv.id,role="user",content_text=data.text))
    result=get_ai_provider().conversation(data.text,lang.code); reply=ConversationMessage(conversation_id=conv.id,role="assistant",content_text=result["reply"],corrections_json=result["corrections"]); db.add(reply); db.commit()
    return {"message_id":reply.id,**result}
@router.get("/{conversation_id}/messages")
def messages(conversation_id:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    conv=db.get(Conversation,conversation_id)
    if not conv: raise APIError(404,"conversation_not_found","Conversa não encontrada.")
    return [{"id":x.id,"role":x.role,"content":x.content_text,"corrections":x.corrections_json} for x in db.scalars(select(ConversationMessage).where(ConversationMessage.conversation_id==conversation_id).order_by(ConversationMessage.created_at))]
