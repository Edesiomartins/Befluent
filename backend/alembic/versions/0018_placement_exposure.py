"""Account-owned exposure ledger; no historical backfill."""
from alembic import op
import sqlalchemy as sa

revision = "0018_placement_exposure"
down_revision = "0017_placement_coverage"
branch_labels = None
depends_on = None


def upgrade():
    if "placement_item_exposures" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table("placement_item_exposures",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("language_code", sa.String(32), nullable=False),
            sa.Column("origin_key", sa.String(100), nullable=False),
            sa.Column("source_test_id", sa.String(36), nullable=False),
            sa.Column("source_item_id", sa.String(36), nullable=False),
            sa.Column("keys_json", sa.JSON(), nullable=False),
            sa.Column("snapshot_json", sa.JSON(), nullable=False),
            sa.Column("seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("answered_at", sa.DateTime(timezone=True)),
            sa.Column("feedback_revealed_at", sa.DateTime(timezone=True)),
            sa.UniqueConstraint("user_id", "origin_key", name="uq_placement_exposure_origin"))
        for column in ("user_id", "language_code", "source_test_id"):
            op.create_index(f"ix_placement_item_exposures_{column}", "placement_item_exposures", [column])


def downgrade():
    op.drop_table("placement_item_exposures")
