"""Additive coverage and planning metadata; no inferred backfill."""
import sqlalchemy as sa
from alembic import op

revision = "0017_placement_coverage"
down_revision = "0016_native_language"
branch_labels = None
depends_on = None


def upgrade():
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("user_languages")}
    for name, type_ in (("last_assessment_id", sa.String(36)), ("assessment_summary_json", sa.JSON()),
                        ("planning_level", sa.String(10)), ("planning_level_source", sa.String(30))):
        if name not in existing:
            op.add_column("user_languages", sa.Column(name, type_, nullable=True))
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("user_languages")}
    if "ix_user_languages_last_assessment_id" not in indexes:
        op.create_index("ix_user_languages_last_assessment_id", "user_languages", ["last_assessment_id"])


def downgrade():
    op.drop_index("ix_user_languages_last_assessment_id", table_name="user_languages")
    for name in ("planning_level_source", "planning_level", "assessment_summary_json", "last_assessment_id"):
        op.drop_column("user_languages", name)
