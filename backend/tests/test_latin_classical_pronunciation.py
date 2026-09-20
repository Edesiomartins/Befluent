"""Regras de pronúncia clássica reconstruída (isoladas do eclesiástico)."""

from __future__ import annotations

from app.services.latin_classical_pronunciation import (
    CLASSICAL_PRONUNCIATION_CONVENTION,
    classical_example_guide,
    describe_classical_rule,
)


def test_convention_is_documented():
    text = CLASSICAL_PRONUNCIATION_CONVENTION.lower()
    assert "reconstruída" in text or "reconstruida" in text


def test_examples_cover_minimal_set():
    guide = classical_example_guide()
    required = {
        "caelum",
        "caesar",
        "cicero",
        "ecclesia",
        "via",
        "vinum",
        "gratia",
        "ratio",
        "regina",
        "angelus",
        "sanctus",
        "credo",
        "quattuor",
        "philosophia",
    }
    keys = {k.lower() for k in guide}
    assert required <= keys


def test_caelum_is_hard_c_not_ecclesiastical_ch():
    note = describe_classical_rule("caelum")
    assert "/k/" in note or "káe" in note.lower() or "kae" in note.lower()
    assert "/tʃ/" not in note
    assert "ché" not in note.lower()


def test_v_is_approximated_as_w():
    note = describe_classical_rule("via")
    assert "/w/" in note or "≈ /w/" in note
