from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
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
    __tablename__="user_languages"; __table_args__=(UniqueConstraint("user_id","language_id"),)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[str]=mapped_column(ForeignKey("languages.id"), index=True)
    level_estimate: Mapped[str|None]=mapped_column(String(30))
    onboarding_completed: Mapped[bool]=mapped_column(Boolean, default=False)
    diagnostic_completed: Mapped[bool]=mapped_column(Boolean, default=False)
    is_active: Mapped[bool]=mapped_column(Boolean, default=False, index=True)
    started_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

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
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

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
