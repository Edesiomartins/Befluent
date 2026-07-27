from abc import ABC, abstractmethod
import httpx
from app.core.config import get_settings
class BaseAIProvider(ABC):
    @abstractmethod
    def conversation(self,text:str,language_code:str)->dict: ...
class MockAIProvider(BaseAIProvider):
    def conversation(self,text,language_code):
        return {"reply":f"Resposta simulada em {language_code}: {text}","corrections":[],"suggestions":["Continue praticando!"],"provider":"mock"}
class OpenRouterProvider(BaseAIProvider):
    def __init__(self): self.s=get_settings()
    def conversation(self,text,language_code):
        if not self.s.openrouter_api_key or not self.s.openrouter_model: return MockAIProvider().conversation(text,language_code)
        payload={"model":self.s.openrouter_model,"messages":[{"role":"system","content":f"Responda como tutor de {language_code} em JSON."},{"role":"user","content":text}],"response_format":{"type":"json_object"}}
        try:
            r=httpx.post(f"{self.s.openrouter_base_url}/chat/completions",json=payload,headers={"Authorization":f"Bearer {self.s.openrouter_api_key}"},timeout=30); r.raise_for_status()
            content=r.json()["choices"][0]["message"]["content"]
            return {"reply":content,"corrections":[],"suggestions":[],"provider":"openrouter"}
        except httpx.HTTPError as exc: raise RuntimeError("Falha temporária no serviço de IA.") from exc
def get_ai_provider():
    s=get_settings()
    return MockAIProvider() if s.ai_mock_mode or not s.openrouter_api_key else OpenRouterProvider()
