from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.models import Language, User, UserPreference
from app.schemas import SettingsIn

router = APIRouter(prefix="/settings", tags=["settings"])


def pref(db: Session, user: User) -> UserPreference:
    item = db.scalar(select(UserPreference).where(UserPreference.user_id == user.id))
    if not item:
        item = UserPreference(user_id=user.id)
        db.add(item)
        db.flush()
    return item


def _payload(p: UserPreference) -> dict:
    return {
        "tts_speed": p.tts_speed,
        "ui_prefs": p.ui_prefs_json,
        "default_language_id": p.default_language_id,
        "timezone": p.timezone,
    }


@router.get("")
def get_settings(db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = pref(db, user)
    db.commit()
    return _payload(p)


@router.patch("")
def update(
    data: SettingsIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    p = pref(db, user)
    if data.tts_speed is not None:
        p.tts_speed = data.tts_speed
    if data.ui_prefs is not None:
        p.ui_prefs_json = data.ui_prefs
    if data.timezone is not None:
        p.timezone = data.timezone
    if data.default_language_code:
        lang = db.scalar(select(Language).where(Language.code == data.default_language_code))
        if not lang:
            raise APIError(404, "language_not_found", "Idioma não encontrado.")
        p.default_language_id = lang.id
    db.commit()
    return _payload(p)
