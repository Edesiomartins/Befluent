"""Biblioteca pedagógica, deliveries de placement e timezone do usuário.

Aditiva: sem DROP de dados. Downgrade é no-op seguro (metadados/sessão não
devem ser removidos automaticamente em ambientes com histórico).

O revision id precisa caber em alembic_version.version_num (VARCHAR(32) no
Postgres legado). Por isso o id curto `0005_content_sessions` — o nome longo
`0005_content_library_and_session_hardening` quebrou o deploy no Coolify.
Esta migration também amplia version_num para VARCHAR(64) para evitar o mesmo
erro em revisões futuras.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0005_content_sessions"
down_revision = "0004_item_provenance"
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    return name in inspector.get_table_names()


def _has_column(inspector, table: str, column: str) -> bool:
    if not _has_table(inspector, table):
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def _widen_alembic_version(bind, inspector) -> None:
    """Garante que version_num aceite ids > 32 caracteres."""
    if not _has_table(inspector, "alembic_version"):
        return
    cols = {c["name"]: c for c in inspector.get_columns("alembic_version")}
    col = cols.get("version_num")
    if not col:
        return
    col_type = col.get("type")
    length = getattr(col_type, "length", None)
    if length is not None and length >= 64:
        return
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.execute(sa.text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)"))
    elif dialect == "sqlite":
        # SQLite ignora length em VARCHAR; noop defensivo.
        return
    else:
        op.alter_column(
            "alembic_version",
            "version_num",
            existing_type=sa.String(length=32),
            type_=sa.String(length=64),
            existing_nullable=False,
        )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    _widen_alembic_version(bind, inspector)
    inspector = inspect(bind)

    if _has_table(inspector, "user_preferences") and not _has_column(
        inspector, "user_preferences", "timezone"
    ):
        op.add_column(
            "user_preferences",
            sa.Column("timezone", sa.String(length=64), nullable=False, server_default="America/Sao_Paulo"),
        )

    if not _has_table(inspector, "placement_item_deliveries"):
        op.create_table(
            "placement_item_deliveries",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("test_id", sa.String(length=36), sa.ForeignKey("placement_tests.id", ondelete="CASCADE"), nullable=False),
            sa.Column("item_id", sa.String(length=36), sa.ForeignKey("placement_items.id", ondelete="CASCADE"), nullable=False),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("test_id", "item_id", name="uq_placement_delivery_test_item"),
        )
        op.create_index("ix_placement_item_deliveries_test_id", "placement_item_deliveries", ["test_id"])
        op.create_index("ix_placement_item_deliveries_expires_at", "placement_item_deliveries", ["expires_at"])
        op.create_index("ix_placement_item_deliveries_consumed_at", "placement_item_deliveries", ["consumed_at"])

    if not _has_table(inspector, "content_sources"):
        op.create_table(
            "content_sources",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("language_id", sa.String(length=36), sa.ForeignKey("languages.id", ondelete="SET NULL"), nullable=True),
            sa.Column("title", sa.String(length=300), nullable=False),
            sa.Column("author", sa.String(length=200), nullable=True),
            sa.Column("publisher", sa.String(length=200), nullable=True),
            sa.Column("source_type", sa.String(length=40), nullable=False),
            sa.Column("original_filename", sa.String(length=300), nullable=True),
            sa.Column("file_hash", sa.String(length=64), nullable=True),
            sa.Column("page_count", sa.Integer(), nullable=True),
            sa.Column("usage_policy", sa.String(length=40), nullable=False),
            sa.Column("license_name", sa.String(length=120), nullable=True),
            sa.Column("license_reference", sa.String(length=300), nullable=True),
            sa.Column("attribution_text", sa.Text(), nullable=True),
            sa.Column("allow_excerpt", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("allow_concept_extraction", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("commercial_use_reviewed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("review_status", sa.String(length=40), nullable=False),
            sa.Column("notes_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_content_sources_file_hash", "content_sources", ["file_hash"])
        op.create_index("ix_content_sources_usage_policy", "content_sources", ["usage_policy"])
        op.create_index("ix_content_sources_review_status", "content_sources", ["review_status"])

    if not _has_table(inspector, "content_units"):
        op.create_table(
            "content_units",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("source_id", sa.String(length=36), sa.ForeignKey("content_sources.id", ondelete="CASCADE"), nullable=False),
            sa.Column("language_id", sa.String(length=36), sa.ForeignKey("languages.id", ondelete="SET NULL"), nullable=True),
            sa.Column("cefr_level", sa.String(length=10), nullable=False),
            sa.Column("skill", sa.String(length=40), nullable=False),
            sa.Column("mode", sa.String(length=40), nullable=False),
            sa.Column("content_type", sa.String(length=40), nullable=False),
            sa.Column("topic", sa.String(length=200), nullable=True),
            sa.Column("title", sa.String(length=300), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("origin_type", sa.String(length=40), nullable=False),
            sa.Column("source_page_start", sa.Integer(), nullable=True),
            sa.Column("source_page_end", sa.Integer(), nullable=True),
            sa.Column("excerpt_text", sa.Text(), nullable=True),
            sa.Column("attribution_text", sa.Text(), nullable=True),
            sa.Column("similarity_score", sa.Float(), nullable=True),
            sa.Column("validation_status", sa.String(length=40), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_content_units_source_id", "content_units", ["source_id"])
        op.create_index("ix_content_units_cefr_level", "content_units", ["cefr_level"])
        op.create_index("ix_content_units_skill", "content_units", ["skill"])
        op.create_index("ix_content_units_mode", "content_units", ["mode"])
        op.create_index("ix_content_units_validation_status", "content_units", ["validation_status"])
        op.create_index("ix_content_units_is_active", "content_units", ["is_active"])

    if not _has_table(inspector, "content_reviews"):
        op.create_table(
            "content_reviews",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("content_unit_id", sa.String(length=36), sa.ForeignKey("content_units.id", ondelete="CASCADE"), nullable=False),
            sa.Column("reviewer_user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("linguistic_status", sa.String(length=40), nullable=False),
            sa.Column("pedagogical_status", sa.String(length=40), nullable=False),
            sa.Column("rights_status", sa.String(length=40), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_content_reviews_content_unit_id", "content_reviews", ["content_unit_id"])

    if not _has_table(inspector, "lesson_content_usages"):
        op.create_table(
            "lesson_content_usages",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("lesson_id", sa.String(length=36), sa.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False),
            sa.Column("content_unit_id", sa.String(length=36), sa.ForeignKey("content_units.id", ondelete="CASCADE"), nullable=False),
            sa.Column("usage_type", sa.String(length=40), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_lesson_content_usages_lesson_id", "lesson_content_usages", ["lesson_id"])
        op.create_index("ix_lesson_content_usages_content_unit_id", "lesson_content_usages", ["content_unit_id"])


def downgrade() -> None:
    """No-op seguro: não remove proveniência, deliveries nem biblioteca."""
    return
