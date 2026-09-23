"""Estado observado de progresso e transições, sem segundo domínio.

Aditiva: não altera mastery, CEFR nem entitlements.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0014_learning_progress"
down_revision = "0013_vocabulary_learning_cycle"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    if not _table_exists("learning_progress_snapshots"):
        op.create_table(
            "learning_progress_snapshots",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_language_id", sa.String(length=36), nullable=False),
            sa.Column("cefr_level", sa.String(length=10), nullable=True),
            sa.Column("milestone_code", sa.String(length=20), nullable=True),
            sa.Column("milestone_index", sa.Integer(), nullable=True),
            sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_language_id"], ["user_languages.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("user_language_id"),
        )
        op.create_index(
            "ix_learning_progress_snapshots_user_language_id",
            "learning_progress_snapshots",
            ["user_language_id"],
        )
    if not _table_exists("learning_progress_events"):
        op.create_table(
            "learning_progress_events",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_language_id", sa.String(length=36), nullable=False),
            sa.Column("event_type", sa.String(length=40), nullable=False),
            sa.Column("dedupe_key", sa.String(length=160), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_language_id"], ["user_languages.id"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "user_language_id",
                "event_type",
                "dedupe_key",
                name="uq_learning_progress_event",
            ),
        )
        op.create_index(
            "ix_learning_progress_events_user_language_id",
            "learning_progress_events",
            ["user_language_id"],
        )
        op.create_index(
            "ix_learning_progress_events_event_type",
            "learning_progress_events",
            ["event_type"],
        )
        op.create_index(
            "ix_learning_progress_events_user_language",
            "learning_progress_events",
            ["user_language_id", "created_at"],
        )


def downgrade() -> None:
    if _table_exists("learning_progress_events"):
        op.drop_table("learning_progress_events")
    if _table_exists("learning_progress_snapshots"):
        op.drop_table("learning_progress_snapshots")
