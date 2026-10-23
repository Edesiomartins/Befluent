"""Cenários de conversa no idioma-alvo, com apoio em português só para pt-BR."""

import pytest

from app.services.lesson_bank import SUPPORTED_LANGUAGES, conversation_situation


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_scenario_is_in_the_target_language_not_portuguese(language):
    situation = conversation_situation(language, "beginner", native_language="pt-BR")
    assert situation["scenario_target"]
    assert situation["situation"] == situation["scenario_target"]
    assert situation["scenario_target"] != situation["scenario_native"]
    assert "Você cumprimenta" not in situation["scenario_target"]
    assert situation["scenario_native"] == "Você cumprimenta alguém que acabou de conhecer."
    assert situation["target_language"] == language


def test_french_intermediate_scenario_is_french():
    situation = conversation_situation("fr", "intermediate", native_language="pt-BR")
    assert situation["scenario_target"].startswith("Vous n'êtes pas d'accord")
    assert "português" not in situation["scenario_target"].casefold()
    assert situation["scenario_native"].startswith("Você discorda")
    assert situation["focus_native"]


def test_non_portuguese_native_does_not_receive_portuguese_as_native_support():
    situation = conversation_situation("fr", "beginner", native_language="en")
    assert situation["scenario_target"].startswith("Vous rencontrez")
    assert situation["scenario_native"] is None
    assert situation["instruction_native"] is None
