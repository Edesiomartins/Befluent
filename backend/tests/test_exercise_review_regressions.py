"""Recovery must remain possible without reviving resolved deferrals."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models import LearningAttempt, TeachingFlowSession
from app.services import activity_pool, session_engine, vocabulary_learning
from test_family_exclusion import _owner


def _attempt(db, owner, word, result, modality, at):
    attempt = LearningAttempt(
        user_language_id=owner.id, vocabulary_item_id=word.id,
        activity_type=modality, result=result, evaluated_at=at,
    )
    db.add(attempt)
    db.flush()
    return attempt


def _deferred_session(db, owner, word, attempt):
    session = TeachingFlowSession(
        user_language_id=owner.id, status="closed",
        payload_json={"deferred_vocabulary_items": [{
            "vocabulary_item_id": word.id, "activity_type": attempt.activity_type,
            "attempt_id": attempt.id,
        }]},
    )
    db.add(session)
    db.flush()
    return session


def test_expired_error_allows_the_only_missing_modality(db_session):
    owner = _owner(db_session)
    word = vocabulary_learning.enroll_item(
        db_session, user_language_id=owner.id, term="apple", translation_pt="maçã"
    )
    now = datetime.now(timezone.utc)
    _attempt(db_session, owner, word, "incorrect", "recognition", now - timedelta(days=8))
    errors = session_engine.last_incorrect_activity_types(db_session, owner.id, [word.id])
    modalities = session_engine.modalities_for_item(
        {"reverse_recognition", "listening_recognition", "lexical_production"},
        available_types={"recognition", "reverse_recognition", "listening_recognition", "lexical_production"},
        last_incorrect_type=errors.get(word.id),
    )
    assert modalities == ["recognition"]


def test_correct_answer_clears_the_recent_modality_block(db_session):
    owner = _owner(db_session)
    word = vocabulary_learning.enroll_item(
        db_session, user_language_id=owner.id, term="apple", translation_pt="maçã"
    )
    now = datetime.now(timezone.utc)
    _attempt(db_session, owner, word, "incorrect", "recognition", now - timedelta(hours=2))
    _attempt(db_session, owner, word, "correct", "reverse_recognition", now - timedelta(hours=1))
    assert session_engine.last_incorrect_activity_types(db_session, owner.id, [word.id]) == {}


def test_partial_answer_does_not_clear_recent_error(db_session):
    owner = _owner(db_session)
    word = vocabulary_learning.enroll_item(
        db_session, user_language_id=owner.id, term="apple", translation_pt="maçã"
    )
    now = datetime.now(timezone.utc)
    _attempt(db_session, owner, word, "incorrect", "recognition", now - timedelta(hours=2))
    _attempt(db_session, owner, word, "partial", "reverse_recognition", now - timedelta(hours=1))
    assert session_engine.last_incorrect_activity_types(db_session, owner.id, [word.id]) == {word.id: "recognition"}


@pytest.mark.parametrize("age_days,blocked", [(6, True), (7, False), (8, False)])
def test_modality_cooldown_boundary(db_session, age_days, blocked):
    owner = _owner(db_session)
    word = vocabulary_learning.enroll_item(
        db_session, user_language_id=owner.id, term="apple", translation_pt="maçã"
    )
    now = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)
    _attempt(db_session, owner, word, "incorrect", "recognition", now - timedelta(days=age_days))
    errors = session_engine.last_incorrect_activity_types(db_session, owner.id, [word.id], now=now)
    assert (word.id in errors) is blocked


def test_resolved_deferral_is_not_resurrected_from_old_session(db_session):
    owner = _owner(db_session)
    word = vocabulary_learning.enroll_item(
        db_session, user_language_id=owner.id, term="apple", translation_pt="maçã"
    )
    now = datetime.now(timezone.utc)
    failed = _attempt(db_session, owner, word, "incorrect", "recognition", now - timedelta(hours=2))
    old = _deferred_session(db_session, owner, word, failed)
    _attempt(db_session, owner, word, "correct", "reverse_recognition", now - timedelta(hours=1))
    before = dict(old.payload_json)
    assert session_engine.load_deferred_vocabulary_items(db_session, owner.id) == []
    assert old.payload_json == before  # Historical snapshot stays intact.


def test_relapse_uses_latest_error_despite_old_session_order(db_session):
    owner = _owner(db_session)
    word = vocabulary_learning.enroll_item(
        db_session, user_language_id=owner.id, term="apple", translation_pt="maçã"
    )
    now = datetime.now(timezone.utc)
    old = _attempt(db_session, owner, word, "incorrect", "recognition", now - timedelta(days=2))
    _attempt(db_session, owner, word, "correct", "reverse_recognition", now - timedelta(days=1))
    latest = _attempt(db_session, owner, word, "incorrect", "listening_recognition", now)
    _deferred_session(db_session, owner, word, latest)
    _deferred_session(db_session, owner, word, old)
    entries = session_engine.load_deferred_vocabulary_items(db_session, owner.id)
    assert entries == [{"vocabulary_item_id": word.id, "activity_type": "listening_recognition", "attempt_id": latest.id}]


def _grammar(prompt, *, objective="be-present", **extra):
    return {
        "type": "fill_gap", "prompt": prompt, "canonical_answer": "is",
        "learning_objective_id": objective, "target_language": "en",
        "native_language": "pt-BR", "cefr_level": "A1", **extra,
    }


def test_short_equal_answers_do_not_retire_unrelated_questions():
    first = _grammar("The station ___ near the river.")
    other = _grammar("Her sister ___ a doctor.")
    payload = {}
    activity_pool.retire_family(payload, first)
    assert not activity_pool.family_retired(other, payload)


def test_same_model_across_modalities_stays_in_one_family():
    gap = _grammar("The station ___ near the river.", pattern_key="station-near-river")
    order = _grammar(
        "Put the words in order.", type="word_order",
        canonical_answer="The station is near the river.", pattern_key="station-near-river",
    )
    assert activity_pool.family_key(gap) == activity_pool.family_key(order)


def test_same_answer_in_different_objectives_is_not_one_family():
    first = _grammar("She ___ here.", objective="present")
    other = _grammar("She ___ here.", objective="passive")
    assert activity_pool.family_key(first) != activity_pool.family_key(other)


def test_legacy_broad_history_is_recomputed_from_snapshot(db_session):
    owner = _owner(db_session)
    first = _grammar("The station ___ near the river.")
    other = _grammar("Her sister ___ a doctor.")
    now = datetime.now(timezone.utc)
    db_session.add(TeachingFlowSession(
        user_language_id=owner.id, status="closed", payload_json={"activity_exposures": {
            activity_pool.activity_id(first): {
                "at": now.isoformat(), "family_key": "pattern:is", "activity": first,
                "fingerprint": activity_pool.fingerprint(first),
            },
        }},
    ))
    db_session.flush()
    history = activity_pool.exposure_history(db_session, owner.id)
    assert activity_pool.recently_exposed(first, history)
    assert not activity_pool.recently_exposed(other, history)


def test_legacy_retirement_uses_snapshot_instead_of_broad_answer():
    first = _grammar("The station ___ near the river.")
    other = _grammar("Her sister ___ a doctor.")
    payload = {"retired_families": ["pattern:is"], "activity_exposures": {
        activity_pool.activity_id(first): {"activity": first},
    }}
    assert activity_pool.family_retired(first, payload)
    assert not activity_pool.family_retired(other, payload)


def test_empty_activity_has_a_stable_fallback_family():
    assert activity_pool.family_key({}) == "id:" + activity_pool.activity_id({})


def test_generated_sibling_modalities_share_an_opaque_pattern_key(db_session):
    from app.services.activity_generator import generate_activities
    from app.services.objective_seed import ensure_en_a1_can_001

    activities = generate_activities(ensure_en_a1_can_001(db_session))
    siblings = [activity for activity in activities if activity["type"] in {"fill_gap", "word_order", "multiple_choice"}]
    assert {activity["type"] for activity in siblings} == {"fill_gap", "word_order", "multiple_choice"}
    assert len({activity_pool.family_key(activity) for activity in siblings}) == 1
    assert all(len(activity["pattern_key"]) == 64 for activity in siblings)


def test_answer_without_prompt_does_not_group_distinct_activities():
    first = {"activity_id": "a", "type": "multiple_choice", "canonical_answer": "is"}
    other = {**first, "activity_id": "b"}
    assert activity_pool.family_key(first) != activity_pool.family_key(other)


@pytest.mark.parametrize("old_type", ["fill_gap", "word_order", "multiple_choice"])
def test_legacy_generated_model_still_blocks_fresh_siblings(db_session, old_type):
    from app.services.activity_generator import generate_activities
    from app.services.objective_seed import ensure_en_a1_can_001

    owner = _owner(db_session)
    objective = ensure_en_a1_can_001(db_session)
    activities = generate_activities(objective)
    for activity in activities:
        activity["learning_objective_id"] = objective.id
    old = dict(next(a for a in activities if a["type"] == old_type))
    old.pop("pattern_key")
    fresh = next(a for a in activities if a["type"] == ("word_order" if old_type == "multiple_choice" else "multiple_choice"))
    legacy_key = "pattern:" + activity_pool.normalize_question_text(old["canonical_answer"])
    payload = {"retired_families": [legacy_key], "activity_exposures": {
        activity_pool.activity_id(old): {
            "activity": old, "family_key": legacy_key,
            "fingerprint": activity_pool.fingerprint(old),
            "at": datetime.now(timezone.utc).isoformat(),
        },
    }}
    db_session.add(TeachingFlowSession(user_language_id=owner.id, status="closed", payload_json=payload))
    db_session.flush()
    assert activity_pool.family_retired(fresh, payload)
    assert activity_pool.recently_exposed(fresh, activity_pool.exposure_history(db_session, owner.id))
