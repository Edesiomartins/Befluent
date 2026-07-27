from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """SQLAlchemy não reconhece o dialeto 'postgres://' (legado)."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://") and "+psycopg" not in url.split("://", 1)[0]:
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


class Settings(BaseSettings):
    app_name: str = "Fluentia API"
    environment: str = "development"
    debug: bool = False
    database_url: str = "sqlite:///./fluentia.db"
    frontend_origin: str = "http://localhost:3000"
    session_cookie_name: str = "fluentia_session"
    session_secure: bool = False
    session_days: int = 30
    ai_mock_mode: bool = True
    openrouter_api_key: str = ""
    openrouter_model: str = ""
    openrouter_fallback_model: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    max_audio_bytes: int = 10_000_000
    max_audio_duration_seconds: int = 120
    stt_provider: str = "mock"
    stt_api_key: str = ""
    stt_model: str = ""
    tts_provider: str = "mock"
    tts_api_key: str = ""
    tts_voice: str = ""
    tts_speed: float = 1.0
    initial_admin_name: str = ""
    initial_admin_email: str = ""
    initial_admin_password: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_db_url(cls, value: str) -> str:
        return normalize_database_url(str(value))


@lru_cache
def get_settings() -> Settings:
    return Settings()
