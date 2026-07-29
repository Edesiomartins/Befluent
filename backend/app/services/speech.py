import io, os, tempfile, wave
from abc import ABC, abstractmethod
from app.core.config import get_settings
class BaseSTTProvider(ABC):
    @abstractmethod
    def transcribe(self,path:str,language_code:str)->dict: ...
class MockSTTProvider(BaseSTTProvider):
    def transcribe(self,path,language_code):
        return {
            "text": "[mock] Transcrição simulada — configure um provedor STT real para reconhecimento de fala.",
            "language_code": language_code,
            "provider": "mock",
        }
class BaseTTSProvider(ABC):
    @abstractmethod
    def synthesize(self,text:str,language_code:str)->bytes: ...
class MockTTSProvider(BaseTTSProvider):
    def synthesize(self,text,language_code): return b"RIFF\x24\x00\x00\x00WAVEfmt "
def save_temp_audio(data:bytes)->str:
    settings=get_settings()
    if len(data)>settings.max_audio_bytes: raise ValueError("Arquivo de áudio excede o limite permitido.")
    try:
        with wave.open(io.BytesIO(data),"rb") as audio:
            duration=audio.getnframes()/max(audio.getframerate(),1)
            if duration>settings.max_audio_duration_seconds:
                raise ValueError("A duração do áudio excede o limite permitido.")
    except (wave.Error,EOFError):
        # Provedores reais validam formatos comprimidos; o mock aceita conteúdo não-WAV.
        pass
    fd,path=tempfile.mkstemp(suffix=".audio")
    try:
        with os.fdopen(fd,"wb") as f: f.write(data)
        return path
    except Exception:
        os.close(fd); os.unlink(path); raise
