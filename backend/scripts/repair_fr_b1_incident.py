"""Bounded repair of the confirmed historical FR/B1 lesson.

Default: dry-run. --apply requires the block ID reviewed in the dry-run.
--apply --rollback rehearses the invalidation and rolls the transaction back.
No AI call, content rewrite, DELETE, progress or enrollment changes.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from app.models import (
    Curriculum, CurriculumBlock, CurriculumDay, CurriculumWeek, Language, Lesson,
    LessonActivityAttempt, LessonContentUsage, User, UserLanguage,
)
from app.services.editorial_validation import has_known_incompatible_english

LESSON_ID = "f2ab192f-36ef-42d0-b7aa-1038c8d230d2"
EXPECTED_TITLE = "Logical Structure for Opinion & Justification in French"
EXPECTED_TOPIC = "Opinião e justificativa — estruturas-chave"
EXPECTED_MODEL = "nvidia/nemotron-3.5-lightning"


def _row(db, model, row_id, lock):
    query = select(model).where(model.id == row_id)
    if lock:
        query = query.with_for_update()
    return db.scalar(query.execution_options(populate_existing=True))


def repair(db: Session, *, apply=False, block_id=None):
    """Flush only; the caller must commit or rollback the entire transaction.

    The production CLI wraps this in a transaction with timeouts. FOR UPDATE
    serializes writes on PostgreSQL; dry-run performs SELECT statements only.
    """
    if apply and not block_id:
        raise ValueError("Writing requires an explicit reviewed --block-id")
    lesson_query = select(Lesson).where(Lesson.id == LESSON_ID)
    if apply:
        lesson_query = lesson_query.with_for_update()
    lesson = db.scalar(lesson_query.execution_options(populate_existing=True))
    if lesson is None:
        raise ValueError("Confirmed lesson_id does not exist in this database")
    owner = _row(db, UserLanguage, lesson.user_language_id, apply)
    language = _row(db, Language, owner.language_id, apply) if owner else None
    user = _row(db, User, owner.user_id, apply) if owner else None
    payload = lesson.content_json if isinstance(lesson.content_json, Mapping) else {}
    if not (language and language.code == "fr" and user and user.native_language == "pt-BR"):
        raise ValueError("Confirmed target/native/owner preconditions changed")
    if not (
        lesson.title == EXPECTED_TITLE and payload.get("target_language") == "fr"
        and payload.get("native_language") is None
        and payload.get("provider") == "openrouter" and payload.get("content_origin") == "openrouter"
        and payload.get("model") == EXPECTED_MODEL
        and (payload.get("content_level") or payload.get("level")) == "B1"
        and has_known_incompatible_english(payload,"fr","pt-BR")
    ):
        raise ValueError("Confirmed lesson content/provenance changed; inspect a fresh dry-run")
    if db.scalar(select(func.count()).select_from(LessonContentUsage).where(LessonContentUsage.lesson_id == LESSON_ID)):
        raise ValueError("Unexpected related ContentUnit; repair requires new review")

    references_query = select(CurriculumBlock).where(CurriculumBlock.lesson_ref == LESSON_ID).order_by(CurriculumBlock.id)
    if apply:
        references_query = references_query.with_for_update()
    references = list(db.scalars(references_query.execution_options(populate_existing=True)))
    if block_id:
        block_query = select(CurriculumBlock).where(CurriculumBlock.id == block_id)
        if apply:
            block_query = block_query.with_for_update()
        block = db.scalar(block_query.execution_options(populate_existing=True))
        if block is None:
            raise ValueError("Reviewed block-id does not exist")
    elif len(references) == 1:
        block = references[0]
    else:
        raise ValueError("Expected exactly one related block; review its IDs before proceeding")
    day = _row(db, CurriculumDay,block.day_id,apply)
    week = _row(db, CurriculumWeek,day.week_id,apply) if day else None
    curriculum = _row(db, Curriculum,week.curriculum_id,apply) if week else None
    if not (
        curriculum and curriculum.user_language_id == owner.id and curriculum.status == "active"
        and day.status in {"pending","in_progress"}
        and block.skill == "grammar" and block.cefr_level == "B1" and block.topic == EXPECTED_TOPIC
        and block.status == "pending" and block.score is None
    ):
        raise ValueError("Reviewed block/curriculum/owner/status preconditions changed")

    already_applied = lesson.status == "language_invalid" and block.lesson_ref == LESSON_ID
    if not already_applied and not (lesson.status == "active" and block.lesson_ref == LESSON_ID):
        raise ValueError("Lesson/block state changed; completed history must remain untouched")
    if len(references) != 1:
        raise ValueError("Unexpected other block references; requires new review")

    result = {
        "incident_id":"2bbf6b59c0cb0b5b", "lesson_id":LESSON_ID,
        "current_status":lesson.status,
        "curriculum_blocks":[{"id":block.id,"day_id":block.day_id,"status":block.status,
                              "lesson_ref":block.lesson_ref,"skill":block.skill,
                              "cefr_level":block.cefr_level,"topic":block.topic}],
        "proposed_action":"already_applied" if already_applied else "invalidate_lesson_pending_regeneration",
        "expected_result":{
            "historical_lesson_status":"language_invalid", "block_lesson_ref":LESSON_ID,
            "block_status":"pending", "next_open":"Generate a validated FR/pt-BR lesson and atomically replace lesson_ref; failure preserves the old reference",
            "preserved":"Historical payload/title, previous answers, curriculum, enrollment, progress, sessions and scores",
        },
        "previous_objective_answers":db.scalar(select(func.count()).select_from(LessonActivityAttempt).where(LessonActivityAttempt.lesson_id == LESSON_ID)),
        "write_performed":False,
    }
    if apply and not already_applied:
        lesson.status = "language_invalid"
        db.flush()
        result["write_performed"] = True
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-id", help="Exact block ID reviewed in the dry-run")
    parser.add_argument("--apply", action="store_true", help="Explicitly enable invalidation of the confirmed lesson")
    parser.add_argument("--rollback", action="store_true", help="Rehearse --apply then rollback instead of commit")
    args = parser.parse_args()
    if args.apply and not args.block_id:
        parser.error("--apply requires --block-id from the reviewed dry-run")
    if args.rollback and not args.apply:
        parser.error("--rollback requires --apply; default dry-run never writes")
    from app.core.config import get_settings
    url = make_url(get_settings().database_url)
    dialect = url.get_backend_name()
    if dialect == "sqlite":
        database = Path(url.database or "").resolve()
        if not database.is_file():
            parser.error("Use an existing database file; none will be created")
        if not args.apply:
            url = url.set(database=f"file:{database.as_posix()}",query={"mode":"ro","uri":"true"})
    elif dialect != "postgresql":
        parser.error("Only PostgreSQL and existing SQLite files are supported")
    engine = create_engine(url)
    try:
        with Session(engine) as db:
            transaction = db.begin()
            conn = db.connection()
            if dialect == "postgresql":
                if not args.apply:
                    conn.exec_driver_sql("SET TRANSACTION READ ONLY")
                conn.exec_driver_sql("SET LOCAL statement_timeout = '15s'")
                conn.exec_driver_sql("SET LOCAL lock_timeout = '2s'")
            elif args.apply:
                conn.exec_driver_sql("BEGIN IMMEDIATE")
            else:
                conn.exec_driver_sql("PRAGMA query_only = ON")
            result = repair(db,apply=args.apply,block_id=args.block_id)
            if args.apply and not args.rollback:
                transaction.commit()
                result["transaction"] = "committed"
            else:
                transaction.rollback()
                result["transaction"] = "rolled_back" if args.apply else "read_only_dry_run"
            result["write_committed"] = bool(args.apply and not args.rollback and result["write_performed"])
        if hasattr(sys.stdout,"reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except ValueError as exc:
        print(f"Repair refused: {exc}. Transaction was not committed.",file=sys.stderr)
        return 1
    except Exception as exc:
        # Driver errors can include connection details: return only the class.
        print(f"Repair failed ({type(exc).__name__}); verify schema/connectivity. Transaction was not committed.",file=sys.stderr)
        return 1
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
