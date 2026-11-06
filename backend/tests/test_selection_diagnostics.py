"""Rastreio da seleção: cada exclusão, a entrega e o esgotamento.

A atividade escolhida tem de ser a mesma de antes. O trace só acrescenta
identidade, proveniência declarada e o motivo de cada candidato.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from app.core.teaching import FlowPhase
from app.models import TeachingFlowSession
from app.services import activity_pool, lesson_attempts, session_engine, teaching_slice
from test_activity_pool import item


SECRET_PROMPT = "PROMPT_SHOULD_NOT_LEAK_9f3a"
SECRET_ANSWER = "ANSWER_SHOULD_NOT_LEAK_9f3a"
NOW = datetime(2026, 11, 6, tzinfo=timezone.utc)


def _codes(rows):
    return {row["activity_id"]: row["code"] for row in rows}


def test_select_activity_names_every_exclusion_and_keeps_the_choice(caplog):
    caplog.set_level(logging.INFO)
    seen = item("seen-one", prompt=SECRET_PROMPT, canonical_answer=SECRET_ANSWER)
    retired = item("retired-one", prompt="Quel est le train de ce soir ?")
    cooled = item("cooled-one", prompt="Gare proche")
    invalid = item(
        "lang-one",
        prompt="Choose the station",
        quality_status="language_invalid",
        target_language="fr",
    )
    draft = item(
        "draft-one",
        prompt="Choisissez.",
        quality_status="generated",
        target_language="fr",
        native_language="pt-BR",
        cefr_level="B1",
    )
    wrong_objective = item(
        "meta-one",
        prompt="L'idée est simple, pourtant elle change la discussion.",
        learning_objective_id="other",
        target_language="fr",
        native_language="pt-BR",
        cefr_level="B1",
    )
    first = item(
        "good-a",
        prompt="Quel train part à huit heures ?",
        canonical_answer="Le train de huit heures.",
        options=["Le train de huit heures.", "Le train de minuit."],
        target_language="fr",
        native_language="pt-BR",
        cefr_level="B1",
        provenance={"source": "editorial", "reviewer": "editor", "provider": "curated", "model": None},
        content_unit_id="unit-fr-b1",
    )
    second = item(
        "good-b",
        prompt="Quelle phrase marque une réserve ?",
        canonical_answer="Mais il coûte trop cher.",
        options=["Mais il coûte trop cher.", "Je m'appelle Ada."],
        target_language="fr",
        native_language="pt-BR",
        cefr_level="B1",
        content_source="curated_fr_b1_slice",
    )
    payload = {}
    activity_pool.record_exposure(payload, seen)
    payload["retired_families"] = [activity_pool.family_key(retired)]
    history = {activity_pool.activity_id(cooled): (NOW - timedelta(days=1)).isoformat()}
    trace = {}
    chosen = activity_pool.select_activity(
        [seen, retired, cooled, invalid, draft, wrong_objective, first, second],
        objective_id="objective-x",
        session_payload=payload,
        exposure_history=history,
        target_language="fr",
        native_language="pt-BR",
        level="B1",
        now=NOW,
        trace=trace,
    )
    assert chosen["activity_id"] == "good-a"
    assert trace["chosen_activity"] == "good-a"
    assert trace["reason"] == "freshness_then_diversity"
    assert trace["fallback_used"] is False
    assert trace["exclusions"] == {"seen": 3, "metadata": 1, "language": 1, "quality": 1}
    assert _codes(trace["excluded_candidates"]) == {
        "seen-one": "seen",
        "retired-one": "family",
        "cooled-one": "cooldown",
        "lang-one": "language",
        "draft-one": "quality",
        "meta-one": "metadata",
    }
    delivered = trace["delivered"]
    assert delivered["activity_id"] == "good-a"
    assert delivered["learning_objective_id"] == "objective-x"
    assert delivered["activity_type"] == "multiple_choice"
    assert delivered["interaction_family"] == "choice"
    assert delivered["source"] == "editorial"
    assert delivered["provider"] == "curated"
    assert delivered["model"] is None
    assert delivered["content_source_id"] is None
    assert delivered["content_unit_id"] == "unit-fr-b1"
    assert delivered["content_version"] is None
    assert delivered["content_version_status"] == "unknown"
    assert delivered["target_language"] == "fr"
    assert delivered["native_language"] == "pt-BR"
    assert delivered["cefr_level"] == "B1"
    assert delivered["selection_reason"] == "freshness_then_diversity"
    assert delivered["retry"] is False
    assert delivered["attempt_id"] is None
    blob = json.dumps(trace, ensure_ascii=False)
    assert SECRET_PROMPT not in blob
    assert SECRET_ANSWER not in blob
    assert SECRET_PROMPT not in caplog.text
    assert SECRET_ANSWER not in caplog.text
    assert "good-a" in caplog.text


def test_select_activity_exhaustion_lists_the_rules_that_removed_candidates():
    seen = item("only-seen")
    payload = {}
    activity_pool.record_exposure(payload, seen)
    trace = {}
    assert activity_pool.select_activity(
        [seen], objective_id="objective-x", session_payload=payload, trace=trace,
    ) is None
    assert trace["reason"] == "pool_exhausted"
    assert trace["fallback_used"] is True
    assert trace["delivered"] is None
    assert trace["exhaustion"]["reason"] == "pool_exhausted"
    assert trace["exhaustion"]["contributing_rules"] == ["seen"]
    assert trace["excluded_candidates"] == [{"activity_id": "only-seen", "legacy_id": None, "code": "seen"}]

    empty = {}
    assert activity_pool.select_activity([], trace=empty) is None
    assert empty["exhaustion"]["reason"] == "pool_exhausted"
    assert empty["exhaustion"]["contributing_rules"] == ["no_candidates"]
    assert empty["excluded_candidates"] == []


def test_declared_version_is_copied_and_missing_version_stays_unknown():
    versioned = item(
        "versioned",
        target_language="fr",
        native_language="pt-BR",
        cefr_level="B1",
        content_version="slice-2026-10",
        provenance={"source": "editorial", "reviewer": "editor", "version": "ignored-when-top-level-exists"},
    )
    trace = {}
    chosen = activity_pool.select_activity(
        [versioned], objective_id="objective-x", target_language="fr",
        native_language="pt-BR", level="B1", trace=trace,
    )
    assert chosen["activity_id"] == "versioned"
    assert trace["delivered"]["content_version"] == "slice-2026-10"
    assert trace["delivered"]["content_version_status"] == "declared"


def test_plan_session_records_duplicate_cooldown_and_does_not_change_the_plan():
    seen = item("seen-plan", target_language="fr", native_language="pt-BR", cefr_level="B1", prompt=SECRET_PROMPT)
    cooled = item("cooled-plan", target_language="fr", native_language="pt-BR", cefr_level="B1", prompt="Train nuit")
    retired = item("retired-plan", target_language="fr", native_language="pt-BR", cefr_level="B1", prompt="Famille retiree")
    invalid = item("lang-plan", target_language="fr", native_language="pt-BR", cefr_level="B1", quality_status="language_invalid")
    draft = item("draft-plan", target_language="fr", native_language="pt-BR", cefr_level="B1", quality_status="generated", prompt="Brouillon court")
    keep = item("keep", target_language="fr", native_language="pt-BR", cefr_level="B1", prompt="Quel quai")
    duplicate = item("keep", target_language="fr", native_language="pt-BR", cefr_level="B1", prompt="Quel quai")
    other = item("other", target_language="fr", native_language="pt-BR", cefr_level="B1", prompt="Votre avis")
    payload = {}
    activity_pool.record_exposure(payload, seen)
    payload["retired_families"] = [activity_pool.family_key(retired)]
    history = {activity_pool.activity_id(cooled): (NOW - timedelta(days=1)).isoformat()}

    def wrap(activity):
        return {
            "activity": activity,
            "area": "grammar",
            "modality": activity["type"],
            "phase_hint": "practicing",
            "priority": 1,
            "item_key": activity["activity_id"],
        }

    plan = session_engine.plan_session(
        [wrap(seen), wrap(cooled), wrap(retired), wrap(invalid), wrap(draft), wrap(keep), wrap(duplicate), wrap(other)],
        session_payload=payload,
        exposure_history=history,
    )
    assert [activity["activity_id"] for activity in plan["activities"]] == ["keep", "other"]
    trace = plan["selection_trace"]
    assert trace["excluded_seen"] == 2
    assert trace["excluded_family"] == 1
    assert trace["excluded_language"] == 1
    assert trace["excluded_quality"] == 1
    assert trace["excluded_duplicate"] == 1
    assert trace["reason"] == "freshness_budget_modality_interaction"
    assert _codes(trace["excluded_candidates"]) == {
        "seen-plan": "seen",
        "cooled-plan": "cooldown",
        "retired-plan": "family",
        "lang-plan": "language",
        "draft-plan": "quality",
        "keep": "duplicate",
    }
    delivered = {row["activity_id"]: row for row in trace["delivered"]}
    assert set(delivered) == {"keep", "other"}
    assert delivered["keep"]["target_language"] == "fr"
    assert delivered["keep"]["native_language"] == "pt-BR"
    assert delivered["keep"]["cefr_level"] == "B1"
    assert delivered["keep"]["content_version_status"] == "unknown"
    assert delivered["keep"]["source"] == "editorial"
    assert SECRET_PROMPT not in json.dumps(trace, ensure_ascii=False)

    exhausted = session_engine.plan_session([wrap(seen)], session_payload=payload, exposure_history={})
    exhaustion = exhausted["selection_trace"]["exhaustion"]
    assert exhausted["activities"] == []
    assert exhausted["selection_trace"]["fallback_used"] is True
    assert exhaustion["reason"] == "pool_exhausted"
    assert exhaustion["contributing_rules"] == ["seen"]

    empty = session_engine.plan_session([])
    assert empty["selection_trace"]["exhaustion"]["contributing_rules"] == ["no_candidates"]


def test_interaction_retry_records_each_rejection_and_keeps_the_first_eligible():
    failed = item(
        "failed",
        type="multiple_choice",
        prompt="Choisissez un nom.",
        canonical_answer="Ada",
        target_language="fr",
        native_language="pt-BR",
        cefr_level="B1",
    )
    orphan = item("orphan", learning_objective_id="obj-other", type="fill_gap", prompt="Je pense que cette idée est utile.")
    same_family = item("same-family", prompt="Choisissez une ville.")
    same_answer = item(
        "same-answer",
        type="fill_gap",
        prompt="Le visiteur s'appelle ___.",
        canonical_answer="Ada",
        options=["Ada", "Rome"],
    )
    seen_gap = item(
        "seen-gap",
        type="fill_gap",
        prompt="La gare ouvre à ___.",
        canonical_answer="huit heures",
        options=["huit heures", "minuit"],
    )
    other_language = item(
        "other-language",
        type="fill_gap",
        prompt="Leave now",
        canonical_answer="huit heures",
        options=["huit heures", "minuit"],
        target_language="en",
        native_language="pt-BR",
        cefr_level="B1",
    )
    draft = item(
        "draft-gap",
        type="fill_gap",
        prompt="Quai deux",
        canonical_answer="deux",
        options=["deux", "trois"],
        quality_status="generated",
        target_language="fr",
        native_language="pt-BR",
        cefr_level="B1",
    )
    winner = item(
        "winner",
        type="fill_gap",
        prompt="Je ne suis pas ___ avec cette idée.",
        canonical_answer="d'accord",
        options=["d'accord", "fatigué"],
        target_language="fr",
        native_language="pt-BR",
        cefr_level="B1",
        content_version="retry-v1",
    )
    later = item(
        "later",
        type="word_order",
        prompt="Remettez la phrase.",
        canonical_answer="Je suis d'accord.",
        tokens=["Je", "suis", "d'accord."],
        target_language="fr",
        native_language="pt-BR",
        cefr_level="B1",
    )
    payload = {}
    activity_pool.record_exposure(payload, seen_gap)
    trace = {}
    chosen = activity_pool.choose_interaction_retry(
        failed,
        [orphan, same_family, same_answer, seen_gap, other_language, draft, winner, later],
        payload,
        objective_id="objective-x",
        trace=trace,
    )
    assert chosen["activity_id"] == "winner"
    assert trace["chosen_activity"] == "winner"
    assert trace["reason"] == "interaction_change_retry"
    assert "later" not in _codes(trace["rejected_candidates"])
    assert _codes(trace["rejected_candidates"]) == {
        "orphan": "metadata",
        "same-family": "family",
        "same-answer": "duplicate",
        "seen-gap": "seen",
        "other-language": "language",
        "draft-gap": "quality",
    }
    assert trace["delivered"]["content_version"] == "retry-v1"
    assert trace["delivered"]["content_version_status"] == "declared"
    assert trace["delivered"]["retry"] is True
    assert trace["exhaustion"] is None
    assert SECRET_PROMPT not in json.dumps(trace, ensure_ascii=False)

    blocked = {}
    assert activity_pool.choose_interaction_retry(
        failed, [orphan, same_family], payload, objective_id="objective-x", trace=blocked,
    ) is None
    assert blocked["reason"] == "pool_exhausted"
    assert blocked["exhaustion"]["reason"] == "pool_exhausted"
    assert blocked["exhaustion"]["contributing_rules"] == ["metadata", "family"]


def test_legacy_retry_trace_names_skipped_pool_items_without_changing_the_variant():
    current = item("current", prompt="Visitor name")
    other_objective = item(
        "other-obj",
        prompt="Platform name",
        learning_objective_id="obj-other",
    )
    usable = item(
        "usable",
        prompt="Train name",
        options=["What", "Where", "Who"],
        canonical_answer="What",
        answer="What",
    )
    content = {
        "target_language": "en",
        "native_language": "pt-BR",
        "level": "A1",
        "activity_pool": [other_objective, usable],
        "exercises": [current],
        "questions": [],
    }
    trace = {}
    variant, strategy = lesson_attempts._build_legacy_retry_activity(
        content=content,
        activity_key="grammar:exercise:0",
        current=current,
        seen_fingerprints=set(),
        seen_activities=[current],
        trace=trace,
    )
    assert strategy == "objective_pool"
    assert variant["activity_id"] == "usable"
    assert _codes(trace["excluded_candidates"])["other-obj"] == "metadata"
    assert trace["delivered"]["activity_id"] == "usable"
    assert trace["delivered"]["retry"] is True
    assert trace["exhaustion"] is None

    empty = {}
    variant, strategy = lesson_attempts._build_legacy_retry_activity(
        content={**content, "activity_pool": [other_objective]},
        activity_key="grammar:exercise:0",
        current=current,
        seen_fingerprints=set(),
        seen_activities=[current],
        trace=empty,
    )
    assert variant is None
    assert strategy == "fallback_continue"
    assert empty["exhaustion"]["reason"] == "pool_exhausted"
    assert "metadata" in empty["exhaustion"]["contributing_rules"]


def test_retry_slice_trace_keeps_the_alternate_and_lists_rejections(db_session):
    from test_activity_pool import unit_for
    from test_seen_activities_acceptance import _flow

    flow, _objective = _flow(
        db_session,
        activities=[item("a")],
        pool=[item("gap", "I think this idea is useful.", type="fill_gap", options=[], canonical_answer="useful")],
    )
    response = teaching_slice.submit_slice_answer(
        db_session, flow, student_response="Rome", activity_index=0,
    )
    assert response["current_activity"]["activity_id"] == "gap"
    trace = flow.payload_json["selection_trace"]
    assert trace["reason"] == "interaction_change_retry"
    assert trace["chosen_activity"] == "gap"
    assert trace["fallback_used"] is False
    assert isinstance(trace["rejected_candidates"], list)
    assert all(row.get("activity_id") and row.get("code") for row in trace["rejected_candidates"])
    assert "gap" not in {row["activity_id"] for row in trace["rejected_candidates"]}
    assert trace["delivered"]["activity_id"] == "gap"
    assert trace["delivered"]["retry"] is True
    assert trace["delivered"]["session_id"] == flow.id
    assert trace["session_id"] == flow.id
    public = response["selection_trace"]
    assert public["chosen_activity"] == "gap"
    assert public["delivered"]["activity_id"] == "gap"
    assert SECRET_PROMPT not in json.dumps(public)


def test_exhausted_flow_records_the_rule_without_mastering(db_session):
    from test_seen_activities_acceptance import _flow

    flow, _objective = _flow(db_session, activities=[item("a")], pool=[])
    flow.activity_cursor = 1
    flow.payload_json = {"activities": [item("a")]}
    db_session.commit()
    locked = db_session.get(TeachingFlowSession, flow.id)
    mastery = teaching_slice._finish_exhausted_flow(db_session, locked)
    assert mastery is not None
    assert mastery["state"] != "mastered"
    trace = locked.payload_json["selection_trace"]
    assert trace["exhaustion"]["reason"] == "activities_exhausted"
    assert "activities_exhausted" in trace["exhaustion"]["contributing_rules"]
    assert trace["exhaustion"]["session_id"] == locked.id
    assert locked.phase == FlowPhase.NEEDS_REVIEW
