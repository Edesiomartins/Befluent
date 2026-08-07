import os
from fastapi import APIRouter,Depends,File,Form,UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
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
class TTSIn(BaseModel): text:str; language_code:str
@router.post("/synthesize")
def synthesize(data:TTSIn,user:User=Depends(current_user)): return Response(synthesize_audio(data.text,data.language_code),media_type="audio/wav")
class PronunciationIn(BaseModel): target_text:str; transcript:str
@router.post("/pronunciation")
def pronunciation(data:PronunciationIn,user:User=Depends(current_user)): return assess_pronunciation(data.target_text,data.transcript)
