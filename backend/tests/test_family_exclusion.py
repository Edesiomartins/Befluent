"""Família aposentada na sessão e histórico recente fora da sessão seguinte."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.teaching import FlowPhase
from app.models import Language, TeachingFlowSession, User, UserLanguage
from app.services import activity_pool, memory_engine, teaching_engine, teaching_flow, teaching_slice
from app.services.objective_seed import ensure_en_a1_can_001
from app.services.session_engine import (
    _candidate,
    load_deferred_vocabulary_items,
    load_session_candidates,
    plan_session,
)
from app.services import vocabulary_learning

from test_activity_pool import item


def _owner(db):
    user = db.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db.scalar(select(Language).where(Language.code == "en"))
    owner = UserLanguage(user_id=user.id, language_id=language.id, is_active=True)
    db.add(owner)
    db.flush()
    return owner


def test_retry_does_not_repeat_family_in_the_same_session(db_session):
    owner = _owner(db_session)
    objective = ensure_en_a1_can_001(db_session)
    first = item("a", "First situation")
    sibling = item("sibling", "Second situation with the same model")
    other = item(
        "other",
        "A different model",
        canonical_answer="Rio",
        options=["Rio", "Lisbon"],
    )
    flow = TeachingFlowSession(
        user_language_id=owner.id,
        objective_id=objective.id,
        phase=FlowPhase.PRACTICING,
        status="active",
        payload_json={"activities": [first, sibling, other]},
    )
    db_session.add(flow)
    db_session.commit()

    response = teaching_slice.submit_slice_answer(
        db_session, flow, student_response="Rome", activity_index=0
    )
    assert response["attempt"]["result"] == "incorrect"
    current = response["current_activity"]
    assert current["activity_id"] == "a"
    assert current["prompt"] == first["prompt"]
    assert activity_pool.family_key(first) in flow.payload_json["retired_families"]
    assert activity_pool.family_key(first) == activity_pool.family_key(sibling)

    retried = teaching_slice.retry_slice(
        db_session,
        flow,
        remediation_id=response["remediation"]["id"],
        student_response="Ada",
    )
    assert retried["attempt"]["result"] == "correct"
    assert teaching_flow.current_activity(flow)["activity_id"] == "other"
    assert flow.activity_cursor == 2


def test_lexical_error_skips_the_same_word_later_in_the_queue(db_session):
    owner = _owner(db_session)
    apple = vocabulary_learning.enroll_item(
        db_session, user_language_id=owner.id, term="apple", translation_pt="maçã"
    )
    bread = vocabulary_learning.enroll_item(
        db_session, user_language_id=owner.id, term="bread", translation_pt="pão"
    )
    failed = {
        "activity_id": "apple-recognition",
        "type": "recognition",
        "vocabulary_item_id": apple.id,
        "phase_hint": "practicing",
        "prompt": "O que significa apple?",
        "options": ["maçã", "pão"],
        "canonical_answer": "maçã",
        "ai_required": False,
    }
    same_word = {
        **failed,
        "activity_id": "apple-listening",
        "type": "listening_recognition",
        "prompt": "Ouça e escolha apple.",
    }
    other_word = {
        **failed,
        "activity_id": "bread-recognition",
        "vocabulary_item_id": bread.id,
        "prompt": "O que significa bread?",
        "canonical_answer": "pão",
        "options": ["pão", "maçã"],
    }
    flow = TeachingFlowSession(
        user_language_id=owner.id,
        phase=FlowPhase.PRACTICING,
        status="active",
        payload_json={
            "activities": [failed, same_word, other_word],
            "lexical_cycle": True,
        },
    )
    db_session.add(flow)
    db_session.commit()

    response = teaching_slice.submit_slice_answer(
        db_session, flow, student_response="pão", activity_index=0
    )
    assert response["attempt"]["result"] == "incorrect"
    assert response["remediation"] is None
    assert teaching_flow.current_activity(flow)["activity_id"] == "bread-recognition"
    assert f"vocab:{apple.id}" in flow.payload_json["retired_families"]
    deferred = flow.payload_json["deferred_vocabulary_items"]
    assert deferred[0]["vocabulary_item_id"] == apple.id
    assert deferred[0]["activity_type"] == "recognition"


def test_recent_family_is_excluded_from_the_next_session(db_session):
    owner = _owner(db_session)
    now = datetime.now(timezone.utc)
    seen = item("seen", "Already practiced")
    sibling = item("sibling", "Same model, different wording")
    fresh = item("fresh", "A new model", canonical_answer="Rio", options=["Rio", "Lisbon"])
    payload = {"activities": [seen]}
    activity_pool.record_exposure(payload, seen, now=now)
    flow = TeachingFlowSession(
        user_language_id=owner.id,
        status="closed",
        payload_json=payload,
    )
    db_session.add(flow)
    db_session.commit()

    history = activity_pool.exposure_history(db_session, owner.id)
    chosen = activity_pool.select_activity(
        [seen, sibling, fresh],
        objective_id="objective-x",
        exposure_history=history,
        now=now,
    )
    assert chosen["activity_id"] == "fresh"

    blocked = plan_session(
        [_candidate(seen, priority=0), _candidate(sibling, priority=0), _candidate(fresh, priority=1)],
        exposure_history=history,
    )
    assert [activity["activity_id"] for activity in blocked["activities"]] == ["fresh"]

    word_seen = {
        "activity_id": "seen-word",
        "type": "recognition",
        "vocabulary_item_id": "word-1",
        "prompt": "O que significa apple?",
        "canonical_answer": "maçã",
        "options": ["maçã", "pão"],
    }
    word_other = {
        **word_seen,
        "activity_id": "other-modality",
        "type": "listening_recognition",
        "prompt": "Ouça apple.",
    }
    word_history = {
        "seen-word": now.isoformat(),
        "vocab:word-1": now.isoformat(),
    }
    repeated = plan_session(
        [
            _candidate(word_seen, priority=0, item_key="word-1"),
            _candidate(word_other, priority=0, item_key="word-1"),
            _candidate(fresh, priority=1),
        ],
        exposure_history=word_history,
    )
    assert [activity["activity_id"] for activity in repeated["activities"]] == ["fresh"]
    deferred_plan = plan_session(
        [
            _candidate(word_seen, priority=0, item_key="word-1"),
            _candidate(word_other, priority=0, item_key="word-1"),
            _candidate(fresh, priority=1),
        ],
        exposure_history=word_history,
        deferred_item_ids={"word-1"},
    )
    deferred_ids = [activity["activity_id"] for activity in deferred_plan["activities"]]
    assert "seen-word" not in deferred_ids
    assert "other-modality" in deferred_ids
    assert "fresh" in deferred_ids


def test_incorrect_vocabulary_is_deferred_for_another_modality(db_session):
    owner = _owner(db_session)
    apple = vocabulary_learning.enroll_item(
        db_session,
        user_language_id=owner.id,
        term="apple",
        translation_pt="maçã",
        examples=[{"example_text": "I eat an apple.", "translation_pt": "Eu como uma maçã."}],
    )
    vocabulary_learning.enroll_item(
        db_session,
        user_language_id=owner.id,
        term="bread",
        translation_pt="pão",
        examples=[{"example_text": "I buy bread.", "translation_pt": "Eu compro pão."}],
    )
    schedule = memory_engine.get_or_create_schedule(
        db_session,
        user_language_id=owner.id,
        subject_type="vocabulary",
        subject_key=apple.id,
    )
    future = datetime.now(timezone.utc) + timedelta(days=5)
    schedule.due_at = future
    db_session.flush()

    failed = teaching_engine.record_attempt(
        db_session,
        user_language_id=owner.id,
        objective_id=None,
        vocabulary_item_id=apple.id,
        activity_type="recognition",
        student_response="pão",
    )
    teaching_engine.evaluate_attempt(db_session, failed, result="incorrect")
    db_session.refresh(schedule)

    stored_due = schedule.due_at
    if stored_due.tzinfo is None:
        stored_due = stored_due.replace(tzinfo=timezone.utc)
    assert stored_due > datetime.now(timezone.utc) + timedelta(days=4)
    assert schedule.lapse_count == 1
    deferred = schedule.payload_json["deferred_vocabulary_items"]
    assert deferred[0]["vocabulary_item_id"] == apple.id
    assert deferred[0]["activity_type"] == "recognition"
    assert load_deferred_vocabulary_items(db_session, owner.id)[0]["vocabulary_item_id"] == apple.id

    candidates = load_session_candidates(
        db_session,
        user_language_id=owner.id,
        lesson_items=[apple],
        language_code="en",
        level="A1",
    )
    apple_types = [
        candidate["activity"]["type"]
        for candidate in candidates
        if candidate.get("item_key") == apple.id
    ]
    assert apple_types
    assert "recognition" not in apple_types
