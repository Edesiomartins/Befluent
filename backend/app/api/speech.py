import os
from fastapi import APIRouter,Depends,File,Form,UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from app.core.deps import current_user
from app.core.errors import APIError
from app.models import User
from app.services.speech import MockSTTProvider,MockTTSProvider,save_temp_audio
router=APIRouter(prefix="/speech",tags=["speech"])
@router.post("/transcribe")
async def transcribe(language_code:str=Form(...),file:UploadFile=File(...),user:User=Depends(current_user)):
    data=await file.read()
    try: path=save_temp_audio(data)
    except ValueError as exc: raise APIError(413,"audio_too_large",str(exc)) from exc
    try: return MockSTTProvider().transcribe(path,language_code)
    finally:
        if os.path.exists(path): os.unlink(path)
class TTSIn(BaseModel): text:str; language_code:str
@router.post("/synthesize")
def synthesize(data:TTSIn,user:User=Depends(current_user)): return Response(MockTTSProvider().synthesize(data.text,data.language_code),media_type="audio/wav")
class PronunciationIn(BaseModel): target_text:str; transcript:str
@router.post("/pronunciation")
def pronunciation(data:PronunciationIn,user:User=Depends(current_user)): return {"score":85.0,"feedback":{"message":"Pronúncia simulada satisfatória."},"provider":"mock"}
