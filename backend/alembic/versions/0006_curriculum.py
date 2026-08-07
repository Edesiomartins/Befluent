"""Cronograma estruturado de estudo (currículo por dias e semanas).

Numeração: o prompt de reestruturação pedia `0004_curriculum`, mas `0004` e
`0005` já existiam neste repositório. Esta é a próxima revisão livre.

Aditiva: cria quatro tabelas novas, sem DROP nem ALTER de nada existente.
Downgrade remove apenas o que esta revisão criou.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0006_curriculum"
down_revision = "0005_content_library_and_session_hardening"
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    return name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _has_table(inspector, "curricula"):
        op.create_table(
            "curricula",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_language_id", sa.String(length=36), sa.ForeignKey("user_languages.id", ondelete="CASCADE"), nullable=False),
            sa.Column("duration_days", sa.Integer(), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("target_level", sa.String(length=10), nullable=False),
            sa.Column("entry_level", sa.String(length=10), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("generated_from", sa.String(length=30), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_curricula_user_language_id", "curricula", ["user_language_id"])
        op.create_index("ix_curricula_status", "curricula", ["status"])

    if not _has_table(inspector, "curriculum_weeks"):
        op.create_table(
            "curriculum_weeks",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("curriculum_id", sa.String(length=36), sa.ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False),
            sa.Column("week_number", sa.Integer(), nullable=False),
            sa.Column("theme", sa.String(length=200), nullable=False),
            sa.Column("cefr_focus", sa.String(length=10), nullable=False),
            sa.Column("is_checkpoint", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.UniqueConstraint("curriculum_id", "week_number", name="uq_curriculum_week_number"),
        )
        op.create_index("ix_curriculum_weeks_curriculum_id", "curriculum_weeks", ["curriculum_id"])

    if not _has_table(inspector, "curriculum_days"):
        op.create_table(
            "curriculum_days",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("week_id", sa.String(length=36), sa.ForeignKey("curriculum_weeks.id", ondelete="CASCADE"), nullable=False),
            sa.Column("day_number", sa.Integer(), nullable=False),
            sa.Column("scheduled_date", sa.Date(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("week_id", "day_number", name="uq_curriculum_day_number"),
        )
        op.create_index("ix_curriculum_days_week_id", "curriculum_days", ["week_id"])
        op.create_index("ix_curriculum_days_day_number", "curriculum_days", ["day_number"])
        op.create_index("ix_curriculum_days_scheduled_date", "curriculum_days", ["scheduled_date"])
        op.create_index("ix_curriculum_days_status", "curriculum_days", ["status"])

    if not _has_table(inspector, "curriculum_blocks"):
        op.create_table(
            "curriculum_blocks",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("day_id", sa.String(length=36), sa.ForeignKey("curriculum_days.id", ondelete="CASCADE"), nullable=False),
            sa.Column("skill", sa.String(length=30), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("estimated_minutes", sa.Integer(), nullable=False),
            sa.Column("cefr_level", sa.String(length=10), nullable=False),
            sa.Column("topic", sa.String(length=200), nullable=False, server_default=""),
            sa.Column("lesson_ref", sa.String(length=36), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("score", sa.Float(), nullable=True),
            sa.UniqueConstraint("day_id", "position", name="uq_curriculum_block_position"),
        )
        op.create_index("ix_curriculum_blocks_day_id", "curriculum_blocks", ["day_id"])
        op.create_index("ix_curriculum_blocks_skill", "curriculum_blocks", ["skill"])
        op.create_index("ix_curriculum_blocks_lesson_ref", "curriculum_blocks", ["lesson_ref"])
        op.create_index("ix_curriculum_blocks_status", "curriculum_blocks", ["status"])


def downgrade() -> None:
    """Remove apenas as tabelas criadas aqui, na ordem das dependências."""
    bind = op.get_bind()
    inspector = inspect(bind)
    for table in ("curriculum_blocks", "curriculum_days", "curriculum_weeks", "curricula"):
        if _has_table(inspector, table):
            op.drop_table(table)
