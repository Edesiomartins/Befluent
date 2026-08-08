from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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


LEVEL_CHOICES = {"beginner", "take_test", "self_declared", "later"}


class OnboardingIn(BaseModel):
    """Payload do onboarding alinhado ao frontend.

    `level_choice` reflete a decisão de nível:
      beginner      -> PRE_A1, origem self_declared_beginner
      take_test     -> cria sessão de teste; nível fica pendente
      self_declared -> exige `cefr_level`, origem self_declared
      later         -> conclui sem nível confirmado (origem pending)

    Aceita também `perceived_level`/`level_estimate`/`goals` por compatibilidade
    com clientes antigos (rótulos legados são convertidos para CEFR).
    """

    language_code: str
    level_choice: str | None = None
    cefr_level: str | None = None
    perceived_level: str | None = None
    level_estimate: str | None = None
    goal: str | None = None
    goals: list[str] = []
    minutes_per_day: int | None = Field(default=20, ge=5, le=180)
    skills: list[str] = []

    @field_validator("level_choice")
    @classmethod
    def validate_choice(cls, value: str | None) -> str | None:
        if value is None:
            return None
        choice = value.strip()
        if choice not in LEVEL_CHOICES:
            raise ValueError("Opção de nível inválida.")
        return choice

    @model_validator(mode="after")
    def normalize_fields(self):
        if not (self.level_choice or self.perceived_level or self.level_estimate):
            raise ValueError("Informe como deseja definir seu nível.")
        if self.level_choice == "self_declared" and not self.cefr_level:
            raise ValueError("Informe o nível ao escolher declará-lo.")
        if not (self.goal or self.goals):
            raise ValueError("Informe pelo menos um objetivo.")
        return self

    @property
    def resolved_level(self) -> str:
        return (self.perceived_level or self.level_estimate or "").strip()

    @property
    def resolved_choice(self) -> str:
        """Decisão efetiva, inferida do payload legado quando ausente."""
        if self.level_choice:
            return self.level_choice
        return "self_declared" if self.resolved_level else "later"

    @property
    def resolved_cefr(self) -> str | None:
        """Código CEFR resultante da decisão (None quando pendente)."""
        from app.core.levels import CEFRLevel, normalize_level

        choice = self.resolved_choice
        if choice == "beginner":
            return CEFRLevel.PRE_A1
        if choice == "self_declared":
            return normalize_level(self.cefr_level or self.resolved_level)
        return None

    @property
    def resolved_goals(self) -> list[str]:
        if self.goal and self.goal.strip():
            return [self.goal.strip()]
        return [g.strip() for g in self.goals if g and g.strip()]


class PlacementTestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language_code: str = Field(min_length=2, max_length=10)
    declared_beginner: bool = False


class PlacementAnswerIn(BaseModel):
    """Resposta a um item objetivo.

    `response_time_ms` é informativo (alimenta a confiança). O score NUNCA vem
    do cliente: é calculado no backend a partir do gabarito.
    """

    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1, max_length=36)
    answer: str | None = Field(default=None, max_length=2000)
    response_time_ms: int | None = Field(default=None, ge=0, le=3_600_000)


class PlacementWritingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1, max_length=36)
    text: str = Field(min_length=1, max_length=4000)
    response_time_ms: int | None = Field(default=None, ge=0, le=3_600_000)


class LanguageProfileUpdate(BaseModel):
    """Ajustes manuais permitidos no perfil linguístico."""

    model_config = ConfigDict(extra="forbid")

    current_level: str | None = None
    goal: str | None = Field(default=None, max_length=200)
    minutes_per_day: int | None = Field(default=None, ge=5, le=180)
    priority_skills: list[str] | None = None

    @field_validator("current_level")
    @classmethod
    def validate_level(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from app.core.levels import is_valid_level

        code = value.strip().upper().replace("-", "_")
        if not is_valid_level(code):
            raise ValueError("Nível inválido.")
        return code


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
    timezone: str | None = Field(default=None, max_length=64)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        tz_name = value.strip()
        if not tz_name:
            raise ValueError("Fuso horário inválido.")
        try:
            ZoneInfo(tz_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Fuso horário inválido.") from exc
        return tz_name


class LessonGenerateIn(BaseModel):
    """Pedido de lição adaptada ao nível do aluno."""

    model_config = ConfigDict(extra="forbid")

    language_code: str = Field(min_length=2, max_length=10)
    mode: str = Field(min_length=2, max_length=30)
    persist: bool = True

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        from app.prompts.library import SUPPORTED_MODES

        mode = value.strip().lower()
        if mode not in SUPPORTED_MODES:
            raise ValueError("Modo de estudo inválido.")
        return mode


class LessonWritingIn(BaseModel):
    """Texto produzido numa lição de escrita, enviado para correção."""

    model_config = ConfigDict(extra="forbid")

    language_code: str = Field(min_length=2, max_length=10)
    prompt: str = Field(min_length=1, max_length=1000)
    content_text: str = Field(min_length=1, max_length=4000)
    target_level: str | None = None
    min_words: int = Field(default=25, ge=1, le=1000)
    max_words: int = Field(default=220, ge=1, le=2000)

    @field_validator("target_level")
    @classmethod
    def validate_target_level(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from app.core.levels import normalize_level

        level = normalize_level(value)
        if not level:
            raise ValueError("Nível inválido.")
        return level


# ------------------------------------------------------------ Teaching Engine


class AttemptCreateIn(BaseModel):
    """Registra uma produção do aluno para um objetivo. Sem áudio bruto —
    `student_response` é sempre texto (transcrição, resposta, redação)."""

    model_config = ConfigDict(extra="forbid")

    objective_id: str = Field(min_length=1, max_length=36)
    activity_type: str = Field(min_length=1, max_length=50)
    student_response: str | None = Field(default=None, max_length=4000)
    curriculum_block_id: str | None = Field(default=None, max_length=36)
    lesson_id: str | None = Field(default=None, max_length=36)


class AttemptEvaluateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: str
    score: float | None = Field(default=None, ge=0, le=1)
    provider: str | None = Field(default=None, max_length=30)
    evidence_type: str | None = None
    is_transfer: bool = False

    @field_validator("result")
    @classmethod
    def validate_result(cls, value: str) -> str:
        from app.core.teaching import AttemptResult

        if value not in {AttemptResult.CORRECT, AttemptResult.PARTIAL, AttemptResult.INCORRECT}:
            raise ValueError("Resultado deve ser correct, partial ou incorrect.")
        return value

    @field_validator("evidence_type")
    @classmethod
    def validate_evidence_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from app.core.teaching import EvidenceType

        if value not in set(EvidenceType):
            raise ValueError("Tipo de evidência inválido.")
        return value


class ErrorCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    original: str = Field(min_length=1, max_length=2000)
    expected: str | None = Field(default=None, max_length=2000)
    explanation: str | None = Field(default=None, max_length=1000)
    severity: str = "moderate"
    language_feature: str | None = Field(default=None, max_length=120)

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        from app.core.teaching import ErrorCategory

        if value not in set(ErrorCategory):
            raise ValueError("Categoria de erro inválida.")
        return value

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        from app.core.teaching import ErrorSeverity

        if value not in set(ErrorSeverity):
            raise ValueError("Gravidade de erro inválida.")
        return value


class RemediationCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str | None = None
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from app.core.teaching import RemediationAction

        if value not in set(RemediationAction):
            raise ValueError("Ação de remediação inválida.")
        return value


class RetryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_response: str | None = Field(default=None, max_length=4000)
    activity_type: str | None = Field(default=None, max_length=50)
    curriculum_block_id: str | None = Field(default=None, max_length=36)
    lesson_id: str | None = Field(default=None, max_length=36)


class FlowStartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective_id: str = Field(min_length=1, max_length=36)
    curriculum_block_id: str | None = Field(default=None, max_length=36)


class FlowTransitionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_phase: str = Field(min_length=1, max_length=30)
    reason: str | None = Field(default=None, max_length=500)


class SliceStartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    curriculum_block_id: str | None = Field(default=None, max_length=36)


class SliceAnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_response: str = Field(default="", max_length=4000)
    activity_index: int | None = Field(default=None, ge=0)


class SliceRetryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    remediation_id: str = Field(min_length=1, max_length=36)
    student_response: str = Field(min_length=1, max_length=4000)


class DeterministicEvaluateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_response: str = Field(min_length=1, max_length=4000)
    canonical_answer: str | None = None
    accepted_variants: list[str] = Field(default_factory=list)
    required_features: list[str] = Field(default_factory=list)
    activity: dict | None = None


class IntelligibilityIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_text: str = Field(min_length=1, max_length=2000)
    transcript: str = Field(min_length=1, max_length=4000)
    provider: str | None = Field(default=None, max_length=30)


class MemoryReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: str = Field(min_length=1, max_length=20)
    result: str | None = Field(default=None, max_length=20)
    response_time_ms: int | None = Field(default=None, ge=0)
