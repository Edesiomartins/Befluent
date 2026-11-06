"""Trace de seleção da Etapa 1: motivo por candidato, sem mudar a escolha."""

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.teaching import FlowPhase
from app.models import Language, TeachingFlowSession, User, UserLanguage
from app.services import activity_pool, lesson_attempts, session_engine, teaching_slice
from app.services.objective_seed import ensure_en_a1_can_001
from test_activity_pool import item, unit_for


SECRET_PROMPT = "PROMPT-SECRETO-NAO-LOGAR"
SECRET_ANSWER = "RESPOSTA-SECRETA-NAO-LOGAR"


def _fr(identity, **changes):
    base = {
        "activity_id": identity,
        "learning_objective_id": "obj-fr",
        "content_unit_id": "unit-fr",
        "skill": "grammar",
        "type": "multiple_choice",
        "prompt": f"Choisissez la phrase {identity} pour cette activité.",
        "canonical_answer": "oui",
        "options": ["oui", "non"],
        "target_language": "fr",
        "native_language": "pt-BR",
        "cefr_level": "B1",
        "quality_status": "approved",
        "provenance": {"source": "editorial", "reviewer": "editor"},
    }
    base.update(changes)
    return base


def test_diagnostic_uses_null_and_unknown_when_provenance_is_absent():
    diagnostic = activity_pool.activity_diagnostic(
        {"type": "fill_gap", "prompt": SECRET_PROMPT, "canonical_answer": SECRET_ANSWER}
    )
    assert diagnostic["source"] == "unknown"
    assert diagnostic["content_version"] is None
    assert diagnostic["content_version_status"] == "unknown"
    assert diagnostic["content_source_id"] is None
    assert diagnostic["content_unit_id"] is None
    assert diagnostic["provider"] is None
    assert diagnostic["model"] is None
    assert "prompt" not in diagnostic
    assert SECRET_PROMPT not in json.dumps(diagnostic)
    assert SECRET_ANSWER not in json.dumps(diagnostic)


def test_diagnostic_keeps_only_declared_provenance():
    diagnostic = activity_pool.activity_diagnostic(
        {
            "activity_id": "fr-b1-gap-utile",
            "id": "legacy-row",
            "type": "fill_gap",
            "learning_objective_id": "curated:fr:B1:pt-BR",
            "target_language": "fr",
            "native_language": "pt-BR",
            "cefr_level": "B1",
            "content_unit_id": "unit-9",
            "content_source": "curated_fr_b1_slice",
            "content_version": "slice-1",
            "prompt": SECRET_PROMPT,
            "provenance": {"source": "editorial", "provider": "mock", "model": "fixture-model"},
        }
    )
    assert diagnostic["activity_id"] == "fr-b1-gap-utile"
    assert diagnostic["legacy_id"] == "legacy-row"
    assert diagnostic["source"] == "editorial"
    assert diagnostic["provider"] == "mock"
    assert diagnostic["model"] == "fixture-model"
    assert diagnostic["content_version"] == "slice-1"
    assert diagnostic["content_version_status"] == "declared"
    assert diagnostic["content_source_id"] is None
    assert diagnostic["content_unit_id"] == "unit-9"
    assert diagnostic["target_language"] == "fr"
    assert diagnostic["native_language"] == "pt-BR"
    assert diagnostic["cefr_level"] == "B1"
    assert diagnostic["interaction_family"] == "inline_gap"


def test_select_activity_records_each_exclusion_without_changing_the_choice(caplog):
    keep = item("keep", prompt="Choose the useful sentence now", canonical_answer="Ada")
    seen = item("seen", prompt="Choose another useful sentence now")
    cooled = item("cooled", prompt="Choose a cooled sentence today please")
    retired = item("retired", prompt="Choose the retired sentence today please")
    invalid = item(
        "invalid",
        prompt="This english sentence should stay out of french delivery now",
        quality_status="language_invalid",
    )
    draft = item("draft", prompt="Choose this generated draft.", quality_status="generated")
    wrong_level = item("level", prompt="Choose the level mismatch sentence please", cefr_level="A2")
    payload = {"seen_activity_ids": ["seen"], "retired_families": [activity_pool.family_key(retired)]}
    history = {
        "cooled": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
    }
    original = json.dumps(
        [keep, seen, cooled, retired, invalid, draft, wrong_level],
        ensure_ascii=False,
        sort_keys=True,
    )
    trace = {}
    with caplog.at_level(logging.INFO, logger="app.services.activity_pool"):
        chosen = activity_pool.select_activity(
            [keep, seen, cooled, retired, invalid, draft, wrong_level],
            objective_id="objective-x",
            session_payload=payload,
            exposure_history=history,
            target_language="en",
            native_language="pt-BR",
            level="A1",
            trace=trace,
        )
    assert chosen["activity_id"] == "keep"
    assert json.dumps(
        [keep, seen, cooled, retired, invalid, draft, wrong_level],
        ensure_ascii=False,
        sort_keys=True,
    ) == original
    codes = {row["activity_id"]: row["code"] for row in trace["excluded_candidates"]}
    assert codes == {
        "seen": "seen",
        "cooled": "cooldown",
        "retired": "family",
        "invalid": "language",
        "draft": "quality",
        "level": "metadata",
    }
    assert trace["exclusions"]["seen"] == 3
    assert trace["exclusions"]["language"] == 1
    assert trace["exclusions"]["quality"] == 1
    assert trace["exclusions"]["metadata"] == 1
    assert trace["chosen_activity"] == "keep"
    assert trace["chosen"]["source"] == "editorial"
    assert trace["chosen"]["content_version_status"] == "unknown"
    assert trace["reason"] == "freshness_then_diversity"
    assert trace["fallback_used"] is False
    assert trace["exhaustion"] is None
    assert SECRET_PROMPT not in caplog.text
    assert "keep" in caplog.text


def test_select_activity_exhaustion_names_the_rules(caplog):
    trace = {}
    with caplog.at_level(logging.INFO, logger="app.services.activity_pool"):
        chosen = activity_pool.select_activity(
            [item("only", cefr_level="B2")],
            objective_id="objective-x",
            target_language="en",
            native_language="pt-BR",
            level="A1",
            trace=trace,
        )
    assert chosen is None
    assert trace["reason"] == "pool_exhausted"
    assert trace["fallback_used"] is True
    assert trace["chosen"] is None
    assert trace["excluded_candidates"] == [{"activity_id": "only", "legacy_id": None, "code": "metadata"}]
    assert trace["exhaustion"]["aggregate_reason"] == "pool_exhausted"
    assert "metadata" in trace["exhaustion"]["contributing_rules"]
    empty = {}
    assert activity_pool.select_activity([], objective_id="objective-x", trace=empty) is None
    assert empty["exhaustion"]["contributing_rules"] == ["no_candidates"]


def test_interaction_retry_records_rejections_and_keeps_the_same_choice():
    failed = _fr("failed", type="multiple_choice", canonical_answer="Ada", options=["Ada", "Rome"])
    orphan = _fr("orphan", type="fill_gap", learning_objective_id="outro", canonical_answer="utile", options=[])
    same_family = _fr("same-family", type="multiple_choice", canonical_answer="autre", options=["autre", "rien"])
    same = _fr("same", type="fill_gap", canonical_answer="utile", options=[])
    trace = {}
    assert activity_pool.choose_interaction_retry(failed, [orphan, same_family], objective_id="obj-fr", trace=trace) is None
    assert {row["activity_id"]: row["code"] for row in trace["excluded_candidates"]} == {
        "orphan": "metadata",
        "same-family": "family",
    }
    assert trace["reason"] == "pool_exhausted"
    assert trace["exhaustion"]["aggregate_reason"] == "pool_exhausted"
    assert set(trace["exhaustion"]["contributing_rules"]) == {"metadata", "family"}
    chosen_trace = {}
    chosen = activity_pool.choose_interaction_retry(
        failed, [orphan, same_family, same], objective_id="obj-fr", trace=chosen_trace,
    )
    assert chosen["activity_id"] == "same"
    assert chosen_trace["chosen_activity"] == "same"
    assert chosen_trace["reason"] == "interaction_change_retry"
    assert chosen_trace["fallback_used"] is False
    assert chosen_trace["chosen"]["target_language"] == "fr"
    assert chosen_trace["chosen"]["native_language"] == "pt-BR"
    assert chosen_trace["chosen"]["cefr_level"] == "B1"
    assert chosen_trace["chosen"]["content_version_status"] == "unknown"
    assert "prompt" not in json.dumps(chosen_trace)


def test_plan_session_names_exclusions_and_preserves_the_selected_id():
    keep = {
        "activity_id": "keep",
        "type": "multiple_choice",
        "prompt": "Choisissez la bonne phrase pour aujourd'hui.",
        "options": ["oui", "non"],
        "canonical_answer": "oui",
        "quality_status": "approved",
        "target_language": "fr",
        "native_language": "pt-BR",
        "cefr_level": "B1",
        "learning_objective_id": "curated:fr:B1:pt-BR",
        "content_source": "curated_fr_b1_slice",
        "phase_hint": "practicing",
    }
    duplicate = dict(keep, activity_id="dup")
    seen = dict(keep, activity_id="seen", prompt="Choisissez une autre phrase pour demain matin.")
    cooled = dict(keep, activity_id="cooled", prompt="Choisissez une phrase laissée au repos aujourd'hui.")
    invalid = dict(keep, activity_id="invalid", quality_status="language_invalid", prompt="This english item stays excluded from the french plan.")
    draft = dict(keep, activity_id="draft", quality_status="generated", prompt="Brouillon.")
    retired = dict(keep, activity_id="retired", prompt="Choisissez la phrase déjà retirée de la famille.")
    candidates = [
        {"activity": item, "area": "grammar", "modality": item["type"], "phase_hint": "practicing", "priority": 1, "item_key": item["activity_id"]}
        for item in (keep, duplicate, seen, cooled, invalid, draft, retired)
    ]
    payload = {
        "seen_activity_ids": ["seen"],
        "retired_families": [activity_pool.family_key(retired)],
    }
    history = {"cooled": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}
    plan = session_engine.plan_session(candidates, session_payload=payload, exposure_history=history)
    assert [activity["activity_id"] for activity in plan["activities"]] == ["keep"]
    codes = {row["activity_id"]: row["code"] for row in plan["selection_trace"]["excluded_candidates"]}
    assert codes["dup"] == "duplicate"
    assert codes["seen"] == "seen"
    assert codes["cooled"] == "cooldown"
    assert codes["invalid"] == "language"
    assert codes["draft"] == "quality"
    assert codes["retired"] == "family"
    assert plan["selection_trace"]["excluded_seen"] == 2
    assert plan["selection_trace"]["excluded_family"] == 1
    assert plan["selection_trace"]["excluded_language"] == 1
    assert plan["selection_trace"]["excluded_quality"] == 1
    assert plan["selection_trace"]["excluded_duplicate"] == 1
    chosen = plan["selection_trace"]["activities"][0]
    assert chosen["activity_id"] == "keep"
    assert chosen["source"] == "curated_fr_b1_slice"
    assert chosen["content_source_id"] is None
    assert chosen["content_version"] is None
    assert chosen["content_version_status"] == "unknown"
    assert chosen["provider"] is None
    assert chosen["model"] is None
    assert chosen["target_language"] == "fr"
    assert chosen["native_language"] == "pt-BR"
    assert chosen["cefr_level"] == "B1"
    assert chosen["selection_reason"] == "freshness_budget_modality_interaction"
    assert plan["selection_trace"]["exhaustion"]["aggregate_reason"] == "budget_shortfall"
    assert "duplicate" in plan["selection_trace"]["exhaustion"]["contributing_rules"]
    assert SECRET_PROMPT not in json.dumps(plan["selection_trace"])


def test_legacy_retry_trace_names_the_rejected_candidate_and_the_choice():
    current = _fr("current")
    other = _fr("other", learning_objective_id="outro", prompt="Choisissez une phrase d'un autre objectif maintenant.")
    usable = _fr("usable", prompt="Choisissez une phrase différente pour le nouvel essai.")
    rejections = []
    variant, strategy = lesson_attempts._build_legacy_retry_activity(
        content={
            "target_language": "fr",
            "native_language": "pt-BR",
            "level": "B1",
            "activity_pool": [other, usable],
        },
        activity_key="grammar:exercise:0",
        current=current,
        rejections=rejections,
    )
    assert strategy == "objective_pool"
    assert variant["activity_id"] == "usable"
    assert rejections == [{"activity_id": "other", "legacy_id": None, "code": "metadata"}]
    trace = lesson_attempts.legacy_selection_trace(
        session_id="lesson-1",
        current=current,
        variant=variant,
        strategy=strategy,
        rejections=rejections,
    )
    assert trace["reason"] == "objective_pool"
    assert trace["fallback_used"] is False
    assert trace["chosen_activity"] == "usable"
    assert trace["chosen"]["target_language"] == "fr"
    assert trace["excluded_candidates"] == [{"activity_id": "other", "legacy_id": None, "code": "metadata"}]
    assert trace["exhaustion"] is None
    blocked = []
    none_variant, none_strategy = lesson_attempts._build_legacy_retry_activity(
        content={
            "target_language": "fr",
            "native_language": "pt-BR",
            "level": "B1",
            "activity_pool": [other],
        },
        activity_key="grammar:exercise:0",
        current=current,
        rejections=blocked,
    )
    assert none_variant is None
    assert none_strategy == "fallback_continue"
    exhausted = lesson_attempts.legacy_selection_trace(
        session_id="lesson-1",
        current=current,
        variant=None,
        strategy=none_strategy,
        rejections=blocked,
    )
    assert exhausted["reason"] == "pool_exhausted"
    assert exhausted["fallback_used"] is True
    assert exhausted["exhaustion"]["aggregate_reason"] == "pool_exhausted"
    assert "objective" in exhausted["exhaustion"]["contributing_rules"] or "metadata" in exhausted["exhaustion"]["contributing_rules"]
    assert SECRET_PROMPT not in json.dumps(exhausted)


def test_slice_retry_trace_keeps_the_alternate_and_records_the_orphan(db_session):
    objective = ensure_en_a1_can_001(db_session)
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    user.native_language = "pt-BR"
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    owner = UserLanguage(user_id=user.id, language_id=language.id, is_active=True)
    db_session.add(owner)
    db_session.flush()
    unit = unit_for(db_session, objective)
    failed = item(
        learning_objective_id=objective.id,
        skill=objective.skill_focus,
        phase_hint="practicing",
        ai_required=False,
        content_unit_id=unit.id,
    )
    same_family = item(
        "same-family",
        "Pick another name from the same interaction family.",
        learning_objective_id=objective.id,
        content_unit_id=unit.id,
        skill=objective.skill_focus,
        phase_hint="practicing",
        ai_required=False,
    )
    alternate = item(
        "gap",
        "I think this idea is useful.",
        type="fill_gap",
        options=[],
        canonical_answer="useful",
        accepted_variants=["useful"],
        learning_objective_id=objective.id,
        content_unit_id=unit.id,
        skill=objective.skill_focus,
        phase_hint="practicing",
        ai_required=False,
    )
    activity_pool.append_objective_batch(
        db_session, objective_id=objective.id, batch=[same_family, alternate],
    )
    flow = TeachingFlowSession(
        user_language_id=owner.id,
        objective_id=objective.id,
        phase=FlowPhase.PRACTICING,
        payload_json={"activities": [failed]},
        status="active",
    )
    db_session.add(flow)
    db_session.commit()
    response = teaching_slice.submit_slice_answer(
        db_session, flow, student_response="Rome", activity_index=0,
    )
    assert response["current_activity"]["activity_id"] == "gap"
    trace = flow.payload_json["selection_trace"]
    assert trace["reason"] == "interaction_change_retry"
    assert trace["chosen_activity"] == "gap"
    assert trace["session_id"] == flow.id
    assert trace["retry"] is True
    codes = {row["activity_id"]: row["code"] for row in trace["excluded_candidates"]}
    assert codes["same-family"] == "family"
    assert "Rome" not in json.dumps(trace)
    assert response["selection_trace"]["chosen_activity"] == "gap"
