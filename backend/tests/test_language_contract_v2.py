"""Language contract v2: target, native support and third-language guard."""

import pytest

from app.services.learner_language_contract import (
    apply_language_contract,
    deliverable,
    dictation_contract,
    language_safety,
)
from app.services.lesson_bank import reading_text


def test_french_contract_keeps_target_and_portuguese_support_apart():
    activity = apply_language_contract({
        "type": "fill_gap",
        "prompt": "Je ___ étudiant.",
        "prompt_native": "Complete a frase.",
        "prompt_pt": "Complete a frase.",
        "target_language": "fr",
        "native_language": "pt-BR",
    })
    assert activity["target_language"] == "fr"
    assert activity["native_language"] == "pt-BR"
    assert activity["prompt_target"] == "Je ___ étudiant."
    assert activity["prompt_native"] == "Complete a frase."
    assert activity["interaction_family"] == "inline_gap"


def test_prompt_pt_is_not_promoted_when_native_support_is_absent():
    activity = apply_language_contract({
        "type": "guided_production",
        "prompt": "Ich heiße Ana.",
        "prompt_pt": "Eu me chamo Ana.",
        "target_language": "de",
        "native_language": "pt-BR",
    })
    assert "prompt_native" not in activity
    assert activity["prompt_target"] == "Ich heiße Ana."


@pytest.mark.parametrize("target", ["fr", "es-ES", "de", "en"])
def test_known_english_clone_is_not_deliverable(target):
    english = reading_text("en", "beginner")
    payload = {
        "title": english["title"],
        "text": english["text"],
        "target_language": target,
        "native_language": "pt-BR",
    }
    if target == "en":
        assert language_safety(payload, target, "pt-BR") != "language_invalid"
        assert deliverable(payload, target, "pt-BR")
    else:
        assert language_safety(payload, target, "pt-BR") == "language_invalid"
        contracted = apply_language_contract(payload)
        assert contracted["quality_status"] == "language_invalid"
        assert deliverable(contracted, target, "pt-BR") is False


def test_dictation_hides_the_transcript():
    item = dictation_contract(
        audio_text="Je suis d'accord.",
        canonical_answer="Je suis d'accord.",
        target_language="fr",
        native_language="pt-BR",
        instruction_native="Escreva o que ouviu.",
    )
    assert item["type"] == "dictation"
    assert item["interaction_family"] == "dictation"
    assert item["show_text"] is False
    assert item["prompt_target"] == ""
    assert item["instruction_native"] == "Escreva o que ouviu."
    assert item["compare"] == "normalized_text"


_CLEAN = {
    "fr": "Je pense que ce plan est utile, mais il coûte trop cher.",
    "es-ES": "No estoy de acuerdo con este plan porque cuesta demasiado dinero.",
    "de": "Ich bin mit diesem Plan nicht einverstanden, weil er zu viel kostet.",
    "en": "I do not agree with this plan because it costs too much money.",
}
_ENGLISH = "The train leaves at eight from platform two and the ticket office is closed."


@pytest.mark.parametrize("target", ["fr", "es-ES", "de", "en"])
def test_detector_keeps_a_clean_target_sentence(target):
    payload = {
        "prompt_target": _CLEAN[target],
        "prompt_native": "Leia a frase e responda.",
        "target_language": target,
        "native_language": "pt-BR",
        "quality_status": "approved",
    }
    assert language_safety(payload, target, "pt-BR") == "approved"
    assert deliverable(payload, target, "pt-BR")


@pytest.mark.parametrize("target", ["fr", "es-ES", "de"])
def test_detector_rejects_high_confidence_english_in_another_target(target):
    payload = {
        "prompt_target": _ENGLISH,
        "target_language": target,
        "native_language": "pt-BR",
        "quality_status": "approved",
    }
    assert language_safety(payload, target, "pt-BR") == "language_invalid"
    contracted = apply_language_contract(payload)
    assert contracted["quality_status"] == "language_invalid"
    assert deliverable(contracted, target, "pt-BR") is False


def test_detector_rejects_french_inside_an_english_target():
    payload = {
        "prompt_target": "Vous n'êtes pas d'accord avec un collègue et vous expliquez pourquoi, poliment.",
        "target_language": "en",
        "native_language": "pt-BR",
        "quality_status": "approved",
    }
    assert language_safety(payload, "en", "pt-BR") == "language_invalid"
    assert deliverable(payload, "en", "pt-BR") is False


def test_short_target_text_is_not_blocked_by_the_detector():
    payload = {
        "prompt_target": "pourtant",
        "target_language": "fr",
        "native_language": "pt-BR",
        "quality_status": "approved",
    }
    assert language_safety(payload, "fr", "pt-BR") == "approved"
    assert deliverable(payload, "fr", "pt-BR")


def test_low_confidence_target_text_needs_review_and_is_not_delivered():
    payload = {
        "prompt_target": "Je ne suis pas d'accord.",
        "target_language": "fr",
        "native_language": "pt-BR",
        "quality_status": "approved",
    }
    assert language_safety(payload, "fr", "pt-BR") == "review_required"
    contracted = apply_language_contract(payload)
    assert contracted["quality_status"] == "review_required"
    assert deliverable(contracted, "fr", "pt-BR") is False
