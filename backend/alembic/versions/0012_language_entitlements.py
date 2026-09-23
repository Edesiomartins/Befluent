"""Cria concessões de acesso por idioma.

Aditiva sobre 0011: cria `language_entitlements` e faz backfill `legacy` para
pares usuário↔idioma já existentes.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0012_language_entitlements"
down_revision = "0011_widen_language_codes"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def _existing_indexes(table_name: str) -> set[str]:
    return {idx["name"] for idx in inspect(op.get_bind()).get_indexes(table_name) if idx.get("name")}


def _create_index_if_missing(
    name: str, table_name: str, columns: list[str], *, unique: bool = False
) -> None:
    if name not in _existing_indexes(table_name):
        op.create_index(name, table_name, columns, unique=unique)


def _create_table() -> None:
    if _table_exists("language_entitlements"):
        return
    op.create_table(
        "language_entitlements",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("language_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["language_id"], ["languages.id"]),
    )


def _ensure_indexes() -> None:
    _create_index_if_missing("ix_language_entitlements_user_id", "language_entitlements", ["user_id"])
    _create_index_if_missing(
        "ix_language_entitlements_language_id", "language_entitlements", ["language_id"]
    )
    _create_index_if_missing("ix_language_entitlements_source", "language_entitlements", ["source"])
    _create_index_if_missing("ix_language_entitlements_status", "language_entitlements", ["status"])
    _create_index_if_missing(
        "ix_language_entitlements_starts_at", "language_entitlements", ["starts_at"]
    )
    _create_index_if_missing(
        "ix_language_entitlements_expires_at", "language_entitlements", ["expires_at"]
    )
    _create_index_if_missing(
        "ix_language_entitlements_cancelled_at", "language_entitlements", ["cancelled_at"]
    )
    _create_index_if_missing(
        "ix_language_entitlements_user_language",
        "language_entitlements",
        ["user_id", "language_id"],
    )
    _create_index_if_missing(
        "ix_language_entitlements_status_period",
        "language_entitlements",
        ["status", "starts_at", "expires_at"],
    )


def _backfill_legacy() -> None:
    language_entitlements = sa.table(
        "language_entitlements",
        sa.column("id"),
        sa.column("user_id"),
        sa.column("language_id"),
        sa.column("source"),
        sa.column("status"),
        sa.column("starts_at"),
        sa.column("expires_at"),
        sa.column("cancelled_at"),
        sa.column("metadata_json"),
        sa.column("created_at"),
        sa.column("updated_at"),
    )
    user_languages = sa.table(
        "user_languages",
        sa.column("id"),
        sa.column("user_id"),
        sa.column("language_id"),
        sa.column("started_at"),
    )
    now = sa.func.current_timestamp()
    select_rows = sa.select(
        user_languages.c.id.label("id"),
        user_languages.c.user_id,
        user_languages.c.language_id,
        sa.literal("legacy").label("source"),
        sa.literal("active").label("status"),
        user_languages.c.started_at.label("starts_at"),
        sa.null().label("expires_at"),
        sa.null().label("cancelled_at"),
        sa.literal({}, type_=sa.JSON()).label("metadata_json"),
        now.label("created_at"),
        now.label("updated_at"),
    ).where(
        ~sa.exists(
            sa.select(1).where(
                language_entitlements.c.user_id == user_languages.c.user_id,
                language_entitlements.c.language_id == user_languages.c.language_id,
                language_entitlements.c.source == "legacy",
            )
        )
    )
    op.execute(language_entitlements.insert().from_select(list(language_entitlements.c), select_rows))


def upgrade() -> None:
    _create_table()
    _ensure_indexes()
    _backfill_legacy()


def downgrade() -> None:
    if _table_exists("language_entitlements"):
        op.drop_table("language_entitlements")
