from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    app_name: str="Fluentia API"; environment: str="development"; debug: bool=False
    database_url: str="sqlite:///./fluentia.db"; frontend_origin: str="http://localhost:3000"
    session_cookie_name: str="fluentia_session"; session_secure: bool=False; session_days: int=30
    ai_mock_mode: bool=True; openrouter_api_key: str=""; openrouter_model: str=""; openrouter_base_url: str="https://openrouter.ai/api/v1"
    max_audio_bytes: int=10_000_000; max_audio_duration_seconds: int=120
    model_config=SettingsConfigDict(env_file=".env", extra="ignore")
@lru_cache
def get_settings(): return Settings()
