"""Persistência do ciclo lexical integrada ao Teaching Engine V2."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql

from app.core.errors import APIError
from app.core.teaching import EvidenceType, MemorySubjectType
from app.models import (
    Language,
    LearningAttempt,
    LearningEvidence,
    MemorySchedule,
    ReviewItem,
    User,
    UserLanguage,
    VocabularyExample,
    VocabularyItem,
)
from app.services import memory_engine, teaching_engine, vocabulary_learning


def _user_language(db_session) -> UserLanguage:
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    profile = UserLanguage(user_id=user.id, language_id=language.id, is_active=True)
    db_session.add(profile)
    db_session.commit()
    return profile


def _enroll(db_session, user_language_id: str) -> VocabularyItem:
    return vocabulary_learning.enroll_item(
        db_session,
        user_language_id=user_language_id,
        term="  Hello  ",
        translation_pt="Olá",
        examples=[
            {
                "example_text": "Hello, Ana!",
                "translation_pt": "Olá, Ana!",
                "audio_ref": "audio/example-hello.mp3",
            }
        ],
    )


def _correct_signal(db_session, profile, item, evidence_type):
    attempt = teaching_engine.record_attempt(
        db_session,
        user_language_id=profile.id,
        objective_id=None,
        vocabulary_item_id=item.id,
        activity_type=evidence_type,
    )
    return teaching_engine.evaluate_attempt(
        db_session,
        attempt,
        result="correct",
        evidence_type=evidence_type,
    )


def _master_item(db_session, profile, item):
    output = None
    for evidence_type in (
        EvidenceType.RECOGNITION,
        EvidenceType.REVERSE_RECOGNITION,
        EvidenceType.LISTENING_RECOGNITION,
        EvidenceType.LEXICAL_PRODUCTION,
    ):
        output = _correct_signal(db_session, profile, item, evidence_type)
    return output


def test_enrollment_is_idempotent_without_unique_constraint(db_session):
    profile = _user_language(db_session)

    first = _enroll(db_session, profile.id)
    second = _enroll(db_session, profile.id)
    db_session.flush()

    assert second.id == first.id
    assert first.term == "Hello"
    assert db_session.scalar(
        select(func.count(VocabularyItem.id)).where(
            VocabularyItem.user_language_id == profile.id
        )
    ) == 1
    assert db_session.scalar(
        select(func.count(VocabularyExample.id)).where(
            VocabularyExample.vocabulary_item_id == first.id
        )
    ) == 1


def test_standalone_lexical_attempt_requires_vocabulary_item(db_session):
    profile = _user_language(db_session)

    try:
        teaching_engine.record_attempt(
            db_session,
            user_language_id=profile.id,
            objective_id=None,
            activity_type="recognition",
        )
    except APIError as exc:
        assert exc.status_code == 422
        assert exc.code == "learning_subject_required"
    else:
        raise AssertionError("Tentativa standalone sem item lexical deveria falhar.")


def test_five_lexical_modalities_are_persisted_by_item(db_session):
    profile = _user_language(db_session)
    item = _enroll(db_session, profile.id)
    evidence_types = (
        EvidenceType.EXPOSURE,
        EvidenceType.RECOGNITION,
        EvidenceType.REVERSE_RECOGNITION,
        EvidenceType.LISTENING_RECOGNITION,
        EvidenceType.LEXICAL_PRODUCTION,
    )

    outputs = []
    for evidence_type in evidence_types:
        attempt = teaching_engine.record_attempt(
            db_session,
            user_language_id=profile.id,
            objective_id=None,
            vocabulary_item_id=item.id,
            activity_type=evidence_type,
            student_response="hello",
        )
        outputs.append(
            teaching_engine.evaluate_attempt(
                db_session,
                attempt,
                result="correct",
                evidence_type=evidence_type,
                provider="heuristic",
            )
        )

    attempts = list(
        db_session.scalars(
            select(LearningAttempt).where(
                LearningAttempt.vocabulary_item_id == item.id
            )
        )
    )
    evidences = list(
        db_session.scalars(
            select(LearningEvidence).where(
                LearningEvidence.vocabulary_item_id == item.id
            )
        )
    )
    assert len(attempts) == 5
    assert {row.evidence_type for row in evidences} == set(evidence_types)
    assert all(row.objective_id is None for row in attempts + evidences)
    assert outputs[-1]["mastery"] is None
    assert outputs[-1]["lexical_memory"]["state"] == "mastered"


def test_exposure_and_one_correct_answer_never_master_item(db_session):
    profile = _user_language(db_session)
    item = _enroll(db_session, profile.id)

    for evidence_type in (EvidenceType.EXPOSURE, EvidenceType.RECOGNITION):
        attempt = teaching_engine.record_attempt(
            db_session,
            user_language_id=profile.id,
            objective_id=None,
            vocabulary_item_id=item.id,
            activity_type=evidence_type,
        )
        output = teaching_engine.evaluate_attempt(
            db_session,
            attempt,
            result="correct",
            evidence_type=evidence_type,
        )

    schedule = db_session.scalar(
        select(MemorySchedule).where(
            MemorySchedule.user_language_id == profile.id,
            MemorySchedule.subject_type == MemorySubjectType.VOCABULARY,
            MemorySchedule.subject_key == item.id,
        )
    )
    assert schedule is not None
    assert output["lexical_memory"]["state"] != "mastered"
    assert schedule.payload_json["evidence_summary"]["evaluated_types"] == ["recognition"]
    assert schedule.payload_json["evidence_summary"]["mastered"] is False

    review = db_session.get(ReviewItem, schedule.review_item_id)
    assert review is not None
    assert review.mastery_state == schedule.state
    assert review.payload_json == schedule.payload_json


def test_attempt_may_carry_objective_and_vocabulary_item(db_session):
    from app.services.objective_seed import ensure_en_a1_can_001

    profile = _user_language(db_session)
    item = _enroll(db_session, profile.id)
    objective = ensure_en_a1_can_001(db_session)
    attempt = teaching_engine.record_attempt(
        db_session,
        user_language_id=profile.id,
        objective_id=objective.id,
        vocabulary_item_id=item.id,
        activity_type="guided_production",
        student_response="Hello!",
    )

    output = teaching_engine.evaluate_attempt(
        db_session,
        attempt,
        result="correct",
        evidence_type=EvidenceType.LEXICAL_PRODUCTION,
    )

    assert output["evidence"].objective_id == objective.id
    assert output["evidence"].vocabulary_item_id == item.id
    assert output["mastery"] is not None
    assert output["lexical_memory"] is not None


def test_incorrect_lexical_attempt_demotes_mastery_and_records_lapse(db_session):
    profile = _user_language(db_session)
    item = _enroll(db_session, profile.id)
    for evidence_type in (
        EvidenceType.RECOGNITION,
        EvidenceType.REVERSE_RECOGNITION,
        EvidenceType.LISTENING_RECOGNITION,
        EvidenceType.LEXICAL_PRODUCTION,
    ):
        attempt = teaching_engine.record_attempt(
            db_session,
            user_language_id=profile.id,
            objective_id=None,
            vocabulary_item_id=item.id,
            activity_type=evidence_type,
        )
        teaching_engine.evaluate_attempt(
            db_session,
            attempt,
            result="correct",
            evidence_type=evidence_type,
        )

    failed = teaching_engine.record_attempt(
        db_session,
        user_language_id=profile.id,
        objective_id=None,
        vocabulary_item_id=item.id,
        activity_type=EvidenceType.RECOGNITION,
        student_response="goodbye",
    )
    output = teaching_engine.evaluate_attempt(db_session, failed, result="incorrect")

    assert output["lexical_memory"]["state"] == "learning"
    schedule = db_session.get(
        MemorySchedule, output["lexical_memory"]["memory_schedule_id"]
    )
    assert schedule.lapse_count == 1
    assert schedule.payload_json["evidence_summary"]["incorrect_attempt_count"] == 1
    assert schedule.payload_json["evidence_summary"]["mastered"] is False


def test_out_of_order_evaluation_uses_attempt_just_evaluated_as_lapse(db_session):
    profile = _user_language(db_session)
    item = _enroll(db_session, profile.id)
    older_pending = teaching_engine.record_attempt(
        db_session,
        user_language_id=profile.id,
        objective_id=None,
        vocabulary_item_id=item.id,
        activity_type=EvidenceType.RECOGNITION,
    )
    mastered = _master_item(db_session, profile, item)
    assert mastered["lexical_memory"]["state"] == "mastered"

    output = teaching_engine.evaluate_attempt(
        db_session, older_pending, result="incorrect"
    )
    schedule = db_session.get(
        MemorySchedule, output["lexical_memory"]["memory_schedule_id"]
    )
    review = db_session.get(ReviewItem, schedule.review_item_id)

    assert output["lexical_memory"]["state"] == "learning"
    assert schedule.lapse_count == 1
    assert schedule.payload_json["evidence_summary"]["lapse_attempt_id"] == older_pending.id
    assert review.mastery_state == "learning"
    assert review.payload_json == schedule.payload_json
    assert review.interval_days == schedule.interval_days == 1
    assert review.next_review_at == schedule.due_at


def test_post_lapse_epoch_requires_four_new_correct_signals(db_session):
    profile = _user_language(db_session)
    item = _enroll(db_session, profile.id)
    _master_item(db_session, profile, item)
    failed = teaching_engine.record_attempt(
        db_session,
        user_language_id=profile.id,
        objective_id=None,
        vocabulary_item_id=item.id,
        activity_type=EvidenceType.RECOGNITION,
    )
    teaching_engine.evaluate_attempt(db_session, failed, result="incorrect")

    one_signal = _correct_signal(
        db_session, profile, item, EvidenceType.RECOGNITION
    )

    assert one_signal["lexical_memory"]["state"] != "mastered"
    summary = one_signal["lexical_memory"]["evidence_summary"]
    assert summary["evaluated_types"] == ["recognition"]
    assert summary["epoch"]["lapse_attempt_id"] == failed.id
    assert summary["mastered"] is False

    for evidence_type in (
        EvidenceType.REVERSE_RECOGNITION,
        EvidenceType.LISTENING_RECOGNITION,
        EvidenceType.LEXICAL_PRODUCTION,
    ):
        remastered = _correct_signal(db_session, profile, item, evidence_type)
    assert remastered["lexical_memory"]["state"] == "mastered"


def test_replaying_processed_lapse_preserves_remastered_state(db_session):
    profile = _user_language(db_session)
    item = _enroll(db_session, profile.id)
    _master_item(db_session, profile, item)
    failed = teaching_engine.record_attempt(
        db_session,
        user_language_id=profile.id,
        objective_id=None,
        vocabulary_item_id=item.id,
        activity_type=EvidenceType.RECOGNITION,
    )
    failed_result = teaching_engine.evaluate_attempt(
        db_session, failed, result="incorrect"
    )
    assert failed_result["lexical_memory"]["state"] == "learning"
    _master_item(db_session, profile, item)

    schedule = db_session.get(
        MemorySchedule, failed_result["lexical_memory"]["memory_schedule_id"]
    )
    review = db_session.get(ReviewItem, schedule.review_item_id)
    db_session.refresh(item)
    assert schedule.state == review.mastery_state == item.status == "mastered"
    before = {
        "schedule": (
            schedule.state,
            schedule.lapse_count,
            schedule.strength,
            schedule.interval_days,
            schedule.due_at,
            deepcopy(schedule.payload_json),
        ),
        "review": (
            review.mastery_state,
            review.interval_days,
            review.next_review_at,
            deepcopy(review.payload_json),
        ),
        "item": (
            item.status,
            item.interval_days,
            item.next_review_at,
        ),
    }

    replayed = memory_engine.update_vocabulary_memory(
        db_session, item=item, current_attempt=failed
    )
    db_session.refresh(review)
    db_session.refresh(item)
    after = {
        "schedule": (
            replayed.state,
            replayed.lapse_count,
            replayed.strength,
            replayed.interval_days,
            replayed.due_at,
            deepcopy(replayed.payload_json),
        ),
        "review": (
            review.mastery_state,
            review.interval_days,
            review.next_review_at,
            deepcopy(review.payload_json),
        ),
        "item": (
            item.status,
            item.interval_days,
            item.next_review_at,
        ),
    }

    assert after == before


def test_partial_lexical_evidence_never_counts_toward_mastery(db_session):
    profile = _user_language(db_session)
    item = _enroll(db_session, profile.id)

    for evidence_type in (
        EvidenceType.RECOGNITION,
        EvidenceType.REVERSE_RECOGNITION,
        EvidenceType.LISTENING_RECOGNITION,
        EvidenceType.LEXICAL_PRODUCTION,
    ):
        attempt = teaching_engine.record_attempt(
            db_session,
            user_language_id=profile.id,
            objective_id=None,
            vocabulary_item_id=item.id,
            activity_type=evidence_type,
        )
        output = teaching_engine.evaluate_attempt(
            db_session,
            attempt,
            result="partial",
            evidence_type=evidence_type,
        )

    assert output["lexical_memory"]["state"] != "mastered"
    assert output["lexical_memory"]["evidence_summary"]["evaluated_types"] == []


def test_enrollment_lock_compiles_to_postgresql_for_update():
    statement = vocabulary_learning._user_language_lock_statement("profile-id")
    compiled = str(
        statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert "FOR UPDATE" in compiled
    assert "user_languages.id = 'profile-id'" in compiled


def test_enrollment_reuses_legacy_term_with_external_spaces(db_session):
    profile = _user_language(db_session)
    legacy = VocabularyItem(
        user_language_id=profile.id,
        term=" Hello ",
        translation_pt="Olá",
    )
    db_session.add(legacy)
    db_session.flush()

    enrolled = vocabulary_learning.enroll_item(
        db_session,
        user_language_id=profile.id,
        term="Hello",
        translation_pt="Olá",
    )

    assert enrolled.id == legacy.id
    assert db_session.scalar(select(func.count(VocabularyItem.id))) == 1


def test_enrollment_preserves_internal_term_spaces(db_session):
    profile = _user_language(db_session)
    item = vocabulary_learning.enroll_item(
        db_session,
        user_language_id=profile.id,
        term="  New   York  ",
        translation_pt="Nova York",
    )
    distinct = vocabulary_learning.enroll_item(
        db_session,
        user_language_id=profile.id,
        term="New York",
        translation_pt="Nova York",
    )

    assert item.term == "New   York"
    assert distinct.id != item.id


def test_downgrade_rejects_standalone_rows_before_not_null(db_session):
    profile = _user_language(db_session)
    item = _enroll(db_session, profile.id)
    teaching_engine.record_attempt(
        db_session,
        user_language_id=profile.id,
        objective_id=None,
        vocabulary_item_id=item.id,
        activity_type=EvidenceType.RECOGNITION,
    )
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0013_vocabulary_learning_cycle.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0013", migration_path)
    migration = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(migration)

    with pytest.raises(RuntimeError, match="standalone.*objective_id NULL"):
        migration._assert_no_standalone_learning_rows(db_session.connection())
