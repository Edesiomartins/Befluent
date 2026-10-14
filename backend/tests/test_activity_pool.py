"""Pool, exposure and remediation contracts (no provider or production DB)."""
from datetime import datetime, timedelta, timezone

import pytest

from app.services import activity_pool


def item(identity="a", prompt="Choose a name", **changes):
    return {
        "activity_id": identity, "learning_objective_id": "objective-x",
        "content_unit_id": "unit", "type": "multiple_choice", "skill": "grammar",
        "target_language": "en", "native_language": "pt-BR", "cefr_level": "A1",
        "prompt": prompt, "canonical_answer": "Ada", "options": ["Ada", "Rome"],
        "quality_status": "approved", "provenance": {"source": "editorial", "reviewer": "editor"},
        **changes,
    }


def choose(candidates, **kwargs):
    return activity_pool.select_activity(candidates, objective_id="objective-x", **kwargs)


def unit_for(db, objective):
    from app.models import ContentSource, ContentUnit
    source = ContentSource(title="Reviewed test source", language_id=objective.language_id,
                           review_status="APPROVED", usage_policy="OPEN_LICENSE")
    db.add(source)
    db.flush()
    unit = ContentUnit(source_id=source.id, language_id=objective.language_id, cefr_level=objective.level,
                       skill=objective.skill_focus, mode="guided", title="Objective unit", validation_status="APPROVED")
    db.add(unit)
    db.flush()
    return unit


def test_seen_id_and_same_content_with_new_id_are_excluded():
    a = item()
    payload = {}
    activity_pool.record_exposure(payload, a)
    assert choose([a, item("clone")], session_payload=payload) is None


def test_remediation_keeps_objective_and_changes_stimulus():
    a = item()
    payload = {}
    activity_pool.record_exposure(payload, a)
    b = item("b", "Who is introducing herself?")
    assert choose([item("wrong", learning_objective_id="other"), a, b], session_payload=payload) == b


def test_unseen_precedes_old_then_recent():
    now = datetime.now(timezone.utc)
    a, b, c = item(), item("b", "Old context"), item("c", "New context")
    history = {"a": now.isoformat(), "b": (now - timedelta(days=20)).isoformat()}
    assert choose([a, b, c], exposure_history=history, now=now) == c
    assert choose([a, b], exposure_history=history, now=now) == b
    assert choose([a], exposure_history=history, now=now) == a


def test_resume_exclusions_survive_json_roundtrip():
    import json
    payload = {}
    activity_pool.record_exposure(payload, item())
    assert choose([item()], session_payload=json.loads(json.dumps(payload))) is None


@pytest.mark.parametrize("change", [
    {"target_language": "fr"}, {"native_language": "de"},
    {"cefr_level": "B2"}, {"quality_status": "language_invalid"},
])
def test_selector_language_level_and_quality_filters(change):
    assert choose([item(**change)], target_language="en", native_language="pt-BR", level="A1") is None


def test_batch_deduplicates_between_batches_and_cosmetic_variants():
    first = activity_pool.validate_batch([], [item()], batch_size=5)
    assert len(first["accepted"]) == 1
    second = activity_pool.validate_batch(first["accepted"], [item("b", "CHOOSE a name!!")], batch_size=5)
    assert not second["accepted"]
    assert second["rejected"][0]["reason"] == "duplicate"


def test_batch_near_duplicates_do_not_inflate_pool():
    a = item(prompt="Je ___ au travail tous les jours.", canonical_answer="vais", options=["vais", "va"])
    b = item("b", "Je ___ au cinéma tous les jours.", canonical_answer="vais", options=["vais", "va"])
    assert not activity_pool.validate_batch([a], [b], batch_size=5)["accepted"]


def test_batch_quality_gate_and_size():
    assert not activity_pool.validate_batch([], [item(provenance={})], batch_size=2)["accepted"]
    assert not activity_pool.validate_batch([], [item(canonical_answer="absent")], batch_size=2)["accepted"]
    with pytest.raises(ValueError):
        activity_pool.validate_batch([], [item(), item("b")], batch_size=1)


def test_insufficient_pool_is_short_and_never_padded():
    from app.services.session_engine import plan_session, _candidate
    a = item()
    plan = plan_session([_candidate(a, priority=1), _candidate(item("clone"), priority=1)])
    assert plan["total"] == 1


def test_legacy_optional_metadata_does_not_get_invented():
    legacy = {"prompt": "A legacy question", "answer": "yes", "options": ["yes", "no"]}
    assert activity_pool.select_activity([legacy]) == legacy
    assert "learning_objective_id" not in legacy
    assert choose([legacy]) is None


def test_incremental_persistence_and_rollback(db_session):
    from app.services.objective_seed import ensure_en_a1_can_001
    from app.models import LearningObjective
    objective = ensure_en_a1_can_001(db_session)
    unit = unit_for(db_session, objective)
    candidate = item(learning_objective_id=objective.id, content_unit_id=unit.id, skill=objective.skill_focus)
    first = activity_pool.append_objective_batch(db_session, objective_id=objective.id, batch=[candidate], batch_size=5)
    assert len(first["accepted"]) == 1
    db_session.commit()
    second = activity_pool.append_objective_batch(db_session, objective_id=objective.id, batch=[{**candidate, "activity_id": "clone"}], batch_size=5)
    assert not second["accepted"]
    third = activity_pool.append_objective_batch(db_session, objective_id=objective.id, batch=[{**candidate, "activity_id": "b", "prompt": "Which visitor is introducing herself?"}], batch_size=5)
    assert len(third["accepted"]) == 1
    db_session.rollback()
    assert len(db_session.get(LearningObjective, objective.id).pedagogy_json["activity_pool"]) == 1


def test_teaching_retry_tracks_correct_seen_and_uses_objective_pool(db_session):
    from sqlalchemy import select
    from app.models import Language, User, UserLanguage, TeachingFlowSession, LearningAttempt
    from app.services import teaching_flow, teaching_slice
    from app.core.teaching import FlowPhase
    from app.services.objective_seed import ensure_en_a1_can_001
    objective = ensure_en_a1_can_001(db_session)
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    owner = UserLanguage(user_id=user.id, language_id=language.id, is_active=True)
    db_session.add(owner)
    db_session.flush()
    a = item(learning_objective_id=objective.id, skill=objective.skill_focus, phase_hint="practicing", ai_required=False)
    unit = unit_for(db_session, objective)
    b = item("b", "Who is the visitor?", type="fill_gap", options=[], learning_objective_id=objective.id, content_unit_id=unit.id, skill=objective.skill_focus, phase_hint="practicing", ai_required=False)
    activity_pool.append_objective_batch(db_session, objective_id=objective.id, batch=[b])
    flow = TeachingFlowSession(user_language_id=owner.id, objective_id=objective.id, phase=FlowPhase.PRACTICING,
                               payload_json={"activities": [a]}, status="active")
    db_session.add(flow)
    db_session.commit()
    response = teaching_slice.submit_slice_answer(db_session, flow, student_response="Rome", activity_index=0)
    assert response["current_activity"]["activity_id"] == "b"
    assert flow.payload_json["seen_activity_ids"] == ["a", "b"]
    db_session.commit()
    db_session.expire_all()
    restored = teaching_slice.restore_session_payload(db_session, db_session.get(TeachingFlowSession, flow.id), objective=objective)
    assert restored["current_activity"]["activity_id"] == "b"
    retried = teaching_slice.retry_slice(db_session, flow, remediation_id=response["remediation"]["id"], student_response="Ada")
    assert retried["attempt"]["result"] == "correct"
    assert db_session.get(LearningAttempt, retried["attempt"]["id"]).activity_type == "fill_gap"
    assert flow.activity_cursor == 1


def test_continuation_skips_a_question_consumed_as_retry(db_session):
    from app.models import TeachingFlowSession, UserLanguage, User, Language
    from sqlalchemy import select
    from app.services import teaching_flow
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    owner = UserLanguage(user_id=user.id, language_id=language.id, is_active=True)
    db_session.add(owner)
    db_session.flush()
    a, b, c = item(), item("b", "Retry context"), item("c", "Fresh context")
    payload = {"activities": [a, b, c]}
    activity_pool.record_exposure(payload, a)
    activity_pool.record_exposure(payload, b)
    flow = TeachingFlowSession(user_language_id=owner.id, payload_json=payload)
    db_session.add(flow)
    db_session.flush()
    teaching_flow.advance_activity_cursor(db_session, flow)
    assert flow.activity_cursor == 2
    assert teaching_flow.current_activity(flow)["activity_id"] == "c"


def test_objective_seed_refresh_preserves_editorial_pool(db_session):
    from app.services.objective_seed import ensure_en_a1_can_001
    objective = ensure_en_a1_can_001(db_session)
    objective.pedagogy_json = {**objective.pedagogy_json, "activity_pool": [item()]}
    db_session.flush()
    assert ensure_en_a1_can_001(db_session).pedagogy_json["activity_pool"] == [item()]


def test_main_plan_excludes_seen_and_prefers_unseen():
    from app.services.session_engine import plan_session, _candidate
    a, b = item(), item("b", "Fresh objective context")
    payload = {}
    activity_pool.record_exposure(payload, a)
    plan = plan_session([_candidate(a, priority=0), _candidate(b, priority=1)], session_payload=payload)
    assert [x["activity_id"] for x in plan["activities"]] == ["b"]


def test_incremental_generator_receives_previous_batch(db_session):
    from app.services.objective_seed import ensure_en_a1_can_001
    objective = ensure_en_a1_can_001(db_session)
    unit = unit_for(db_session, objective)
    calls = []
    def generate_batch(*, objective, existing, batch_size):
        calls.append(len(existing))
        return [item(learning_objective_id=objective.id, content_unit_id=unit.id, skill=objective.skill_focus)]
    results = activity_pool.generate_incremental_batches(db_session, objective_id=objective.id, generate_batch=generate_batch, batch_count=2, batch_size=5)
    assert calls == [0, 1]
    assert len(results[0]["accepted"]) == 1
    assert not results[1]["accepted"]


def test_legacy_unknown_objective_has_explicit_safe_fallback():
    from app.services.lesson_attempts import _build_legacy_retry_activity
    a = {"prompt": "An original question", "answer": "yes", "options": ["yes", "no"]}
    b = {"prompt": "Another question", "answer": "yes", "options": ["yes", "no"]}
    variant, strategy = _build_legacy_retry_activity(content={"questions": [a, b]}, activity_key="reading:question:0", current=a)
    assert variant is None
    assert strategy == "fallback_continue"


def test_batch_answer_alias_is_evaluable_without_inventing_an_answer():
    from app.services.deterministic_evaluator import evaluate_response
    candidate = item()
    candidate.pop("canonical_answer")
    candidate["answer"] = "Ada"
    accepted = activity_pool.validate_batch([], [candidate])["accepted"][0]
    assert evaluate_response(student_response="Ada", activity=accepted)["result"] == "correct"


def test_quality_rejects_valid_answer_as_distractor_and_empty_word_order():
    assert not activity_pool.validate_batch([], [item(accepted_variants=["Ada", "Rome"])])["accepted"]
    assert not activity_pool.validate_batch([], [item(type="word_order", tokens=[])])["accepted"]


def test_shared_pool_rejects_learner_owned_vocabulary_references():
    result = activity_pool.validate_batch([], [item(vocabulary_item_id="another-learner-item")])
    assert not result["accepted"]
    assert result["rejected"][0]["reason"] == "learner_specific_reference"


def test_legacy_retry_fingerprints_survive_new_exposure_ledger():
    from app.services.question_identity import question_fingerprint
    a, b = item(), item("b", "A different current question")
    payload = {"seen_question_fingerprints": [question_fingerprint(a)]}
    activity_pool.record_exposure(payload, b)
    assert choose([a], session_payload=payload) is None


def test_legacy_pool_supports_canonical_answer_and_typed_options():
    from app.services.lesson_attempts import _build_legacy_retry_activity
    a = item(prompt="Who introduced herself yesterday?")
    b = item("b", "Which visitor is arriving?", options=[{"text": "Ada"}, {"text": "Rome"}])
    content = {"language_code": "en", "native_language": "pt-BR", "level": "A1",
               "exercises": [a], "activity_pool": [b]}
    variant, _ = _build_legacy_retry_activity(content=content, activity_key="grammar:exercise:0", current=a)
    assert variant["answer"] == "Ada"
    assert variant["options"] == ["Ada", "Rome"]


def test_standalone_cycle_can_submit_pool_retry_without_replaying_original(db_session, client, auth):
    from sqlalchemy import select
    from app.models import User, UserLanguage, Language, Lesson, TeachingFlowSession
    from app.services.objective_seed import ensure_en_a1_can_001
    from app.core.teaching import FlowPhase
    objective = ensure_en_a1_can_001(db_session)
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    owner = UserLanguage(user_id=user.id, language_id=language.id, is_active=True)
    db_session.add(owner)
    db_session.flush()
    lesson = Lesson(user_language_id=owner.id, title="Unit", objective="Introduce yourself", status="active",
                    content_json={"language_code": "en", "native_language": "pt-BR"})
    db_session.add(lesson)
    db_session.flush()
    unit = unit_for(db_session, objective)
    a = item(learning_objective_id=objective.id, skill=objective.skill_focus, phase_hint="practicing")
    b = item("b", "Which visitor arrived?", learning_objective_id=objective.id, skill=objective.skill_focus,
             content_unit_id=unit.id, phase_hint="practicing")
    activity_pool.append_objective_batch(db_session, objective_id=objective.id, batch=[b])
    flow = TeachingFlowSession(user_language_id=owner.id, lesson_id=lesson.id, objective_id=objective.id,
                               phase=FlowPhase.PRACTICING, status="active",
                               payload_json={"activities": [a], "lexical_cycle": True, "session_engine_v2": True})
    db_session.add(flow)
    db_session.commit()
    path = f"/api/v1/lessons/{lesson.id}/vocabulary-cycle/answer"
    first = client.post(path, headers=auth, json={"activity_index": 0, "student_response": "Rome"})
    assert first.status_code == 200
    assert first.json()["current_activity"]["activity_id"] == "b"
    assert "canonical_answer" not in first.json()["current_activity"]
    stale = client.post(path, headers=auth, json={"activity_index": 0, "student_response": "Rome"})
    assert stale.status_code == 409
    retried = client.post(path, headers=auth, json={"activity_index": 0, "student_response": "Ada",
                                                   "remediation_id": first.json()["remediation"]["id"]})
    assert retried.status_code == 200
    assert retried.json()["attempt"]["result"] == "correct"
