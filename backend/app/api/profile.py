from fastapi import APIRouter,Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import current_user
from app.models import User
router=APIRouter(prefix="/profile",tags=["profile"])
class ProfileIn(BaseModel): name:str
@router.get("")
def get_profile(user:User=Depends(current_user)): return {"id":user.id,"email":user.email,"name":user.name}
@router.patch("")
def update(data:ProfileIn,db:Session=Depends(get_db),user:User=Depends(current_user)): user.name=data.name; db.commit(); return {"id":user.id,"email":user.email,"name":user.name}
