"""Forma contextual do vocabulário: dado declarado, nunca inferido da frase."""

from __future__ import annotations

from app.core.levels import CEFRLevel, LevelSource
from app.services.learner_context import LearnerContext
from app.services.lesson_bank import BAND_ELEMENTARY, vocabulary
from app.services.lesson_envelope import apply_lesson_envelope
from app.services.lexical_form import normalize_lexical_item


def _context(**overrides) -> LearnerContext:
    base = dict(
        language_code="de",
        language_name_pt="Alemão",
        language_native_name="Deutsch",
        level=CEFRLevel.A1,
        level_name_pt="A1",
        level_description="desc",
        level_source=LevelSource.PLACEMENT_TEST,
        level_is_estimated=True,
    )
    base.update(overrides)
    return LearnerContext(**base)


def test_distinct_form_is_kept():
    item = normalize_lexical_item(
        {
            "term": "können",
            "example": "Ich kann Deutsch.",
            "example_form": "kann",
            "form_note": "“kann” é uma forma de “können” usada com ich.",
        }
    )
    assert item["example_form"] == "kann"
    assert "können" in item["form_note"]


def test_same_form_is_dropped_without_guessing_from_the_sentence():
    item = normalize_lexical_item(
        {
            "term": "water",
            "example": "Can I have some water, please?",
            "example_form": "water",
            "form_note": "nota redundante",
        }
    )
    assert "example_form" not in item
    assert "form_note" not in item
    assert item["example"] == "Can I have some water, please?"


def test_missing_fields_do_not_invent_a_form():
    item = normalize_lexical_item(
        {"term": "können", "example": "Ich kann Deutsch.", "translation": "poder"}
    )
    assert "example_form" not in item
    assert "form_note" not in item
    assert item["translation"] == "poder"


def test_empty_and_blank_fields_are_removed():
    item = normalize_lexical_item(
        {"term": "merci", "example": "Merci.", "example_form": "  ", "form_note": ""}
    )
    assert "example_form" not in item
    assert "form_note" not in item


def test_spanish_bank_declares_soler_without_a_language_rule():
    items = vocabulary("es-ES", BAND_ELEMENTARY)
    soler = next(item for item in items if item["term"] == "soler")
    normalized = normalize_lexical_item(soler)
    assert normalized["example"] == "Suelo desayunar a las ocho."
    assert normalized["example_form"] == "suelo"
    assert "soler" in normalized["form_note"]


def test_envelope_keeps_declared_form_and_strips_redundant_one():
    payload = {
        "title": "Vocabulário",
        "objective": "Formas",
        "items": [
            {
                "term": "können",
                "translation": "poder",
                "example": "Ich kann Deutsch.",
                "example_translation": "Eu sei alemão.",
                "usage_note": "Verbo modal.",
                "example_form": "kann",
                "form_note": "“kann” é uma forma de “können” usada com ich.",
            },
            {
                "term": "danke",
                "translation": "obrigado",
                "example": "Danke.",
                "example_translation": "Obrigado.",
                "usage_note": "Curto.",
                "example_form": "Danke",
                "form_note": "igual",
            },
        ],
    }
    lesson = apply_lesson_envelope(
        payload,
        context=_context(),
        mode="vocabulary",
        provider="mock",
    )
    können, danke = lesson["items"]
    assert können["example_form"] == "kann"
    assert "example_form" not in danke
    assert "form_note" not in danke
    assert danke["example"] == "Danke."
