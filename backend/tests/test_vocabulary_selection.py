"""Seleção diária de vocabulário — subconjunto novo vs spiral."""

from __future__ import annotations

from app.core.levels import CEFRLevel, LevelSource
from app.services.ai import MockAIProvider
from app.services.learner_context import LearnerContext
from app.services import lesson_bank
from app.services.vocabulary_selection import DAILY_NEW_COUNT, select_daily_vocabulary


def _ctx(**overrides) -> LearnerContext:
    base = dict(
        language_code="en",
        language_name_pt="Inglês",
        language_native_name="English",
        level=CEFRLevel.B2,
        level_name_pt="B2 — Intermediário superior",
        level_description="desc",
        level_source=LevelSource.PLACEMENT_TEST,
        level_is_estimated=True,
        day_number=1,
        curriculum_week_theme="Argumentar e refutar",
    )
    base.update(overrides)
    return LearnerContext(**base)


def test_upper_bank_expanded_with_themes():
    items = lesson_bank.vocabulary("en", lesson_bank.BAND_UPPER)
    assert len(items) >= 40
    themed = [i for i in items if i.get("themes")]
    assert len(themed) >= 40
    assert any("to back up" == i["term"] for i in items)


def test_daily_subset_size_and_roles():
    selected = select_daily_vocabulary(
        "en",
        lesson_bank.BAND_UPPER,
        day_number=1,
        week_theme="Argumentar e refutar",
    )
    assert len(selected["new_items"]) == DAILY_NEW_COUNT
    assert selected["selection_policy"] == "curriculum_history_first_exposure"
    assert selected["content_roles"]["items"] == "new_first_exposure"
    assert selected["content_roles"]["revisited_items"] == "spiral_curriculum"
    assert selected["content_roles"]["srs"] == "review_block_only"


def test_day1_and_day2_new_terms_differ_same_theme():
    d1 = select_daily_vocabulary(
        "en",
        lesson_bank.BAND_UPPER,
        day_number=1,
        week_theme="Argumentar e refutar",
    )
    d2 = select_daily_vocabulary(
        "en",
        lesson_bank.BAND_UPPER,
        day_number=2,
        week_theme="Argumentar e refutar",
        recycled_items=d1["new_items"],
    )
    t1 = {i["term"].casefold() for i in d1["new_items"]}
    t2 = {i["term"].casefold() for i in d2["new_items"]}
    assert t1
    assert t2
    assert t1 != t2
    assert not t1 & t2


def test_mock_vocabulary_payload_exposes_roles():
    lesson = MockAIProvider().generate_lesson("vocabulary", _ctx(day_number=1))
    assert len(lesson["items"]) == DAILY_NEW_COUNT
    assert "content_roles" in lesson
    assert lesson["content_roles"]["items"] == "new_first_exposure"
    assert lesson["selection_policy"] == "curriculum_history_first_exposure"

    day2 = MockAIProvider().generate_lesson(
        "vocabulary",
        _ctx(day_number=2, recycled_items=list(lesson["items"])),
    )
    assert {i["term"] for i in lesson["items"]} != {i["term"] for i in day2["items"]}
    assert len(day2["revisited_items"]) >= 1
