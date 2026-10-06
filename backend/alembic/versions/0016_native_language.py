"""Língua nativa global, nullable, sem inferência ou backfill."""
import sqlalchemy as sa
from alembic import op
revision = "0016_native_language"
down_revision = "0015_lesson_report"
branch_labels = None
depends_on = None

def upgrade():
    if "native_language" not in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("users")}:
        op.add_column("users", sa.Column("native_language", sa.String(32), nullable=True))

def downgrade():
    op.drop_column("users", "native_language")
