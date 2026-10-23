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
