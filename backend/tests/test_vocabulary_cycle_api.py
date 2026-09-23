"""Contratos HTTP do ciclo lexical em lições avulsas e no currículo."""

from copy import deepcopy
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.curriculum import BlockSkill
from app.models import (
    CurriculumBlock,
    CurriculumDay,
    CurriculumWeek,
    Language,
    LearningAttempt,
    Lesson,
    MemorySchedule,
    ReviewItem,
    TeachingFlowSession,
    User,
    UserLanguage,
    UserObjectiveProgress,
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


def _first_vocabulary_block(db, curriculum_id: str) -> CurriculumBlock:
    return db.scalar(
        select(CurriculumBlock)
        .join(CurriculumDay, CurriculumDay.id == CurriculumBlock.day_id)
        .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
        .where(
            CurriculumWeek.curriculum_id == curriculum_id,
            CurriculumBlock.skill == BlockSkill.VOCABULARY,
        )
        .order_by(CurriculumDay.day_number)
    )


def _persistence_snapshot(db) -> dict[str, int]:
    return {
        "items": db.scalar(select(func.count(VocabularyItem.id))) or 0,
        "examples": db.scalar(select(func.count(VocabularyExample.id))) or 0,
        "memory": db.scalar(select(func.count(MemorySchedule.id))) or 0,
        "reviews": db.scalar(select(func.count(ReviewItem.id))) or 0,
        "progress": db.scalar(select(func.count(UserObjectiveProgress.id))) or 0,
        "flows": db.scalar(select(func.count(TeachingFlowSession.id))) or 0,
    }


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

    flow = db_session.get(TeachingFlowSession, body["flow"]["id"])
    activities = (flow.payload_json or {}).get("activities") or []
    recognition_index = next(
        index
        for index, activity in enumerate(activities)
        if activity.get("type") == "recognition" and activity.get("vocabulary_item_id")
    )
    for activity_index, activity in enumerate(activities[:recognition_index]):
        answer = ""
        if activity.get("type") in {
            "multiple_choice",
            "recognition",
            "reverse_recognition",
            "listening_recognition",
        }:
            answer = activity.get("canonical_answer") or ""
            if not answer and activity.get("options"):
                first = activity["options"][0]
                answer = first["text"] if isinstance(first, dict) else first
        response = client.post(
            f"/api/v1/lessons/{lesson.id}/vocabulary-cycle/answer",
            json={"activity_index": activity_index, "student_response": answer},
            headers=auth,
        )
        assert response.status_code == 200, response.json()

    recognition = response.json()["current_activity"]
    assert recognition["type"] == "recognition"
    assert "canonical_answer" not in recognition
    assert "accepted_variants" not in recognition
    assert "correct_option" not in recognition

    answered = client.post(
        f"/api/v1/lessons/{lesson.id}/vocabulary-cycle/answer",
        json={"activity_index": recognition_index, "student_response": "olá"},
        headers=auth,
    )
    assert answered.status_code == 200
    assert answered.json()["attempt"]["result"] == "correct"


def test_standalone_restore_and_answer_ignore_curriculum_session_for_same_lesson(
    client, auth, db_session
):
    profile = _profile(db_session)
    lesson = _lesson(db_session, profile)
    standalone = _start(client, auth, lesson.id).json()
    standalone_id = standalone["flow"]["id"]

    curriculum = generate_curriculum(db_session, profile.id, 90)
    block = _first_vocabulary_block(db_session, curriculum.id)
    block.lesson_ref = lesson.id
    db_session.commit()
    curriculum_started = client.post(
        f"/api/v1/curriculum/block/{block.id}/start", headers=auth
    )
    assert curriculum_started.status_code == 200
    curriculum_id = curriculum_started.json()["teaching"]["flow"]["id"]
    assert curriculum_id != standalone_id

    restored = client.get(
        f"/api/v1/lessons/{lesson.id}/vocabulary-cycle", headers=auth
    )
    assert restored.status_code == 200
    assert restored.json()["flow"]["id"] == standalone_id

    curriculum_flow = db_session.get(TeachingFlowSession, curriculum_id)
    curriculum_cursor = curriculum_flow.activity_cursor
    answered = client.post(
        f"/api/v1/lessons/{lesson.id}/vocabulary-cycle/answer",
        json={"activity_index": 0, "student_response": ""},
        headers=auth,
    )
    assert answered.status_code == 200
    assert answered.json()["flow"]["id"] == standalone_id
    db_session.refresh(curriculum_flow)
    assert curriculum_flow.activity_cursor == curriculum_cursor
    attempt = db_session.scalar(
        select(LearningAttempt).order_by(LearningAttempt.created_at.desc())
    )
    assert attempt.curriculum_block_id is None


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


@pytest.mark.parametrize(
    "invalid_root",
    [["item"], "texto", 7, True, None],
    ids=["list", "string", "number", "bool", "null"],
)
def test_non_mapping_content_root_returns_safe_empty_contract(
    client, auth, db_session, invalid_root
):
    profile = _profile(db_session)
    lesson = Lesson(
        user_language_id=profile.id,
        title="Conteúdo legado",
        objective="Continuar com segurança",
        status="active",
        content_json=invalid_root,
    )
    db_session.add(lesson)
    db_session.commit()

    response = _start(client, auth, lesson.id)

    assert response.status_code == 200
    assert response.json()["status"] == "no_vocabulary_due"
    assert _persistence_snapshot(db_session) == {
        "items": 0,
        "examples": 0,
        "memory": 0,
        "reviews": 0,
        "progress": 0,
        "flows": 0,
    }


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
    activity = response.json()["current_activity"]
    assert activity["type"] == "presentation"
    assert activity["term"] == "legacy"
    assert activity["translation_pt"] == "legado"
    assert activity["index"] == 0
    assert activity["session_area"] == "vocabulary"


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


def test_standalone_no_due_rolls_back_enrollment_side_effects(
    client, auth, db_session
):
    from app.services.vocabulary_learning import enroll_item

    profile = _profile(db_session)
    lesson = _lesson(
        db_session,
        profile,
        items=[{"term": "known", "translation": "conhecido"}],
    )
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
    content = deepcopy(lesson.content_json)
    content["items"][0]["example"] = "A newly imported example."
    lesson.content_json = content
    db_session.commit()
    before = _persistence_snapshot(db_session)

    response = _start(client, auth, lesson.id)

    assert response.status_code == 200
    assert response.json()["status"] == "no_vocabulary_due"
    assert _persistence_snapshot(db_session) == before


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


def test_curriculum_rejects_lesson_ref_from_another_profile_without_enrollment(
    client, auth, db_session, other_user
):
    profile = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90)
    block = _first_vocabulary_block(db_session, curriculum.id)
    other = db_session.get(User, other_user)
    foreign_lesson = _lesson(
        db_session,
        _profile(db_session, email=other.email),
        items=[{"term": "private", "translation": "privado"}],
    )
    block.lesson_ref = foreign_lesson.id
    db_session.commit()
    before = _persistence_snapshot(db_session)

    response = client.post(
        f"/api/v1/curriculum/block/{block.id}/start", headers=auth
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "lesson_not_found"
    assert _persistence_snapshot(db_session) == before


def test_curriculum_vocabulary_handles_legacy_lesson_with_non_mapping_root(
    client, auth, db_session
):
    profile = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90)
    block = _first_vocabulary_block(db_session, curriculum.id)
    legacy = Lesson(
        user_language_id=profile.id,
        title="Lição legada inválida",
        objective="Continuar sem erro interno",
        status="active",
        content_json=["formato", "antigo"],
    )
    db_session.add(legacy)
    db_session.flush()
    block.lesson_ref = legacy.id
    db_session.commit()

    response = client.post(
        f"/api/v1/curriculum/block/{block.id}/start", headers=auth
    )

    assert response.status_code == 200
    body = response.json()
    assert body["lesson"] == {"lesson_id": legacy.id}
    assert body["teaching"]["status"] == "no_vocabulary_due"
    assert db_session.scalar(select(func.count(VocabularyItem.id))) == 0


def test_curriculum_orphan_lesson_ref_regenerates_owned_lesson(
    client, auth, db_session
):
    profile = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90)
    block = _first_vocabulary_block(db_session, curriculum.id)
    orphan_id = "00000000-0000-0000-0000-000000000404"
    block.lesson_ref = orphan_id
    db_session.commit()

    response = client.post(
        f"/api/v1/curriculum/block/{block.id}/start", headers=auth
    )

    assert response.status_code == 200
    body = response.json()
    generated_id = body["lesson"]["lesson_id"]
    assert generated_id != orphan_id
    generated = db_session.get(Lesson, generated_id)
    assert generated is not None
    assert generated.user_language_id == profile.id
    db_session.refresh(block)
    assert block.lesson_ref == generated_id


def test_curriculum_no_due_rolls_back_examples_memory_progress_and_flow(
    client, auth, db_session
):
    from app.services.progression import build_block_lesson
    from app.services.vocabulary_learning import enroll_lesson_content

    profile = _profile(db_session)
    user = db_session.scalar(
        select(User).where(User.email == "admin@befluent.local")
    )
    curriculum = generate_curriculum(db_session, profile.id, 90)
    block = _first_vocabulary_block(db_session, curriculum.id)
    day = db_session.get(CurriculumDay, block.day_id)
    built = build_block_lesson(db_session, user=user, block=block, day=day)
    lesson = db_session.get(Lesson, built["lesson_id"])
    items = enroll_lesson_content(
        db_session,
        user_language_id=profile.id,
        content=lesson.content_json,
    )
    for item in items:
        schedule = db_session.scalar(
            select(MemorySchedule).where(MemorySchedule.subject_key == item.id)
        )
        schedule.state = "mastered"
        schedule.due_at = now() + timedelta(days=30)
    content = deepcopy(lesson.content_json)
    content["items"][0]["example"] = "A new curricular example."
    lesson.content_json = content
    db_session.commit()
    before = _persistence_snapshot(db_session)

    response = client.post(
        f"/api/v1/curriculum/block/{block.id}/start", headers=auth
    )

    assert response.status_code == 200
    assert response.json()["teaching"]["status"] == "no_vocabulary_due"
    assert _persistence_snapshot(db_session) == before


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


def test_curriculum_lexical_answer_requires_activity_index(
    client, auth, db_session
):
    profile = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90)
    block = _first_vocabulary_block(db_session, curriculum.id)
    db_session.commit()
    started = client.post(
        f"/api/v1/curriculum/block/{block.id}/start", headers=auth
    )
    assert started.status_code == 200
    before_attempts = db_session.scalar(select(func.count(LearningAttempt.id)))

    response = client.post(
        f"/api/v1/curriculum/block/{block.id}/teaching/answer",
        json={"student_response": ""},
        headers=auth,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "activity_index_required"
    assert db_session.scalar(select(func.count(LearningAttempt.id))) == before_attempts


def test_speech_production_contract_accepts_transcript_and_rejects_raw_audio(
    client, auth, db_session
):
    profile = _profile(db_session)
    lesson = _lesson(db_session, profile)
    started = _start(client, auth, lesson.id).json()
    flow = db_session.get(TeachingFlowSession, started["flow"]["id"])
    activities = list(flow.payload_json["activities"])
    production = {
        "type": "lexical_production",
        "vocabulary_item_id": activities[0]["vocabulary_item_id"],
        "phase_hint": "producing",
        "evidence_type": "lexical_production",
        "prompt_pt": "Recupere o termo a partir do significado.",
        "prompt": "olá",
        "canonical_answer": "hello",
        "accepted_variants": ["hello"],
        "response_modes": ["typing", "speech"],
        "audio_targets": [],
        "ai_required": False,
        "session_area": "production",
        "index": len(activities),
    }
    activities.append(production)
    payload = dict(flow.payload_json or {})
    payload["activities"] = activities
    flow.payload_json = payload
    flow.activity_cursor = production["index"]
    flow.phase = "producing"
    db_session.commit()

    rejected = client.post(
        f"/api/v1/lessons/{lesson.id}/vocabulary-cycle/answer",
        json={
            "activity_index": production["index"],
            "student_response": "hello",
            "audio": "base64-raw-audio",
        },
        headers=auth,
    )
    assert rejected.status_code == 422

    accepted = client.post(
        f"/api/v1/lessons/{lesson.id}/vocabulary-cycle/answer",
        json={
            "activity_index": production["index"],
            "student_response": "hello",
        },
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
    before_schedules = db_session.scalar(select(func.count(MemorySchedule.id)))

    completed = client.post(
        f"/api/v1/curriculum/block/{block.id}/complete", json={}, headers=auth
    )

    assert completed.status_code == 200
    assert completed.json()["review_items_added"] == 0
    assert db_session.scalar(select(func.count(VocabularyItem.id))) == before_items
    assert db_session.scalar(select(func.count(ReviewItem.id))) == before_reviews
    assert db_session.scalar(select(func.count(MemorySchedule.id))) == before_schedules


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
