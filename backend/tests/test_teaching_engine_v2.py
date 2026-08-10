"""Teaching Engine V2 — flow, activity generator, memória, intelligibility, slice."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
from sqlalchemy import select

from app.core.teaching import (
    ActivityType,
    EvidenceType,
    FlowPhase,
    MasteryState,
    MemorySubjectType,
    is_valid_flow_transition,
)
from app.models import Language, LearningObjective, MemoryReviewEvent, User, UserLanguage
from app.services import (
    activity_generator,
    ai_cache,
    deterministic_evaluator,
    memory_engine,
    provider_resilience,
    speech_intelligibility,
    teaching_engine as engine,
    teaching_flow,
    teaching_slice,
)
from app.services.objective_seed import ensure_en_a1_can_001


def _ul(db_session, email: str = "admin@befluent.local") -> UserLanguage:
    user = db_session.scalar(select(User).where(User.email == email))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    existing = db_session.scalar(
        select(UserLanguage).where(
            UserLanguage.user_id == user.id, UserLanguage.language_id == language.id
        )
    )
    if existing:
        return existing
    ul = UserLanguage(user_id=user.id, language_id=language.id, is_active=True)
    db_session.add(ul)
    db_session.commit()
    return ul


# 1. objective carregado


def test_en_a1_can_001_seeded(db_session):
    objective = ensure_en_a1_can_001(db_session)
    db_session.commit()
    assert objective.code == "EN-A1-CAN-001"
    assert "apresentar" in objective.can_do.lower() or "Apresentar" in objective.title
    assert objective.target_expressions_json
    assert objective.pedagogy_json.get("transfer_prompts")


# 2–3. teaching flow


def test_flow_starts_activating(db_session):
    objective = ensure_en_a1_can_001(db_session)
    ul = _ul(db_session)
    session = teaching_flow.start_flow(
        db_session, user_language_id=ul.id, objective_id=objective.id
    )
    assert session.phase == FlowPhase.ACTIVATING
    assert session.payload_json.get("activities")


def test_invalid_flow_transition_rejected(db_session):
    objective = ensure_en_a1_can_001(db_session)
    ul = _ul(db_session)
    session = teaching_flow.start_flow(
        db_session, user_language_id=ul.id, objective_id=objective.id
    )
    with pytest.raises(Exception) as exc:
        teaching_flow.transition(db_session, session, target_phase=FlowPhase.MASTERED)
    assert "invalid_flow_transition" in str(exc.value).lower() or exc.value.status_code == 409


def test_valid_flow_transitions_table():
    assert is_valid_flow_transition(FlowPhase.PRACTICING, FlowPhase.NEEDS_REMEDIATION)
    assert not is_valid_flow_transition(FlowPhase.NOT_STARTED, FlowPhase.MASTERED)


# 4–9. attempt/evidence/error/remediation via slice


def test_slice_correct_answer_creates_evidence(db_session):
    ul = _ul(db_session)
    started = teaching_slice.start_slice(db_session, user_language_id=ul.id)
    flow_id = started["flow"]["id"]
    session = teaching_flow.get_flow(db_session, flow_id)
    # ack activating
    teaching_slice.submit_slice_answer(db_session, session, student_response="")
    session = teaching_flow.get_flow(db_session, flow_id)
    teaching_slice.submit_slice_answer(db_session, session, student_response="")
    session = teaching_flow.get_flow(db_session, flow_id)
    teaching_slice.submit_slice_answer(db_session, session, student_response="")
    session = teaching_flow.get_flow(db_session, flow_id)
    # fill_gap / practice
    activity = teaching_flow.current_activity(session)
    assert activity is not None
    answer = activity.get("canonical_answer") or (activity.get("accepted_variants") or ["Ana"])[0]
    # se ainda for recognition, avança até fill_gap
    guard = 0
    while activity and activity.get("type") not in {
        ActivityType.FILL_GAP,
        ActivityType.WORD_ORDER,
        ActivityType.MULTIPLE_CHOICE,
    } and guard < 6:
        teaching_slice.submit_slice_answer(db_session, session, student_response="")
        session = teaching_flow.get_flow(db_session, flow_id)
        activity = teaching_flow.current_activity(session)
        guard += 1
    assert activity is not None
    if activity.get("type") == ActivityType.MULTIPLE_CHOICE:
        answer = activity["canonical_answer"]
    elif activity.get("type") == ActivityType.WORD_ORDER:
        answer = " ".join(activity["tokens"])
    else:
        answer = activity.get("canonical_answer")
    out = teaching_slice.submit_slice_answer(db_session, session, student_response=answer)
    assert out["ai_called"] is False
    assert out["attempt"]["result"] == "correct"
    assert out["evaluation"]["ai_called"] is False


def test_slice_error_remediation_retry(db_session):
    ul = _ul(db_session)
    started = teaching_slice.start_slice(db_session, user_language_id=ul.id)
    session = teaching_flow.get_flow(db_session, started["flow"]["id"])
    for _ in range(3):
        teaching_slice.submit_slice_answer(db_session, session, student_response="")
        session = teaching_flow.get_flow(db_session, session.id)
    activity = teaching_flow.current_activity(session)
    guard = 0
    while activity and activity.get("type") not in {
        ActivityType.FILL_GAP,
        ActivityType.WORD_ORDER,
        ActivityType.MULTIPLE_CHOICE,
    } and guard < 6:
        teaching_slice.submit_slice_answer(db_session, session, student_response="")
        session = teaching_flow.get_flow(db_session, session.id)
        activity = teaching_flow.current_activity(session)
        guard += 1
    wrong = teaching_slice.submit_slice_answer(
        db_session, session, student_response="zzzz totally wrong"
    )
    assert wrong["remediation"] is not None
    assert session.phase == FlowPhase.NEEDS_REMEDIATION
    # Retry usa variante pós-revelação (current_activity), não a questão original.
    retry_activity = teaching_flow.current_activity(session) or {}
    if retry_activity.get("type") == ActivityType.WORD_ORDER:
        correct = " ".join(retry_activity.get("tokens") or [])
    else:
        correct = (
            retry_activity.get("canonical_answer")
            or (retry_activity.get("accepted_variants") or ["ok"])[0]
        )
    retried = teaching_slice.retry_slice(
        db_session,
        session,
        remediation_id=wrong["remediation"]["id"],
        student_response=correct,
    )
    assert retried["attempt"]["result"] == "correct"
    assert retried["ai_called"] is False


# 10. completion ≠ mastery


def test_activity_completed_flag_does_not_equal_mastery(db_session):
    objective = ensure_en_a1_can_001(db_session)
    ul = _ul(db_session)
    mastery = engine.evaluate_mastery(
        db_session,
        user_language_id=ul.id,
        objective_id=objective.id,
        activity_completed=True,
    )
    assert mastery["state"] != MasteryState.MASTERED


# 11–12. transfer required by policy


def test_transfer_required_blocks_mastery_without_transfer(db_session):
    objective = ensure_en_a1_can_001(db_session)
    ul = _ul(db_session)
    attempt = engine.record_attempt(
        db_session,
        user_language_id=ul.id,
        objective_id=objective.id,
        activity_type="guided_production",
        student_response="My name is Ana. I'm from Brazil. I live in Goiânia. I like coffee.",
    )
    engine.evaluate_attempt(
        db_session,
        attempt,
        result="correct",
        evidence_type=EvidenceType.CORRECT_RESPONSE,
    )
    attempt2 = engine.record_attempt(
        db_session,
        user_language_id=ul.id,
        objective_id=objective.id,
        activity_type="guided_production",
        student_response="My name is Ana.",
    )
    engine.evaluate_attempt(
        db_session,
        attempt2,
        result="correct",
        evidence_type=EvidenceType.WRITTEN_PRODUCTION,
    )
    mastery = engine.evaluate_mastery(
        db_session, user_language_id=ul.id, objective_id=objective.id
    )
    assert mastery["state"] != MasteryState.MASTERED


def test_transfer_evidence_can_reach_mastery(db_session):
    objective = ensure_en_a1_can_001(db_session)
    ul = _ul(db_session)
    a1 = engine.record_attempt(
        db_session, user_language_id=ul.id, objective_id=objective.id, activity_type="practice"
    )
    engine.evaluate_attempt(
        db_session, a1, result="correct", evidence_type=EvidenceType.CORRECT_RESPONSE
    )
    a2 = engine.record_attempt(
        db_session, user_language_id=ul.id, objective_id=objective.id, activity_type="transfer"
    )
    out = engine.evaluate_attempt(
        db_session,
        a2,
        result="correct",
        evidence_type=EvidenceType.TRANSFER,
        is_transfer=True,
    )
    assert out["mastery"]["state"] == MasteryState.MASTERED
    assert out["mastery"].get("memory_schedule_id")


# 13–15. memory + review event


def test_learner_error_enters_memory_and_review_event(db_session):
    objective = ensure_en_a1_can_001(db_session)
    ul = _ul(db_session)
    attempt = engine.record_attempt(
        db_session, user_language_id=ul.id, objective_id=objective.id, activity_type="practice"
    )
    engine.evaluate_attempt(db_session, attempt, result="incorrect")
    error = engine.record_error(
        db_session,
        attempt,
        category="grammar",
        original="I live here since 20 years.",
        expected="I have lived here for 20 years.",
        language_feature="duration_present_perfect_since_for",
        severity="critical",
    )
    rem = engine.choose_remediation(db_session, error, escalate=True)
    retry = engine.record_retry(db_session, rem, student_response="I have lived here for 20 years.")
    engine.evaluate_attempt(
        db_session, retry, result="correct", evidence_type=EvidenceType.ERROR_REPAIRED
    )
    due = memory_engine.list_due(db_session, user_language_id=ul.id)
    assert any(item.subject_type == MemorySubjectType.LEARNER_ERROR for item in due)
    schedule = next(item for item in due if item.subject_type == MemorySubjectType.LEARNER_ERROR)
    event = memory_engine.record_review(db_session, schedule, rating="good")
    assert isinstance(event, MemoryReviewEvent)
    assert event.due_after is not None


# 16–18. accepted variants + generator + no AI


def test_accepted_variants_deterministic():
    result = deterministic_evaluator.evaluate_response(
        student_response="I'm a professor.",
        canonical_answer="I work as a professor.",
        accepted_variants=["I'm a professor.", "I am a professor."],
    )
    assert result["result"] == "correct"
    assert result["ai_called"] is False


def test_activity_generator_produces_valid_activities(db_session):
    objective = ensure_en_a1_can_001(db_session)
    activities = activity_generator.generate_activities(objective)
    assert len(activities) >= 5
    types = {a["type"] for a in activities}
    assert ActivityType.TRANSFER_QUESTION in types
    assert all(a.get("ai_required") is False for a in activities)


# 19–20. AI cache


def test_ai_cache_hit_avoids_recompute(db_session):
    key = ai_cache.build_cache_key(
        capability="example_generation",
        language_code="en",
        level="A1",
        objective_code="EN-A1-CAN-001",
        input_payload={"topic": "presentations"},
    )
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return {"examples": ["My name is Ana."], "provider": "test"}

    first, hit1 = ai_cache.cached_or_compute(
        db_session, cache_key=key, capability="example_generation", compute=compute
    )
    second, hit2 = ai_cache.cached_or_compute(
        db_session, cache_key=key, capability="example_generation", compute=compute
    )
    assert hit1 is False
    assert hit2 is True
    assert calls["n"] == 1
    assert first["examples"] == second["examples"]


def test_personal_content_not_marked_cacheable():
    assert ai_cache.is_personal_content({"student_response": "hi"}) is True
    assert ai_cache.is_personal_content({"topic": "greetings"}) is False


# 21–22. intelligibility


def test_transcript_alignment_finds_missed_tokens():
    out = speech_intelligibility.assess_intelligibility(
        target_text="I would like to book a table for two",
        transcript="I would like book a table for two",
        provider="groq",
    )
    assert "to" in out["intelligibility"]["missed_tokens"]
    assert out["is_phonetic_score"] is False
    assert "pronunciation_score" not in out
    assert out["intelligibility"]["metric_name"] == "speech_correspondence"


# 23–27. providers / resilience


def test_401_does_not_infinite_retry():
    provider_resilience.reset_circuits()
    calls = {"n": 0}

    def boom():
        calls["n"] += 1
        request = httpx.Request("POST", "https://example.test")
        response = httpx.Response(401, request=request)
        raise httpx.HTTPStatusError("auth", request=request, response=response)

    result = provider_resilience.call_with_policy(
        provider_name="test-401", operation=boom, max_retries=5
    )
    assert result.ok is False
    assert calls["n"] == 1


def test_429_respects_retry_after():
    provider_resilience.reset_circuits()
    calls = {"n": 0}

    def limited():
        calls["n"] += 1
        if calls["n"] == 1:
            request = httpx.Request("POST", "https://example.test")
            response = httpx.Response(
                429, headers={"Retry-After": "0"}, request=request
            )
            raise httpx.HTTPStatusError("rate", request=request, response=response)
        return {"ok": True}

    result = provider_resilience.call_with_policy(
        provider_name="test-429", operation=limited, max_retries=2, base_backoff=0.01
    )
    assert result.ok is True
    assert result.rate_limited is False or calls["n"] >= 2


def test_fallback_still_used_on_primary_failure():
    provider_resilience.reset_circuits()

    def fail():
        raise RuntimeError("primary down")

    result = provider_resilience.call_with_policy(
        provider_name="test-fallback",
        operation=fail,
        max_retries=0,
        on_fallback=lambda: {"via": "fallback"},
    )
    assert result.ok is True
    assert result.fallback_used is True
    assert result.value == {"via": "fallback"}


# 28–29. API ownership + old endpoints


def test_slice_api_and_old_reviews(client, auth, db_session):
    _ul(db_session)
    start = client.post("/api/v1/teaching/slice/en-a1-can-001/start", json={}, headers=auth)
    assert start.status_code == 200
    body = start.json()
    assert body["objective"]["code"] == "EN-A1-CAN-001"
    assert body["flow"]["phase"] == FlowPhase.ACTIVATING
    assert client.get("/api/v1/reviews/due", headers=auth).status_code == 200


def test_users_cannot_access_other_flow(client, auth, db_session, other_user):
    outro = db_session.get(User, other_user)
    ul = _ul(db_session, email=outro.email)
    started = teaching_slice.start_slice(db_session, user_language_id=ul.id)
    db_session.commit()
    resp = client.get(f"/api/v1/teaching/flows/{started['flow']['id']}", headers=auth)
    assert resp.status_code == 404


def test_intelligibility_api_has_no_phonetic_score(client, auth):
    resp = client.post(
        "/api/v1/teaching/intelligibility",
        json={
            "target_text": "I live in Goiânia",
            "transcript": "I live Goiânia",
            "provider": "groq",
        },
        headers=auth,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_phonetic_score"] is False
    assert "pronunciation_score" not in data


def test_invalid_transition_api(client, auth, db_session):
    _ul(db_session)
    start = client.post("/api/v1/teaching/slice/en-a1-can-001/start", json={}, headers=auth)
    flow_id = start.json()["flow"]["id"]
    resp = client.post(
        f"/api/v1/teaching/flows/{flow_id}/transition",
        json={"target_phase": "mastered"},
        headers=auth,
    )
    assert resp.status_code == 409
