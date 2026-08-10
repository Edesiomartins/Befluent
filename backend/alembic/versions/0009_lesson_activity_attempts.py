"""LessonActivityAttempt — tentativas autoritativas de lições legadas.

Aditiva sobre 0008:
- tabela `lesson_activity_attempts` (append-only por geração)
- unique (lesson_id, activity_key, attempt_number) para idempotência

Não altera LearningAttempt / mastery. Downgrade remove apenas esta tabela.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0009_lesson_activity_attempts"
down_revision = "0008_teaching_engine_v2"
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    return name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if _has_table(inspector, "lesson_activity_attempts"):
        return

    op.create_table(
        "lesson_activity_attempts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("lesson_id", sa.String(length=36), sa.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "user_language_id",
            sa.String(length=36),
            sa.ForeignKey("user_languages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("activity_key", sa.String(length=120), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("activity_type", sa.String(length=50), nullable=False, server_default="multiple_choice"),
        sa.Column("answer_json", sa.JSON(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "revealed_correct_answer",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("feedback_json", sa.JSON(), nullable=False),
        sa.Column("question_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="submitted"),
        sa.Column(
            "retry_of_id",
            sa.String(length=36),
            sa.ForeignKey("lesson_activity_attempts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "pedagogical_effect",
            sa.String(length=40),
            nullable=False,
            server_default="completion_only",
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "lesson_id",
            "activity_key",
            "attempt_number",
            name="uq_lesson_activity_attempt_gen",
        ),
    )
    op.create_index(
        "ix_lesson_activity_attempts_lesson_id",
        "lesson_activity_attempts",
        ["lesson_id"],
    )
    op.create_index(
        "ix_lesson_activity_attempts_user_language_id",
        "lesson_activity_attempts",
        ["user_language_id"],
    )
    op.create_index(
        "ix_lesson_activity_attempts_activity_key",
        "lesson_activity_attempts",
        ["activity_key"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_table(inspector, "lesson_activity_attempts"):
        op.drop_table("lesson_activity_attempts")
