"""Small, deterministic candidate pool and exposure policy.

Pools live in LearningObjective.pedagogy_json; per-session exposure lives in
TeachingFlowSession.payload_json. No inferred objective IDs or provider choice.
Editorial approval is required: mechanical checks cannot certify CEFR/semantics.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
import hashlib
import json
import logging

from app.services.question_identity import question_fingerprint, normalize_question_text

logger = logging.getLogger(__name__)


def fingerprint(activity: dict) -> str:
    # Expository activities often have the same instruction but different input.
    stimulus = {key: activity.get(key) for key in ("models", "examples", "text", "audio_text", "vocabulary_item_id") if activity.get(key)}
    base = question_fingerprint(activity)
    if activity.get("type") in {"presentation", "listen", "matching", "recognition", "conversation_prompt"} and not activity.get("canonical_answer") and not activity.get("answer"):
        base = str(activity.get("type")) + "|" + base
    return base + ("|" + json.dumps(stimulus, ensure_ascii=False, sort_keys=True) if stimulus else "")


def activity_id(activity: dict) -> str:
    explicit = activity.get("activity_id") or activity.get("id")
    return str(explicit) if explicit else hashlib.sha256(
        (str(activity.get("type") or "") + "|" + fingerprint(activity)).encode("utf-8")
    ).hexdigest()


def same_stimulus(left: dict, right: dict) -> bool:
    if fingerprint(left) == fingerprint(right):
        return True
    # Conservative near-duplicate check: same answer/options, long almost equal
    # prompt. Short prompts and different modalities aren't collapsed by guesses.
    if left.get("type") != right.get("type"):
        return False
    lf, rf = question_fingerprint(left).split("|", 1), question_fingerprint(right).split("|", 1)
    if len(lf) != 2 or len(rf) != 2 or lf[1] != rf[1]:
        return False
    if any(left.get(key) != right.get(key) for key in ("models", "examples", "vocabulary_item_id")):
        return False
    lt, rt = lf[0].split(), rf[0].split()
    single_context_swap = len(lt) == len(rt) and len(lt) >= 4 and lt[:2] == rt[:2] and sum(a != b for a, b in zip(lt, rt)) <= 1
    return single_context_swap or (min(len(lt), len(rt)) >= 6 and SequenceMatcher(None, lf[0], rf[0]).ratio() >= .82)


def record_exposure(payload: dict, activity: dict | None, *, now: datetime | None = None) -> None:
    if not isinstance(activity, dict) or activity.get("retry_safe") is False:
        return
    identity = activity_id(activity)
    payload["seen_activity_ids"] = sorted(set(payload.get("seen_activity_ids") or []) | {identity})
    payload["seen_question_fingerprints"] = sorted(set(payload.get("seen_question_fingerprints") or []) | {question_fingerprint(activity)})
    exposures = dict(payload.get("activity_exposures") or {})
    # Refresh/resume does not restart cooldown or count a second presentation.
    exposures.setdefault(identity, {
        "at": (now or datetime.now(timezone.utc)).isoformat(),
        "fingerprint": fingerprint(activity), "activity": dict(activity),
    })
    payload["activity_exposures"] = exposures


def restore_known_exposures(payload: dict) -> None:
    """Recover only submitted/completed legacy slots; never invent a timestamp."""
    activities = payload.get("activities") or []
    known = set(payload.get("submitted_indices") or []) | set(payload.get("completed_indices") or [])
    exposures = dict(payload.get("activity_exposures") or {})
    ids = set(payload.get("seen_activity_ids") or [])
    for index in known:
        if isinstance(index, int) and 0 <= index < len(activities):
            activity = activities[index]
            identity = activity_id(activity)
            ids.add(identity)
            exposures.setdefault(identity, {"at": None, "fingerprint": fingerprint(activity), "activity": dict(activity)})
    payload["seen_activity_ids"] = sorted(ids)
    payload["activity_exposures"] = exposures


def is_seen(activity: dict, payload: dict) -> bool:
    if activity_id(activity) in set(payload.get("seen_activity_ids") or []):
        return True
    # Old retry fingerprints remain authoritative even after the new ledger
    # gains its first entry. Expository input needs the fuller stimulus identity.
    if not any(activity.get(key) for key in ("models", "examples", "text", "audio_text", "vocabulary_item_id")) and question_fingerprint(activity) in set(payload.get("seen_question_fingerprints") or []):
        return True
    exposures = payload.get("activity_exposures") or {}
    if exposures:
        return any(same_stimulus(activity, entry.get("activity") or {}) for entry in exposures.values())
    # Compatibility with pre-ledger flows: only known fingerprints are used.
    return question_fingerprint(activity) in set(payload.get("seen_question_fingerprints") or [])


def freshness_rank(activity: dict, history: dict, *, now: datetime | None = None, cooldown_days: int = 7) -> int:
    raw = history.get(activity_id(activity)) or history.get(fingerprint(activity))
    if not raw:
        return 0
    date = datetime.fromisoformat(raw)
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    return 2 if date > (now or datetime.now(timezone.utc)) - timedelta(days=cooldown_days) else 1


def select_activity(candidates: list[dict], *, objective_id: str | None = None,
                    session_payload: dict | None = None, exposure_history: dict | None = None,
                    target_language: str | None = None, native_language: str | None = None,
                    level: str | None = None, previous: dict | None = None,
                    now: datetime | None = None, cooldown_days: int = 7,
                    trace: dict | None = None) -> dict | None:
    payload, history = session_payload or {}, exposure_history or {}
    current = now or datetime.now(timezone.utc)
    excluded = {"seen": 0, "metadata": 0}
    eligible = []
    for position, candidate in enumerate(candidates):
        if is_seen(candidate, payload):
            excluded["seen"] += 1
            continue
        if (objective_id and candidate.get("learning_objective_id") != objective_id) or any(
            expected is not None and candidate.get(key) != expected
            for key, expected in (("target_language", target_language), ("native_language", native_language), ("cefr_level", level))
        ) or candidate.get("quality_status", "approved") != "approved":
            excluded["metadata"] += 1
            continue
        identity = activity_id(candidate)
        raw = history.get(identity) or history.get(fingerprint(candidate))
        date = datetime.fromisoformat(raw) if raw else None
        if date and date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        freshness = freshness_rank(candidate, history, now=current, cooldown_days=cooldown_days)
        diversity = 0
        difficulty_distance = 0
        if previous:
            diversity = int(candidate.get("context") == previous.get("context")) + int(candidate.get("type") == previous.get("type"))
            if isinstance(candidate.get("difficulty"), (int, float)) and isinstance(previous.get("difficulty"), (int, float)):
                difficulty_distance = abs(candidate["difficulty"] - previous["difficulty"])
        eligible.append(((freshness, diversity, difficulty_distance, date.isoformat() if date else "", position), candidate))
    chosen = min(eligible, key=lambda pair: pair[0])[1] if eligible else None
    if trace is not None:
        trace.update(candidate_count=len(candidates), exclusions=excluded, seen_count=len(payload.get("seen_activity_ids") or []),
                     chosen_activity=activity_id(chosen) if chosen else None,
                     reason="freshness_then_diversity" if chosen else "pool_exhausted", fallback_used=chosen is None)
    return chosen


def validate_batch(existing: list[dict], batch: list[dict], *, batch_size: int = 50) -> dict:
    if batch_size < 1 or len(batch) > batch_size:
        raise ValueError("Batch exceeds configured size")
    accepted, rejected = [], []
    from app.services.language_policy import ensure_stored_content_language, language_policy
    from app.core.teaching import ActivityType
    from app.core.errors import APIError
    for candidate in batch:
        reason = None
        try:
            language_policy(candidate.get("target_language"), candidate.get("native_language"), candidate.get("cefr_level"))
            ensure_stored_content_language(candidate, candidate.get("native_language"), target_language=candidate.get("target_language"), lesson_status=candidate.get("quality_status"))
        except (ValueError, APIError):
            reason = "language"
        if not all(candidate.get(key) for key in ("learning_objective_id", "content_unit_id", "skill", "type", "prompt")):
            reason = "metadata"
        if candidate.get("type") not in set(ActivityType):
            reason = "unsupported_type"
        if candidate.get("vocabulary_item_id") or candidate.get("user_language_id"):
            reason = "learner_specific_reference"
        provenance = candidate.get("provenance") or {}
        if candidate.get("quality_status") != "approved" or not provenance.get("source") or not provenance.get("reviewer"):
            reason = "editorial_approval_required"
        answer = candidate.get("canonical_answer") or candidate.get("answer")
        options = candidate.get("options") or []
        if candidate.get("type") == "multiple_choice" and not options:
            reason = "missing_options"
        if options:
            texts = [normalize_question_text(o.get("text") if isinstance(o, dict) else o) for o in options]
            if len(texts) < 2 or len(set(texts)) != len(texts) or texts.count(normalize_question_text(answer)) != 1:
                reason = "ambiguous_answer"
            variants = {normalize_question_text(value) for value in candidate.get("accepted_variants") or []}
            if any(text != normalize_question_text(answer) and text in variants for text in texts):
                reason = "ambiguous_answer"
        elif not answer and candidate.get("type") not in {"presentation", "listen", "matching", "conversation_prompt"}:
            reason = "missing_answer"
        if candidate.get("type") == "word_order":
            tokens = candidate.get("tokens") or []
            if len(tokens) < 2 or normalize_question_text(" ".join(tokens)) != normalize_question_text(answer):
                reason = "invalid_tokens"
        if any(activity_id(candidate) == activity_id(other) or same_stimulus(candidate, other) for other in existing + accepted):
            reason = "duplicate"
        if reason:
            rejected.append({"activity_id": activity_id(candidate), "reason": reason})
        else:
            normalized = dict(candidate)
            if answer:
                normalized["canonical_answer"] = answer
                normalized.setdefault("accepted_variants", [answer])
            accepted.append(normalized)
    return {"accepted": accepted, "rejected": rejected}


def generate_incremental_batches(db, *, objective_id: str, generate_batch, batch_count: int,
                                 batch_size: int = 50) -> list[dict]:
    """Provider-neutral editorial pipeline, one batch at a time.

    Caller supplies generation/review and owns transaction boundaries. Existing
    candidates are passed to prevent recycling between calls. No implicit model
    selection and no target=200 fill loop. Rejected batches remain unavailable.
    """
    from app.models import LearningObjective
    if batch_count < 1 or batch_size < 1:
        raise ValueError("Positive batch count and size required")
    results = []
    for _ in range(batch_count):
        objective = db.get(LearningObjective, objective_id)
        if objective is None:
            raise ValueError("Unknown learning objective")
        existing = list((objective.pedagogy_json or {}).get("activity_pool") or [])
        batch = generate_batch(objective=objective, existing=existing, batch_size=batch_size)
        results.append(append_objective_batch(db, objective_id=objective_id, batch=batch, batch_size=batch_size))
    return results


def append_objective_batch(db, *, objective_id: str, batch: list[dict], batch_size: int = 50) -> dict:
    """Internal editorial entrypoint. Locks and appends one validated batch;
    never commits, calls an LLM, fills a quota or rewrites legacy metadata.
    """
    from sqlalchemy import select
    from app.models import LearningObjective, Language, ContentUnit, ContentSource
    objective = db.scalar(select(LearningObjective).where(LearningObjective.id == objective_id).with_for_update().execution_options(populate_existing=True))
    if objective is None or not objective.is_active:
        raise ValueError("Unknown active learning objective")
    language = db.get(Language, objective.language_id)
    if any(item.get("learning_objective_id") != objective.id or item.get("target_language") != language.code
           or item.get("cefr_level") != objective.level or item.get("skill") != objective.skill_focus for item in batch):
        raise ValueError("Batch does not match objective/language/CEFR/skill")
    for item in batch:
        unit = db.get(ContentUnit, item.get("content_unit_id"))
        source = db.get(ContentSource, unit.source_id) if unit else None
        if unit is None or not unit.is_active or unit.validation_status != "APPROVED" or unit.language_id != objective.language_id or unit.cefr_level != objective.level or source is None or source.review_status != "APPROVED":
            raise ValueError("Activity requires an approved compatible content unit/source")
    pedagogy = dict(objective.pedagogy_json or {})
    existing = list(pedagogy.get("activity_pool") or [])
    result = validate_batch(existing, batch, batch_size=batch_size)
    pedagogy["activity_pool"] = existing + result["accepted"]
    objective.pedagogy_json = pedagogy
    db.flush()
    return result


def objective_candidates(db, objective, *, native_language: str) -> list[dict]:
    """Delivery gate: stale/editorially invalid metadata is never relabeled."""
    from app.models import Language, ContentUnit, ContentSource
    target = db.get(Language, objective.language_id).code
    raw = [candidate for candidate in (objective.pedagogy_json or {}).get("activity_pool", [])
           if candidate.get("learning_objective_id") == objective.id and candidate.get("target_language") == target
           and candidate.get("native_language") == native_language and candidate.get("cefr_level") == objective.level
           and candidate.get("skill") == objective.skill_focus and not candidate.get("ai_required")]
    approved = validate_batch([], raw, batch_size=max(len(raw), 1))["accepted"]
    eligible = []
    for candidate in approved:
        unit = db.get(ContentUnit, candidate.get("content_unit_id"))
        source = db.get(ContentSource, unit.source_id) if unit else None
        if unit and unit.is_active and unit.validation_status == "APPROVED" and unit.language_id == objective.language_id and unit.cefr_level == objective.level and source and source.review_status == "APPROVED":
            eligible.append(candidate)
    return eligible


def exposure_history(db, user_language_id: str, *, exclude_session_id: str | None = None) -> dict:
    from sqlalchemy import select
    from app.models import TeachingFlowSession
    history = {}
    for session in db.scalars(select(TeachingFlowSession).where(TeachingFlowSession.user_language_id == user_language_id)):
        if session.id == exclude_session_id:
            continue
        for identity, entry in ((session.payload_json or {}).get("activity_exposures") or {}).items():
            for key in (identity, entry.get("fingerprint")):
                if key and entry.get("at") and entry["at"] > history.get(key, ""):
                    history[key] = entry["at"]
    return history
