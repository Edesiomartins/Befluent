from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session as DB
from app.core.config import get_settings
from app.core.security import new_token, token_hash
from app.models import Session
def create_session(db:DB,user_id:str):
    token=new_token(); db.add(Session(user_id=user_id,token_hash=token_hash(token),expires_at=datetime.now(timezone.utc)+timedelta(days=get_settings().session_days))); db.commit(); return token
