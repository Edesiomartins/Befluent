"""Cronograma flexível: jornadas, não dias civis obrigatórios."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.curriculum import BlockStatus, DayStatus
from app.core.errors import APIError
from app.core.levels import CEFRLevel, LevelSource
from app.core.teaching import MasteryState, MemorySubjectType
from app.models import (
    CurriculumBlock,
    CurriculumDay,
    CurriculumWeek,
    Language,
    MemorySchedule,
    ReviewItem,
    User,
    UserLanguage,
    UserObjectiveProgress,
)
from app.services.curriculum_generator import generate_curriculum
from app.services.objective_seed import ensure_en_a1_can_001
from app.services.progression import ensure_block_unlocked

START = date(2026, 8, 3)


def _profile(db, language_code="en", entry=CEFRLevel.A2):
    user = db.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db.scalar(select(Language).where(Language.code == language_code))
    profile = UserLanguage(
        user_id=user.id,
        language_id=language.id,
        is_active=True,
        diagnostic_completed=True,
        current_level=entry,
        level_source=LevelSource.PLACEMENT_TEST,
        vocabulary_grammar_level=entry,
        reading_level=entry,
        listening_level=entry,
        writing_level=entry,
        speaking_level=entry,
    )
    db.add(profile)
    db.commit()
    return profile, user


def _days(db, curriculum):
    return list(
        db.scalars(
            select(CurriculumDay)
            .join(CurriculumWeek)
            .where(CurriculumWeek.curriculum_id == curriculum.id)
            .order_by(CurriculumDay.day_number)
        )
    )


def _blocks(db, day):
    return list(
        db.scalars(
            select(CurriculumBlock)
            .where(CurriculumBlock.day_id == day.id)
            .order_by(CurriculumBlock.position)
        )
    )


def _complete_day(db, day):
    for block in _blocks(db, day):
        block.status = BlockStatus.COMPLETED
    day.status = DayStatus.COMPLETED
    day.completed_at = datetime.now(timezone.utc)
    db.flush()


def test_completing_day1_unlocks_day2_immediately(client, auth, db_session):
    profile, _ = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    days = _days(db_session, curriculum)
    day1, day2 = days[0], days[1]
    assert day2.scheduled_date > day1.scheduled_date

    for block in _blocks(db_session, day1)[:-1]:
        assert client.post(
            f"/api/v1/curriculum/block/{block.id}/complete", headers=auth
        ).status_code == 200

    last = _blocks(db_session, day1)[-1]
    done = client.post(f"/api/v1/curriculum/block/{last.id}/complete", headers=auth)
    assert done.status_code == 200
    body = done.json()
    assert body["day_completed"] is True
    assert body["next_day"]["id"] == day2.id
    assert body["next_day"]["available"] is True
    assert body["progress"]["current_day_number"] == 2

    detail = client.get(f"/api/v1/curriculum/day/{day1.id}", headers=auth).json()
    assert detail["day"]["next_day"]["available"] is True

    # scheduled_date futura não bloqueia
    first_b2 = _blocks(db_session, day2)[0]
    assert client.post(
        f"/api/v1/curriculum/block/{first_b2.id}/start", headers=auth
    ).status_code == 200


def test_day2_then_day3_same_civil_day(client, auth, db_session):
    profile, _ = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    days = _days(db_session, curriculum)
    _complete_day(db_session, days[0])
    _complete_day(db_session, days[1])
    db_session.commit()

    today = client.get("/api/v1/curriculum/day/today?language_code=en", headers=auth)
    assert today.json()["day"]["day_number"] == 3


def test_cannot_skip_block_inside_day(db_session):
    profile, _ = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    day = _days(db_session, curriculum)[0]
    blocks = _blocks(db_session, day)
    with pytest.raises(APIError) as exc:
        ensure_block_unlocked(db_session, blocks[1], day)
    assert exc.value.code == "curriculum_block_locked"


def test_pause_resumes_first_incomplete(client, auth, db_session):
    profile, _ = _profile(db_session)
    start = date.today() - timedelta(days=12)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=start)
    db_session.commit()
    days = _days(db_session, curriculum)
    _complete_day(db_session, days[0])
    days[1].status = DayStatus.IN_PROGRESS
    db_session.commit()

    today = client.get("/api/v1/curriculum/day/today?language_code=en", headers=auth).json()
    assert today["day"]["day_number"] == 2


def test_fast_progress_does_not_advance_future_reviews(db_session):
    profile, _ = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    future = datetime.now(timezone.utc) + timedelta(days=2)
    item = ReviewItem(
        user_language_id=profile.id,
        item_type="vocabulary",
        reference_id="ref-future",
        priority=1,
        interval_days=2,
        next_review_at=future,
        mastery_state="learning",
        payload_json={"term": "later"},
    )
    schedule = MemorySchedule(
        user_language_id=profile.id,
        subject_type=MemorySubjectType.VOCABULARY,
        subject_key="later",
        state="learning",
        interval_days=2,
        due_at=future,
        payload_json={},
    )
    db_session.add(item)
    db_session.add(schedule)
    db_session.commit()

    for day in _days(db_session, curriculum)[:3]:
        _complete_day(db_session, day)
    db_session.commit()

    db_session.refresh(item)
    db_session.refresh(schedule)
    assert item.next_review_at.replace(tzinfo=timezone.utc) == future.replace(
        tzinfo=timezone.utc
    ) or item.next_review_at == future
    assert schedule.due_at == future or schedule.due_at.replace(tzinfo=timezone.utc) == future.replace(
        tzinfo=timezone.utc
    )


def test_empty_review_does_not_invent_and_allows_complete(client, auth, db_session):
    profile, _ = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    day = _days(db_session, curriculum)[0]
    blocks = _blocks(db_session, day)
    review = next(b for b in blocks if b.skill == "review")
    for block in blocks:
        if block.position < review.position:
            assert client.post(
                f"/api/v1/curriculum/block/{block.id}/complete", headers=auth
            ).status_code == 200

    started = client.post(f"/api/v1/curriculum/block/{review.id}/start", headers=auth)
    assert started.status_code == 200
    lesson = started.json()["lesson"]
    assert lesson["queue_empty"] is True
    assert lesson["items"] == []
    assert "Nenhuma revisão está vencida" in (lesson.get("empty_notice") or "")

    completed = client.post(
        f"/api/v1/curriculum/block/{review.id}/complete", headers=auth
    )
    assert completed.status_code == 200
    assert completed.json()["day_completed"] is True


def test_completion_does_not_imply_mastery(db_session):
    profile, _ = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    objective = ensure_en_a1_can_001(db_session)
    db_session.commit()
    for day in _days(db_session, curriculum)[:3]:
        _complete_day(db_session, day)
    db_session.commit()

    progress = db_session.scalar(
        select(UserObjectiveProgress).where(
            UserObjectiveProgress.user_language_id == profile.id,
            UserObjectiveProgress.objective_id == objective.id,
        )
    )
    assert progress is None or progress.state != MasteryState.MASTERED


def test_user_cannot_read_another_users_next_day(client, auth, db_session, other_user):
    outro = db_session.get(User, other_user)
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    profile = UserLanguage(
        user_id=outro.id,
        language_id=language.id,
        diagnostic_completed=True,
        vocabulary_grammar_level=CEFRLevel.A2,
        reading_level=CEFRLevel.A2,
        listening_level=CEFRLevel.A2,
        writing_level=CEFRLevel.A2,
        speaking_level=CEFRLevel.A2,
    )
    db_session.add(profile)
    db_session.commit()
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    day = _days(db_session, curriculum)[0]
    # auth = admin; dia pertence a other_user
    assert client.get(f"/api/v1/curriculum/day/{day.id}", headers=auth).status_code == 404


def test_last_day_next_day_null(client, auth, db_session):
    profile, _ = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    last = _days(db_session, curriculum)[-1]
    _complete_day(db_session, last)
    db_session.commit()

    detail = client.get(f"/api/v1/curriculum/day/{last.id}", headers=auth).json()
    assert detail["day"]["next_day"] is None


def test_refresh_after_complete_shows_next_as_current(client, auth, db_session):
    profile, _ = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    days = _days(db_session, curriculum)
    _complete_day(db_session, days[0])
    db_session.commit()

    a = client.get("/api/v1/curriculum/day/today?language_code=en", headers=auth).json()
    b = client.get("/api/v1/curriculum/day/today?language_code=en", headers=auth).json()
    assert a["day"]["day_number"] == 2
    assert b["day"]["id"] == a["day"]["id"] == days[1].id


def test_pace_ahead_when_completing_early(client, auth, db_session):
    profile, _ = _profile(db_session)
    future_start = date.today() + timedelta(days=5)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=future_start)
    db_session.commit()
    days = _days(db_session, curriculum)
    _complete_day(db_session, days[0])
    _complete_day(db_session, days[1])
    db_session.commit()

    progress = client.get(
        "/api/v1/curriculum/active?language_code=en", headers=auth
    ).json()["progress"]
    assert progress["pace_status"] == "ahead"
    assert progress["pace_delta"] >= 2
