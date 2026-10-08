"""Deterministic exposure accounting, not a psychometric model."""
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from sqlalchemy import select, or_, and_
from app.models import PlacementItem, PlacementItemDelivery, PlacementItemExposure, PlacementTest, PlacementTestAnswer

POLICY = "placement-exposure-v2"
EXPOSURE_POLICY = {"version": POLICY, "cooldown_days": 30,
                   "reused_evidence_eligible": False, "preserve_history_on_reset": True}


def grading_contract(item):
    """Immutable delivery contract; semantic identity deliberately ignores versions."""
    fields = ("language_code", "skill", "cefr_level", "version", "item_type", "instructions",
              "prompt", "passage", "audio_script", "audio_url", "options_json",
              "correct_answer_json", "rubric_json")
    return hashlib.sha256(json.dumps({field: getattr(item, field) for field in fields},
        ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def delivery_changed(item, exposure):
    contract = exposure.snapshot_json.get("grading_contract")
    return (contract != grading_contract(item) if contract else
            exposure.keys_json != semantic_keys(item))


def semantic_keys(item):
    def clean(value):
        return re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(value or ""))).strip()
    def digest(value):
        return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    options = item.options_json or []
    texts = [clean(x.get("text", x.get("label", x.get("value", "")))) if isinstance(x, dict) else clean(x) for x in options]
    answer = dict(item.correct_answer_json or {})
    value = answer.get("value")
    option_map = {str(x.get("id", x.get("value"))): text for x, text in zip(options, texts)
                  if isinstance(x, dict) and x.get("id", x.get("value")) is not None}
    if str(value) in option_map:
        answer["value"] = option_map[str(value)]
    if isinstance(answer.get("accepted"), list):
        answer["accepted"] = sorted(clean(option_map.get(str(x), x)) for x in answer["accepted"])
    keys = {"exact": digest([item.language_code, item.skill, item.item_type, clean(item.instructions),
        clean(item.prompt), clean(item.passage), clean(item.audio_script), sorted(texts), answer])}
    for name, content in (("passage", item.passage), ("audio", item.audio_script or item.audio_url)):
        if clean(content):
            keys[name] = digest([item.language_code, name, clean(content)])
    if not item.passage and not item.audio_script and not item.audio_url:
        keys["prompt"] = digest([item.language_code, item.skill, clean(item.prompt), sorted(texts)])
    family = (item.rubric_json or {}).get("stimulus_family_key")
    if family:
        keys["family"] = digest([item.language_code, family])
    return keys


def exposure_history(db, user_id, language_code, exclude_test_id=None):
    events = {}
    ledger = db.scalars(select(PlacementItemExposure).where(
        PlacementItemExposure.user_id == user_id, PlacementItemExposure.language_code == language_code))
    for row in ledger:
        if row.source_test_id != exclude_test_id:
            events[row.origin_key] = {"keys": row.keys_json, "answered": row.answered_at is not None,
                "item_id": row.source_item_id,
                "revealed": row.feedback_revealed_at is not None,
                "origin": row.snapshot_json.get("origin", "snapshot"), "seen_at": row.seen_at}
    tests = list(db.scalars(select(PlacementTest.id).where(PlacementTest.user_id == user_id,
        PlacementTest.language_code == language_code, PlacementTest.id != (exclude_test_id or ""))))
    if not tests:
        return list(events.values())
    deliveries = list(db.scalars(select(PlacementItemDelivery).where(PlacementItemDelivery.test_id.in_(tests))))
    delivered = {(d.test_id, d.item_id): d for d in deliveries}
    answers = {(a.test_id, a.item_id): a for a in db.scalars(select(PlacementTestAnswer).where(PlacementTestAnswer.test_id.in_(tests)))}
    for identity in set(delivered) | set(answers):
        delivery, answer = delivered.get(identity), answers.get(identity)
        origin_key = f"delivery:{delivery.id}" if delivery else f"answer:{answer.id}"
        if origin_key in events:
            continue
        item = db.get(PlacementItem, identity[1])
        if item:
            feedback = answer.feedback_json or {} if answer else {}
            events[origin_key] = {"keys": semantic_keys(item), "answered": answer is not None,
                "item_id": item.id,
                "revealed": bool(feedback.get("feedback_revealed")), "origin": "legacy_current_item",
                "seen_at": delivery.delivered_at if delivery else answer.created_at}
    return list(events.values())


def exposure_metadata(item, history, keys=None):
    keys = keys if keys is not None else semantic_keys(item)
    matches = [event for event in history if (item.id is not None and event.get("item_id") == item.id)
               or any(event["keys"].get(k) == value for k, value in keys.items())]
    revealed = any(e.get("revealed") for e in matches)
    answered = any(e.get("answered") for e in matches)
    reused = bool(matches)
    return {"policy_version": POLICY, "reused": reused, "previous_exposure_count": len(matches),
        "exposure_status": "feedback_revealed" if revealed else "answered" if answered else "seen" if reused else "fresh",
        "seen": reused, "answered": answered, "feedback_revealed": revealed,
        "feedback_revelation_known": revealed or not any(e.get("origin") == "legacy_current_item" for e in matches),
        "stimulus_reused": any(any(e["keys"].get(k) == keys.get(k) for k in ("passage", "audio", "family") if k in keys) for e in matches),
        "evidence_eligible": not reused, "reuse_reason": "fresh_bank_exhausted" if reused else None}


def record_delivery(db, test, item, delivery):
    origin = f"delivery:{delivery.id}"
    row = db.scalar(select(PlacementItemExposure).where(PlacementItemExposure.user_id == test.user_id,
        PlacementItemExposure.origin_key == origin))
    if row is None:
        metadata = exposure_metadata(item, exposure_history(db, test.user_id, test.language_code, test.id))
        row = PlacementItemExposure(user_id=test.user_id, language_code=test.language_code,
            origin_key=origin, source_test_id=test.id, source_item_id=item.id, keys_json=semantic_keys(item),
            snapshot_json={"exposure": metadata, "skill": item.skill, "cefr": item.cefr_level,
                "item_version": item.version, "grading_contract": grading_contract(item),
                "key_version": POLICY, "origin": "snapshot"}, seen_at=delivery.delivered_at)
        db.add(row); db.flush()
    return row


def record_answer(db, test, item):
    delivery = db.scalar(select(PlacementItemDelivery).where(PlacementItemDelivery.test_id == test.id,
        PlacementItemDelivery.item_id == item.id))
    row = record_delivery(db, test, item, delivery)
    row.answered_at = datetime.now(timezone.utc)
    return row.snapshot_json["exposure"]


def fresh_pool(items, history):
    return [item for item in items if not exposure_metadata(item, history)["reused"]]


def bank_freshness(db, user_id, language_code, test_id=None):
    from app.services.placement_delivery import approved_active_filter
    from app.services import placement_engine as engine
    items = list(db.scalars(select(PlacementItem).where(PlacementItem.language_code == language_code,
        *approved_active_filter(), PlacementItem.cefr_level.in_(engine.TESTABLE_LEVELS),
        or_(and_(PlacementItem.skill.in_(engine.OBJECTIVE_SKILLS), PlacementItem.item_type.in_([
            "multiple_choice", "fill_blank", "reading_comprehension", "listening_comprehension"])),
            and_(PlacementItem.skill == "writing", PlacementItem.item_type == "short_writing"),
            and_(PlacementItem.skill == "speaking", PlacementItem.item_type == "speaking_prompt")))))
    history = exposure_history(db, user_id, language_code, test_id)
    matrix = {}
    groups = {"fresh": set(), "seen": set(), "revealed": set()}
    for item in items:
        cell = matrix.setdefault(item.skill, {}).setdefault(item.cefr_level, {"fresh": 0, "seen": 0, "revealed": 0})
        meta = exposure_metadata(item, history)
        status = "fresh" if not meta["reused"] else "revealed" if meta["feedback_revealed"] else "seen"
        cell[status] += 1
        keys = semantic_keys(item)
        group = keys.get("family") or keys.get("passage") or keys.get("audio") or keys.get("prompt") or keys["exact"]
        groups[status].add((item.skill, group))
    return {"by_skill_cefr": matrix, "fresh_items": len(fresh_pool(items, history)),
        "seen_items": len(items) - len(fresh_pool(items, history)), "independent_groups": {k: len(v) for k, v in groups.items()}, "policy_version": POLICY}


def archive_legacy_history(db, user_id):
    """Preserve known legacy exposures before a destructive pedagogical reset."""
    tests = list(db.scalars(select(PlacementTest).where(PlacementTest.user_id == user_id)))
    for test in tests:
        deliveries = list(db.scalars(select(PlacementItemDelivery).where(PlacementItemDelivery.test_id == test.id)))
        answered = {a.item_id: a for a in db.scalars(select(PlacementTestAnswer).where(PlacementTestAnswer.test_id == test.id))}
        for delivery in deliveries:
            item = db.get(PlacementItem, delivery.item_id)
            if item:
                origin = f"delivery:{delivery.id}"
                existing = db.scalar(select(PlacementItemExposure).where(PlacementItemExposure.user_id == user_id, PlacementItemExposure.origin_key == origin))
                if existing is None:
                    row = record_delivery(db, test, item, delivery)
                    row.snapshot_json = {**row.snapshot_json, "origin": "legacy_current_item"}
                    if item.id in answered:
                        row.answered_at = answered[item.id].created_at
                        if (answered[item.id].feedback_json or {}).get("feedback_revealed"):
                            row.feedback_revealed_at = answered[item.id].created_at
        delivered_ids = {d.item_id for d in deliveries}
        for item_id, answer in answered.items():
            if item_id in delivered_ids:
                continue
            origin = f"answer:{answer.id}"
            if db.scalar(select(PlacementItemExposure.id).where(PlacementItemExposure.user_id == user_id, PlacementItemExposure.origin_key == origin)):
                continue
            item = db.get(PlacementItem, item_id)
            if item:
                db.add(PlacementItemExposure(user_id=user_id, language_code=test.language_code, origin_key=origin,
                    source_test_id=test.id, source_item_id=item.id, keys_json=semantic_keys(item),
                    snapshot_json={"origin": "legacy_current_item", "key_version": POLICY},
                    seen_at=answer.created_at, answered_at=answer.created_at,
                    feedback_revealed_at=answer.created_at if (answer.feedback_json or {}).get("feedback_revealed") else None))
        db.flush()


def mark_feedback_revealed(db, test, item):
    """For an explicit review flow; assessment submit never calls this."""
    delivery = db.scalar(select(PlacementItemDelivery).where(PlacementItemDelivery.test_id == test.id,
        PlacementItemDelivery.item_id == item.id))
    if delivery is None:
        raise ValueError("Cannot reveal an item that was not delivered")
    row = record_delivery(db, test, item, delivery)
    if row.feedback_revealed_at is None:
        row.feedback_revealed_at = datetime.now(timezone.utc)


def rotation_metadata(db, user_id, language_code):
    """Validate operational forms before choosing one; no equivalence claim."""
    from app.services import placement_engine as engine
    from app.services.placement_delivery import approved_active_filter
    rows = list(db.scalars(select(PlacementItem).where(PlacementItem.language_code == language_code,
        *approved_active_filter(), PlacementItem.skill.in_(engine.OBJECTIVE_SKILLS),
        PlacementItem.cefr_level.in_(engine.TESTABLE_LEVELS),
        PlacementItem.item_type.in_(["multiple_choice", "fill_blank", "reading_comprehension", "listening_comprehension"]))))
    forms = {}
    for row in rows:
        form = (row.rubric_json or {}).get("form_id")
        if isinstance(form, str) and form:
            forms.setdefault(form, []).append(row)
    valid = {}
    for form, items in forms.items():
        deficits = []
        for skill in engine.OBJECTIVE_SKILLS:
            from app.services.placement_coverage import independent_item_groups
            groups = {}
            for group in independent_item_groups([item for item in items if item.skill == skill]):
                item = group[0]
                groups.setdefault(item.cefr_level, []).append(item)
            if sum(map(len, groups.values())) < engine.MIN_ITEMS_PER_SKILL or not any(len(g) >= engine.MIN_ITEMS_AT_DECIDING_BAND for g in groups.values()):
                deficits.append(skill)
        if not deficits:
            valid[form] = items
    history = exposure_history(db, user_id, language_code)
    selected = min(valid, key=lambda name: (-len(fresh_pool(valid[name], history)), name)) if valid else None
    return {"version": "operational-rotation-v1", "selected_form": selected,
            "valid_forms": sorted(valid), "unusable_forms": sorted(set(forms) - set(valid)), "psychometric_equivalence": False}


def adjust_result(result, answers):
    """Raw performance and fresh, independent support are separate facts."""
    for skill, data in result["skills"].items():
        rows = [a for a in answers if a.skill == skill and (a.feedback_json or {}).get("status") != "skipped"]
        fresh = [a for a in rows if not (a.feedback_json or {}).get("exposure", {}).get("reused", False)]
        reused = len(rows) - len(fresh)
        counts = data["evidence_counts"]
        from collections import Counter
        counts["by_cefr"] = dict(Counter(a.cefr_level for a in rows if a.normalized_score is not None))
        counts.update(answered=len(rows), fresh=len(fresh), reused=reused, excluded=len(rows) - counts.get("valid", 0),
            independent=counts.get("valid", 0))
        if rows and reused:
            scores = [a.normalized_score for a in rows if a.normalized_score is not None]
            data["score"] = round(sum(scores), 3) if scores else None
            data["max_score"] = float(len(scores)) if scores else None
            if not fresh:
                data.update(status="insufficient_evidence", estimated_level=None, eligible_for_overall=False)
        data["exposure_adjusted_evidence_support"] = {"status": "sufficient" if data["eligible_for_overall"] else "insufficient",
            "reused_excluded": reused, "policy_version": POLICY}
    result["exposure_policy_version"] = POLICY
    result["exposure_policy"] = dict(EXPOSURE_POLICY)
    result["assessment_coverage"]["reused_evidence"] = sum(d["evidence_counts"]["reused"] for d in result["skills"].values())
