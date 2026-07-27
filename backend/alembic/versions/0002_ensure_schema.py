"""Garante schema completo sem destruir dados existentes.

A revision 0001 usava Base.metadata.create_all(), que nao adiciona colunas
em tabelas ja existentes. Em bancos parcialmente criados (caso tipico no
Coolify), o login falha com UndefinedColumn / column does not exist.

Esta migration:
- cria tabelas ausentes;
- adiciona colunas ausentes de forma incremental;
- preenche valores em registros existentes quando a coluna for NOT NULL;
- cria indices/uniques ausentes;
- nao faz DROP TABLE / DROP COLUMN.
"""

from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

from app.models import Base

revision = "0002_ensure_schema"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _existing_columns(inspector, table_name: str) -> set[str]:
    return {col["name"] for col in inspector.get_columns(table_name)}


def _existing_indexes(inspector, table_name: str) -> set[str]:
    return {idx["name"] for idx in inspector.get_indexes(table_name) if idx.get("name")}


def _existing_uniques(inspector, table_name: str) -> set[tuple[str, ...]]:
    result: set[tuple[str, ...]] = set()
    for uc in inspector.get_unique_constraints(table_name):
        cols = tuple(uc.get("column_names") or ())
        if cols:
            result.add(cols)
    for idx in inspector.get_indexes(table_name):
        if idx.get("unique"):
            cols = tuple(idx.get("column_names") or ())
            if cols:
                result.add(cols)
    # Unique flags on columns (SQLite/Postgres)
    for col in inspector.get_columns(table_name):
        # some dialects expose unique only via constraints/indexes
        _ = col
    return result


def _python_default(column: sa.Column):
    if column.default is None:
        return None
    arg = column.default.arg
    if callable(arg):
        try:
            return arg()
        except TypeError:
            return arg(None)
    return arg


def _backfill_value(column: sa.Column):
    value = _python_default(column)
    if value is not None:
        return value
    col_type = column.type
    if isinstance(col_type, sa.Boolean):
        return False
    if isinstance(col_type, sa.Integer):
        return 0
    if isinstance(col_type, sa.Float):
        return 0.0
    if isinstance(col_type, sa.JSON):
        return {}
    if isinstance(col_type, sa.DateTime):
        return datetime.now(timezone.utc)
    if isinstance(col_type, (sa.String, sa.Text)):
        return ""
    return None


def _set_not_null(table_name: str, column_name: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(column_name, nullable=False)
    else:
        op.alter_column(table_name, column_name, nullable=False)


def _add_missing_column(table_name: str, column: sa.Column) -> None:
    """Adiciona coluna de forma segura em tabelas com dados."""
    wants_not_null = not column.nullable
    create_nullable = True if wants_not_null else column.nullable

    new_col = sa.Column(
        column.name,
        column.type,
        nullable=create_nullable,
        server_default=column.server_default,
    )
    op.add_column(table_name, new_col)

    if wants_not_null:
        fill = _backfill_value(column)
        if fill is not None:
            tbl = sa.table(table_name, sa.column(column.name))
            op.execute(tbl.update().where(sa.column(column.name).is_(None)).values({column.name: fill}))
        _set_not_null(table_name, column.name)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            table.create(bind=bind)
            inspector = inspect(bind)
            continue

        existing_cols = _existing_columns(inspector, table.name)
        for column in table.columns:
            if column.name in existing_cols:
                continue
            _add_missing_column(table.name, column)

        inspector = inspect(bind)
        existing_idxs = _existing_indexes(inspector, table.name)
        existing_ucs = _existing_uniques(inspector, table.name)
        existing_idx_cols = [
            (tuple(i.get("column_names") or []), bool(i.get("unique")), i.get("name"))
            for i in inspector.get_indexes(table.name)
        ]

        for index in table.indexes:
            cols = tuple(col.name for col in index.columns)
            if index.name and index.name in existing_idxs:
                continue
            if any(cols == existing_cols_tuple for existing_cols_tuple, _, _ in existing_idx_cols):
                continue
            if index.unique and cols in existing_ucs:
                continue
            op.create_index(
                index.name or f"ix_{table.name}_{'_'.join(cols)}",
                table.name,
                list(cols),
                unique=bool(index.unique),
            )

        for constraint in table.constraints:
            if not isinstance(constraint, sa.UniqueConstraint):
                continue
            cols = tuple(col.name for col in constraint.columns)
            if cols in existing_ucs:
                continue
            # coluna unique ja existente (ex.: email UNIQUE na DDL legada)
            if len(cols) == 1:
                col_info = next(
                    (c for c in inspector.get_columns(table.name) if c["name"] == cols[0]),
                    None,
                )
                # nao da para detectar unique de coluna em todos dialetos; tentar e ignorar conflito
            name = constraint.name or f"uq_{table.name}_{'_'.join(cols)}"
            try:
                op.create_unique_constraint(name, table.name, list(cols))
            except Exception:
                # Constraint ja existe sob outro nome
                pass

        inspector = inspect(bind)


def downgrade() -> None:
    """No-op seguro: remover colunas/tabelas poderia apagar dados em producao."""
    pass
