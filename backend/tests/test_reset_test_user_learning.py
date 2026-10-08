"""Account-preserving reset, with actual FK enforcement and file transactions."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, event, insert, select, update

from app.models import Base
from app.core.security import hash_password


RESET_TABLES = {
    "user_languages", "placement_tests", "learning_goals", "learning_plans",
    "learning_plan_items", "curricula", "curriculum_weeks", "curriculum_days",
    "curriculum_blocks", "study_sessions", "lessons", "lesson_activities",
    "lesson_activity_attempts", "exercises", "exercise_attempts", "conversations",
    "conversation_messages", "vocabulary_items", "vocabulary_examples", "review_items",
    "user_grammar_progress", "pronunciation_attempts", "listening_activities",
    "writing_submissions", "assessments", "assessment_questions", "assessment_attempts",
    "placement_test_sections", "placement_test_answers", "placement_item_deliveries",
    "progress_metrics", "lesson_content_usages", "user_objective_progress",
    "learning_attempts", "learning_evidence", "learning_errors", "remediations",
    "teaching_flow_sessions", "memory_schedules", "memory_review_events",
    "learning_progress_snapshots", "learning_progress_events",
}


def snapshot(engine):
    with engine.connect() as conn:
        return {t.name: [dict(row) for row in conn.execute(select(t).order_by(t.c.id)).mappings()]
                for t in Base.metadata.tables.values()}


def seed_row(conn, table, ids, tag, **overrides):
    values = {"id": f"{tag}-{table.name}"}
    for column in table.c:
        if column.name == "id":
            continue
        if column.foreign_keys:
            fk = next(iter(column.foreign_keys))
            # Self references are optional and not yet available.
            if fk.column.table.name in ids:
                values[column.name] = ids[fk.column.table.name]
        elif not column.nullable and column.default is None and column.server_default is None:
            typ = column.type.python_type
            values[column.name] = {
                str: f"{tag}-{column.name}", int: 1, float: 0.5, bool: True,
                datetime: datetime.now(timezone.utc), dict: {}, list: [],
            }.get(typ)
    values.update(overrides)
    conn.execute(insert(table).values(**values))
    return values["id"]


@pytest.fixture
def reset_database(tmp_path):
    from sqlalchemy import Date
    from datetime import date
    path = tmp_path / "reset_test.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    @event.listens_for(engine, "connect")
    def foreign_keys(dbapi, _):
        dbapi.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    ids_by_user = {}
    with engine.begin() as conn:
        global_ids = {}
        for table in Base.metadata.sorted_tables:
            if table.name in RESET_TABLES or table.name in {
                "users", "user_preferences", "sessions", "password_reset_tokens",
                "language_entitlements", "audit_logs", "content_reviews",
            }:
                continue
            overrides = {"code": "fr"} if table.name == "languages" else {}
            global_ids[table.name] = seed_row(conn, table, global_ids, "global", **overrides)
        for tag in ("target", "other"):
            ids = dict(global_ids)
            ids["users"] = seed_row(conn, Base.metadata.tables["users"], ids, tag,
                                    email=f"{tag}@example.test", name=tag,
                                    password_hash=hash_password("senha-segura"), native_language="pt-BR")
            for table in Base.metadata.sorted_tables:
                if table.name not in RESET_TABLES:
                    continue
                overrides = {}
                for column in table.c:
                    if isinstance(column.type, Date) and not column.nullable and column.default is None:
                        overrides[column.name] = date(2026, 10, 6)
                if table.name == "user_languages":
                    overrides.update(is_active=True, onboarding_completed=True, diagnostic_completed=True)
                ids[table.name] = seed_row(conn, table, ids, tag, **overrides)
            # Soft references must be audited too, not just declared FKs.
            conn.execute(update(Base.metadata.tables["curriculum_blocks"])
                         .where(Base.metadata.tables["curriculum_blocks"].c.id == ids["curriculum_blocks"])
                         .values(lesson_ref=ids["lessons"]))
            conn.execute(update(Base.metadata.tables["user_languages"])
                         .where(Base.metadata.tables["user_languages"].c.id == ids["user_languages"])
                         .values(placement_test_id=ids["placement_tests"]))
            for name in ("user_preferences", "sessions", "password_reset_tokens",
                         "language_entitlements", "audit_logs", "content_reviews"):
                overrides = {}
                if name == "user_preferences":
                    overrides = {"default_language_id": global_ids["languages"],
                                 "ui_prefs_json": {"theme": "dark", "primary_goal": "travel",
                                                   "skills": ["reading"], "minutes_per_day": 20}}
                if name in {"sessions", "password_reset_tokens"}:
                    overrides = {"expires_at": datetime.now(timezone.utc) + timedelta(days=1)}
                ids[name] = seed_row(conn, Base.metadata.tables[name], ids, tag, **overrides)
            ids_by_user[tag] = ids
    yield engine, path, ids_by_user
    engine.dispose()


def test_dry_run_select_only_and_reports_every_personal_table(reset_database):
    from scripts.reset_test_user_learning import run_reset
    engine, _, ids = reset_database
    before = snapshot(engine)
    statements = []
    def capture(conn, cursor, statement, parameters, context, many):
        statements.append(statement.strip().split()[0].upper())
    event.listen(engine, "before_cursor_execute", capture)
    report = run_reset(engine, user_email="target@example.test")
    event.remove(engine, "before_cursor_execute", capture)
    assert report["transaction"] == "read_only_dry_run"
    assert not report["write_committed"]
    assert set(report["before"]) == RESET_TABLES
    assert all(count == 1 for count in report["before"].values())
    assert report["estimated_deleted_records"] == 42
    assert not ({"DELETE", "UPDATE", "INSERT"} & set(statements))
    assert "password_hash" not in json.dumps(report) and "token_hash" not in json.dumps(report)
    assert snapshot(engine) == before


def test_apply_preserves_account_auth_globals_other_user_and_removes_all_learning(reset_database):
    from scripts.reset_test_user_learning import run_reset
    engine, _, ids = reset_database
    before = snapshot(engine)
    report = run_reset(engine, user_id=ids["target"]["users"], apply=True)
    after = snapshot(engine)
    assert report["transaction"] == "committed" and report["write_committed"]
    assert all(count == 0 for count in report["after"].values())
    for name in RESET_TABLES:
        assert after[name] == [row for row in before[name] if row["id"] == ids["other"][name]], name
    for name in before.keys() - RESET_TABLES - {"users", "user_preferences"}:
        assert after[name] == before[name], name
    old_user = next(row for row in before["users"] if row["id"] == ids["target"]["users"])
    new_user = next(row for row in after["users"] if row["id"] == old_user["id"])
    assert new_user == {**old_user, "native_language": None}
    assert next(row for row in after["users"] if row["id"] == ids["other"]["users"]) == next(
        row for row in before["users"] if row["id"] == ids["other"]["users"])
    target_pref = next(row for row in after["user_preferences"] if row["user_id"] == old_user["id"])
    original_pref = next(row for row in before["user_preferences"] if row["id"] == target_pref["id"])
    assert target_pref == {**original_pref, "default_language_id": None, "ui_prefs_json": {"theme": "dark"}}
    assert next(row for row in after["user_preferences"] if row["user_id"] == ids["other"]["users"]) == next(
        row for row in before["user_preferences"] if row["user_id"] == ids["other"]["users"])
    again = run_reset(engine, user_id=old_user["id"], apply=True)
    assert again["estimated_deleted_records"] == 0
    assert snapshot(engine) == after
    # Native NULL and no profiles make the real onboarding endpoint initial;
    # authentication is separately tested through the actual HTTP endpoints.


def test_rollback_and_mid_delete_failure_are_atomic(reset_database):
    from scripts.reset_test_user_learning import run_reset
    engine, _, ids = reset_database
    before = deepcopy(snapshot(engine))
    report = run_reset(engine, user_id=ids["target"]["users"], apply=True, rollback=True)
    assert report["transaction"] == "rolled_back" and not report["write_committed"]
    assert report["rollback_verified"]
    assert snapshot(engine) == before
    deletes = []
    def fail_after_deletes(conn, cursor, statement, parameters, context, many):
        if statement.lstrip().upper().startswith("DELETE"):
            deletes.append(statement)
            if len(deletes) == 4:
                raise RuntimeError("injected partial reset failure")
    event.listen(engine, "before_cursor_execute", fail_after_deletes)
    try:
        with pytest.raises(RuntimeError, match="partial reset"):
            run_reset(engine, user_id=ids["target"]["users"], apply=True)
    finally:
        event.remove(engine, "before_cursor_execute", fail_after_deletes)
    assert len(deletes) == 4 and snapshot(engine) == before


@pytest.mark.parametrize("args", [{}, {"user_id": "no-user"}, {"user_email": "missing@example.test"},
                                  {"user_id": "target-users", "user_email": "target@example.test"},
                                  {"user_id": "target-users", "rollback": True}])
def test_invalid_identifiers_and_flags_refused(reset_database, args):
    from scripts.reset_test_user_learning import run_reset
    engine, _, _ = reset_database
    before = snapshot(engine)
    with pytest.raises(ValueError):
        run_reset(engine, **args)
    assert snapshot(engine) == before


def test_ambiguous_email_is_refused(reset_database):
    from scripts.reset_test_user_learning import run_reset
    engine, _, ids = reset_database
    with engine.begin() as conn:
        conn.execute(update(Base.metadata.tables["users"]).where(
            Base.metadata.tables["users"].c.id == ids["other"]["users"]).values(email="TARGET@example.test"))
    before = snapshot(engine)
    with pytest.raises(ValueError, match="ambiguous"):
        run_reset(engine, user_email="target@example.test", apply=True)
    assert snapshot(engine) == before


@pytest.mark.parametrize("table,column,parent", [
    ("learning_evidence", "attempt_id", "learning_attempts"),
    ("conversations", "study_session_id", "study_sessions"),
    ("curriculum_blocks", "lesson_ref", "lessons"),
    ("user_languages", "placement_test_id", "placement_tests"),
    ("user_languages", "last_assessment_id", "placement_tests"),
])
@pytest.mark.parametrize("reverse", [False, True])
def test_cross_account_links_refused_in_both_directions(reset_database, table, column, parent, reverse):
    from scripts.reset_test_user_learning import run_reset
    engine, _, ids = reset_database
    child_owner, parent_owner = ("other", "target") if reverse else ("target", "other")
    with engine.begin() as conn:
        t = Base.metadata.tables[table]
        conn.execute(update(t).where(t.c.id == ids[child_owner][table]).values({column: ids[parent_owner][parent]}))
    before = snapshot(engine)
    with pytest.raises(ValueError, match="reference"):
        run_reset(engine, user_id=ids["target"]["users"], apply=True)
    assert snapshot(engine) == before


@pytest.mark.parametrize("change", ["extra_table", "extra_column", "missing_table"])
def test_unknown_schema_is_refused_before_writing(reset_database, change):
    from scripts.reset_test_user_learning import run_reset
    engine, _, _ = reset_database
    with engine.begin() as conn:
        if change == "extra_table": conn.exec_driver_sql("CREATE TABLE new_personal_cache (id TEXT PRIMARY KEY, user_id TEXT)")
        if change == "extra_column": conn.exec_driver_sql("ALTER TABLE users ADD COLUMN new_learning_state TEXT")
        if change == "missing_table": conn.exec_driver_sql("DROP TABLE memory_review_events")
    writes = []
    def capture(conn, cursor, statement, parameters, context, many):
        if statement.lstrip().split()[0].upper() in {"DELETE", "UPDATE", "INSERT"}:
            writes.append(statement)
    event.listen(engine, "before_cursor_execute", capture)
    try:
        with pytest.raises(ValueError, match="schema"):
            run_reset(engine, user_email="target@example.test", apply=True)
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert not writes


@pytest.mark.parametrize("flags,transaction,committed", [([], "read_only_dry_run", False),
    (["--apply", "--rollback"], "rolled_back", False), (["--apply"], "committed", True)])
def test_cli_file_database_modes(reset_database, flags, transaction, committed):
    engine, path, ids = reset_database
    before = snapshot(engine)
    original_bytes = path.read_bytes()
    result = subprocess.run([sys.executable, "scripts/reset_test_user_learning.py",
                             "--user-email", "target@example.test", *flags],
                            cwd=Path(__file__).resolve().parents[1],
                            env={**os.environ, "DATABASE_URL": f"sqlite:///{path.as_posix()}"},
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["transaction"] == transaction and report["write_committed"] == committed
    assert "password_hash" not in result.stdout and "senha-segura" not in result.stdout
    if not committed:
        assert snapshot(engine) == before
    if not flags:
        assert path.read_bytes() == original_bytes


def test_all_languages_including_inactive_profiles_are_reset(reset_database):
    from scripts.reset_test_user_learning import run_reset
    engine, _, ids = reset_database
    with engine.begin() as conn:
        language = Base.metadata.tables["languages"]
        conn.execute(insert(language).values(id="second-language", code="en", name_pt="Inglês", native_name="English"))
        profiles = Base.metadata.tables["user_languages"]
        conn.execute(insert(profiles).values(id="inactive-profile", user_id=ids["target"]["users"],
                                             language_id="second-language", is_active=False, onboarding_completed=True))
        lessons = Base.metadata.tables["lessons"]
        conn.execute(insert(lessons).values(id="inactive-lesson", user_language_id="inactive-profile",
                                           title="History", objective="Practice"))
        attempts = Base.metadata.tables["placement_tests"]
        conn.execute(insert(attempts).values(id="standalone-placement", user_id=ids["target"]["users"],
                                            language_code="ja"))
    report = run_reset(engine, user_id=ids["target"]["users"], apply=True)
    assert report["before"]["user_languages"] == 2
    assert report["before"]["lessons"] == 2
    assert report["before"]["placement_tests"] == 2
    assert all(count == 0 for count in report["after"].values())
    assert len(snapshot(engine)["languages"]) == 2


def test_failure_after_native_update_rolls_back_everything(reset_database):
    from scripts.reset_test_user_learning import run_reset
    engine, _, ids = reset_database
    before = snapshot(engine)
    updated_user = []
    def interrupt(conn, cursor, statement, parameters, context, many):
        if statement.lstrip().upper().startswith("UPDATE USERS"):
            updated_user.append(True)
            raise RuntimeError("failure after account field update")
    event.listen(engine, "after_cursor_execute", interrupt)
    try:
        with pytest.raises(RuntimeError, match="account field"):
            run_reset(engine, user_id=ids["target"]["users"], apply=True)
    finally:
        event.remove(engine, "after_cursor_execute", interrupt)
    assert updated_user == [True] and snapshot(engine) == before


def test_postcondition_failure_rolls_back_unexpected_remaining_learning(reset_database):
    from scripts.reset_test_user_learning import run_reset
    engine, _, ids = reset_database
    before = snapshot(engine)
    def add_unexpected(conn, cursor, statement, parameters, context, many):
        if statement.lstrip().upper().startswith("UPDATE USERS"):
            conn.execute(insert(Base.metadata.tables["placement_tests"]).values(
                id="unexpected-leftover", user_id=ids["target"]["users"], language_code="fr"))
    event.listen(engine, "after_cursor_execute", add_unexpected)
    try:
        with pytest.raises(ValueError, match="postconditions"):
            run_reset(engine, user_id=ids["target"]["users"], apply=True)
    finally:
        event.remove(engine, "after_cursor_execute", add_unexpected)
    assert snapshot(engine) == before


def test_cli_refuses_missing_identifier_and_does_not_create_database(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    path = tmp_path / "must_not_exist.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{path.as_posix()}"}
    missing = subprocess.run([sys.executable, "scripts/reset_test_user_learning.py"],
                             cwd=backend, env=env, capture_output=True, text=True, timeout=30)
    assert missing.returncode == 2
    nonexistent = subprocess.run([sys.executable, "scripts/reset_test_user_learning.py",
                                  "--user-email", "target@example.test"], cwd=backend, env=env,
                                 capture_output=True, text=True, timeout=30)
    assert nonexistent.returncode == 2 and not path.exists()


def test_existing_login_and_fresh_onboarding_after_reset(client, db_session):
    from scripts.reset_test_user_learning import reset_learning
    from app.models import User, UserLanguage, Language
    from sqlalchemy import select
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db_session.scalar(select(Language).where(Language.code == "fr"))
    db_session.add(UserLanguage(user_id=user.id, language_id=language.id,
                                is_active=True, onboarding_completed=True))
    db_session.commit()
    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": "senha-segura"})
    assert login.status_code == 200
    # The core helper shares the caller's transaction, without implicit commit.
    reset_learning(db_session.connection(), user_id=user.id, apply=True)
    db_session.commit()
    response = client.get("/api/v1/onboarding/status")
    assert response.status_code == 200
    assert response.json()["completed"] is False
    assert response.json()["native_language_required"] is True
    assert response.json()["languages"] == []
    assert client.get("/api/v1/auth/me").status_code == 200
    fresh_login = client.post("/api/v1/auth/login", json={"email": user.email, "password": "senha-segura"})
    assert fresh_login.status_code == 200
