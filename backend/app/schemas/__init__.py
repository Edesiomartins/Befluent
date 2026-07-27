from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _normalize_email(value: str) -> str:
    email = value.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("E-mail inválido.")
    return email


class LoginIn(BaseModel):
    email: str
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalize_email(value)


class RegisterIn(BaseModel):
    """Apenas name, email, password e password_confirmation são aceitos."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=8, max_length=128)
    password_confirmation: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        name = value.strip()
        if len(name) < 2:
            raise ValueError("O nome deve ter pelo menos 2 caracteres.")
        return name

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalize_email(value)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.password_confirmation:
            raise ValueError("As senhas não coincidem.")
        return self


class LanguageActivate(BaseModel):
    code: str


class OnboardingIn(BaseModel):
    """Payload do onboarding alinhado ao frontend.

    Aceita também `level_estimate`/`goals` por compatibilidade com clientes antigos.
    """

    language_code: str
    perceived_level: str | None = None
    level_estimate: str | None = None
    goal: str | None = None
    goals: list[str] = []
    minutes_per_day: int | None = Field(default=20, ge=5, le=180)
    skills: list[str] = []

    @model_validator(mode="after")
    def normalize_fields(self):
        if not (self.perceived_level or self.level_estimate):
            raise ValueError("Informe o nível percebido.")
        if not (self.goal or self.goals):
            raise ValueError("Informe pelo menos um objetivo.")
        return self

    @property
    def resolved_level(self) -> str:
        return (self.perceived_level or self.level_estimate or "").strip()

    @property
    def resolved_goals(self) -> list[str]:
        if self.goal and self.goal.strip():
            return [self.goal.strip()]
        return [g.strip() for g in self.goals if g and g.strip()]


class TextIn(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class VocabularyIn(BaseModel):
    language_code: str
    term: str
    translation_pt: str
    reading_or_pinyin: str | None = None
    notes: str | None = None


class VocabularyUpdate(BaseModel):
    translation_pt: str | None = None
    reading_or_pinyin: str | None = None
    notes: str | None = None
    status: str | None = None


class ReviewAnswer(BaseModel):
    rating: str


class SettingsIn(BaseModel):
    tts_speed: float | None = Field(None, ge=0.5, le=2)
    ui_prefs: dict | None = None
    default_language_code: str | None = None
