from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """SQLAlchemy não reconhece o dialeto 'postgres://' (legado)."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://") and "+psycopg" not in url.split("://", 1)[0]:
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


class Settings(BaseSettings):
    app_name: str = "BeFluent API"
    environment: str = "development"
    debug: bool = False
    database_url: str = "sqlite:///./befluent.db"
    frontend_origin: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("FRONTEND_ORIGIN", "FRONTEND_URL"),
    )
    session_cookie_name: str = Field(
        default="befluent_session",
        validation_alias=AliasChoices("SESSION_COOKIE_NAME", "COOKIE_NAME"),
    )
    session_secure: bool = Field(
        default=False,
        validation_alias=AliasChoices("SESSION_SECURE", "COOKIE_SECURE"),
    )
    cookie_samesite: str = Field(
        default="lax",
        validation_alias=AliasChoices("COOKIE_SAMESITE", "SESSION_SAMESITE"),
    )
    cookie_domain: str | None = Field(
        default=None,
        validation_alias=AliasChoices("COOKIE_DOMAIN", "SESSION_COOKIE_DOMAIN"),
    )
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

    @field_validator("cookie_domain", mode="before")
    @classmethod
    def _empty_domain_to_none(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("cookie_samesite", mode="before")
    @classmethod
    def _normalize_samesite(cls, value: object) -> str:
        text = str(value or "lax").strip().lower()
        if text not in {"lax", "strict", "none"}:
            return "lax"
        return text


@lru_cache
def get_settings() -> Settings:
    return Settings()
