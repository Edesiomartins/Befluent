"""Contratos HTTP do ciclo lexical em lições avulsas e no currículo."""

from datetime import timedelta

from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.curriculum import BlockSkill
from app.models import (
    CurriculumBlock,
    CurriculumDay,
    CurriculumWeek,
    Language,
    Lesson,
    MemorySchedule,
    ReviewItem,
    TeachingFlowSession,
    User,
    UserLanguage,
    VocabularyExample,
    VocabularyItem,
    now,
)
from app.services.curriculum_generator import generate_curriculum


def _profile(db, *, email: str = "admin@befluent.local") -> UserLanguage:
    user = db.scalar(select(User).where(User.email == email))
    language = db.scalar(select(Language).where(Language.code == "en"))
    profile = UserLanguage(
        user_id=user.id,
        language_id=language.id,
        is_active=True,
        onboarding_completed=True,
        diagnostic_completed=True,
        current_level="A2",
        level_source="placement_test",
        vocabulary_grammar_level="A2",
        reading_level="A2",
        listening_level="A2",
        writing_level="A2",
        speaking_level="A2",
    )
    db.add(profile)
    db.flush()
    return profile


def _lesson(db, profile: UserLanguage, *, items: list[dict] | None = None) -> Lesson:
    lesson = Lesson(
        user_language_id=profile.id,
        title="Vocabulário de viagem",
        objective="Usar palavras de viagem",
        status="active",
        content_json={
            "mode": "vocabulary",
            "language_code": "en",
            "items": items
            if items is not None
            else [
                {
                    "term": "hello",
                    "translation": "olá",
                    "example": "Hello, Ana!",
                    "example_translation": "Olá, Ana!",
                },
                {"term": "goodbye", "translation": "tchau"},
            ],
        },
    )
    db.add(lesson)
    db.commit()
    return lesson


def _start(client, auth, lesson_id: str):
    return client.post(
        f"/api/v1/lessons/{lesson_id}/vocabulary-cycle/start", headers=auth
    )


def test_standalone_start_restore_answer_and_hide_answer_key(
    client, auth, db_session
):
    profile = _profile(db_session)
    lesson = _lesson(db_session, profile)

    started = _start(client, auth, lesson.id)
    assert started.status_code == 200
    body = started.json()
    assert body["status"] == "active"
    assert body["flow"]["id"]
    assert body["current_activity"]["type"] == "presentation"
    assert db_session.scalar(
        select(func.count(VocabularyItem.id)).where(
            VocabularyItem.user_language_id == profile.id
        )
    ) == 2
    assert db_session.scalar(select(func.count(VocabularyExample.id))) == 1

    restored = client.get(
        f"/api/v1/lessons/{lesson.id}/vocabulary-cycle", headers=auth
    )
    assert restored.status_code == 200
    assert restored.json()["flow"]["id"] == body["flow"]["id"]

    for activity_index in (0, 1):
        response = client.post(
            f"/api/v1/lessons/{lesson.id}/vocabulary-cycle/answer",
            json={"activity_index": activity_index, "student_response": ""},
            headers=auth,
        )
        assert response.status_code == 200

    recognition = response.json()["current_activity"]
    assert recognition["type"] == "recognition"
    assert "canonical_answer" not in recognition
    assert "accepted_variants" not in recognition
    assert "correct_option" not in recognition

    answered = client.post(
        f"/api/v1/lessons/{lesson.id}/vocabulary-cycle/answer",
        json={"activity_index": 2, "student_response": "olá"},
        headers=auth,
    )
    assert answered.status_code == 200
    assert answered.json()["attempt"]["result"] == "correct"


def test_cycle_rejects_foreign_lesson(client, auth, db_session, other_user):
    other = db_session.get(User, other_user)
    lesson = _lesson(db_session, _profile(db_session, email=other.email))

    response = _start(client, auth, lesson.id)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "lesson_not_found"


def test_cycle_denies_enabled_entitlement_without_grant(
    client, auth, db_session, monkeypatch
):
    monkeypatch.setattr(get_settings(), "language_entitlements_enabled", True)
    lesson = _lesson(db_session, _profile(db_session))

    response = _start(client, auth, lesson.id)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "language_locked"


def test_old_incomplete_content_stays_safe(client, auth, db_session):
    profile = _profile(db_session)
    lesson = _lesson(
        db_session,
        profile,
        items=[
            {"term": "legacy", "translation_pt": "legado"},
            {"term": "sem tradução"},
            {"translation": "sem termo"},
            "formato inválido",
        ],
    )

    response = _start(client, auth, lesson.id)

    assert response.status_code == 200
    assert response.json()["current_activity"] == {
        "type": "presentation",
        "vocabulary_item_id": response.json()["current_activity"][
            "vocabulary_item_id"
        ],
        "index": 0,
        "phase_hint": "input",
        "evidence_type": "exposure",
        "prompt_pt": "Conheça este item de vocabulário.",
        "term": "legacy",
        "translation_pt": "legado",
        "audio_targets": [
            {"audio_target_type": "vocabulary_item", "audio_text": "legacy"}
        ],
        "ai_required": False,
    }


def test_no_vocabulary_due_returns_controlled_contract(client, auth, db_session):
    profile = _profile(db_session)
    lesson = _lesson(
        db_session,
        profile,
        items=[{"term": "known", "translation": "conhecido"}],
    )
    from app.services.vocabulary_learning import enroll_item

    item = enroll_item(
        db_session,
        user_language_id=profile.id,
        term="known",
        translation_pt="conhecido",
    )
    schedule = db_session.scalar(
        select(MemorySchedule).where(MemorySchedule.subject_key == item.id)
    )
    schedule.state = "mastered"
    schedule.due_at = now() + timedelta(days=30)
    db_session.commit()

    response = _start(client, auth, lesson.id)

    assert response.status_code == 200
    assert response.json() == {
        "status": "no_vocabulary_due",
        "lesson_id": lesson.id,
        "flow": None,
        "current_activity": None,
        "activities_total": 0,
    }


def test_curriculum_vocabulary_uses_lexical_flow_with_optional_objective(
    client, auth, db_session
):
    profile = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90)
    db_session.commit()
    block = db_session.scalar(
        select(CurriculumBlock)
        .join(CurriculumDay, CurriculumDay.id == CurriculumBlock.day_id)
        .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
        .where(
            CurriculumWeek.curriculum_id == curriculum.id,
            CurriculumBlock.skill == BlockSkill.VOCABULARY,
        )
        .order_by(CurriculumDay.day_number)
    )

    response = client.post(
        f"/api/v1/curriculum/block/{block.id}/start", headers=auth
    )

    assert response.status_code == 200
    body = response.json()
    assert body["teaching"]["status"] == "active"
    flow = db_session.get(TeachingFlowSession, body["teaching"]["flow"]["id"])
    assert flow.lesson_id == body["lesson"]["lesson_id"]
    assert flow.curriculum_block_id == block.id
    assert flow.objective_id == block.objective_id
    assert (flow.payload_json or {})["lexical_cycle"] is True

    answered = client.post(
        f"/api/v1/curriculum/block/{block.id}/teaching/answer",
        json={"activity_index": 0, "student_response": ""},
        headers=auth,
    )
    assert answered.status_code == 200


def test_curriculum_direct_routes_recheck_entitlement(
    client, auth, db_session, monkeypatch
):
    profile = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90)
    db_session.commit()
    block = db_session.scalar(
        select(CurriculumBlock)
        .join(CurriculumDay, CurriculumDay.id == CurriculumBlock.day_id)
        .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
        .where(CurriculumWeek.curriculum_id == curriculum.id)
    )
    monkeypatch.setattr(get_settings(), "language_entitlements_enabled", True)

    response = client.post(
        f"/api/v1/curriculum/block/{block.id}/start", headers=auth
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "language_locked"


def test_curriculum_lexical_answer_rejects_raw_audio(
    client, auth, db_session
):
    profile = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90)
    db_session.commit()
    block = db_session.scalar(
        select(CurriculumBlock)
        .join(CurriculumDay, CurriculumDay.id == CurriculumBlock.day_id)
        .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
        .where(
            CurriculumWeek.curriculum_id == curriculum.id,
            CurriculumBlock.skill == BlockSkill.VOCABULARY,
        )
        .order_by(CurriculumDay.day_number)
    )
    started = client.post(
        f"/api/v1/curriculum/block/{block.id}/start", headers=auth
    ).json()

    response = client.post(
        f"/api/v1/curriculum/block/{block.id}/teaching/answer",
        json={
            "activity_index": started["teaching"]["flow"]["activity_cursor"],
            "student_response": "",
            "audio": "base64-raw-audio",
        },
        headers=auth,
    )

    assert response.status_code == 422


def test_speech_production_contract_accepts_transcript_and_rejects_raw_audio(
    client, auth, db_session
):
    profile = _profile(db_session)
    lesson = _lesson(db_session, profile)
    started = _start(client, auth, lesson.id).json()
    flow = db_session.get(TeachingFlowSession, started["flow"]["id"])
    production_index = next(
        index
        for index, activity in enumerate(flow.payload_json["activities"])
        if activity["type"] == "lexical_production"
    )
    flow.activity_cursor = production_index
    flow.phase = "producing"
    db_session.commit()

    rejected = client.post(
        f"/api/v1/lessons/{lesson.id}/vocabulary-cycle/answer",
        json={
            "activity_index": production_index,
            "student_response": "hello",
            "audio": "base64-raw-audio",
        },
        headers=auth,
    )
    assert rejected.status_code == 422

    accepted = client.post(
        f"/api/v1/lessons/{lesson.id}/vocabulary-cycle/answer",
        json={"activity_index": production_index, "student_response": "hello"},
        headers=auth,
    )
    assert accepted.status_code == 200
    assert accepted.json()["attempt"]["result"] == "correct"


def test_completing_curriculum_block_does_not_duplicate_cycle_enrollment(
    client, auth, db_session
):
    profile = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90)
    db_session.commit()
    block = db_session.scalar(
        select(CurriculumBlock)
        .join(CurriculumDay, CurriculumDay.id == CurriculumBlock.day_id)
        .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
        .where(
            CurriculumWeek.curriculum_id == curriculum.id,
            CurriculumBlock.skill == BlockSkill.VOCABULARY,
        )
        .order_by(CurriculumDay.day_number)
    )
    started = client.post(
        f"/api/v1/curriculum/block/{block.id}/start", headers=auth
    )
    assert started.status_code == 200
    before_items = db_session.scalar(select(func.count(VocabularyItem.id)))
    before_reviews = db_session.scalar(select(func.count(ReviewItem.id)))

    completed = client.post(
        f"/api/v1/curriculum/block/{block.id}/complete", json={}, headers=auth
    )

    assert completed.status_code == 200
    assert completed.json()["review_items_added"] == 0
    assert db_session.scalar(select(func.count(VocabularyItem.id))) == before_items
    assert db_session.scalar(select(func.count(ReviewItem.id))) == before_reviews


def test_completion_normalizes_legacy_term_before_counting_new_enrollment(
    client, auth, db_session
):
    profile = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90)
    db_session.commit()
    block = db_session.scalar(
        select(CurriculumBlock)
        .join(CurriculumDay, CurriculumDay.id == CurriculumBlock.day_id)
        .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
        .where(
            CurriculumWeek.curriculum_id == curriculum.id,
            CurriculumBlock.skill == BlockSkill.VOCABULARY,
        )
        .order_by(CurriculumDay.day_number)
    )
    started = client.post(
        f"/api/v1/curriculum/block/{block.id}/start", headers=auth
    )
    assert started.status_code == 200
    items = list(
        db_session.scalars(
            select(VocabularyItem).where(
                VocabularyItem.user_language_id == profile.id
            )
        )
    )
    before_reviews = db_session.scalar(select(func.count(ReviewItem.id)))
    for item in items:
        item.term = f"  {item.term.swapcase()}  "
    db_session.commit()

    completed = client.post(
        f"/api/v1/curriculum/block/{block.id}/complete", json={}, headers=auth
    )

    assert completed.status_code == 200
    assert completed.json()["review_items_added"] == 0
    assert db_session.scalar(select(func.count(VocabularyItem.id))) == len(items)
    assert db_session.scalar(select(func.count(ReviewItem.id))) == before_reviews
