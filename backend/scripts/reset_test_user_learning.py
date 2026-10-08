"""Reset ONE explicitly selected learner; preserve account/login.

Default is read-only. --apply --rollback rehearses the same writes without commit.
Run from backend. A committed reset can only be restored from an external backup.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import MetaData, and_, create_engine, delete, func, inspect, or_, select, update
from sqlalchemy.engine import make_url
from app.models import Base

# Explicitly audited ownership paths. Secondary FKs never expand ownership:
# a cross-account reference aborts instead of including the other account.
OWNERSHIP = {
    "user_languages": ("user_id", "users"),
    "placement_tests": ("user_id", "users"),
    **{name: ("user_language_id", "user_languages") for name in (
        "learning_goals", "learning_plans", "curricula", "study_sessions", "lessons",
        "lesson_activity_attempts", "exercises", "conversations", "vocabulary_items",
        "review_items", "user_grammar_progress", "pronunciation_attempts",
        "listening_activities", "writing_submissions", "assessments", "progress_metrics",
        "user_objective_progress", "learning_attempts", "learning_evidence", "learning_errors",
        "teaching_flow_sessions", "memory_schedules", "learning_progress_snapshots",
        "learning_progress_events",
    )},
    "learning_plan_items": ("plan_id", "learning_plans"),
    "curriculum_weeks": ("curriculum_id", "curricula"),
    "curriculum_days": ("week_id", "curriculum_weeks"),
    "curriculum_blocks": ("day_id", "curriculum_days"),
    "lesson_activities": ("lesson_id", "lessons"),
    "exercise_attempts": ("exercise_id", "exercises"),
    "conversation_messages": ("conversation_id", "conversations"),
    "vocabulary_examples": ("vocabulary_item_id", "vocabulary_items"),
    "assessment_questions": ("assessment_id", "assessments"),
    "assessment_attempts": ("assessment_id", "assessments"),
    "placement_test_sections": ("test_id", "placement_tests"),
    "placement_test_answers": ("test_id", "placement_tests"),
    "placement_item_deliveries": ("test_id", "placement_tests"),
    "lesson_content_usages": ("lesson_id", "lessons"),
    "remediations": ("error_id", "learning_errors"),
    "memory_review_events": ("memory_schedule_id", "memory_schedules"),
}
PRESERVED = {
    "users", "user_preferences", "sessions", "password_reset_tokens",
    "language_entitlements", "audit_logs", "content_reviews",
}
GLOBALS = {
    "languages", "grammar_topics", "placement_items", "content_sources",
    "content_units", "learning_objectives", "ai_response_cache",
}
PEDAGOGICAL_PREF_KEYS = {"minutes_per_day", "skills", "primary_goal"}
SOFT_LINKS = (
    ("curriculum_blocks", "lesson_ref", "lessons"),
    ("user_languages", "placement_test_id", "placement_tests"),
    ("user_languages", "last_assessment_id", "placement_tests"),
)


def audited_order(tables):
    """Parent-first order for locks; reverse for deletion. Ignore self retries."""
    pending = set(OWNERSHIP)
    order = []
    while pending:
        ready = sorted(name for name in pending if not {
            fk.column.table.name for fk in tables[name].foreign_keys
            if fk.column.table.name != name
        }.intersection(pending))
        if not ready:
            raise ValueError("Unsupported schema: cyclic deletion dependencies")
        order.extend(ready)
        pending.difference_update(ready)
    return order


def validate_schema(conn):
    """Fail closed on unreviewed schema, hidden rows, or custom write triggers."""
    inspector = inspect(conn)
    expected = set(Base.metadata.tables)
    if expected != set(OWNERSHIP) | PRESERVED | GLOBALS:
        raise ValueError("Unsupported schema: model has unclassified tables")
    actual = set(inspector.get_table_names())
    if actual - {"alembic_version"} != expected:
        raise ValueError("Unsupported schema: missing or unreviewed tables")
    for name, table in Base.metadata.tables.items():
        columns = {c["name"]: c for c in inspector.get_columns(name)}
        if set(columns) != set(table.c.keys()):
            raise ValueError(f"Unsupported schema: column mismatch in {name}")
        if inspector.get_pk_constraint(name)["constrained_columns"] != ["id"]:
            raise ValueError(f"Unsupported schema: primary key mismatch in {name}")
        wanted = {(tuple(f.parent.name for f in fk.elements), fk.referred_table.name,
                   tuple(f.column.name for f in fk.elements), (fk.ondelete or "").upper())
                  for fk in table.foreign_key_constraints}
        found = {(tuple(f["constrained_columns"]), f["referred_table"],
                  tuple(f["referred_columns"]), (f.get("options", {}).get("ondelete") or "").upper())
                 for f in inspector.get_foreign_keys(name)}
        if wanted != found:
            raise ValueError(f"Unsupported schema: FK mismatch in {name}")
    if not {c["name"]: c for c in inspector.get_columns("users")}["native_language"]["nullable"]:
        raise ValueError("Unsupported schema: users.native_language must be nullable")
    if conn.dialect.name == "sqlite":
        triggers = conn.exec_driver_sql("SELECT tbl_name FROM sqlite_master WHERE type='trigger'").scalars()
        if set(triggers).intersection(set(OWNERSHIP) | {"users", "user_preferences"}):
            raise ValueError("Unsupported schema: unreviewed write triggers")
    elif conn.dialect.name == "postgresql":
        # RLS could hide another user's referencing rows from the integrity scan.
        hidden = conn.exec_driver_sql(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname=current_schema() AND (c.relrowsecurity OR EXISTS "
            "(SELECT 1 FROM pg_trigger t WHERE t.tgrelid=c.oid AND NOT t.tgisinternal))"
        ).scalars()
        if set(hidden).intersection(expected):
            raise ValueError("Unsupported schema: RLS or unreviewed triggers")
        # Reflection inspects outgoing FKs in the current schema only. An
        # incoming FK from another schema could cascade DELETEs outside scope.
        incoming = conn.exec_driver_sql(
            "SELECT cn.nspname AS child_schema, child.relname AS child_table, "
            "parent.relname AS parent_table, k.convalidated "
            "FROM pg_constraint k JOIN pg_class child ON child.oid=k.conrelid "
            "JOIN pg_namespace cn ON cn.oid=child.relnamespace "
            "JOIN pg_class parent ON parent.oid=k.confrelid "
            "JOIN pg_namespace pn ON pn.oid=parent.relnamespace "
            "WHERE k.contype='f' AND pn.nspname=current_schema()"
        ).mappings()
        current_schema = conn.scalar(select(func.current_schema()))
        for fk in incoming:
            if fk["parent_table"] in OWNERSHIP and (
                fk["child_schema"] != current_schema or fk["child_table"] not in OWNERSHIP
                or not fk["convalidated"]
            ):
                raise ValueError("Unsupported schema: unaudited or unvalidated incoming FK")
    else:
        raise ValueError("Only PostgreSQL and SQLite are supported")
    reflected = MetaData()
    reflected.reflect(bind=conn, only=sorted(expected))
    return reflected.tables


def resolve_user(conn, tables, user_id, user_email, apply):
    if bool(user_id) == bool(user_email):
        raise ValueError("Exactly one --user-id OR --user-email is required")
    t = tables["users"]
    criterion = t.c.id == user_id if user_id else func.lower(t.c.email) == user_email.strip().lower()
    query = select(t).where(criterion)
    if apply:
        query = query.with_for_update()
    rows = list(conn.execute(query).mappings())
    if len(rows) != 1:
        raise ValueError("User does not exist or email is ambiguous; no reset allowed")
    return dict(rows[0])


def scoped_queries(tables, user_id):
    queries = {"users": select(tables["users"].c.id).where(tables["users"].c.id == user_id)}
    pending = dict(OWNERSHIP)
    while pending:
        for name, (column, parent) in list(pending.items()):
            if parent in queries:
                t = tables[name]
                queries[name] = select(t.c.id).where(t.c[column].in_(queries[parent]))
                del pending[name]
    return queries


def check_references(conn, tables, queries):
    links = [(name, fk.parent.name, fk.column.table.name)
             for name in OWNERSHIP for fk in tables[name].foreign_keys
             if fk.column.table.name in OWNERSHIP]
    links.extend(SOFT_LINKS)
    for name, column, parent in links:
        t = tables[name]
        child_owned = t.c.id.in_(queries[name])
        parent_owned = t.c[column].in_(queries[parent])
        mismatch = or_(and_(child_owned, t.c[column].is_not(None), ~parent_owned),
                       and_(~child_owned, parent_owned))
        if conn.scalar(select(t.c.id).where(mismatch).limit(1)):
            raise ValueError(f"Inconsistent/cross-account reference: {name}.{column} -> {parent}")


def personal_snapshot(conn, tables, queries, user_id):
    """Internal fingerprint only; never print row data, credential hashes or tokens."""
    state = {name: [dict(row) for row in conn.execute(
        select(tables[name]).where(tables[name].c.id.in_(queries[name])).order_by(tables[name].c.id)
    ).mappings()] for name in ["users", *OWNERSHIP]}
    for name in PRESERVED - {"users"}:
        t = tables[name]
        owner = "reviewer_user_id" if name == "content_reviews" else "user_id"
        state[name] = [dict(row) for row in conn.execute(
            select(t).where(t.c[owner] == user_id).order_by(t.c.id)).mappings()]
    return state


def fingerprint(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True, default=str).encode()).hexdigest()


def _execute_reset(conn, *, user_id=None, user_email=None, apply=False):
    tables = validate_schema(conn)
    if apply and conn.dialect.name == "postgresql":
        # Non-FK pointers do not acquire parent key-share locks. Fence writes
        # to BOTH pointer tables until commit; this briefly blocks other users'
        # writes there, without changing their data. Application writers must
        # still be paused/drained operationally to prevent stale post-commit IDs.
        quoted_schema = conn.dialect.identifier_preparer.quote(conn.scalar(select(func.current_schema())))
        conn.exec_driver_sql(
            f"LOCK TABLE {quoted_schema}.curriculum_blocks, {quoted_schema}.user_languages "
            "IN SHARE ROW EXCLUSIVE MODE"
        )
    user = resolve_user(conn, tables, user_id, user_email, apply)
    user_id = user["id"]
    queries = scoped_queries(tables, user_id)
    parent_order = audited_order(tables)
    if apply:
        # FK insertions take key-share locks on parents in PostgreSQL. Lock the
        # entire existing personal graph before writing, in deterministic order.
        for name in [*parent_order, "user_preferences"]:
            t = tables[name]
            criterion = t.c.id.in_(queries[name]) if name in queries else t.c.user_id == user_id
            list(conn.execute(select(t.c.id).where(criterion).order_by(t.c.id).with_for_update()))
    check_references(conn, tables, queries)
    before_state = personal_snapshot(conn, tables, queries, user_id)
    before = {name: len(before_state[name]) for name in OWNERSHIP}
    prefs = before_state["user_preferences"]
    if any(row["ui_prefs_json"] is not None and not isinstance(row["ui_prefs_json"], Mapping) for row in prefs):
        raise ValueError("Unsupported schema/data: user preferences must be a JSON object")
    updates = int(user["native_language"] is not None) + sum(
        row["default_language_id"] is not None or bool(PEDAGOGICAL_PREF_KEYS & set(row["ui_prefs_json"] or {}))
        for row in prefs)
    report = {
        "user": {"id": user_id, "email": user["email"]},
        "mode": "apply" if apply else "dry_run", "before": before,
        "deletion_order": list(reversed(parent_order)),
        "estimated_deleted_records": sum(before.values()), "estimated_updated_records": updates,
        "estimated_affected_records": sum(before.values()) + updates,
        "preserved_tables": sorted(PRESERVED), "global_tables_untouched": sorted(GLOBALS),
        "reset_fields": {"users": ["native_language -> NULL"],
                         "user_preferences": ["default_language_id -> NULL", *sorted(PEDAGOGICAL_PREF_KEYS)]},
        "after": None, "write_performed": False, "write_committed": False,
        "onboarding_after_apply": {"completed": False, "native_language_required": True, "languages": []},
    }
    if apply:
        for name in reversed(parent_order):
            t = tables[name]
            # Use captured IDs, never a broad/cascading DELETE or a scope that
            # vanishes after its parent is removed. Bound batches avoid SQL limits.
            ids = [row["id"] for row in before_state[name]]
            for start in range(0, len(ids), 400):
                result = conn.execute(delete(t).where(t.c.id.in_(ids[start:start + 400])))
                if result.rowcount != len(ids[start:start + 400]):
                    raise ValueError(f"Reset incomplete: delete count changed in {name}")
        t = tables["users"]
        if user["native_language"] is not None:
            conn.execute(update(t).where(t.c.id == user_id).values(native_language=None))
        t = tables["user_preferences"]
        for row in prefs:
            cleaned = {k: v for k, v in (row["ui_prefs_json"] or {}).items() if k not in PEDAGOGICAL_PREF_KEYS}
            if row["default_language_id"] is not None or cleaned != (row["ui_prefs_json"] or {}):
                conn.execute(update(t).where(t.c.id == row["id"]).values(default_language_id=None, ui_prefs_json=cleaned))
        after_state = personal_snapshot(conn, tables, queries, user_id)
        report["after"] = {name: len(after_state[name]) for name in OWNERSHIP}
        # Check captured IDs too: ownership disappears once user_languages is gone.
        for name in OWNERSHIP:
            t = tables[name]
            ids = [row["id"] for row in before_state[name]]
            for start in range(0, len(ids), 400):
                if conn.scalar(select(func.count()).select_from(t).where(t.c.id.in_(ids[start:start + 400]))):
                    raise ValueError(f"Reset incomplete: remaining rows in {name}")
        if any(report["after"].values()) or after_state["users"] != [{**user, "native_language": None}]:
            raise ValueError("Reset incomplete: account or learning postconditions failed")
        for name in PRESERVED - {"users", "user_preferences"}:
            if before_state[name] != after_state[name]:
                raise ValueError(f"Preservation failed: {name}")
        expected_prefs = [{**row, "default_language_id": None,
                           "ui_prefs_json": {k: v for k, v in (row["ui_prefs_json"] or {}).items()
                                             if k not in PEDAGOGICAL_PREF_KEYS}}
                          if row["default_language_id"] is not None or PEDAGOGICAL_PREF_KEYS & set(row["ui_prefs_json"] or {})
                          else row for row in prefs]
        if after_state["user_preferences"] != expected_prefs:
            raise ValueError("Preservation failed: profile/UI preferences")
        report["write_performed"] = bool(sum(before.values()) + updates)
    return report, fingerprint(before_state)


def reset_learning(conn, *, user_id=None, user_email=None, apply=False):
    """Caller-owned transaction: does not commit or rollback. Use run_reset for CLI."""
    return _execute_reset(conn, user_id=user_id, user_email=user_email, apply=apply)[0]


def run_reset(engine, *, user_id=None, user_email=None, apply=False, rollback=False):
    if bool(user_id) == bool(user_email):
        raise ValueError("Exactly one --user-id OR --user-email is required")
    if rollback and not apply:
        raise ValueError("--rollback requires --apply")
    dialect = engine.dialect.name
    if dialect not in {"sqlite", "postgresql"}:
        raise ValueError("Only PostgreSQL and SQLite are supported")
    with engine.connect() as conn:
        if dialect == "postgresql":
            conn = conn.execution_options(isolation_level="SERIALIZABLE")
        else:
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")
            conn.exec_driver_sql("PRAGMA query_only=" + ("OFF" if apply else "ON"))
            conn.commit()
        tx = conn.begin()
        try:
            if dialect == "sqlite":
                conn.exec_driver_sql("BEGIN IMMEDIATE" if apply else "BEGIN")
            else:
                if not apply:
                    conn.exec_driver_sql("SET TRANSACTION READ ONLY")
                conn.exec_driver_sql("SET LOCAL lock_timeout = '2s'")
                conn.exec_driver_sql("SET LOCAL statement_timeout = '60s'")
            report, before_hash = _execute_reset(conn, user_id=user_id, user_email=user_email, apply=apply)
            if apply and not rollback:
                tx.commit()
                report["transaction"] = "committed"
                report["write_committed"] = report["write_performed"]
            else:
                tx.rollback()
                report["transaction"] = "rolled_back" if apply else "read_only_dry_run"
                if rollback:
                    tables = validate_schema(conn)
                    uid = report["user"]["id"]
                    restored = personal_snapshot(conn, tables, scoped_queries(tables, uid), uid)
                    report["rollback_verified"] = fingerprint(restored) == before_hash
                    if not report["rollback_verified"]:
                        raise ValueError("Rollback comparison failed; inspect concurrent activity")
                    report["persisted_after"] = dict(report["before"])
            return report
        except Exception:
            if tx.is_active:
                tx.rollback()
            raise
        finally:
            if dialect == "sqlite":
                # query_only belongs to the connection and survives rollback.
                conn.rollback()
                conn.exec_driver_sql("PRAGMA query_only=OFF")
                conn.commit()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    who = parser.add_mutually_exclusive_group(required=True)
    who.add_argument("--user-id")
    who.add_argument("--user-email")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    args = parser.parse_args(argv)
    if args.rollback and not args.apply:
        parser.error("--rollback requires --apply")
    from app.core.config import get_settings
    url = make_url(get_settings().database_url)
    if url.get_backend_name() == "sqlite":
        path = Path(url.database or "").resolve()
        if not path.is_file():
            parser.error("Use an existing SQLite database file; none will be created")
        if not args.apply:
            url = url.set(database=f"file:{path.as_posix()}", query={"mode": "ro", "uri": "true"})
    elif url.get_backend_name() != "postgresql":
        parser.error("Only PostgreSQL and SQLite are supported")
    engine = create_engine(url)
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        report = run_reset(engine, user_id=args.user_id, user_email=args.user_email,
                           apply=args.apply, rollback=args.rollback)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except ValueError as exc:
        print(f"Reset refused: {exc}. No reset was committed.", file=sys.stderr)
        return 1
    except Exception as exc:
        # Driver exceptions may contain SQL parameters, credentials or URL.
        print(f"Reset failed ({type(exc).__name__}); no partial reset is allowed. "
              "Inspect schema/connectivity and concurrent activity before retrying.", file=sys.stderr)
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
