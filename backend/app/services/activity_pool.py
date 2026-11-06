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

from app.core.errors import APIError
from app.core.teaching import ActivityType
from app.services.language_detection import target_field_status
from app.services.language_policy import ensure_stored_content_language, language_policy
from app.services.learner_language_contract import deliverable, interaction_family, language_safety
from app.services.question_identity import question_fingerprint, normalize_question_text

logger = logging.getLogger(__name__)

_LOG_OMIT = {
    "accepted_variants",
    "answer",
    "audio_text",
    "authorization",
    "canonical_answer",
    "cookie",
    "cookies",
    "correct_explanation",
    "email",
    "examples",
    "explanation",
    "models",
    "option_rationales",
    "options",
    "password",
    "prompt",
    "prompt_native",
    "prompt_pt",
    "prompt_target",
    "rationale",
    "reply",
    "reply_translation",
    "scenario_native",
    "scenario_target",
    "secret",
    "student_response",
    "text",
    "token",
}


def _omit_private(value):
    if isinstance(value, dict):
        return {
            key: _omit_private(item)
            for key, item in value.items()
            if key not in _LOG_OMIT
        }
    if isinstance(value, list):
        return [_omit_private(item) for item in value]
    return value


def _declared(*values):
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
        if value not in (None, "", [], {}):
            return value
    return None


def activity_diagnostic(activity: dict | None) -> dict:
    """Identidade de diagnóstico. Não inclui enunciado, resposta nem texto privado."""
    empty = {
        "activity_id": None,
        "legacy_id": None,
        "learning_objective_id": None,
        "type": None,
        "interaction_family": None,
        "content_source_id": None,
        "content_unit_id": None,
        "source": "unknown",
        "provider": None,
        "model": None,
        "content_version": None,
        "content_version_status": "unknown",
        "target_language": None,
        "native_language": None,
        "cefr_level": None,
        "quality_status": None,
    }
    if not isinstance(activity, dict):
        return empty
    provenance = activity.get("provenance") if isinstance(activity.get("provenance"), dict) else {}
    version = _declared(
        activity.get("content_version"),
        provenance.get("content_version"),
        provenance.get("version"),
    )
    source = _declared(provenance.get("source"), activity.get("content_source"), activity.get("source"))
    row_id = activity.get("id")
    return {
        "activity_id": activity_id(activity),
        "legacy_id": str(row_id) if row_id else None,
        "learning_objective_id": activity.get("learning_objective_id"),
        "type": activity.get("type"),
        "interaction_family": activity.get("interaction_family") or interaction_family(activity.get("type")),
        "content_source_id": _declared(
            activity.get("content_source_id"),
            provenance.get("content_source_id"),
            provenance.get("source_id"),
        ),
        "content_unit_id": _declared(activity.get("content_unit_id"), provenance.get("content_unit_id")),
        "source": source if source else "unknown",
        "provider": _declared(activity.get("provider"), provenance.get("provider")),
        "model": _declared(activity.get("model"), provenance.get("model")),
        "content_version": version,
        "content_version_status": "declared" if version else "unknown",
        "target_language": activity.get("target_language"),
        "native_language": activity.get("native_language"),
        "cefr_level": activity.get("cefr_level"),
        "quality_status": activity.get("quality_status"),
    }


def log_selection(trace: dict) -> None:
    logger.info(
        "activity_selection %s",
        json.dumps(_omit_private(trace), ensure_ascii=False, sort_keys=True, default=str),
    )


def public_selection_trace(trace: dict | None) -> dict | None:
    if not isinstance(trace, dict):
        return None
    return _omit_private(trace)


def stamp_selection_trace(
    trace: dict,
    *,
    session_id: str | None,
    attempt_id: str | None = None,
    retry: bool | None = None,
) -> dict:
    stamped = json.loads(json.dumps(_omit_private(trace), ensure_ascii=False, default=str))
    stamped["session_id"] = session_id
    if attempt_id is not None:
        stamped["attempt_id"] = attempt_id
    if retry is not None:
        stamped["retry"] = retry
    def _stamp_row(row: dict) -> None:
        row["session_id"] = session_id
        if attempt_id is not None:
            row["attempt_id"] = attempt_id
        if retry is not None:
            row["retry"] = retry

    for key in ("activities", "delivered"):
        rows = stamped.get(key)
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    _stamp_row(row)
        elif isinstance(rows, dict):
            _stamp_row(rows)
    chosen = stamped.get("chosen")
    if isinstance(chosen, dict):
        _stamp_row(chosen)
    return stamped


def exclusion_row(candidate, code: str) -> dict:
    if not isinstance(candidate, dict):
        return {"activity_id": None, "legacy_id": None, "code": code}
    diagnostic = activity_diagnostic(candidate)
    return {"activity_id": diagnostic["activity_id"], "legacy_id": diagnostic["legacy_id"], "code": code}


def delivery_record(
    activity: dict | None,
    *,
    reason: str,
    retry: bool = False,
    session_id: str | None = None,
    attempt_id: str | None = None,
) -> dict | None:
    if not isinstance(activity, dict):
        return None
    diagnostic = activity_diagnostic(activity)
    return {
        **diagnostic,
        "activity_type": diagnostic.get("type"),
        "selection_reason": reason,
        "retry": retry,
        "session_id": session_id,
        "attempt_id": attempt_id,
    }


def exhaustion_record(reason: str, rules: list[str], **extra) -> dict:
    return {
        "reason": reason,
        "aggregate_reason": reason,
        "contributing_rules": list(rules),
        **extra,
    }


def _rule_order(rows: list[dict]) -> list[str]:
    rules = []
    for row in rows:
        code = row.get("code")
        if code and code not in rules:
            rules.append(code)
    return rules


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


def _model_pattern_key(activity: dict) -> str | None:
    """Use explicit metadata or a complete model actually present in a snapshot."""
    if activity.get("pattern_key"):
        return str(activity["pattern_key"])
    answer = activity.get("canonical_answer") or activity.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return None
    prompt = str(activity.get("prompt") or activity.get("prompt_pt") or "")
    model = None
    if activity.get("type") == "fill_gap" and prompt.count("___") == 1:
        # A single explicit gap and its answer define a complete model.
        model = prompt.replace("___", answer)
    elif activity.get("type") == "word_order" and activity.get("tokens"):
        model = answer
    elif activity.get("type") == "multiple_choice" and normalize_question_text(prompt) == (
        "qual frase corresponde ao padrão trabalhado"
    ):
        model = answer
    if model is None:
        return None
    return hashlib.sha256(normalize_question_text(model).encode("utf-8")).hexdigest()


def family_key(activity: dict) -> str:
    """A word, an explicit model, or a contextual question; never an answer alone."""
    vocabulary_item_id = activity.get("vocabulary_item_id")
    if vocabulary_item_id:
        return f"vocab:{vocabulary_item_id}"
    scope = {key: activity.get(key) for key in (
        "learning_objective_id", "target_language", "native_language", "cefr_level",
    )}
    if not scope["learning_objective_id"]:
        scope["content_unit_id"] = activity.get("content_unit_id")
    pattern = _model_pattern_key(activity)
    if pattern:
        scope["model"] = str(pattern)
    else:
        parts = question_fingerprint(activity).split("|", 2)
        if len(parts) != 3 or not parts[0] or not parts[1]:
            return f"id:{activity_id(activity)}"
        scope["question"] = parts[:2]
    digest = hashlib.sha256(json.dumps(scope, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return f"pattern:v2:{digest}"


def retire_family(payload: dict, activity: dict | None) -> str | None:
    if not isinstance(activity, dict):
        return None
    key = family_key(activity)
    retired = set(payload.get("retired_families") or [])
    retired.add(key)
    payload["retired_families"] = sorted(retired)
    return key


def family_retired(activity: dict, payload: dict | None) -> bool:
    if not isinstance(activity, dict):
        return False
    payload = payload or {}
    retired = set(payload.get("retired_families") or [])
    key = family_key(activity)
    if key in retired:
        return True
    # Old broad keys are meaningful only together with the original snapshot.
    # Reinterpret in memory; do not rewrite historical payloads on resume.
    for entry in (payload.get("activity_exposures") or {}).values():
        stored = entry.get("activity") if isinstance(entry, dict) else None
        if not isinstance(stored, dict):
            continue
        answer = stored.get("canonical_answer")
        if answer is None:
            answer = stored.get("answer")
        legacy = f"pattern:{normalize_question_text(answer)}"
        if legacy in retired and family_key(stored) == key:
            return True
    return False


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
        "fingerprint": fingerprint(activity),
        "family_key": family_key(activity),
        "activity": dict(activity),
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
            exposures.setdefault(identity, {
                "at": None,
                "fingerprint": fingerprint(activity),
                "family_key": family_key(activity),
                "activity": dict(activity),
            })
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


def _history_instant(raw: str) -> datetime:
    date = datetime.fromisoformat(raw)
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    return date


def recently_exposed(
    activity: dict,
    history: dict | None,
    *,
    now: datetime | None = None,
    cooldown_days: int = 7,
    allow_deferred_family: bool = False,
) -> bool:
    """Atividade ou família vista na janela recente fica fora da seleção.

    Família adiada pode voltar numa sessão futura, em outra modalidade: a
    atividade exata continua bloqueada.
    """
    if not history:
        return False
    current = now or datetime.now(timezone.utc)
    if freshness_rank(activity, history, now=current, cooldown_days=cooldown_days) >= 2:
        return True
    if allow_deferred_family:
        return False
    raw = history.get(family_key(activity))
    if not raw:
        return False
    return _history_instant(raw) > current - timedelta(days=cooldown_days)


def freshness_rank(activity: dict, history: dict, *, now: datetime | None = None, cooldown_days: int = 7) -> int:
    raw = history.get(activity_id(activity)) or history.get(fingerprint(activity))
    if not raw:
        return 0
    date = datetime.fromisoformat(raw)
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    return 2 if date > (now or datetime.now(timezone.utc)) - timedelta(days=cooldown_days) else 1


def _select_exclusion(candidate: dict, *, payload: dict, history: dict, objective_id: str | None,
                      target_language: str | None, native_language: str | None, level: str | None,
                      now: datetime, cooldown_days: int) -> tuple[str, str] | None:
    """Primeira regra que já excluía o candidato. O balde agregado permanece o antigo."""
    safety = language_safety(candidate, target_language, native_language)
    if safety == "language_invalid":
        return "language", "language"
    if safety in {"review_required", "rejected", "draft", "generated"}:
        return "quality", "quality"
    if is_seen(candidate, payload):
        return "seen", "seen"
    if family_retired(candidate, payload):
        return "family", "seen"
    if recently_exposed(candidate, history, now=now, cooldown_days=cooldown_days):
        if freshness_rank(candidate, history, now=now, cooldown_days=cooldown_days) >= 2:
            return "cooldown", "seen"
        return "family", "seen"
    if (objective_id and candidate.get("learning_objective_id") != objective_id) or any(
        expected is not None and candidate.get(key) != expected
        for key, expected in (("target_language", target_language), ("native_language", native_language), ("cefr_level", level))
    ) or candidate.get("quality_status", "approved") != "approved":
        return "metadata", "metadata"
    return None


def select_activity(candidates: list[dict], *, objective_id: str | None = None,
                    session_payload: dict | None = None, exposure_history: dict | None = None,
                    target_language: str | None = None, native_language: str | None = None,
                    level: str | None = None, previous: dict | None = None,
                    now: datetime | None = None, cooldown_days: int = 7,
                    trace: dict | None = None) -> dict | None:
    payload, history = session_payload or {}, exposure_history or {}
    current = now or datetime.now(timezone.utc)
    excluded = {"seen": 0, "metadata": 0, "language": 0, "quality": 0}
    rejected = []
    eligible = []
    for position, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            rejected.append(exclusion_row(candidate, "metadata"))
            excluded["metadata"] += 1
            continue
        found = _select_exclusion(
            candidate, payload=payload, history=history, objective_id=objective_id,
            target_language=target_language, native_language=native_language, level=level,
            now=current, cooldown_days=cooldown_days,
        )
        if found is not None:
            code, bucket = found
            rejected.append(exclusion_row(candidate, code))
            excluded[bucket] += 1
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
            diversity += int(interaction_family(candidate.get("type")) == interaction_family(previous.get("type")))
            if isinstance(candidate.get("difficulty"), (int, float)) and isinstance(previous.get("difficulty"), (int, float)):
                difficulty_distance = abs(candidate["difficulty"] - previous["difficulty"])
        eligible.append(((freshness, diversity, difficulty_distance, date.isoformat() if date else "", position), candidate))
    chosen = min(eligible, key=lambda pair: pair[0])[1] if eligible else None
    reason = "freshness_then_diversity" if chosen else "pool_exhausted"
    rules = _rule_order(rejected)
    decision = {
        "candidate_count": len(candidates),
        "exclusions": excluded,
        "excluded_candidates": rejected,
        "rejected_candidates": rejected,
        "seen_count": len(payload.get("seen_activity_ids") or []),
        "chosen_activity": activity_id(chosen) if chosen else None,
        "chosen": activity_diagnostic(chosen) if chosen else None,
        "delivered": delivery_record(chosen, reason=reason) if chosen else None,
        "reason": reason,
        "fallback_used": chosen is None,
        "exhaustion": None if chosen else exhaustion_record(reason, rules or ["no_candidates"]),
        "learning_objective_id": objective_id,
        "target_language": target_language,
        "native_language": native_language,
        "cefr_level": level,
        "retry": False,
        "session_id": None,
        "attempt_id": None,
    }
    if trace is not None:
        trace.update(decision)
    log_selection(decision)
    return chosen


def interaction_retry_rejection(failed: dict, candidate, payload: dict, objective_id: str | None) -> str | None:
    """Primeiro motivo do `continue` já existente. Não muda a ordem nem a escolha."""
    if not isinstance(candidate, dict):
        return "metadata"
    if objective_id and candidate.get("learning_objective_id") != objective_id:
        return "metadata"
    if activity_id(candidate) == activity_id(failed):
        return "same_activity"
    family = interaction_family(candidate.get("type"))
    if family == interaction_family(failed.get("type")) or family == "unknown":
        return "family"
    failed_answer = normalize_question_text(str(failed.get("canonical_answer") or failed.get("answer") or ""))
    candidate_answer = normalize_question_text(str(candidate.get("canonical_answer") or candidate.get("answer") or ""))
    if failed_answer and candidate_answer == failed_answer:
        return "duplicate"
    if family_key(candidate) == family_key(failed) or family_retired(candidate, payload):
        return "family"
    if is_seen(candidate, payload):
        return "seen"
    if not deliverable(candidate, candidate.get("target_language"), candidate.get("native_language")):
        safety = language_safety(candidate, candidate.get("target_language"), candidate.get("native_language"))
        return "language" if safety == "language_invalid" else "quality"
    if candidate.get("quality_status") not in {None, "approved"}:
        return "quality"
    if failed.get("target_language") and candidate.get("target_language") and candidate.get("target_language") != failed.get("target_language"):
        return "language"
    if failed.get("cefr_level") and candidate.get("cefr_level") and candidate.get("cefr_level") != failed.get("cefr_level"):
        return "cefr"
    return None


_RETRY_BUCKET = {
    "seen": "seen",
    "same_activity": "seen",
    "cooldown": "cooldown",
    "family": "family",
    "language": "language",
    "quality": "quality",
    "metadata": "metadata",
    "objective": "metadata",
    "cefr": "metadata",
    "duplicate": "duplicate",
}


def choose_interaction_retry(failed: dict, candidates: list[dict], payload: dict | None = None, *,
                             objective_id: str | None = None, trace: dict | None = None) -> dict | None:
    """Outra interação do mesmo objetivo, se houver item seguro. Não fabrica exercício."""
    payload = payload or {}
    rejected = []
    counts = {"seen": 0, "cooldown": 0, "family": 0, "language": 0, "quality": 0, "metadata": 0, "duplicate": 0}
    chosen = None
    for candidate in candidates:
        code = interaction_retry_rejection(failed, candidate, payload, objective_id)
        if code is not None:
            rejected.append({
                "activity_id": activity_id(candidate) if isinstance(candidate, dict) else None,
                "legacy_id": activity_diagnostic(candidate)["legacy_id"] if isinstance(candidate, dict) else None,
                "code": code,
            })
            counts[_RETRY_BUCKET[code]] += 1
            continue
        chosen = candidate
        break
    reason = "interaction_change_retry" if chosen else "pool_exhausted"
    rules = _rule_order(rejected)
    decision = {
        "candidate_count": len(candidates),
        "exclusions": counts,
        "excluded_candidates": rejected,
        "rejected_candidates": rejected,
        "chosen_activity": activity_id(chosen) if chosen else None,
        "chosen": activity_diagnostic(chosen) if chosen else None,
        "delivered": delivery_record(chosen, reason=reason, retry=True) if chosen else None,
        "reason": reason,
        "fallback_used": chosen is None,
        "exhaustion": None if chosen else exhaustion_record(reason, rules or ["no_candidates"]),
        "learning_objective_id": objective_id,
        "retry": True,
    }
    if trace is not None:
        trace.update(decision)
    log_selection(decision)
    return chosen


def validate_batch(existing: list[dict], batch: list[dict], *, batch_size: int = 50,
                   required_quality: str = "approved") -> dict:
    if batch_size < 1 or len(batch) > batch_size:
        raise ValueError("Batch exceeds configured size")
    accepted, rejected = [], []
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
        if required_quality == "approved":
            if candidate.get("quality_status") != "approved" or not provenance.get("source") or not provenance.get("reviewer"):
                reason = "editorial_approval_required"
        elif candidate.get("quality_status") not in {"generated", "review_required"}:
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
        if candidate.get("type") == "dictation":
            if candidate.get("show_text") is not False or not candidate.get("audio_text"):
                reason = "dictation_reveals_transcript"
        if candidate.get("type") == "word_order":
            tokens = candidate.get("tokens") or []
            if len(tokens) < 2 or normalize_question_text(" ".join(str(token) for token in tokens)) != normalize_question_text(answer or ""):
                reason = "invalid_tokens"
        candidate = dict(candidate)
        candidate["interaction_family"] = candidate.get("interaction_family") or interaction_family(candidate.get("type"))
        detected = target_field_status(candidate, candidate.get("target_language"))
        if detected == "language_invalid" or language_safety(
            candidate, candidate.get("target_language"), candidate.get("native_language"),
        ) == "language_invalid":
            reason = "language"
        elif detected == "review_required":
            reason = "review_required"
        if any(activity_id(candidate) == activity_id(other) or same_stimulus(candidate, other) for other in existing + accepted):
            reason = "duplicate"
        if reason:
            rejected.append({"activity_id": activity_id(candidate), "reason": reason})
        else:
            normalized = dict(candidate)
            if normalized.get("quality_status") == "generated":
                normalized["quality_status"] = "review_required"
            if required_quality == "approved" and normalized.get("quality_status") != "approved":
                rejected.append({"activity_id": activity_id(candidate), "reason": "editorial_approval_required"})
                continue
            if answer:
                normalized["canonical_answer"] = answer
                normalized.setdefault("accepted_variants", [answer])
            accepted.append(normalized)
    return {"accepted": accepted, "rejected": rejected}


def generate_incremental_batches(db, *, objective_id: str, generate_batch, batch_count: int,
                                 batch_size: int = 50, required_quality: str = "approved") -> list[dict]:
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
        results.append(append_objective_batch(
            db, objective_id=objective_id, batch=batch, batch_size=batch_size, required_quality=required_quality,
        ))
    return results


def append_objective_batch(db, *, objective_id: str, batch: list[dict], batch_size: int = 50,
                           required_quality: str = "approved") -> dict:
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
    result = validate_batch(existing, batch, batch_size=batch_size, required_quality=required_quality)
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
            stored = entry.get("activity") if isinstance(entry, dict) else None
            family = entry.get("family_key") if isinstance(entry, dict) else None
            if isinstance(stored, dict):
                family = family_key(stored)
            elif isinstance(family, str) and family.startswith("pattern:") and not family.startswith("pattern:v2:"):
                family = None  # An answer-only key cannot prove a shared model.
            for key in (identity, entry.get("fingerprint") if isinstance(entry, dict) else None, family):
                if key and isinstance(entry, dict) and entry.get("at") and entry["at"] > history.get(key, ""):
                    history[key] = entry["at"]
    return history
