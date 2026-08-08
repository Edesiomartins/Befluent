"""Teaching Engine V2 — flow, memória universal, cache de IA, pedagogia.

Aditiva sobre 0007:
- colunas em `learning_objectives` (`target_expressions_json`, `pedagogy_json`)
- `teaching_flow_sessions`
- `memory_schedules` + `memory_review_events`
- `ai_response_cache`

Sem DROP nem ALTER destrutivo. Downgrade remove apenas o que esta revisão criou.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0008_teaching_engine_v2"
down_revision = "0007_teaching_engine"
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    return name in inspector.get_table_names()


def _has_column(inspector, table: str, column: str) -> bool:
    if not _has_table(inspector, table):
        return False
    return column in {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if _has_table(inspector, "learning_objectives"):
        if not _has_column(inspector, "learning_objectives", "target_expressions_json"):
            op.add_column(
                "learning_objectives",
                sa.Column("target_expressions_json", sa.JSON(), nullable=True),
            )
        if not _has_column(inspector, "learning_objectives", "pedagogy_json"):
            op.add_column(
                "learning_objectives",
                sa.Column("pedagogy_json", sa.JSON(), nullable=True),
            )

    inspector = inspect(bind)
    if not _has_table(inspector, "teaching_flow_sessions"):
        op.create_table(
            "teaching_flow_sessions",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "user_language_id",
                sa.String(length=36),
                sa.ForeignKey("user_languages.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "objective_id",
                sa.String(length=36),
                sa.ForeignKey("learning_objectives.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "curriculum_block_id",
                sa.String(length=36),
                sa.ForeignKey("curriculum_blocks.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("phase", sa.String(length=30), nullable=False),
            sa.Column("activity_cursor", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("remediation_cycles", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_teaching_flow_sessions_user_language_id", "teaching_flow_sessions", ["user_language_id"])
        op.create_index("ix_teaching_flow_sessions_objective_id", "teaching_flow_sessions", ["objective_id"])
        op.create_index("ix_teaching_flow_sessions_curriculum_block_id", "teaching_flow_sessions", ["curriculum_block_id"])
        op.create_index("ix_teaching_flow_sessions_phase", "teaching_flow_sessions", ["phase"])
        op.create_index("ix_teaching_flow_sessions_status", "teaching_flow_sessions", ["status"])

    inspector = inspect(bind)
    if not _has_table(inspector, "memory_schedules"):
        op.create_table(
            "memory_schedules",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "user_language_id",
                sa.String(length=36),
                sa.ForeignKey("user_languages.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("subject_type", sa.String(length=40), nullable=False),
            sa.Column("subject_key", sa.String(length=160), nullable=False),
            sa.Column("state", sa.String(length=20), nullable=False),
            sa.Column("interval_days", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("lapse_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("strength", sa.Float(), nullable=False, server_default="0"),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column(
                "review_item_id",
                sa.String(length=36),
                sa.ForeignKey("review_items.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "user_language_id", "subject_type", "subject_key", name="uq_memory_schedule_subject"
            ),
        )
        op.create_index("ix_memory_schedules_user_language_id", "memory_schedules", ["user_language_id"])
        op.create_index("ix_memory_schedules_subject_type", "memory_schedules", ["subject_type"])
        op.create_index("ix_memory_schedules_due_at", "memory_schedules", ["due_at"])
        op.create_index("ix_memory_schedules_review_item_id", "memory_schedules", ["review_item_id"])

    inspector = inspect(bind)
    if not _has_table(inspector, "memory_review_events"):
        op.create_table(
            "memory_review_events",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "memory_schedule_id",
                sa.String(length=36),
                sa.ForeignKey("memory_schedules.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("rating", sa.String(length=20), nullable=False),
            sa.Column("result", sa.String(length=20), nullable=True),
            sa.Column("due_before", sa.DateTime(timezone=True), nullable=True),
            sa.Column("due_after", sa.DateTime(timezone=True), nullable=True),
            sa.Column("response_time_ms", sa.Integer(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "ix_memory_review_events_memory_schedule_id", "memory_review_events", ["memory_schedule_id"]
        )

    inspector = inspect(bind)
    if not _has_table(inspector, "ai_response_cache"):
        op.create_table(
            "ai_response_cache",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("cache_key", sa.String(length=64), nullable=False),
            sa.Column("capability", sa.String(length=40), nullable=False),
            sa.Column("language_code", sa.String(length=10), nullable=True),
            sa.Column("level", sa.String(length=10), nullable=True),
            sa.Column("provider", sa.String(length=30), nullable=True),
            sa.Column("model", sa.String(length=80), nullable=True),
            sa.Column("prompt_version", sa.String(length=40), nullable=False, server_default="v1"),
            sa.Column("response_json", sa.JSON(), nullable=False),
            sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("cache_key", name="uq_ai_response_cache_key"),
        )
        op.create_index("ix_ai_response_cache_cache_key", "ai_response_cache", ["cache_key"])
        op.create_index("ix_ai_response_cache_capability", "ai_response_cache", ["capability"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if _has_table(inspector, "ai_response_cache"):
        op.drop_table("ai_response_cache")
    inspector = inspect(bind)
    if _has_table(inspector, "memory_review_events"):
        op.drop_table("memory_review_events")
    inspector = inspect(bind)
    if _has_table(inspector, "memory_schedules"):
        op.drop_table("memory_schedules")
    inspector = inspect(bind)
    if _has_table(inspector, "teaching_flow_sessions"):
        op.drop_table("teaching_flow_sessions")

    inspector = inspect(bind)
    if _has_column(inspector, "learning_objectives", "pedagogy_json"):
        op.drop_column("learning_objectives", "pedagogy_json")
    if _has_column(inspector, "learning_objectives", "target_expressions_json"):
        op.drop_column("learning_objectives", "target_expressions_json")
