"""Integra persistência lexical ao Teaching Engine.

Migration exclusivamente aditiva: os novos vínculos são opcionais e nenhuma
restrição unique é criada sobre vocabulário legado.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0013_vocabulary_learning_cycle"
down_revision = "0012_language_entitlements"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    return {
        index["name"]
        for index in inspect(op.get_bind()).get_indexes(table_name)
        if index.get("name")
    }


def _add_optional_fk(
    table_name: str,
    column_name: str,
    target: str,
    *,
    ondelete: str = "SET NULL",
) -> None:
    if column_name in _columns(table_name):
        return
    with op.batch_alter_table(table_name) as batch:
        batch.add_column(sa.Column(column_name, sa.String(length=36), nullable=True))
        batch.create_foreign_key(
            f"fk_{table_name}_{column_name}",
            target.split(".")[0],
            [column_name],
            [target.split(".")[1]],
            ondelete=ondelete,
        )


def _index_optional_fk(table_name: str, column_name: str) -> None:
    name = f"ix_{table_name}_{column_name}"
    if name not in _indexes(table_name):
        op.create_index(name, table_name, [column_name], unique=False)


def upgrade() -> None:
    _add_optional_fk("teaching_flow_sessions", "lesson_id", "lessons.id")
    _add_optional_fk("learning_attempts", "vocabulary_item_id", "vocabulary_items.id")
    _add_optional_fk("learning_evidence", "vocabulary_item_id", "vocabulary_items.id")
    _add_optional_fk("learning_errors", "vocabulary_item_id", "vocabulary_items.id")

    for table_name, column_name in (
        ("teaching_flow_sessions", "lesson_id"),
        ("learning_attempts", "vocabulary_item_id"),
        ("learning_evidence", "vocabulary_item_id"),
        ("learning_errors", "vocabulary_item_id"),
    ):
        _index_optional_fk(table_name, column_name)

    with op.batch_alter_table("teaching_flow_sessions") as batch:
        batch.alter_column("objective_id", existing_type=sa.String(length=36), nullable=True)
    with op.batch_alter_table("learning_attempts") as batch:
        batch.alter_column("objective_id", existing_type=sa.String(length=36), nullable=True)
    with op.batch_alter_table("learning_evidence") as batch:
        batch.alter_column("objective_id", existing_type=sa.String(length=36), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("learning_evidence") as batch:
        batch.alter_column("objective_id", existing_type=sa.String(length=36), nullable=False)
    with op.batch_alter_table("learning_attempts") as batch:
        batch.alter_column("objective_id", existing_type=sa.String(length=36), nullable=False)
    with op.batch_alter_table("teaching_flow_sessions") as batch:
        batch.alter_column("objective_id", existing_type=sa.String(length=36), nullable=False)

    for table_name, column_name in (
        ("learning_errors", "vocabulary_item_id"),
        ("learning_evidence", "vocabulary_item_id"),
        ("learning_attempts", "vocabulary_item_id"),
        ("teaching_flow_sessions", "lesson_id"),
    ):
        with op.batch_alter_table(table_name) as batch:
            batch.drop_index(f"ix_{table_name}_{column_name}")
            batch.drop_constraint(
                f"fk_{table_name}_{column_name}", type_="foreignkey"
            )
            batch.drop_column(column_name)
