"""Export one placement and its evidence. No seeds, repairs or writes.

Run in the backend container:
    python scripts/audit_placement_result.py --test-id UUID

PostgreSQL uses a verified REPEATABLE READ, READ ONLY transaction. JSON goes
to stdout only; credentials and unrelated users are never exported.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.api.placement_tests import _add_diagnostic_contract, _records
from app.core.levels import ESSENTIAL_SKILLS, LEVEL_INDEX, SKILL_WEIGHTS, Skill
from app.models import Language, PlacementItem, PlacementItemDelivery, PlacementTest, PlacementTestAnswer, PlacementTestSection, UserLanguage
from app.services import placement_engine as engine


@contextmanager
def read_only_snapshot(db_engine):
    """Database-enforced read-only, rollback on every exit, no commit."""
    dialect = db_engine.dialect.name
    if dialect not in {"postgresql", "sqlite"}:
        raise ValueError("unsupported_database_dialect")
    with db_engine.connect() as conn:
        if dialect == "postgresql":
            conn = conn.execution_options(isolation_level="REPEATABLE READ")
            conn.begin()
            conn.exec_driver_sql("SET TRANSACTION READ ONLY")
            conn.exec_driver_sql("SET LOCAL statement_timeout = '15s'")
            if conn.exec_driver_sql("SHOW transaction_read_only").scalar() != "on":
                raise RuntimeError("read_only_transaction_not_verified")
        else:
            # Local tests only; preserve the connection's prior safety setting.
            previous = conn.exec_driver_sql("PRAGMA query_only").scalar()
            conn.exec_driver_sql("PRAGMA query_only=ON")
            if conn.exec_driver_sql("PRAGMA query_only").scalar() != 1:
                raise RuntimeError("read_only_transaction_not_verified")
        try:
            yield conn
        finally:
            conn.rollback()
            if dialect == "sqlite":
                conn.exec_driver_sql(f"PRAGMA query_only={int(previous)}")
                conn.rollback()


def _rows(conn, model, *conditions, order_by=None):
    query = select(model.__table__).where(*conditions)
    if order_by is not None:
        query = query.order_by(order_by)
    return [dict(row) for row in conn.execute(query).mappings()]


def _utc(value):
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _source_fingerprints():
    root = Path(__file__).resolve().parents[1]
    files = ["app/api/placement_tests.py", "app/services/placement_engine.py",
             "app/services/writing_evaluation.py", "app/services/placement_delivery.py",
             "app/core/levels.py", "scripts/audit_placement_result.py"]
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() if (root / name).is_file() else None
            for name in files}


def _skill_evidence(records):
    result = {}
    for skill in Skill:
        answers = [record for record in records if record.skill == skill]
        bands = defaultdict(list)
        for record in answers:
            bands[record.cefr_level].append(record.normalized_score)
        band_rows = []
        for band, scores in sorted(bands.items(), key=lambda item: LEVEL_INDEX.get(item[0], -1)):
            mean = sum(scores) / len(scores)
            band_rows.append({
                "cefr_level": band, "count": len(scores), "score_sum": sum(scores),
                "accuracy": mean,
                "meets_deciding_band_rule": mean >= engine.BAND_MASTERY_THRESHOLD
                and len(scores) >= engine.MIN_ITEMS_AT_DECIDING_BAND and band in LEVEL_INDEX,
            })
        level = None if skill in engine.PRODUCTION_SKILLS else engine.estimate_skill_level(answers)
        if skill in engine.PRODUCTION_SKILLS:
            reason = "production_skill_excluded_by_records_and_skill_results"
        elif len(answers) < engine.MIN_ITEMS_PER_SKILL:
            reason = "fewer_than_min_items_per_skill"
        elif level is None:
            reason = "no_band_meets_minimum_count_and_accuracy"
        else:
            reason = None
        result[skill] = {"records": len(answers), "bands": band_rows,
                         "estimated_level": level, "no_cefr_reason": reason}
    return result


def _confidence_calculation(result, records):
    skills = {skill: data for skill, data in result["skills"].items() if data["estimated_level"]}
    if not records or not skills:
        return {"final": 0.0, "reason": "no_records_or_no_assessed_skills"}
    n = len(records)
    volume = 25 if n >= engine.RECOMMENDED_OBJECTIVE_ITEMS else 15 if n >= engine.MIN_OBJECTIVE_ITEMS else 5
    indexes = [LEVEL_INDEX[value["estimated_level"]] for value in skills.values()]
    spread = max(indexes) - min(indexes)
    fast = sum(record.response_time_ms is not None and record.response_time_ms < engine.FAST_RESPONSE_MS for record in records)
    fast_penalty = min(fast / n, 0.5) * 20
    missing = sorted(set(ESSENTIAL_SKILLS) - set(skills))
    raw = 40 + volume + min(len(skills), 5) * 4 - spread * 5 - fast_penalty - len(missing) * 7
    return {
        "base": 40, "records_count": n, "volume_bonus": volume,
        "assessed_skills_count": len(skills), "coverage_bonus": min(len(skills), 5) * 4,
        "level_spread": spread, "spread_penalty": spread * 5,
        "fast_response_threshold_ms": engine.FAST_RESPONSE_MS, "fast_responses": fast,
        "fast_response_penalty": fast_penalty, "missing_essential_skills": missing,
        "missing_essential_penalty": len(missing) * 7, "before_clamp": raw,
        "final": round(max(0.0, min(100.0, raw)), 1),
        "meaning": "legacy_heuristic_index_not_used_in_v2_result",
    }


def collect_report(conn, test_id):
    tests = _rows(conn, PlacementTest, PlacementTest.id == test_id)
    if not tests:
        raise ValueError("placement_test_not_found")
    test = tests[0]
    answers = _rows(conn, PlacementTestAnswer, PlacementTestAnswer.test_id == test_id,
                    order_by=PlacementTestAnswer.created_at)
    deliveries = _rows(conn, PlacementItemDelivery, PlacementItemDelivery.test_id == test_id,
                       order_by=PlacementItemDelivery.delivered_at)
    sections = _rows(conn, PlacementTestSection, PlacementTestSection.test_id == test_id)
    items = _rows(conn, PlacementItem, PlacementItem.language_code == test["language_code"])
    item_ids = {row["item_id"] for row in answers + deliveries}
    missing = item_ids - {row["id"] for row in items}
    if missing:
        items.extend(_rows(conn, PlacementItem, PlacementItem.id.in_(missing)))
    by_item = {row["id"]: row for row in items}
    by_answer = {row["item_id"]: row for row in answers}
    by_delivery = {row["item_id"]: row for row in deliveries}
    records = _records([SimpleNamespace(**row) for row in answers])
    raw_result = engine.build_result(records, duration_seconds=test.get("duration_seconds"))
    result = dict(raw_result)
    _add_diagnostic_contract(result, records)
    evidence = _skill_evidence(records)
    activities = []
    ordered_ids = sorted(item_ids, key=lambda item_id: (
        _utc((by_delivery.get(item_id) or {}).get("delivered_at") or (by_answer.get(item_id) or {}).get("created_at")), item_id))
    for order, item_id in enumerate(ordered_ids, 1):
        item = by_item.get(item_id)
        answer = by_answer.get(item_id)
        delivery = by_delivery.get(item_id)
        included = answer is not None and answer["normalized_score"] is not None and answer["skill"] not in engine.PRODUCTION_SKILLS
        exclusion = "no_answer" if answer is None else "normalized_score_is_null" if answer["normalized_score"] is None else "production_skill_excluded_by_records" if answer["skill"] in engine.PRODUCTION_SKILLS else None
        audio = bool(item and (item.get("audio_script") or item.get("audio_url")))
        answer_payload = (answer or {}).get("answer_json") or {}
        voice_keys = [key for key in ("audio", "audio_url", "audio_base64", "recording", "recording_url", "voice") if answer_payload.get(key)]
        answer_skill = (answer or {}).get("skill")
        activities.append({
            "order": order, "placement_item_id": item_id, "delivery_id": (delivery or {}).get("id"),
            "item_type": (item or {}).get("item_type"), "item_skill": (item or {}).get("skill"),
            "answer_skill": answer_skill, "skill_used_by_engine": answer_skill if included else None,
            "modality_inferred_from_fields": "text_and_audio" if audio else "text",
            "has_text": bool(item and any(item.get(key) for key in ("prompt", "instructions", "passage"))),
            "has_reading_passage": bool(item and item.get("passage")),
            "has_audio_available": audio, "has_voice_recording": bool(voice_keys), "voice_payload_keys": voice_keys,
            "response_kind": "writing_text" if "text" in answer_payload else "selected_value" if "value" in answer_payload else "unknown_or_unanswered",
            "normalized_max_score": 1.0 if answer and answer["normalized_score"] is not None else None,
            "max_score_basis": "normalized_0_to_1_scale_not_a_persisted_answer_column",
            "entered_records": included, "records_exclusion_reason": exclusion,
            "entered_candidate_skill_estimation": included,
            "skill_cefr_emitted": bool(included and evidence[answer_skill]["estimated_level"]),
            "skill_no_cefr_reason": evidence.get(answer_skill, {}).get("no_cefr_reason"),
            "item_answer_skill_mismatch": bool(item and answer and item["skill"] != answer_skill),
            "item_answer_cefr_mismatch": bool(item and answer and item["cefr_level"] != answer["cefr_level"]),
            "item_language_mismatch": bool(item and item["language_code"] != test["language_code"]),
            "item_updated_after_answer": bool(item and answer and _utc(item["updated_at"]) > _utc(answer["created_at"])),
            "item": item, "delivery": delivery, "answer": answer,
        })

    counts = {}
    for skill in Skill:
        eligible_items = [item for item in items if item["language_code"] == test["language_code"] and item["skill"] == skill and item["is_active"] and item["review_status"] == "approved"]
        counts[skill] = {
            "delivered_by_current_item_skill": sum(row["item_skill"] == skill and row["delivery"] is not None for row in activities),
            "answered": sum(row["skill"] == skill for row in answers),
            "scored_answers": sum(row["skill"] == skill and row["normalized_score"] is not None for row in answers),
            "records": evidence[skill]["records"], "cefr_emitted": evidence[skill]["estimated_level"] is not None,
            "eligible_bank_items_now": len(eligible_items),
            "eligible_bank_items_remaining_now": sum(item["id"] not in by_answer for item in eligible_items),
        }
    matrix = defaultdict(Counter)
    for item in items:
        if item["language_code"] == test["language_code"]:
            key = (item["skill"], item["cefr_level"])
            matrix[key]["total"] += 1
            if item["is_active"] and item["review_status"] == "approved":
                matrix[key]["eligible_now"] += 1
    inventory = [{key: item.get(key) for key in (
        "id", "external_key", "skill", "cefr_level", "item_type", "difficulty", "discrimination",
        "is_active", "review_status", "source", "version", "updated_at")}
        for item in items if item["language_code"] == test["language_code"]]
    for row in inventory:
        item = by_item[row["id"]]
        row.update({"has_audio_script": bool(item.get("audio_script")),
                    "has_audio_url": bool(item.get("audio_url")), "has_passage": bool(item.get("passage"))})
    selector_trace = []
    declared_beginner = bool((test.get("result_json") or {}).get("declared_beginner"))
    state = engine.TestState(current_band=engine.initial_band(declared_beginner))
    for answer in answers:
        if answer["skill"] == Skill.WRITING:
            continue
        preferred = engine.next_skill(state)
        selector_trace.append({"answer_id": answer["id"], "item_id": answer["item_id"],
                               "preferred_skill_before_answer": preferred, "actual_answer_skill": answer["skill"],
                               "preferred_band": engine.state_for(state, preferred).current_band,
                               "fallback_or_mismatch": preferred != answer["skill"]})
        engine.register_answer(state, engine.AnswerRecord(answer["skill"], answer["cefr_level"], answer["normalized_score"] or 0.0, answer["response_time_ms"]))
    raw_weights = result["weights_used"]
    weighted = None
    cap_skills = []
    cap = None
    language = _rows(conn, Language, Language.code == test["language_code"])
    profiles = _rows(conn, UserLanguage, UserLanguage.user_id == test["user_id"],
                     UserLanguage.language_id == language[0]["id"]) if language else []
    stored = test.get("result_json") or {}
    comparisons = {key: {"stored": stored.get(key, test.get(key)), "recomputed": result.get(key),
                         "matches": stored.get(key, test.get(key)) == result.get(key)}
                   for key in ("overall_level", "confidence_score", "items_answered", "skills", "weights_used", "assessed_skills", "not_assessed_skills")}
    return {
        "audit_version": 1, "test_id": test_id, "captured_at_utc": datetime.now(timezone.utc),
        "read_only": True, "database_dialect": conn.dialect.name, "source_sha256": _source_fingerprints(),
        "test": test, "sections": sections, "user_language": profiles,
        "activities": activities, "counts_by_skill": counts, "skill_evidence": evidence,
        "raw_engine_result": raw_result, "recomputed_result": result, "stored_vs_recomputed": comparisons,
        "confidence_calculation": _confidence_calculation(result, records),
        "overall_calculation": {"aggregation_method": "minimum_supported_skill", "overall_estimate_status": result["overall_estimate_status"], "level_indexes": dict(LEVEL_INDEX), "weights": raw_weights,
                                "weights_rounded_in_api_payload": result["weights_used"],
                                "weighted_index": weighted, "rounded_index": round(weighted) if weighted is not None else None,
                                "cap_skills": cap_skills, "cap_index": cap,
                                "maximum_testable_index": max(LEVEL_INDEX[level] for level in engine.TESTABLE_LEVELS),
                                "overall_level": result["overall_level"]},
        "bank_matrix_now": [{"skill": skill, "cefr_level": band, **values} for (skill, band), values in sorted(matrix.items())],
        "bank_inventory_now": inventory, "selector_preference_replay": selector_trace,
        "engine_rules": {"minimum": engine.MIN_OBJECTIVE_ITEMS, "target": engine.RECOMMENDED_OBJECTIVE_ITEMS,
                         "maximum": engine.MAX_OBJECTIVE_ITEMS, "minimum_items_per_skill": engine.MIN_ITEMS_PER_SKILL,
                         "minimum_items_at_deciding_band": engine.MIN_ITEMS_AT_DECIDING_BAND,
                         "band_mastery_threshold": engine.BAND_MASTERY_THRESHOLD,
                         "production_skills_excluded": sorted(engine.PRODUCTION_SKILLS)},
        "limitations": [
            "Current item fields and bank inventory are not historical snapshots. Answer skill and CEFR are persisted at submission.",
            "Delivery stores item_id only; no historical skill, modality or payload snapshot.",
            "Audio fields prove availability, not playback. No playback telemetry in these tables.",
            "Voice flag inspects explicit answer payload keys; it does not prove absence of external recordings.",
            "Selector replay shows preferred skill from saved answers; it cannot prove historic inventory, query ordering or fallback reason.",
            "Answer max_score is not persisted; 1.0 is the normalized score scale.",
            "Read-only exporter never re-evaluates writing via AI or calls complete/next-item.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-id", required=True, type=lambda value: str(uuid.UUID(value)))
    args = parser.parse_args(argv)
    from app.core.database import engine as configured_engine
    if configured_engine.dialect.name != "postgresql":
        print(json.dumps({"error": "production_diagnostic_requires_postgresql", "read_only": True}), file=sys.stderr)
        return 1
    try:
        with read_only_snapshot(configured_engine) as conn:
            report = collect_report(conn, args.test_id)
        print(json.dumps(report, ensure_ascii=False, indent=2, default=lambda value: value.isoformat() if isinstance(value, datetime) else str(value)))
        return 0
    except Exception as exc:
        # Do not print exception/DSN text: SQLAlchemy errors can include secrets.
        print(json.dumps({"error": "placement_audit_failed", "exception_type": type(exc).__name__,
                          "reason": str(exc) if isinstance(exc, ValueError) and str(exc) == "placement_test_not_found" else "read_failed_no_database_changes",
                          "read_only": True}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
