"""Completion regressions with the production autoflush configuration."""
import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.placement_tests import complete_test
from app.core.levels import Skill
from app.models import (
    Base, PlacementItem, PlacementTest, PlacementTestAnswer,
    PlacementTestSection, User,
)


def prepared_test(db):
    user = db.scalar(select(User).where(User.email == "admin@befluent.local"))
    test = PlacementTest(user_id=user.id, language_code="en", status="in_progress")
    db.add(test)
    db.flush()
    for skill in (Skill.VOCABULARY_GRAMMAR, Skill.READING, Skill.LISTENING, Skill.WRITING):
        items = list(db.scalars(select(PlacementItem).where(
            PlacementItem.language_code == "en", PlacementItem.skill == skill,
        ).limit(4 if skill != Skill.WRITING else 1)))
        for item in items:
            db.add(PlacementTestAnswer(
                test_id=test.id, item_id=item.id, skill=skill, cefr_level="A2",
                normalized_score=0.96 if skill == Skill.WRITING else 1.0,
                evaluated_by="heuristic" if skill == Skill.WRITING else "auto",
            ))
    db.commit()
    db.autoflush = False
    return user, test


@pytest.mark.parametrize("preexisting", [False, True])
def test_complete_with_writing_and_retry_preserves_all_rows(db_session, preexisting):
    user, test = prepared_test(db_session)
    section_ids = {}
    if preexisting:
        for skill in (Skill.WRITING, Skill.READING):
            section = PlacementTestSection(test_id=test.id, skill=skill, score=0.1)
            db_session.add(section)
            db_session.flush()
            section_ids[skill] = section.id
        db_session.commit()

    first = complete_test(test.id, db_session, user)
    assert first["status"] == "completed"
    assert first["curriculum"] is not None
    sections = list(db_session.scalars(select(PlacementTestSection).where(
        PlacementTestSection.test_id == test.id)))
    assert len(sections) == 5
    assert len({section.skill for section in sections}) == 5
    for section in sections:
        if section.skill in section_ids:
            assert section.id == section_ids[section.skill]
        if section.skill == Skill.WRITING:
            assert section.status == "calibrating"
            assert section.score == 0.96
            assert section.estimated_level is None
        elif section.skill == Skill.SPEAKING:
            assert section.status == "not_available"
        else:
            assert section.status == "assessed"
            assert section.estimated_level == "A2"

    # Compare every table, including curriculum descendants, goals and results.
    def snapshot():
        return {table.name: list(db_session.execute(select(table)).mappings())
                for table in Base.metadata.sorted_tables}
    before = snapshot()
    second = complete_test(test.id, db_session, user)
    # SQLite drops timezone metadata on reload; compare the same UTC instant.
    for payload in (first, second):
        payload["completed_at"] = datetime.fromisoformat(payload["completed_at"]).replace(tzinfo=timezone.utc)
    assert second == first
    assert snapshot() == before


def test_sections_unique_constraint_remains_enforced(db_session):
    _, test = prepared_test(db_session)
    db_session.add_all([
        PlacementTestSection(test_id=test.id, skill=Skill.WRITING),
        PlacementTestSection(test_id=test.id, skill=Skill.WRITING),
    ])
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_unscored_writing_uses_nonnullable_scores_without_cefr(db_session):
    user, test = prepared_test(db_session)
    answer = db_session.scalar(select(PlacementTestAnswer).where(
        PlacementTestAnswer.test_id == test.id, PlacementTestAnswer.skill == Skill.WRITING))
    answer.normalized_score = None
    db_session.commit()
    result = complete_test(test.id, db_session, user)
    writing = next(section for section in result["skills"] if section["skill"] == "writing")
    assert writing["status"] == "calibrating"
    assert writing["estimated_level"] is None
    assert writing["score"] == 0.0
    assert writing["max_score"] == 0.0


@pytest.mark.parametrize("api_error", [False, True])
def test_failed_finalization_rolls_back_and_can_retry(db_session, monkeypatch, api_error):
    from app.api import placement_tests
    from app.core.errors import APIError
    user, test = prepared_test(db_session)
    original = placement_tests.ensure_active_curriculum
    def interrupted(*args, **kwargs):
        original(*args, **kwargs)
        if api_error:
            raise APIError(409, "curriculum_interrupted", "Interrupted before commit")
        raise RuntimeError("response interrupted before commit")
    monkeypatch.setattr(placement_tests, "ensure_active_curriculum", interrupted)
    with pytest.raises(APIError if api_error else RuntimeError):
        complete_test(test.id, db_session, user)
    db_session.rollback()
    assert db_session.get(PlacementTest, test.id).status == "in_progress"
    assert not list(db_session.scalars(select(PlacementTestSection)))
    monkeypatch.setattr(placement_tests, "ensure_active_curriculum", original)
    assert complete_test(test.id, db_session, user)["status"] == "completed"


def test_partial_consolidation_reuses_profile_and_curriculum(db_session):
    user, test = prepared_test(db_session)
    complete_test(test.id, db_session, user)
    ids = {table.name: {row[0] for row in db_session.execute(select(table.c.id))}
           for table in Base.metadata.sorted_tables if "id" in table.c}
    # Simulate persisted partial state from an older implementation/import.
    test.status = "in_progress"
    db_session.commit()
    assert complete_test(test.id, db_session, user)["status"] == "completed"
    assert {table.name: {row[0] for row in db_session.execute(select(table.c.id))}
            for table in Base.metadata.sorted_tables if "id" in table.c} == ids
