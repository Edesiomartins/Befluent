from __future__ import annotations
import uuid
from datetime import date, datetime, timezone
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc)

class Base(DeclarativeBase): pass
class UUIDMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)

class User(UUIDMixin, Base):
    __tablename__="users"
    email: Mapped[str]=mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str]=mapped_column(String(255))
    name: Mapped[str]=mapped_column(String(120))
    is_active: Mapped[bool]=mapped_column(Boolean, default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    last_login_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))

class Language(UUIDMixin, Base):
    __tablename__="languages"
    code: Mapped[str]=mapped_column(String(10), unique=True)
    name_pt: Mapped[str]=mapped_column(String(80))
    native_name: Mapped[str]=mapped_column(String(80))
    variant_note: Mapped[str|None]=mapped_column(String(160))
    description: Mapped[str]=mapped_column(Text, default="")
    strategy_summary: Mapped[str]=mapped_column(Text, default="")
    is_active: Mapped[bool]=mapped_column(Boolean, default=True)

class UserLanguage(UUIDMixin, Base):
    """Perfil linguístico do usuário por idioma.

    As colunas de nível CEFR foram adicionadas aqui (migration 0003) em vez de
    criar uma tabela `user_language_profiles` separada: esta entidade já é a
    relação usuário↔idioma e duplicá-la geraria duas fontes de verdade.
    `level_estimate` guarda o rótulo legado; `current_level` é o código CEFR.
    """
    __tablename__="user_languages"; __table_args__=(UniqueConstraint("user_id","language_id"),)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[str]=mapped_column(ForeignKey("languages.id"), index=True)
    level_estimate: Mapped[str|None]=mapped_column(String(30))
    onboarding_completed: Mapped[bool]=mapped_column(Boolean, default=False)
    diagnostic_completed: Mapped[bool]=mapped_column(Boolean, default=False)
    is_active: Mapped[bool]=mapped_column(Boolean, default=False, index=True)
    started_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    current_level: Mapped[str|None]=mapped_column(String(10))
    level_source: Mapped[str|None]=mapped_column(String(30))
    level_assessed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    placement_test_id: Mapped[str|None]=mapped_column(String(36), index=True)
    vocabulary_grammar_level: Mapped[str|None]=mapped_column(String(10))
    reading_level: Mapped[str|None]=mapped_column(String(10))
    listening_level: Mapped[str|None]=mapped_column(String(10))
    writing_level: Mapped[str|None]=mapped_column(String(10))
    speaking_level: Mapped[str|None]=mapped_column(String(10))
    confidence_score: Mapped[float|None]=mapped_column(Float)
    recommendations_json: Mapped[list|None]=mapped_column(JSON, default=list)

class LearningGoal(UUIDMixin, Base):
    __tablename__="learning_goals"
    user_language_id: Mapped[str]=mapped_column(ForeignKey("user_languages.id", ondelete="CASCADE"), index=True)
    goal_type: Mapped[str]=mapped_column(String(50)); description: Mapped[str]=mapped_column(Text)
    priority: Mapped[int]=mapped_column(Integer, default=1); target_date: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    status: Mapped[str]=mapped_column(String(20), default="active"); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class LearningPlan(UUIDMixin, Base):
    __tablename__="learning_plans"
    user_language_id: Mapped[str]=mapped_column(ForeignKey("user_languages.id", ondelete="CASCADE"), index=True)
    version: Mapped[int]=mapped_column(Integer, default=1); status: Mapped[str]=mapped_column(String(20), default="active")
    generated_from: Mapped[str]=mapped_column(String(50), default="manual")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class LearningPlanItem(UUIDMixin, Base):
    __tablename__="learning_plan_items"; __table_args__=(UniqueConstraint("plan_id","position"),)
    plan_id: Mapped[str]=mapped_column(ForeignKey("learning_plans.id", ondelete="CASCADE"))
    position: Mapped[int]=mapped_column(Integer); activity_type: Mapped[str]=mapped_column(String(50)); title: Mapped[str]=mapped_column(String(200))
    status: Mapped[str]=mapped_column(String(20), default="pending"); due_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); metadata_json: Mapped[dict]=mapped_column(JSON, default=dict)

class Curriculum(UUIDMixin, Base):
    """Cronograma estruturado de estudo, gerado a partir do teste de nivelamento.

    Coexiste com `LearningPlan` (lista curta e sem datas, mantida por
    compatibilidade). A diferença é o eixo temporal: aqui cada dia tem data
    prevista, tema semanal e blocos por competência, do nível de entrada até a
    meta. Regenerar não apaga: o currículo anterior vira `regenerated`.
    """
    __tablename__="curricula"
    user_language_id: Mapped[str]=mapped_column(ForeignKey("user_languages.id", ondelete="CASCADE"), index=True)
    duration_days: Mapped[int]=mapped_column(Integer, default=90)
    start_date: Mapped[date]=mapped_column(Date)
    #: CEFR alvo ao fim do cronograma e CEFR de entrada (mediana das competências).
    target_level: Mapped[str]=mapped_column(String(10))
    entry_level: Mapped[str]=mapped_column(String(10))
    status: Mapped[str]=mapped_column(String(20), default="active", index=True)
    generated_from: Mapped[str]=mapped_column(String(30), default="placement")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class CurriculumWeek(UUIDMixin, Base):
    __tablename__="curriculum_weeks"; __table_args__=(UniqueConstraint("curriculum_id","week_number"),)
    curriculum_id: Mapped[str]=mapped_column(ForeignKey("curricula.id", ondelete="CASCADE"), index=True)
    week_number: Mapped[int]=mapped_column(Integer)
    #: Tema comunicativo da semana (ex.: "Apresentações e rotina").
    theme: Mapped[str]=mapped_column(String(200))
    cefr_focus: Mapped[str]=mapped_column(String(10))
    #: Semanas pares carregam mini-avaliação das quatro competências.
    is_checkpoint: Mapped[bool]=mapped_column(Boolean, default=False)

class CurriculumDay(UUIDMixin, Base):
    __tablename__="curriculum_days"; __table_args__=(UniqueConstraint("week_id","day_number"),)
    week_id: Mapped[str]=mapped_column(ForeignKey("curriculum_weeks.id", ondelete="CASCADE"), index=True)
    #: 1..duration_days — numeração global do cronograma, não da semana.
    day_number: Mapped[int]=mapped_column(Integer, index=True)
    scheduled_date: Mapped[date]=mapped_column(Date, index=True)
    status: Mapped[str]=mapped_column(String(20), default="pending", index=True)
    completed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))

class CurriculumBlock(UUIDMixin, Base):
    __tablename__="curriculum_blocks"; __table_args__=(UniqueConstraint("day_id","position"),)
    day_id: Mapped[str]=mapped_column(ForeignKey("curriculum_days.id", ondelete="CASCADE"), index=True)
    #: `app.core.curriculum.BlockSkill` — oito áreas de estudo.
    skill: Mapped[str]=mapped_column(String(30), index=True)
    position: Mapped[int]=mapped_column(Integer)
    estimated_minutes: Mapped[int]=mapped_column(Integer, default=10)
    cefr_level: Mapped[str]=mapped_column(String(10))
    topic: Mapped[str]=mapped_column(String(200), default="")
    #: Lição gerada ao iniciar o bloco. Nulo enquanto o bloco não foi aberto.
    lesson_ref: Mapped[str|None]=mapped_column(String(36), index=True)
    status: Mapped[str]=mapped_column(String(20), default="pending", index=True)
    score: Mapped[float|None]=mapped_column(Float)
    #: Ponte opcional com o Teaching Engine (migration 0007). Nulo em todo
    #: bloco existente: `block.status == "completed"` continua sendo só sinal
    #: de atividade concluída, nunca de domínio — ver `app.core.teaching`.
    objective_id: Mapped[str|None]=mapped_column(ForeignKey("learning_objectives.id", ondelete="SET NULL"), index=True)

class StudySession(UUIDMixin, Base):
    __tablename__="study_sessions"
    user_language_id: Mapped[str]=mapped_column(ForeignKey("user_languages.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now); ended_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    status: Mapped[str]=mapped_column(String(20), default="active"); summary_short: Mapped[str|None]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class Lesson(UUIDMixin, Base):
    __tablename__="lessons"
    study_session_id: Mapped[str|None]=mapped_column(ForeignKey("study_sessions.id", ondelete="SET NULL"))
    user_language_id: Mapped[str]=mapped_column(ForeignKey("user_languages.id", ondelete="CASCADE"), index=True)
    title: Mapped[str]=mapped_column(String(200)); objective: Mapped[str]=mapped_column(Text); content_json: Mapped[dict]=mapped_column(JSON, default=dict)
    status: Mapped[str]=mapped_column(String(20), default="draft"); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class LessonActivity(UUIDMixin, Base):
    __tablename__="lesson_activities"; __table_args__=(UniqueConstraint("lesson_id","position"),)
    lesson_id: Mapped[str]=mapped_column(ForeignKey("lessons.id", ondelete="CASCADE")); position: Mapped[int]=mapped_column(Integer)
    activity_type: Mapped[str]=mapped_column(String(50)); prompt: Mapped[str]=mapped_column(Text); payload_json: Mapped[dict]=mapped_column(JSON, default=dict)
    status: Mapped[str]=mapped_column(String(20), default="pending")

class Exercise(UUIDMixin, Base):
    __tablename__="exercises"
    lesson_activity_id: Mapped[str|None]=mapped_column(ForeignKey("lesson_activities.id", ondelete="SET NULL"))
    user_language_id: Mapped[str]=mapped_column(ForeignKey("user_languages.id", ondelete="CASCADE"))
    exercise_type: Mapped[str]=mapped_column(String(50)); prompt: Mapped[str]=mapped_column(Text); answer_key_json: Mapped[dict]=mapped_column(JSON, default=dict)
    difficulty: Mapped[str]=mapped_column(String(20), default="medium"); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class ExerciseAttempt(UUIDMixin, Base):
    __tablename__="exercise_attempts"
    exercise_id: Mapped[str]=mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"), index=True)
    study_session_id: Mapped[str|None]=mapped_column(ForeignKey("study_sessions.id", ondelete="SET NULL"))
    response_json: Mapped[dict]=mapped_column(JSON, default=dict); is_correct: Mapped[bool]=mapped_column(Boolean)
    score: Mapped[float|None]=mapped_column(Float); feedback_json: Mapped[dict]=mapped_column(JSON, default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class Conversation(UUIDMixin, Base):
    __tablename__="conversations"
    study_session_id: Mapped[str]=mapped_column(ForeignKey("study_sessions.id", ondelete="CASCADE"))
    user_language_id: Mapped[str]=mapped_column(ForeignKey("user_languages.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str]=mapped_column(String(20), default="text"); topic: Mapped[str]=mapped_column(String(200))
    status: Mapped[str]=mapped_column(String(20), default="active"); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    ended_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))

class ConversationMessage(UUIDMixin, Base):
    __tablename__="conversation_messages"
    conversation_id: Mapped[str]=mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str]=mapped_column(String(20)); content_text: Mapped[str]=mapped_column(Text); corrections_json: Mapped[dict|None]=mapped_column(JSON)
    source: Mapped[str]=mapped_column(String(20), default="text"); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class VocabularyItem(UUIDMixin, Base):
    __tablename__="vocabulary_items"
    user_language_id: Mapped[str]=mapped_column(ForeignKey("user_languages.id", ondelete="CASCADE"), index=True)
    term: Mapped[str]=mapped_column(String(200), index=True); reading_or_pinyin: Mapped[str|None]=mapped_column(String(200))
    translation_pt: Mapped[str]=mapped_column(String(300)); notes: Mapped[str|None]=mapped_column(Text); status: Mapped[str]=mapped_column(String(20), default="learning")
    interval_days: Mapped[int]=mapped_column(Integer, default=1); next_review_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class VocabularyExample(UUIDMixin, Base):
    __tablename__="vocabulary_examples"
    vocabulary_item_id: Mapped[str]=mapped_column(ForeignKey("vocabulary_items.id", ondelete="CASCADE"), index=True)
    example_text: Mapped[str]=mapped_column(Text); translation_pt: Mapped[str|None]=mapped_column(Text); audio_ref: Mapped[str|None]=mapped_column(String(500))

class ReviewItem(UUIDMixin, Base):
    __tablename__="review_items"
    user_language_id: Mapped[str]=mapped_column(ForeignKey("user_languages.id", ondelete="CASCADE"), index=True)
    item_type: Mapped[str]=mapped_column(String(50)); reference_id: Mapped[str]=mapped_column(String(36), index=True)
    priority: Mapped[int]=mapped_column(Integer, default=1); interval_days: Mapped[int]=mapped_column(Integer, default=1)
    next_review_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, index=True)
    suspended: Mapped[bool]=mapped_column(Boolean, default=False); mastery_state: Mapped[str]=mapped_column(String(20), default="learning")
    payload_json: Mapped[dict]=mapped_column(JSON, default=dict); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class GrammarTopic(UUIDMixin, Base):
    __tablename__="grammar_topics"; __table_args__=(UniqueConstraint("language_id","code"),)
    language_id: Mapped[str]=mapped_column(ForeignKey("languages.id"), index=True); code: Mapped[str]=mapped_column(String(80))
    title_pt: Mapped[str]=mapped_column(String(200)); description: Mapped[str]=mapped_column(Text); difficulty_band: Mapped[str]=mapped_column(String(30))

class UserGrammarProgress(UUIDMixin, Base):
    __tablename__="user_grammar_progress"; __table_args__=(UniqueConstraint("user_language_id","grammar_topic_id"),)
    user_language_id: Mapped[str]=mapped_column(ForeignKey("user_languages.id", ondelete="CASCADE"))
    grammar_topic_id: Mapped[str]=mapped_column(ForeignKey("grammar_topics.id"))
    mastery: Mapped[float]=mapped_column(Float, default=0); last_practiced_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    error_count: Mapped[int]=mapped_column(Integer, default=0); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class PronunciationAttempt(UUIDMixin, Base):
    __tablename__="pronunciation_attempts"
    user_language_id: Mapped[str]=mapped_column(ForeignKey("user_languages.id", ondelete="CASCADE"), index=True)
    study_session_id: Mapped[str|None]=mapped_column(ForeignKey("study_sessions.id", ondelete="SET NULL"))
    target_text: Mapped[str]=mapped_column(Text); transcript: Mapped[str|None]=mapped_column(Text); score: Mapped[float|None]=mapped_column(Float)
    feedback_json: Mapped[dict]=mapped_column(JSON, default=dict); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class ListeningActivity(UUIDMixin, Base):
    __tablename__="listening_activities"
    user_language_id: Mapped[str]=mapped_column(ForeignKey("user_languages.id", ondelete="CASCADE"), index=True)
    study_session_id: Mapped[str|None]=mapped_column(ForeignKey("study_sessions.id", ondelete="SET NULL"))
    prompt: Mapped[str]=mapped_column(Text); audio_source_type: Mapped[str]=mapped_column(String(30), default="tts")
    questions_json: Mapped[list]=mapped_column(JSON, default=list); result_json: Mapped[dict]=mapped_column(JSON, default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class WritingSubmission(UUIDMixin, Base):
    __tablename__="writing_submissions"
    user_language_id: Mapped[str]=mapped_column(ForeignKey("user_languages.id", ondelete="CASCADE"), index=True)
    study_session_id: Mapped[str|None]=mapped_column(ForeignKey("study_sessions.id", ondelete="SET NULL"))
    prompt: Mapped[str]=mapped_column(Text); content_text: Mapped[str]=mapped_column(Text); feedback_json: Mapped[dict]=mapped_column(JSON, default=dict)
    score: Mapped[float|None]=mapped_column(Float); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class Assessment(UUIDMixin, Base):
    __tablename__="assessments"
    user_language_id: Mapped[str]=mapped_column(ForeignKey("user_languages.id", ondelete="CASCADE"), index=True)
    assessment_type: Mapped[str]=mapped_column(String(30), default="diagnostic"); framework_ref: Mapped[str|None]=mapped_column(String(30))
    status: Mapped[str]=mapped_column(String(20), default="pending"); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))

class AssessmentQuestion(UUIDMixin, Base):
    __tablename__="assessment_questions"; __table_args__=(UniqueConstraint("assessment_id","position"),)
    assessment_id: Mapped[str]=mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    position: Mapped[int]=mapped_column(Integer); skill: Mapped[str]=mapped_column(String(30)); prompt: Mapped[str]=mapped_column(Text)
    payload_json: Mapped[dict]=mapped_column(JSON, default=dict)

class AssessmentAttempt(UUIDMixin, Base):
    __tablename__="assessment_attempts"
    assessment_id: Mapped[str]=mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[str|None]=mapped_column(ForeignKey("assessment_questions.id", ondelete="SET NULL"))
    response_json: Mapped[dict]=mapped_column(JSON, default=dict); result_json: Mapped[dict]=mapped_column(JSON, default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class PlacementTest(UUIDMixin, Base):
    """Teste de nivelamento CEFR. Distinto do stub legado `assessments`."""
    __tablename__="placement_tests"
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_code: Mapped[str]=mapped_column(String(10), index=True)
    status: Mapped[str]=mapped_column(String(20), default="pending", index=True)
    version: Mapped[int]=mapped_column(Integer, default=1)
    source: Mapped[str]=mapped_column(String(30), default="placement_test")
    started_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    current_level_band: Mapped[str|None]=mapped_column(String(10))
    overall_level: Mapped[str|None]=mapped_column(String(10))
    confidence_score: Mapped[float|None]=mapped_column(Float)
    total_score: Mapped[float|None]=mapped_column(Float)
    duration_seconds: Mapped[int|None]=mapped_column(Integer)
    result_json: Mapped[dict|None]=mapped_column(JSON, default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class PlacementTestSection(UUIDMixin, Base):
    __tablename__="placement_test_sections"; __table_args__=(UniqueConstraint("test_id","skill"),)
    test_id: Mapped[str]=mapped_column(ForeignKey("placement_tests.id", ondelete="CASCADE"), index=True)
    skill: Mapped[str]=mapped_column(String(30))
    score: Mapped[float]=mapped_column(Float, default=0)
    max_score: Mapped[float]=mapped_column(Float, default=0)
    estimated_level: Mapped[str|None]=mapped_column(String(10))
    confidence_score: Mapped[float|None]=mapped_column(Float)
    status: Mapped[str]=mapped_column(String(30), default="assessed")
    completed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))

class PlacementItem(UUIDMixin, Base):
    """Item do banco de nivelamento. Carregado por seed versionado, não por migration."""
    __tablename__="placement_items"; __table_args__=(UniqueConstraint("language_code","external_key"),)
    external_key: Mapped[str]=mapped_column(String(80), index=True)
    language_code: Mapped[str]=mapped_column(String(10), index=True)
    cefr_level: Mapped[str]=mapped_column(String(10), index=True)
    skill: Mapped[str]=mapped_column(String(30), index=True)
    item_type: Mapped[str]=mapped_column(String(40))
    prompt: Mapped[str]=mapped_column(Text)
    instructions: Mapped[str|None]=mapped_column(Text)
    passage: Mapped[str|None]=mapped_column(Text)
    options_json: Mapped[list|None]=mapped_column(JSON, default=list)
    correct_answer_json: Mapped[dict|None]=mapped_column(JSON, default=dict)
    explanation: Mapped[str|None]=mapped_column(Text)
    audio_url: Mapped[str|None]=mapped_column(String(500))
    audio_script: Mapped[str|None]=mapped_column(Text)
    rubric_json: Mapped[dict|None]=mapped_column(JSON, default=dict)
    difficulty: Mapped[float]=mapped_column(Float, default=0.5)
    discrimination: Mapped[float]=mapped_column(Float, default=1.0)
    is_active: Mapped[bool]=mapped_column(Boolean, default=True, index=True)
    version: Mapped[int]=mapped_column(Integer, default=1)
    # Proveniência (migration 0004): sem isso não há como auditar a origem de um
    # item nem remover uma fonte inteira se a licença mudar.
    source: Mapped[str|None]=mapped_column(String(60), index=True)
    license: Mapped[str|None]=mapped_column(String(80))
    attribution: Mapped[str|None]=mapped_column(Text)
    source_ref: Mapped[str|None]=mapped_column(String(200))
    #: pending_review | approved | rejected. Item importado nunca é servido ao
    #: aluno antes de revisão — calibragem automática de nível é heurística.
    review_status: Mapped[str|None]=mapped_column(String(20), index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class PlacementTestAnswer(UUIDMixin, Base):
    __tablename__="placement_test_answers"; __table_args__=(UniqueConstraint("test_id","item_id"),)
    test_id: Mapped[str]=mapped_column(ForeignKey("placement_tests.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[str]=mapped_column(ForeignKey("placement_items.id", ondelete="CASCADE"), index=True)
    skill: Mapped[str]=mapped_column(String(30))
    cefr_level: Mapped[str]=mapped_column(String(10))
    answer_json: Mapped[dict|None]=mapped_column(JSON, default=dict)
    is_correct: Mapped[bool|None]=mapped_column(Boolean)
    raw_score: Mapped[float|None]=mapped_column(Float)
    normalized_score: Mapped[float|None]=mapped_column(Float)
    response_time_ms: Mapped[int|None]=mapped_column(Integer)
    evaluated_by: Mapped[str]=mapped_column(String(30), default="auto")
    feedback_json: Mapped[dict|None]=mapped_column(JSON, default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class ProgressMetric(UUIDMixin, Base):
    __tablename__="progress_metrics"
    user_language_id: Mapped[str]=mapped_column(ForeignKey("user_languages.id", ondelete="CASCADE"), index=True)
    metric_key: Mapped[str]=mapped_column(String(80)); metric_value: Mapped[float]=mapped_column(Float); period: Mapped[str]=mapped_column(String(30))
    computed_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now); source: Mapped[str]=mapped_column(String(50))

class UserPreference(UUIDMixin, Base):
    __tablename__="user_preferences"
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    default_language_id: Mapped[str|None]=mapped_column(ForeignKey("languages.id", ondelete="SET NULL"))
    tts_speed: Mapped[float]=mapped_column(Float, default=1.0); ui_prefs_json: Mapped[dict]=mapped_column(JSON, default=dict)
    timezone: Mapped[str]=mapped_column(String(64), default="America/Sao_Paulo")
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class PlacementItemDelivery(UUIDMixin, Base):
    """Entrega de item de nivelamento a um teste (anti-IDOR / anti-escolha de item)."""
    __tablename__="placement_item_deliveries"
    __table_args__=(UniqueConstraint("test_id", "item_id", name="uq_placement_delivery_test_item"),)
    test_id: Mapped[str]=mapped_column(ForeignKey("placement_tests.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[str]=mapped_column(ForeignKey("placement_items.id", ondelete="CASCADE"), index=True)
    delivered_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class ContentSource(UUIDMixin, Base):
    __tablename__="content_sources"
    language_id: Mapped[str|None]=mapped_column(ForeignKey("languages.id", ondelete="SET NULL"), index=True)
    title: Mapped[str]=mapped_column(String(300))
    author: Mapped[str|None]=mapped_column(String(200))
    publisher: Mapped[str|None]=mapped_column(String(200))
    source_type: Mapped[str]=mapped_column(String(40), default="book")
    original_filename: Mapped[str|None]=mapped_column(String(300))
    file_hash: Mapped[str|None]=mapped_column(String(64), index=True)
    page_count: Mapped[int|None]=mapped_column(Integer)
    usage_policy: Mapped[str]=mapped_column(String(40), default="UNREVIEWED", index=True)
    license_name: Mapped[str|None]=mapped_column(String(120))
    license_reference: Mapped[str|None]=mapped_column(String(300))
    attribution_text: Mapped[str|None]=mapped_column(Text)
    allow_excerpt: Mapped[bool]=mapped_column(Boolean, default=False)
    allow_concept_extraction: Mapped[bool]=mapped_column(Boolean, default=True)
    commercial_use_reviewed: Mapped[bool]=mapped_column(Boolean, default=False)
    review_status: Mapped[str]=mapped_column(String(40), default="PENDING_REVIEW", index=True)
    notes_json: Mapped[dict]=mapped_column(JSON, default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class ContentUnit(UUIDMixin, Base):
    __tablename__="content_units"
    source_id: Mapped[str]=mapped_column(ForeignKey("content_sources.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[str|None]=mapped_column(ForeignKey("languages.id", ondelete="SET NULL"), index=True)
    cefr_level: Mapped[str]=mapped_column(String(10), index=True)
    skill: Mapped[str]=mapped_column(String(40), index=True)
    mode: Mapped[str]=mapped_column(String(40), index=True)
    content_type: Mapped[str]=mapped_column(String(40), default="lesson_unit")
    topic: Mapped[str|None]=mapped_column(String(200))
    title: Mapped[str]=mapped_column(String(300))
    payload_json: Mapped[dict]=mapped_column(JSON, default=dict)
    origin_type: Mapped[str]=mapped_column(String(40), default="CONCEPT_DERIVED")
    source_page_start: Mapped[int|None]=mapped_column(Integer)
    source_page_end: Mapped[int|None]=mapped_column(Integer)
    excerpt_text: Mapped[str|None]=mapped_column(Text)
    attribution_text: Mapped[str|None]=mapped_column(Text)
    similarity_score: Mapped[float|None]=mapped_column(Float)
    validation_status: Mapped[str]=mapped_column(String(40), default="PENDING_REVIEW", index=True)
    is_active: Mapped[bool]=mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class ContentReview(UUIDMixin, Base):
    __tablename__="content_reviews"
    content_unit_id: Mapped[str]=mapped_column(ForeignKey("content_units.id", ondelete="CASCADE"), index=True)
    reviewer_user_id: Mapped[str|None]=mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    linguistic_status: Mapped[str]=mapped_column(String(40), default="PENDING_REVIEW")
    pedagogical_status: Mapped[str]=mapped_column(String(40), default="PENDING_REVIEW")
    rights_status: Mapped[str]=mapped_column(String(40), default="PENDING_REVIEW")
    notes: Mapped[str|None]=mapped_column(Text)
    reviewed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class LessonContentUsage(UUIDMixin, Base):
    __tablename__="lesson_content_usages"
    lesson_id: Mapped[str]=mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    content_unit_id: Mapped[str]=mapped_column(ForeignKey("content_units.id", ondelete="CASCADE"), index=True)
    usage_type: Mapped[str]=mapped_column(String(40), default="primary")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class AuditLog(UUIDMixin, Base):
    __tablename__="audit_logs"
    user_id: Mapped[str|None]=mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str]=mapped_column(String(80), index=True); resource_type: Mapped[str]=mapped_column(String(80))
    resource_id: Mapped[str|None]=mapped_column(String(36)); ip_hash: Mapped[str|None]=mapped_column(String(128))
    metadata_json: Mapped[dict]=mapped_column(JSON, default=dict); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class Session(UUIDMixin, Base):
    __tablename__="sessions"
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str]=mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True)); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    revoked_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))

# ------------------------------------------------------------ Teaching Engine
#
# Núcleo pedagógico entre currículo e atividades (migration 0007). Distingue
# atividade concluída (CurriculumBlock/Lesson, acima) de aprendizagem
# demonstrada. `LearningObjective` é catálogo versionado por idioma+nível —
# mesma separação de `GrammarTopic`/`UserGrammarProgress`: o objetivo não
# pertence a um usuário, o progresso sim (`UserObjectiveProgress`).

class LearningObjective(UUIDMixin, Base):
    """Aquilo que o aluno precisa ser capaz de **fazer** — observável.

    `code` segue o padrão `EN-A1-CAN-001`. `can_do` é a descrição observável
    ("diz nome, origem, profissão"), não um tópico de estudo ("verbo to be").
    """
    __tablename__="learning_objectives"; __table_args__=(UniqueConstraint("language_id","code"),)
    language_id: Mapped[str]=mapped_column(ForeignKey("languages.id"), index=True)
    level: Mapped[str]=mapped_column(String(10), index=True)
    code: Mapped[str]=mapped_column(String(40))
    title: Mapped[str]=mapped_column(String(200))
    can_do: Mapped[str]=mapped_column(Text)
    description: Mapped[str|None]=mapped_column(Text)
    #: `app.core.curriculum.BlockSkill` ou `app.core.levels.Skill` — o que este
    #: objetivo treina, não uma competência CEFR isolada necessariamente.
    skill_focus: Mapped[str]=mapped_column(String(30), index=True)
    prerequisites_json: Mapped[list]=mapped_column(JSON, default=list)
    target_vocabulary_json: Mapped[list]=mapped_column(JSON, default=list)
    target_patterns_json: Mapped[list]=mapped_column(JSON, default=list)
    pronunciation_focus_json: Mapped[list]=mapped_column(JSON, default=list)
    #: Override de `app.core.teaching.DEFAULT_MASTERY_POLICY`. Vazio = padrão.
    mastery_policy_json: Mapped[dict]=mapped_column(JSON, default=dict)
    is_active: Mapped[bool]=mapped_column(Boolean, default=True, index=True)
    version: Mapped[int]=mapped_column(Integer, default=1)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class UserObjectiveProgress(UUIDMixin, Base):
    """Estado de domínio (`app.core.teaching.MasteryState`) de um aluno sobre
    um objetivo. Nunca setado a `mastered` diretamente por request — só
    `evaluate_mastery` decide, a partir de evidência registrada."""
    __tablename__="user_objective_progress"; __table_args__=(UniqueConstraint("user_language_id","objective_id"),)
    user_language_id: Mapped[str]=mapped_column(ForeignKey("user_languages.id", ondelete="CASCADE"), index=True)
    objective_id: Mapped[str]=mapped_column(ForeignKey("learning_objectives.id", ondelete="CASCADE"), index=True)
    state: Mapped[str]=mapped_column(String(30), default="not_started", index=True)
    started_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    mastered_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    last_evaluated_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    last_reasons_json: Mapped[list]=mapped_column(JSON, default=list)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class LearningAttempt(UUIDMixin, Base):
    """Uma produção relevante do aluno para um objetivo. Não guarda áudio bruto
    — `student_response` é sempre texto (transcrição, resposta, texto)."""
    __tablename__="learning_attempts"
    user_language_id: Mapped[str]=mapped_column(ForeignKey("user_languages.id", ondelete="CASCADE"), index=True)
    objective_id: Mapped[str]=mapped_column(ForeignKey("learning_objectives.id", ondelete="CASCADE"), index=True)
    curriculum_block_id: Mapped[str|None]=mapped_column(ForeignKey("curriculum_blocks.id", ondelete="SET NULL"), index=True)
    lesson_id: Mapped[str|None]=mapped_column(ForeignKey("lessons.id", ondelete="SET NULL"))
    activity_type: Mapped[str]=mapped_column(String(50))
    attempt_number: Mapped[int]=mapped_column(Integer, default=1)
    student_response: Mapped[str|None]=mapped_column(Text)
    result: Mapped[str]=mapped_column(String(20), default="pending")
    score: Mapped[float|None]=mapped_column(Float)
    #: Quem avaliou: "heuristic", "openrouter", "groq", "self" etc. Rastreável,
    #: mas nunca autoridade para marcar mastery sozinho — ver `evaluate_mastery`.
    provider: Mapped[str|None]=mapped_column(String(30))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    evaluated_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))

class LearningEvidence(UUIDMixin, Base):
    """Evidência de aprendizagem — o que faz `evaluate_mastery` mover o estado
    além de LEARNING/PRACTICING. "Clicou em concluir" nunca gera isto."""
    __tablename__="learning_evidence"
    user_language_id: Mapped[str]=mapped_column(ForeignKey("user_languages.id", ondelete="CASCADE"), index=True)
    objective_id: Mapped[str]=mapped_column(ForeignKey("learning_objectives.id", ondelete="CASCADE"), index=True)
    attempt_id: Mapped[str]=mapped_column(ForeignKey("learning_attempts.id", ondelete="CASCADE"), index=True)
    #: `app.core.teaching.EvidenceType`.
    evidence_type: Mapped[str]=mapped_column(String(40))
    is_transfer: Mapped[bool]=mapped_column(Boolean, default=False)
    weight: Mapped[float]=mapped_column(Float, default=1.0)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class LearningError(UUIDMixin, Base):
    """Erro real do aluno. `resolved` só vira True quando um retry decorrente
    de uma `Remediation` volta correto — ver `teaching_engine.evaluate_attempt`."""
    __tablename__="learning_errors"
    user_language_id: Mapped[str]=mapped_column(ForeignKey("user_languages.id", ondelete="CASCADE"), index=True)
    objective_id: Mapped[str|None]=mapped_column(ForeignKey("learning_objectives.id", ondelete="SET NULL"), index=True)
    attempt_id: Mapped[str|None]=mapped_column(ForeignKey("learning_attempts.id", ondelete="SET NULL"))
    #: `app.core.teaching.ErrorCategory`.
    category: Mapped[str]=mapped_column(String(40), index=True)
    original: Mapped[str]=mapped_column(Text)
    expected: Mapped[str|None]=mapped_column(Text)
    explanation: Mapped[str|None]=mapped_column(Text)
    severity: Mapped[str]=mapped_column(String(20), default="moderate")
    language_feature: Mapped[str|None]=mapped_column(String(120))
    recurring: Mapped[bool]=mapped_column(Boolean, default=False)
    resolved: Mapped[bool]=mapped_column(Boolean, default=False, index=True)
    occurrences: Mapped[int]=mapped_column(Integer, default=1)
    first_seen: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    last_seen: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class Remediation(UUIDMixin, Base):
    """Ação recomendada após um erro. `next_attempt_id` é preenchido quando o
    retry decorrente é registrado — liga o ciclo erro → remediação → retry."""
    __tablename__="remediations"
    error_id: Mapped[str]=mapped_column(ForeignKey("learning_errors.id", ondelete="CASCADE"), index=True)
    #: `app.core.teaching.RemediationAction`.
    action: Mapped[str]=mapped_column(String(30))
    reason: Mapped[str|None]=mapped_column(Text)
    next_attempt_id: Mapped[str|None]=mapped_column(ForeignKey("learning_attempts.id", ondelete="SET NULL"))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
