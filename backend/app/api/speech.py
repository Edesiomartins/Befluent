import os
from fastapi import APIRouter,Depends,File,Form,UploadFile
from fastapi.responses import Response
from pydantic import BaseModel,Field
from app.core.deps import current_user
from app.core.errors import APIError
from app.models import User
from app.services.speech import assess_pronunciation,save_temp_audio,synthesize_audio,transcribe_audio
router=APIRouter(prefix="/speech",tags=["speech"])
@router.post("/transcribe")
async def transcribe(language_code:str=Form(...),file:UploadFile=File(...),user:User=Depends(current_user)):
    data=await file.read()
    try: path=save_temp_audio(data)
    except ValueError as exc: raise APIError(413,"audio_too_large",str(exc)) from exc
    try: return transcribe_audio(path,language_code,file.content_type)
    finally:
        if os.path.exists(path): os.unlink(path)
class TTSIn(BaseModel):
    text:str=Field(min_length=1,max_length=2000)
    language_code:str=Field(min_length=1,max_length=20)
    speed:float|None=Field(default=None,ge=0.5,le=2.0)
@router.post("/synthesize")
def synthesize(data:TTSIn,user:User=Depends(current_user)):
    audio,content_type=synthesize_audio(data.text,data.language_code,data.speed)
    return Response(audio,media_type=content_type)
class PronunciationIn(BaseModel): target_text:str; transcript:str
@router.post("/pronunciation")
def pronunciation(data:PronunciationIn,user:User=Depends(current_user)): return assess_pronunciation(data.target_text,data.transcript)
