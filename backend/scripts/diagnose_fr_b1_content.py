"""Trace the reported FR/B1 incident. No repair, cache access, or ORM writes.

Run from backend: python scripts/diagnose_fr_b1_content.py
Uses DATABASE_URL from existing settings; never prints the connection URL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import String, cast, create_engine, func, or_, select
from sqlalchemy.engine import make_url
from app.models import (
    AiResponseCache, ContentSource, ContentUnit, CurriculumBlock, Language,
    Lesson, LessonContentUsage, User, UserLanguage,
)

NEEDLES = (
    "Logical Structure for Opinion & Justification in French",
    "Logic: In French", "we create a chain", "Connectors have fixed roles",
)
FIELDS = (
    "title", "subtitle", "objective", "explanation", "logic_title",
    "logic_title_native", "explanation_native", "support_language",
)
PROVENANCE_FIELDS = (
    "provider", "content_origin", "model", "source_id", "template_id", "prompt_version",
)


def normal(value):
    return " ".join(unicodedata.normalize("NFKC", str(value)).casefold().split())


def contaminated_fields(payload, path=""):
    """Known incident markers only; this is not a general language detector."""
    if isinstance(payload, dict):
        return [p for key, value in payload.items()
                for p in contaminated_fields(value, f"{path}.{key}".lstrip("."))]
    if isinstance(payload, list):
        return [p for index, value in enumerate(payload)
                for p in contaminated_fields(value, f"{path}[{index}]")]
    if isinstance(payload, str) and any(normal(n) in normal(payload) for n in NEEDLES):
        return [path]
    return []


def describe_payload(payload):
    payload = payload if isinstance(payload, dict) else {}
    thread = payload.get("thread")
    return {
        "learner_fields": {key: str(payload[key])[:1500] for key in FIELDS if key in payload},
        "cefr_level": payload.get("content_level") or payload.get("level"),
        "native_language": payload.get("native_language"),
        "payload_target_language": payload.get("target_language") or payload.get("language_code"),
        "provenance": {key: payload.get(key) for key in PROVENANCE_FIELDS},
        "thread_metadata": {key: thread[key] for key in ("guaranteed", "sources") if key in thread}
        if isinstance(thread, dict) else None,
        "contaminated_fields": contaminated_fields(payload),
    }


def match_clause(payload_column, title_column=None):
    columns = [cast(payload_column, String)]
    if title_column is not None:
        columns.append(title_column)
    return or_(*(column.ilike(f"%{needle}%") for column in columns for needle in NEEDLES))


def unit_details(conn, ids):
    if not ids:
        return []
    units, sources = ContentUnit.__table__, ContentSource.__table__
    stmt = select(units.c.id, units.c.source_id, units.c.title, units.c.origin_type,
                  units.c.validation_status, units.c.is_active, units.c.payload_json,
                  sources.c.source_type).select_from(
                      units.outerjoin(sources, units.c.source_id == sources.c.id)
                  ).where(units.c.id.in_(ids)).order_by(units.c.id)
    return [{**{key: row[key] for key in (
        "id", "source_id", "title", "origin_type", "validation_status", "is_active", "source_type"
    )}, **describe_payload(row["payload_json"])} for row in conn.execute(stmt).mappings()]


def diagnose(conn, limit=200):
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    units, lessons, cache = ContentUnit.__table__, Lesson.__table__, AiResponseCache.__table__
    langs, owners, users = Language.__table__, UserLanguage.__table__, User.__table__
    sources, usage, blocks = ContentSource.__table__, LessonContentUsage.__table__, CurriculumBlock.__table__
    conditions = {
        "content_units": match_clause(units.c.payload_json, units.c.title),
        "lessons": match_clause(lessons.c.content_json, lessons.c.title),
        "ai_response_cache": match_clause(cache.c.response_json),
    }
    report = {"incident_id": "2bbf6b59c0b5b", "read_only": True,
              "scope": "known text markers across all languages/levels; no generic English classification",
              "counts": {}, "records": [], "limit_per_table": limit, "truncated_tables": []}
    for table in (units, lessons, cache):
        count = conn.scalar(select(func.count()).select_from(table).where(conditions[table.name]))
        report["counts"][table.name] = count
        if count > limit:
            report["truncated_tables"].append(table.name)
    report["matched_users_count"] = conn.scalar(
        select(func.count(func.distinct(owners.c.user_id))).select_from(
            lessons.join(owners, lessons.c.user_language_id == owners.c.id)
        ).where(conditions["lessons"])
    )

    stmt = select(units, langs.c.code.label("language_code"), sources.c.source_type).select_from(
        units.outerjoin(langs, units.c.language_id == langs.c.id)
        .outerjoin(sources, units.c.source_id == sources.c.id)
    ).where(conditions["content_units"]).order_by(units.c.id).limit(limit)
    for row in conn.execute(stmt).mappings():
        record = {**describe_payload(row["payload_json"]), "record_type": "content_units",
                  **{key: row[key] for key in ("id", "title", "language_code", "cefr_level", "is_active", "validation_status")}}
        record["provenance"].update(source_id=row["source_id"], origin_type=row["origin_type"], source_type=row["source_type"])
        record["materialized_lesson_ids"] = list(conn.scalars(select(usage.c.lesson_id).where(usage.c.content_unit_id == row["id"]).distinct().order_by(usage.c.lesson_id)))
        if contaminated_fields(row["title"]):
            record["contaminated_fields"].append("stored_title")
        report["records"].append(record)

    stmt = select(lessons, langs.c.code.label("language_code"), owners.c.user_id,
                  users.c.native_language.label("current_user_native_language")).select_from(
        lessons.join(owners, lessons.c.user_language_id == owners.c.id)
        .outerjoin(langs, owners.c.language_id == langs.c.id)
        .outerjoin(users, owners.c.user_id == users.c.id)
    ).where(conditions["lessons"]).order_by(lessons.c.id).limit(limit)
    for row in conn.execute(stmt).mappings():
        record = {**describe_payload(row["content_json"]), "record_type": "lessons",
                  **{key: row[key] for key in ("id", "title", "objective", "status", "language_code", "current_user_native_language")},
                  "created_at": str(row["created_at"]),
                  "user_ref": hashlib.sha256(str(row["user_id"]).encode()).hexdigest()[:16]}
        record["linked_content_unit_ids"] = list(conn.scalars(select(usage.c.content_unit_id).where(usage.c.lesson_id == row["id"]).distinct().order_by(usage.c.content_unit_id)))
        record["linked_units"] = unit_details(conn, record["linked_content_unit_ids"])
        record["curriculum_references"] = [dict(b) for b in conn.execute(select(
            blocks.c.id, blocks.c.day_id, blocks.c.status, blocks.c.cefr_level,
            blocks.c.skill, blocks.c.topic
        ).where(blocks.c.lesson_ref == row["id"]).order_by(blocks.c.id)).mappings()]
        if contaminated_fields(row["title"]):
            record["contaminated_fields"].append("stored_title")
        report["records"].append(record)

    for row in conn.execute(select(cache).where(conditions["ai_response_cache"]).order_by(cache.c.id).limit(limit)).mappings():
        record = {**describe_payload(row["response_json"]), "record_type": "ai_response_cache",
                  "id": row["id"], "language_code": row["language_code"], "cefr_level": row["level"],
                  "hit_count": row["hit_count"]}
        # Keep payload declarations and stored cache provenance distinct.
        record["cache_provenance"] = {key: row[key] for key in ("provider", "model", "prompt_version", "capability")}
        report["records"].append(record)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()
    from app.core.config import get_settings
    url = make_url(get_settings().database_url)
    dialect = url.get_backend_name()
    if dialect == "sqlite":
        if not url.database or url.database == ":memory:":
            parser.error("Use an existing file database for this read-only diagnostic")
        database = Path(url.database).resolve()
        if not database.is_file():
            parser.error("Database file does not exist; no file will be created")
        url = url.set(database=f"file:{database.as_posix()}", query={"mode": "ro", "uri": "true"})
    elif dialect != "postgresql":
        parser.error("Only PostgreSQL and existing SQLite files are supported")
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            if dialect == "postgresql":
                conn.exec_driver_sql("SET TRANSACTION READ ONLY")
                conn.exec_driver_sql("SET LOCAL statement_timeout = '15s'")
                conn.exec_driver_sql("SET LOCAL lock_timeout = '2s'")
            else:
                conn.exec_driver_sql("PRAGMA query_only = ON")
            report = diagnose(conn, args.limit)
            conn.rollback()
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except Exception as exc:
        # Driver exceptions can contain URLs/parameters; do not print them.
        print(f"Read-only diagnostic failed ({type(exc).__name__}); verify connectivity and schema including migration 0016. No repair was executed.", file=sys.stderr)
        return 1
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
