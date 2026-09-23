"""Review adaptativo do ciclo lexical — fila, prioridade e legado."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.teaching import EvidenceType, MemorySubjectType
from app.models import (
    Language,
    MemorySchedule,
    ReviewItem,
    User,
    UserLanguage,
    VocabularyExample,
    VocabularyItem,
)
from app.services import memory_engine, teaching_engine, vocabulary_learning, vocabulary_review


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _profile(db_session) -> UserLanguage:
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    existing = db_session.scalar(
        select(UserLanguage).where(
            UserLanguage.user_id == user.id, UserLanguage.language_id == language.id
        )
    )
    if existing:
        return existing
    profile = UserLanguage(user_id=user.id, language_id=language.id, is_active=True)
    db_session.add(profile)
    db_session.commit()
    return profile


def _signal(db_session, profile, item, evidence_type, *, result="correct"):
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
        result=result,
        evidence_type=evidence_type if result == "correct" else None,
    )


def _master(db_session, profile, item):
    for evidence_type in (
        EvidenceType.RECOGNITION,
        EvidenceType.REVERSE_RECOGNITION,
        EvidenceType.LISTENING_RECOGNITION,
        EvidenceType.LEXICAL_PRODUCTION,
    ):
        _signal(db_session, profile, item, evidence_type)


def test_weak_item_is_selected_before_mastered_item(db_session):
    profile = _profile(db_session)
    weak = vocabulary_learning.enroll_item(
        db_session,
        user_language_id=profile.id,
        term="können",
        translation_pt="poder",
        examples=[{"example_text": "Ich kann Deutsch.", "translation_pt": "Eu sei alemão."}],
    )
    strong = vocabulary_learning.enroll_item(
        db_session,
        user_language_id=profile.id,
        term="apple",
        translation_pt="maçã",
        examples=[{"example_text": "I eat an apple.", "translation_pt": "Eu como uma maçã."}],
    )
    _master(db_session, profile, strong)
    _signal(db_session, profile, weak, EvidenceType.RECOGNITION, result="incorrect")

    weak_schedule = db_session.scalar(
        select(MemorySchedule).where(MemorySchedule.subject_key == weak.id)
    )
    strong_schedule = db_session.scalar(
        select(MemorySchedule).where(MemorySchedule.subject_key == strong.id)
    )
    weak_schedule.due_at = _now() - timedelta(minutes=5)
    strong_schedule.due_at = _now() - timedelta(hours=2)
    strong_schedule.state = "mastered"
    strong_schedule.strength = 0.9
    memory_engine._project_review_item(db_session, weak_schedule)
    memory_engine._project_review_item(db_session, strong_schedule)
    db_session.commit()

    queue = vocabulary_review.select_due_reviews(db_session, profile.id)
    terms = [item["payload"]["term"] for item in queue]
    assert terms[0] == "können"
    assert "apple" in terms


def test_mastered_items_are_capped_when_weak_items_are_due(db_session):
    profile = _profile(db_session)
    weak = vocabulary_learning.enroll_item(
        db_session, user_language_id=profile.id, term="weak", translation_pt="fraco"
    )
    mastered_a = vocabulary_learning.enroll_item(
        db_session, user_language_id=profile.id, term="strong-a", translation_pt="forte a"
    )
    mastered_b = vocabulary_learning.enroll_item(
        db_session, user_language_id=profile.id, term="strong-b", translation_pt="forte b"
    )
    _signal(db_session, profile, weak, EvidenceType.RECOGNITION, result="incorrect")
    _master(db_session, profile, mastered_a)
    _master(db_session, profile, mastered_b)

    for item in (weak, mastered_a, mastered_b):
        schedule = db_session.scalar(
            select(MemorySchedule).where(MemorySchedule.subject_key == item.id)
        )
        schedule.due_at = _now() - timedelta(minutes=1)
        if item is not weak:
            schedule.state = "mastered"
            schedule.strength = 0.95
        memory_engine._project_review_item(db_session, schedule)
    db_session.commit()

    queue = vocabulary_review.select_due_reviews(db_session, profile.id)
    terms = [item["payload"]["term"] for item in queue]
    assert terms[0] == "weak"
    mastered_shown = [term for term in terms if term.startswith("strong-")]
    assert len(mastered_shown) <= 1


def test_incorrect_item_returns_in_review_without_repeating_same_exercise(db_session):
    profile = _profile(db_session)
    item = vocabulary_learning.enroll_item(
        db_session,
        user_language_id=profile.id,
        term="bonjour",
        translation_pt="olá",
        examples=[{"example_text": "Bonjour, Ana!", "translation_pt": "Olá, Ana!"}],
    )
    _signal(db_session, profile, item, EvidenceType.RECOGNITION, result="incorrect")
    db_session.commit()

    queue = vocabulary_review.select_due_reviews(db_session, profile.id)
    assert len(queue) == 1
    card = queue[0]
    assert card["payload"]["term"] == "bonjour"
    assert card["payload"]["review_mode"] == "lexical_v2"
    assert card["payload"]["example"] == "Bonjour, Ana!"
    assert card["item_type"] == MemorySubjectType.VOCABULARY
    assert card["payload"].get("activity_type") != "recognition"
    assert card["payload"]["suggested_modality"] != "recognition"
    assert card["payload"]["suggested_modality"] == "reverse_recognition"


def test_legacy_review_item_without_memory_schedule_still_works(db_session):
    profile = _profile(db_session)
    item = VocabularyItem(
        user_language_id=profile.id,
        term="house",
        translation_pt="casa",
    )
    db_session.add(item)
    db_session.flush()
    review = ReviewItem(
        user_language_id=profile.id,
        item_type="vocabulary",
        reference_id=item.id,
        payload_json={"term": "house"},
        next_review_at=_now() - timedelta(minutes=1),
    )
    db_session.add(review)
    db_session.commit()

    queue = vocabulary_review.select_due_reviews(db_session, profile.id)
    assert len(queue) == 1
    assert queue[0]["id"] == review.id
    assert queue[0]["payload"]["term"] == "house"
    assert queue[0]["payload"]["review_mode"] == "legacy"
    assert "example" not in queue[0]["payload"] or not queue[0]["payload"].get("example")

    answered = memory_engine.answer_review_item(db_session, review, rating="good")
    db_session.commit()
    assert answered["source_of_truth"] == "review_item"
    assert answered["interval_days"] == 2


def test_old_content_without_example_does_not_invent_grammar(db_session):
    profile = _profile(db_session)
    item = vocabulary_learning.enroll_item(
        db_session, user_language_id=profile.id, term="chat", translation_pt="gato"
    )
    assert db_session.scalar(
        select(VocabularyExample).where(VocabularyExample.vocabulary_item_id == item.id)
    ) is None
    db_session.commit()

    queue = vocabulary_review.select_due_reviews(db_session, profile.id)
    card = next(row for row in queue if row["payload"]["term"] == "chat")
    assert card["payload"]["translation_pt"] == "gato"
    assert not card["payload"].get("example")
    assert not card["payload"].get("form_note")
    assert "é uma forma de" not in str(card["payload"])


def test_reviews_due_api_uses_adaptive_order(client, auth, db_session):
    assert client.post("/api/v1/languages/activate", json={"code": "en"}, headers=auth).status_code == 200
    profile = _profile(db_session)
    weak = vocabulary_learning.enroll_item(
        db_session, user_language_id=profile.id, term="können", translation_pt="poder"
    )
    strong = vocabulary_learning.enroll_item(
        db_session, user_language_id=profile.id, term="apple", translation_pt="maçã"
    )
    _master(db_session, profile, strong)
    _signal(db_session, profile, weak, EvidenceType.LISTENING_RECOGNITION, result="incorrect")
    for item in (weak, strong):
        schedule = db_session.scalar(
            select(MemorySchedule).where(MemorySchedule.subject_key == item.id)
        )
        schedule.due_at = _now() - timedelta(minutes=1)
        memory_engine._project_review_item(db_session, schedule)
    db_session.commit()

    response = client.get("/api/v1/reviews/due?language_code=en", headers=auth)
    assert response.status_code == 200
    terms = [row["payload"]["term"] for row in response.json()]
    assert terms[0] == "können"
