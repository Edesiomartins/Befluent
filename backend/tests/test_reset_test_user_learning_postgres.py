"""Opt-in PostgreSQL safety checks. Never uses DATABASE_URL or production.

Needs POSTGRES_TEST_URL for a dedicated PostgreSQL 18 database ending in _test.
Creates/drops only UUID-named temporary schemas inside that test database.
"""
from datetime import date
import os
import uuid

import pytest
from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.engine import make_url

from app.models import Base


def seed_safety_rows(conn):
    t = Base.metadata.tables
    conn.execute(insert(t["users"]), [
        {"id": "target", "email": "target@test.local", "name": "Target", "password_hash": "preserve", "native_language": "pt-BR"},
        {"id": "other", "email": "other@test.local", "name": "Other", "password_hash": "preserve", "native_language": "pt-BR"},
    ])
    conn.execute(insert(t["languages"]).values(id="fr", code="fr", name_pt="Francês", native_name="Français"))
    conn.execute(insert(t["user_languages"]), [
        {"id": "target-profile", "user_id": "target", "language_id": "fr"},
        {"id": "other-profile", "user_id": "other", "language_id": "fr"},
    ])
    conn.execute(insert(t["lessons"]).values(id="target-lesson", user_language_id="target-profile", title="Historic", objective="Practice"))
    conn.execute(insert(t["curricula"]).values(id="other-curriculum", user_language_id="other-profile", start_date=date(2026,10,6), target_level="B1", entry_level="A1"))
    conn.execute(insert(t["curriculum_weeks"]).values(id="other-week", curriculum_id="other-curriculum", week_number=1, theme="Test", cefr_focus="A1"))
    conn.execute(insert(t["curriculum_days"]).values(id="other-day", week_id="other-week", day_number=1, scheduled_date=date(2026,10,6)))
    conn.execute(insert(t["curriculum_blocks"]).values(id="other-block", day_id="other-day", skill="grammar", position=1, topic="Test", cefr_level="A1"))


@pytest.fixture
def postgres_reset_database():
    url = os.environ.get("POSTGRES_TEST_URL")
    if not url:
        pytest.skip("POSTGRES_TEST_URL not configured; PostgreSQL safety remains unverified")
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").endswith("_test"):
        pytest.fail("POSTGRES_TEST_URL must name a dedicated PostgreSQL database ending in _test")
    admin = create_engine(url)
    schema = "reset_test_" + uuid.uuid4().hex
    extra_schema = schema + "_external"
    with admin.begin() as conn:
        version = int(conn.exec_driver_sql("SHOW server_version_num").scalar())
        if version // 10000 != 18:
            pytest.fail("Dedicated PostgreSQL 18 instance required")
        conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        conn.exec_driver_sql(f'CREATE SCHEMA "{extra_schema}"')
    engine = create_engine(url)
    @event.listens_for(engine, "connect")
    def search_path(dbapi, _):
        cursor = dbapi.cursor()
        cursor.execute(f'SET SESSION search_path TO "{schema}"')
        dbapi.commit()
        cursor.close()
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            seed_safety_rows(conn)
        yield engine, schema, extra_schema
    finally:
        engine.dispose()
        # Names are UUID literals created above, never supplied/computed from a
        # production identifier. No public tables/database are dropped.
        with admin.begin() as conn:
            conn.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{extra_schema}" CASCADE')
            conn.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        admin.dispose()


def test_postgres_refuses_cross_schema_incoming_cascade(postgres_reset_database):
    from scripts.reset_test_user_learning import run_reset
    engine, schema, external = postgres_reset_database
    with engine.begin() as conn:
        conn.exec_driver_sql(f'CREATE TABLE "{external}".unreviewed_copy '
                             f'(id TEXT PRIMARY KEY, lesson_id VARCHAR(36) REFERENCES "{schema}".lessons(id) ON DELETE CASCADE)')
        conn.exec_driver_sql(f'INSERT INTO "{external}".unreviewed_copy VALUES (\'keep\', \'target-lesson\')')
    with pytest.raises(ValueError, match="incoming FK"):
        run_reset(engine, user_id="target", apply=True)
    with engine.connect() as conn:
        assert conn.exec_driver_sql(f'SELECT count(*) FROM "{external}".unreviewed_copy').scalar() == 1
        assert conn.scalar(select(Base.metadata.tables["lessons"].c.id)) == "target-lesson"


def test_postgres_apply_fences_other_account_soft_pointer_writes(postgres_reset_database):
    from scripts.reset_test_user_learning import run_reset
    engine, _, _ = postgres_reset_database
    observed = []
    def concurrent_write(conn, cursor, statement, parameters, context, many):
        if statement.startswith("LOCK TABLE"):
            with engine.connect() as other:
                tx = other.begin()
                try:
                    other.exec_driver_sql("SET LOCAL lock_timeout='100ms'")
                    with pytest.raises(Exception) as error:
                        other.exec_driver_sql("UPDATE curriculum_blocks SET lesson_ref='target-lesson' WHERE id='other-block'")
                    original = getattr(error.value, "orig", None)
                    assert getattr(original, "sqlstate", getattr(original, "pgcode", None)) == "55P03"
                    observed.append(True)
                finally:
                    tx.rollback()
    event.listen(engine, "after_cursor_execute", concurrent_write)
    try:
        report = run_reset(engine, user_id="target", apply=True, rollback=True)
    finally:
        event.remove(engine, "after_cursor_execute", concurrent_write)
    assert observed == [True]
    assert report["rollback_verified"] and not report["write_committed"]
    with engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT lesson_ref FROM curriculum_blocks WHERE id='other-block'").scalar() is None
