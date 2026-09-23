"""Gerador determinístico e adaptação lexical do Teaching Engine V2."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.errors import APIError
from app.core.teaching import ActivityType, EvidenceType, MemorySubjectType
from app.models import (
    Language,
    LearningAttempt,
    LearningError,
    LearningEvidence,
    MemorySchedule,
    User,
    UserLanguage,
    VocabularyExample,
)
from app.services import (
    activity_generator,
    teaching_flow,
    teaching_slice,
    vocabulary_learning,
)


def _profile(db_session) -> UserLanguage:
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    profile = UserLanguage(user_id=user.id, language_id=language.id, is_active=True)
    db_session.add(profile)
    db_session.flush()
    return profile


def _items(db_session, profile: UserLanguage):
    rows = [
        ("apple", "maçã", "I eat an apple.", "Eu como uma maçã."),
        ("bread", "pão", "The bread is fresh.", "O pão está fresco."),
        ("water", "água", "Water is essential.", "Água é essencial."),
    ]
    return [
        vocabulary_learning.enroll_item(
            db_session,
            user_language_id=profile.id,
            term=term,
            translation_pt=translation,
            examples=[{"example_text": example, "translation_pt": example_pt}],
        )
        for term, translation, example, example_pt in rows
    ]


def _examples(db_session, items):
    item_ids = [item.id for item in items]
    rows = db_session.scalars(
        select(VocabularyExample).where(
            VocabularyExample.vocabulary_item_id.in_(item_ids)
        )
    )
    grouped = {item_id: [] for item_id in item_ids}
    for row in rows:
        grouped[row.vocabulary_item_id].append(row)
    return grouped


def test_generator_interleaves_set_by_stage_and_declares_exact_audio_contract(
    db_session,
):
    profile = _profile(db_session)
    items = _items(db_session, profile)

    activities = activity_generator.generate_vocabulary_activities(
        items, examples_by_item=_examples(db_session, items)
    )

    assert [activity["type"] for activity in activities] == [
        ActivityType.PRESENTATION,
        ActivityType.PRESENTATION,
        ActivityType.PRESENTATION,
        ActivityType.RECOGNITION,
        ActivityType.RECOGNITION,
        ActivityType.RECOGNITION,
        ActivityType.REVERSE_RECOGNITION,
        ActivityType.REVERSE_RECOGNITION,
        ActivityType.REVERSE_RECOGNITION,
        ActivityType.LISTENING_RECOGNITION,
        ActivityType.LISTENING_RECOGNITION,
        ActivityType.LISTENING_RECOGNITION,
        ActivityType.LEXICAL_PRODUCTION,
        ActivityType.LEXICAL_PRODUCTION,
        ActivityType.LEXICAL_PRODUCTION,
    ]
    assert [activity["vocabulary_item_id"] for activity in activities[:3]] == [
        item.id for item in items
    ]
    assert all("phase_hint" in activity for activity in activities)
    assert all("evidence_type" in activity for activity in activities)
    assert all("audio_targets" in activity for activity in activities)

    presentation = activities[0]
    assert presentation["audio_targets"] == [
        {
            "audio_target_type": "vocabulary_item",
            "audio_text": "apple",
        },
        {
            "audio_target_type": "example_sentence",
            "audio_text": "I eat an apple.",
        },
    ]
    assert presentation["term"] == "apple"
    assert presentation["example_sentence"] == "I eat an apple."

    recognition = activities[3]
    assert recognition["prompt"] == "apple"
    assert set(recognition["options"]) == {"maçã", "pão", "água"}
    assert recognition["canonical_answer"] == "maçã"

    reverse = activities[6]
    assert reverse["prompt"] == "maçã"
    assert set(reverse["options"]) == {"apple", "bread", "water"}
    assert reverse["canonical_answer"] == "apple"

    listening = activities[9]
    assert listening["audio_target_type"] == "vocabulary_item"
    assert listening["audio_text"] == "apple"
    assert listening["audio_targets"] == [
        {"audio_target_type": "vocabulary_item", "audio_text": "apple"}
    ]
    assert listening["show_text"] is False
    assert "term" not in listening
    assert set(listening["options"]) == {"maçã", "pão", "água"}

    production = activities[12]
    assert production["prompt"] == "maçã"
    assert production["canonical_answer"] == "apple"
    assert production["response_modes"] == ["typing", "speech"]


def test_generator_degrades_without_inventing_distractors_or_example(db_session):
    profile = _profile(db_session)
    item = vocabulary_learning.enroll_item(
        db_session,
        user_language_id=profile.id,
        term="hello",
        translation_pt="olá",
    )

    first = activity_generator.generate_vocabulary_activities([item])
    second = activity_generator.generate_vocabulary_activities([item])

    assert first == second
    assert [activity["options"] for activity in first if "options" in activity] == [
        ["olá"],
        ["hello"],
        ["olá"],
    ]
    presentation = first[0]
    assert "example_sentence" not in presentation
    assert presentation["audio_targets"] == [
        {"audio_target_type": "vocabulary_item", "audio_text": "hello"}
    ]


def test_generator_omits_mastered_not_due_but_keeps_due_and_weak_items(db_session):
    profile = _profile(db_session)
    items = _items(db_session, profile)
    now = datetime.now(timezone.utc)
    schedules = {
        items[0].id: MemorySchedule(
            user_language_id=profile.id,
            subject_type=MemorySubjectType.VOCABULARY,
            subject_key=items[0].id,
            state="mastered",
            due_at=now + timedelta(days=7),
        ),
        items[1].id: MemorySchedule(
            user_language_id=profile.id,
            subject_type=MemorySubjectType.VOCABULARY,
            subject_key=items[1].id,
            state="mastered",
            due_at=now - timedelta(minutes=1),
        ),
    }

    activities = activity_generator.generate_vocabulary_activities(
        items,
        examples_by_item=_examples(db_session, items),
        memory_by_item=schedules,
        now=now,
    )

    selected_ids = {activity["vocabulary_item_id"] for activity in activities}
    assert items[0].id not in selected_ids
    assert items[1].id in selected_ids
    assert items[2].id in selected_ids


def test_correct_lexical_answers_record_every_payload_evidence_type(db_session):
    profile = _profile(db_session)
    items = _items(db_session, profile)
    session = teaching_flow.start_vocabulary_flow(
        db_session,
        user_language_id=profile.id,
        vocabulary_item_ids=[item.id for item in items],
    )
    # Apresentações registram exposure; avançar até recognition.
    for _ in items:
        teaching_slice.submit_slice_answer(db_session, session, student_response="")

    activity = teaching_flow.current_activity(session)
    assert activity["type"] == ActivityType.RECOGNITION
    output = teaching_slice.submit_slice_answer(
        db_session,
        session,
        student_response=activity["canonical_answer"],
    )

    attempt = db_session.get(LearningAttempt, output["attempt"]["id"])
    evidence = db_session.scalar(
        select(LearningEvidence).where(LearningEvidence.attempt_id == attempt.id)
    )
    assert attempt.vocabulary_item_id == activity["vocabulary_item_id"]
    assert evidence.evidence_type == activity["evidence_type"] == EvidenceType.RECOGNITION

    while activity := teaching_flow.current_activity(session):
        teaching_slice.submit_slice_answer(
            db_session,
            session,
            student_response=activity["canonical_answer"],
        )

    expected = {
        EvidenceType.EXPOSURE,
        EvidenceType.RECOGNITION,
        EvidenceType.REVERSE_RECOGNITION,
        EvidenceType.LISTENING_RECOGNITION,
        EvidenceType.LEXICAL_PRODUCTION,
    }
    for item in items:
        evidence_types = set(
            db_session.scalars(
                select(LearningEvidence.evidence_type).where(
                    LearningEvidence.vocabulary_item_id == item.id
                )
            )
        )
        assert evidence_types == expected


def test_listening_public_payload_hides_text_and_answer(db_session):
    profile = _profile(db_session)
    items = _items(db_session, profile)
    session = teaching_flow.start_vocabulary_flow(
        db_session,
        user_language_id=profile.id,
        vocabulary_item_ids=[item.id for item in items],
    )

    output = None
    while (activity := teaching_flow.current_activity(session))[
        "type"
    ] != ActivityType.LISTENING_RECOGNITION:
        response = (
            ""
            if activity["type"] == ActivityType.PRESENTATION
            else activity["canonical_answer"]
        )
        output = teaching_slice.submit_slice_answer(
            db_session, session, student_response=response
        )

    public_activity = output["current_activity"]
    assert public_activity["type"] == ActivityType.LISTENING_RECOGNITION
    assert public_activity["show_text"] is False
    assert public_activity["audio_target_type"] == "vocabulary_item"
    assert public_activity["audio_text"] == "apple"
    assert "prompt" not in public_activity
    assert "term" not in public_activity
    assert "canonical_answer" not in public_activity
    assert "accepted_variants" not in public_activity


def test_incorrect_lexical_answer_defers_item_and_preserves_replay_idempotency(
    db_session,
):
    profile = _profile(db_session)
    items = _items(db_session, profile)
    session = teaching_flow.start_vocabulary_flow(
        db_session,
        user_language_id=profile.id,
        vocabulary_item_ids=[item.id for item in items],
    )
    for _ in items:
        teaching_slice.submit_slice_answer(db_session, session, student_response="")

    failed_index = session.activity_cursor
    failed_activity = teaching_flow.current_activity(session)
    output = teaching_slice.submit_slice_answer(
        db_session,
        session,
        student_response=next(
            option
            for option in failed_activity["options"]
            if option != failed_activity["canonical_answer"]
        ),
        activity_index=failed_index,
    )

    next_activity = teaching_flow.current_activity(session)
    schedule = db_session.scalar(
        select(MemorySchedule).where(
            MemorySchedule.subject_type == MemorySubjectType.VOCABULARY,
            MemorySchedule.subject_key == failed_activity["vocabulary_item_id"],
        )
    )
    assert output["remediation"] is None
    assert session.activity_cursor == failed_index + 1
    assert next_activity["vocabulary_item_id"] != failed_activity["vocabulary_item_id"]
    assert schedule.lapse_count == 1
    due_at = schedule.due_at
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=timezone.utc)
    assert due_at <= datetime.now(timezone.utc)
    assert db_session.scalar(
        select(func.count(LearningError.id)).where(
            LearningError.vocabulary_item_id == failed_activity["vocabulary_item_id"]
        )
    ) == 1

    with pytest.raises(APIError) as exc:
        teaching_slice.submit_slice_answer(
            db_session,
            session,
            student_response="resposta inexistente",
            activity_index=failed_index,
        )
    assert exc.value.code == "attempt_already_submitted"
    db_session.refresh(schedule)
    assert schedule.lapse_count == 1
