"""Boletim da lição: snapshot da correção junto da tentativa.

Aditiva e nula por padrão. Tentativas antigas ficam sem snapshot — o boletim
declara isso em vez de reconstruir correção a posteriori, o que seria inventar
o que o aluno viu na hora.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0015_lesson_report"
down_revision = "0014_learning_progress"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_column("learning_attempts", "report_json"):
        op.add_column(
            "learning_attempts",
            sa.Column("report_json", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    if _has_column("learning_attempts", "report_json"):
        op.drop_column("learning_attempts", "report_json")
