"""Persistência do ciclo lexical integrada ao Teaching Engine V2."""

from __future__ import annotations

from sqlalchemy import func, select

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
from app.services import teaching_engine, vocabulary_learning


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
