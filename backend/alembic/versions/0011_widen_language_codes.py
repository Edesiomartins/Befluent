"""Alarga colunas de código de idioma para caber `la-classical` (12 chars).

Aditiva sobre 0010. Não altera dados existentes de `la`.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0011_widen_language_codes"
down_revision = "0010_password_reset_tokens"
branch_labels = None
depends_on = None

#: Códigos internos podem incluir variantes como `la-classical`.
_LANG_CODE_LEN = 32

_TABLE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("languages", "code"),
    ("placement_tests", "language_code"),
    ("placement_items", "language_code"),
)


def _widen(table: str, column: str) -> None:
    op.alter_column(
        table,
        column,
        existing_type=sa.String(length=10),
        type_=sa.String(length=_LANG_CODE_LEN),
        existing_nullable=False,
    )


def _narrow(table: str, column: str) -> None:
    op.alter_column(
        table,
        column,
        existing_type=sa.String(length=_LANG_CODE_LEN),
        type_=sa.String(length=10),
        existing_nullable=False,
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    for table, column in _TABLE_COLUMNS:
        if table not in tables:
            continue
        cols = {c["name"] for c in inspector.get_columns(table)}
        if column not in cols:
            continue
        _widen(table, column)

    # Coluna opcional de cache/telemetria (migration 0008), se existir.
    if "ai_generation_logs" in tables:
        cols = {c["name"] for c in inspector.get_columns("ai_generation_logs")}
        if "language_code" in cols:
            op.alter_column(
                "ai_generation_logs",
                "language_code",
                existing_type=sa.String(length=10),
                type_=sa.String(length=_LANG_CODE_LEN),
                existing_nullable=True,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    for table, column in reversed(_TABLE_COLUMNS):
        if table not in tables:
            continue
        cols = {c["name"] for c in inspector.get_columns(table)}
        if column not in cols:
            continue
        _narrow(table, column)

    if "ai_generation_logs" in tables:
        cols = {c["name"] for c in inspector.get_columns("ai_generation_logs")}
        if "language_code" in cols:
            op.alter_column(
                "ai_generation_logs",
                "language_code",
                existing_type=sa.String(length=_LANG_CODE_LEN),
                type_=sa.String(length=10),
                existing_nullable=True,
            )
