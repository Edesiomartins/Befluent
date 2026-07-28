"""Testa migration 0002 em schema incompleto (simula banco legado)."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def test_ensure_schema_adds_missing_user_columns(tmp_path: Path):
    db_path = tmp_path / "legacy.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)

    # Schema legado incompleto (falta last_login_at e is_active — tipico de login quebrado)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE users (
                    id VARCHAR(36) PRIMARY KEY,
                    email VARCHAR(320) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    name VARCHAR(120) NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, name, created_at) "
                "VALUES ('u1', 'a@b.c', 'hash', 'A', '2026-01-01')"
            )
        )
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('0001_initial')"))

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    # Forca env.py a usar este banco via env var
    import os

    os.environ["DATABASE_URL"] = url
    # limpa cache de settings
    from app.core import config as config_mod

    config_mod.get_settings.cache_clear()

    command.upgrade(cfg, "head")

    with engine.connect() as conn:
        cols = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(users)")).fetchall()
        }
        assert "last_login_at" in cols
        assert "is_active" in cols
        assert "updated_at" in cols
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert version == "0003_levels_placement"
        # dado preservado
        name = conn.execute(text("SELECT name FROM users WHERE id='u1'")).scalar()
        assert name == "A"
