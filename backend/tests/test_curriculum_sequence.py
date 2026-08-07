"""Sequência pedagógica do dia: blocos travados até o anterior concluir."""

from datetime import date

from sqlalchemy import select

from app.core.curriculum import LessonPhase, block_phase
from app.core.levels import CEFRLevel, LevelSource
from app.models import CurriculumBlock, CurriculumDay, CurriculumWeek, Language, User, UserLanguage
from app.services.curriculum_generator import generate_curriculum

START = date(2026, 8, 3)


def _profile(db, language_code="en", entry=CEFRLevel.A2):
    user = db.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db.scalar(select(Language).where(Language.code == language_code))
    profile = UserLanguage(
        user_id=user.id,
        language_id=language.id,
        is_active=True,
        onboarding_completed=True,
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


def _full_day(db, curriculum):
    days = list(
        db.scalars(
            select(CurriculumDay)
            .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
            .where(CurriculumWeek.curriculum_id == curriculum.id)
            .order_by(CurriculumDay.day_number)
        )
    )
    for day in days:
        blocks = list(
            db.scalars(
                select(CurriculumBlock)
                .where(CurriculumBlock.day_id == day.id)
                .order_by(CurriculumBlock.position)
            )
        )
        if len(blocks) >= 5:
            return day, blocks
    day = days[0]
    blocks = list(
        db.scalars(
            select(CurriculumBlock)
            .where(CurriculumBlock.day_id == day.id)
            .order_by(CurriculumBlock.position)
        )
    )
    return day, blocks


def test_day_follows_activate_to_consolidate_phases(db_session):
    profile, _ = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    _, blocks = _full_day(db_session, curriculum)
    phases = [block_phase(block.skill) for block in blocks]
    assert phases[0] == LessonPhase.ACTIVATE
    assert LessonPhase.STRUCTURE in phases
    assert LessonPhase.INPUT in phases or LessonPhase.OUTPUT in phases
    assert phases[-1] == LessonPhase.CONSOLIDATE


def test_start_block_rejects_skipping_ahead(client, auth, db_session):
    profile, _ = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    _, blocks = _full_day(db_session, curriculum)
    assert len(blocks) >= 2
    locked = client.post(
        f"/api/v1/curriculum/block/{blocks[1].id}/start", headers=auth, json={}
    )
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "curriculum_block_locked"

    opened = client.post(
        f"/api/v1/curriculum/block/{blocks[0].id}/start", headers=auth, json={}
    )
    assert opened.status_code == 200
    assert opened.json()["block"]["locked"] is False
    assert opened.json()["block"]["is_current"] is True


def test_day_payload_marks_locked_blocks(client, auth, db_session):
    profile, _ = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    day, _ = _full_day(db_session, curriculum)
    detail = client.get(f"/api/v1/curriculum/day/{day.id}", headers=auth)
    assert detail.status_code == 200
    body = detail.json()["day"]
    assert "Ativar" in body["sequence_label"]
    blocks = body["blocks"]
    assert blocks[0]["locked"] is False
    assert blocks[0]["is_current"] is True
    assert blocks[1]["locked"] is True

    first_id = blocks[0]["id"]
    assert (
        client.post(f"/api/v1/curriculum/block/{first_id}/start", headers=auth, json={}).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/curriculum/block/{first_id}/complete", headers=auth, json={}
        ).status_code
        == 200
    )
    again = client.get(f"/api/v1/curriculum/day/{day.id}", headers=auth).json()["day"]["blocks"]
    assert again[1]["locked"] is False
    assert again[1]["is_current"] is True


def test_dashboard_prefers_curriculum_path(client, auth, db_session):
    profile, _ = _profile(db_session)
    generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    dash = client.get("/api/v1/dashboard", headers=auth)
    assert dash.status_code == 200
    body = dash.json()
    assert body["next_activity"]["kind"] == "curriculum"
    assert "/cronograma/dia/" in body["next_activity"]["href"]
    assert body["day_plan"]["source"] == "curriculum"
