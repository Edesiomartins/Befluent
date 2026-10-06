from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import current_user
from app.models import User
from app.services.language_codes import validate_native_language, native_language_metadata

router = APIRouter(prefix="/profile", tags=["profile"])

class ProfileIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    native_language: str | None = None
    _native = field_validator("native_language")(validate_native_language)

def _profile(user):
    return {"id": user.id, "email": user.email, "name": user.name, **native_language_metadata(user)}

@router.get("")
def get_profile(user: User = Depends(current_user)):
    return _profile(user)

@router.patch("")
def update(data: ProfileIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if data.name is not None:
        user.name = data.name
    if "native_language" in data.model_fields_set:
        user.native_language = data.native_language
    db.commit()
    return _profile(user)
