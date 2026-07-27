#!/usr/bin/env python3
"""Relatorio de divergencia entre models e schema do banco (sem secrets)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings
from app.models import Base


def main() -> int:
    url = get_settings().database_url
    safe_target = url.split("@")[-1] if "@" in url else url
    print(f"Target: {safe_target}")
    engine = create_engine(url)
    with engine.connect() as conn:
        insp = inspect(conn)
        if insp.has_table("alembic_version"):
            rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
            print(f"alembic_version: {[r[0] for r in rows]}")
        else:
            print("alembic_version: AUSENTE")

        missing_tables: list[str] = []
        missing_columns: list[str] = []
        for table in Base.metadata.sorted_tables:
            if not insp.has_table(table.name):
                missing_tables.append(table.name)
                continue
            existing = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name not in existing:
                    missing_columns.append(f"{table.name}.{col.name}")

        print(f"missing_tables ({len(missing_tables)}): {missing_tables}")
        print(f"missing_columns ({len(missing_columns)}): {missing_columns}")
        return 1 if missing_tables or missing_columns else 0


if __name__ == "__main__":
    raise SystemExit(main())
