"""Selector, pool gates, FR B1 slice and remediation with another interaction."""

from sqlalchemy import select

from app.core.teaching import EvidenceType, FlowPhase
from app.models import Language, LearningAttempt, LearningEvidence, TeachingFlowSession, User, UserLanguage
from app.services import activity_pool, session_engine, teaching_slice
from app.services.deterministic_evaluator import evaluate_response
from app.services.fr_b1_slice import activities, count
from app.services.learner_language_contract import interaction_family
from app.services.lesson_bank import reading_text
from app.services.objective_seed import ensure_en_a1_can_001
from test_activity_pool import item, unit_for


def _candidate(activity, *, area, priority=1):
    return {
        "activity": activity,
        "area": area,
        "modality": activity["type"],
        "phase_hint": activity.get("phase_hint") or "practicing",
        "priority": priority,
        "item_key": activity["activity_id"],
    }


def test_selector_breaks_three_identical_interaction_families():
    kinds = ["guided_production", "guided_production", "guided_production", "multiple_choice"]
    areas = ["production", "production", "production", "grammar"]
    candidates = [
        _candidate(
            {
                "activity_id": str(index),
                "type": kind,
                "prompt": f"prompt {index}",
                "canonical_answer": f"answer {index}",
                "phase_hint": "practicing",
                "quality_status": "approved",
                "target_language": "fr",
                "native_language": "pt-BR",
                "learning_objective_id": "same-objective",
            },
            area=area,
        )
        for index, (kind, area) in enumerate(zip(kinds, areas))
    ]
    plan = session_engine.plan_session(candidates)
    families = [activity["interaction_family"] for activity in plan["activities"]]
    assert families.count("guided_input") == 3
    assert "choice" in families
    for left, middle, right in zip(families, families[1:], families[2:]):
        assert not (left == middle == right)
    assert {activity["learning_objective_id"] for activity in plan["activities"]} == {"same-objective"}
    trace = plan["selection_trace"]
    assert trace["candidate_count"] == 4
    assert trace["selected_count"] == 4
    assert trace["diversity_adjustment"] >= 1
    assert trace["excluded_diversity"] == 0


def test_language_invalid_and_unapproved_items_stay_out():
    bad_language = {
        "activity_id": "bad",
        "type": "multiple_choice",
        "prompt": reading_text("en", "beginner")["text"],
        "quality_status": "language_invalid",
        "target_language": "fr",
        "native_language": "pt-BR",
        "learning_objective_id": "same-objective",
        "options": ["a", "b"],
        "canonical_answer": "a",
    }
    draft = {
        "activity_id": "draft",
        "type": "fill_gap",
        "prompt": "Je ___ étudiant.",
        "canonical_answer": "suis",
        "quality_status": "generated",
        "target_language": "fr",
        "native_language": "pt-BR",
        "learning_objective_id": "same-objective",
    }
    good = {
        "activity_id": "good",
        "type": "multiple_choice",
        "prompt": "Choisissez.",
        "options": ["oui", "non"],
        "canonical_answer": "oui",
        "quality_status": "approved",
        "target_language": "fr",
        "native_language": "pt-BR",
        "cefr_level": "B1",
        "learning_objective_id": "same-objective",
    }
    plan = session_engine.plan_session([
        _candidate(bad_language, area="grammar"),
        _candidate(draft, area="grammar"),
        _candidate(good, area="grammar"),
    ])
    assert [activity["activity_id"] for activity in plan["activities"]] == ["good"]
    assert plan["selection_trace"]["excluded_language"] == 1
    assert plan["selection_trace"]["excluded_quality"] == 1
    chosen = activity_pool.select_activity(
        [bad_language, good], objective_id="same-objective", target_language="fr",
        native_language="pt-BR", level="B1",
    )
    assert chosen["activity_id"] == "good"
    wrong_level = activity_pool.select_activity(
        [good], objective_id="same-objective", target_language="fr",
        native_language="pt-BR", level="A1",
    )
    assert wrong_level is None


def test_validate_batch_rejects_generated_and_third_language():
    english = reading_text("en", "beginner")["text"]
    contaminated = {
        "learning_objective_id": "obj",
        "content_unit_id": "unit",
        "skill": "reading",
        "type": "multiple_choice",
        "prompt": english,
        "target_language": "fr",
        "native_language": "pt-BR",
        "cefr_level": "B1",
        "quality_status": "approved",
        "provenance": {"source": "editorial", "reviewer": "editor"},
        "canonical_answer": "oui",
        "options": ["oui", "non"],
    }
    generated = dict(contaminated, prompt="Je pense que cette idée est utile.", quality_status="generated", activity_id="generated")
    result = activity_pool.validate_batch([], [contaminated, generated])
    assert result["accepted"] == []
    reasons = {item["reason"] for item in result["rejected"]}
    assert "language" in reasons
    assert "editorial_approval_required" in reasons


def test_due_item_keeps_priority_over_a_fresh_visual_alternative():
    due = _candidate({
        "activity_id": "due",
        "type": "recognition",
        "prompt": "bonjour",
        "canonical_answer": "olá",
        "quality_status": "approved",
        "target_language": "fr",
        "learning_objective_id": "vocab",
        "phase_hint": "activating",
    }, area="vocabulary", priority=0)
    fresh = _candidate({
        "activity_id": "fresh",
        "type": "multiple_choice",
        "prompt": "Choisissez.",
        "options": ["oui", "non"],
        "canonical_answer": "oui",
        "quality_status": "approved",
        "target_language": "fr",
        "learning_objective_id": "other",
        "phase_hint": "practicing",
    }, area="grammar", priority=2)
    plan = session_engine.plan_session([due, fresh])
    ids = [activity["activity_id"] for activity in plan["activities"]]
    assert ids[0] == "due"


def test_fr_b1_slice_is_french_and_varied():
    items = activities()
    assert count() == 10
    types = {item["type"] for item in items}
    assert {
        "presentation", "listening_recognition", "multiple_choice", "fill_gap",
        "word_order", "matching", "guided_production", "repeat",
        "transfer_question", "dictation",
    } <= types
    families = {interaction_family(item["type"]) for item in items}
    assert len(families) >= 8
    for item in items:
        assert item["target_language"] == "fr"
        assert item["native_language"] == "pt-BR"
        assert item["cefr_level"] == "B1"
        assert item["quality_status"] == "approved"
        assert "Você" not in (item.get("prompt") or "")
        assert "Você" not in (item.get("scenario_target") or "")
    ordered = next(item for item in items if item["type"] == "word_order")
    assert evaluate_response(student_response="Je ne suis pas d'accord.", activity=ordered)["result"] == "correct"
    dictated = next(item for item in items if item["type"] == "dictation")
    assert dictated["show_text"] is False
    assert evaluate_response(
        student_response="Je suis d'accord avec cette idée.", activity=dictated,
    )["result"] == "correct"
    planned = session_engine.plan_session([
        _candidate(item, area=session_engine.activity_area(item["type"]) or "grammar", priority=0)
        for item in items
    ])
    planned_types = {activity["type"] for activity in planned["activities"]}
    assert "fill_gap" in planned_types
    assert "dictation" in planned_types
    assert "transfer_question" in planned_types
    assert "word_order" not in planned_types
    assert planned["selection_trace"]["excluded_language"] == 0
    assert planned["selection_trace"]["excluded_quality"] >= 1
    supported = session_engine.supporting_candidates(
        language_code="fr", level="B1", native_language="pt-BR",
    )
    conversation = next(
        item["activity"] for item in supported if item["activity"]["type"] == "conversation_prompt"
    )
    assert conversation["scenario_target"].startswith("Vous n'êtes pas d'accord")
    assert "Você" not in conversation["scenario_target"]
    assert "fr-b1-presentation-pourtant" not in {
        item["activity"].get("activity_id") for item in supported
    }


def test_curated_bank_matches_metadata_and_the_selector():
    from app.services.curated_bank import candidates_for

    french = candidates_for(target_language="fr", native_language="pt-BR", cefr_level="B1")
    assert len(french) == 10
    for item in french:
        assert item["learning_objective_id"] == "curated:fr:B1:pt-BR"
        assert item["cefr_level"] == "B1"
        assert item["target_language"] == "fr"
        assert item["native_language"] == "pt-BR"
        assert item["quality_status"] == "approved"
        assert item["interaction_family"]
    assert candidates_for(target_language="es-ES", native_language="pt-BR", cefr_level="B1") == []
    assert candidates_for(target_language="fr", native_language="en", cefr_level="B1") == []
    chosen = activity_pool.select_activity(
        french, objective_id="curated:fr:B1:pt-BR", target_language="fr",
        native_language="pt-BR", level="B1",
    )
    assert chosen is not None
    assert chosen["learning_objective_id"] == "curated:fr:B1:pt-BR"
    assert activity_pool.select_activity(
        french, objective_id="another-objective", target_language="fr",
        native_language="pt-BR", level="B1",
    ) is None


def test_interaction_retry_requires_the_same_objective():
    failed = {
        "activity_id": "failed",
        "type": "multiple_choice",
        "prompt": "Choisissez un nom.",
        "canonical_answer": "Ada",
        "learning_objective_id": "obj-1",
        "target_language": "fr",
        "native_language": "pt-BR",
        "cefr_level": "B1",
        "quality_status": "approved",
        "options": ["Ada", "Rome"],
    }
    orphan = {
        "activity_id": "orphan",
        "type": "fill_gap",
        "prompt": "Je pense que cette idée est ___.",
        "canonical_answer": "utile",
        "target_language": "fr",
        "native_language": "pt-BR",
        "cefr_level": "B1",
        "quality_status": "approved",
    }
    same = dict(orphan, activity_id="same", learning_objective_id="obj-1")
    assert activity_pool.choose_interaction_retry(failed, [orphan], objective_id="obj-1") is None
    chosen = activity_pool.choose_interaction_retry(failed, [orphan, same], objective_id="obj-1")
    assert chosen["activity_id"] == "same"


def test_conversation_candidate_omits_portuguese_support_for_other_natives():
    supported = session_engine.supporting_candidates(
        language_code="fr", level="B1", native_language="en",
    )
    conversation = next(
        item["activity"] for item in supported if item["activity"]["type"] == "conversation_prompt"
    )
    assert conversation["native_language"] == "en"
    assert conversation["target_language"] == "fr"
    assert conversation["scenario_target"].startswith("Vous n'êtes pas d'accord")
    assert conversation.get("scenario_native") is None
    assert conversation.get("prompt_pt") is None
    assert conversation.get("prompt_native") is None


def test_wrong_answer_retries_a_different_interaction_then_repairs(db_session):
    objective = ensure_en_a1_can_001(db_session)
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    user.native_language = "pt-BR"
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    owner = UserLanguage(user_id=user.id, language_id=language.id, is_active=True)
    db_session.add(owner)
    db_session.flush()
    unit = unit_for(db_session, objective)
    failed = item(
        learning_objective_id=objective.id, skill=objective.skill_focus,
        phase_hint="practicing", ai_required=False, content_unit_id=unit.id,
    )
    alternate = item(
        "gap", "Je pense que cette idée est utile.", type="fill_gap", options=[],
        canonical_answer="utile", accepted_variants=["utile"],
        learning_objective_id=objective.id, content_unit_id=unit.id,
        skill=objective.skill_focus, phase_hint="practicing", ai_required=False,
    )
    activity_pool.append_objective_batch(db_session, objective_id=objective.id, batch=[alternate])
    flow = TeachingFlowSession(
        user_language_id=owner.id, objective_id=objective.id, phase=FlowPhase.PRACTICING,
        payload_json={"activities": [failed]}, status="active",
    )
    db_session.add(flow)
    db_session.commit()
    response = teaching_slice.submit_slice_answer(db_session, flow, student_response="Rome", activity_index=0)
    current = response["current_activity"]
    assert current["activity_id"] == "gap"
    assert current["interaction_family"] == "inline_gap"
    assert current["retry_strategy"] == "interaction_change"
    assert flow.payload_json["selection_trace"]["reason"] == "interaction_change_retry"
    repaired = teaching_slice.retry_slice(
        db_session, flow, remediation_id=response["remediation"]["id"], student_response="utile",
    )
    assert repaired["attempt"]["result"] == "correct"
    evidence = db_session.scalar(select(LearningEvidence).where(
        LearningEvidence.attempt_id == repaired["attempt"]["id"]
    ))
    assert evidence is not None
    assert evidence.evidence_type == EvidenceType.ERROR_REPAIRED
    assert db_session.get(LearningAttempt, repaired["attempt"]["id"]).activity_type == "fill_gap"
