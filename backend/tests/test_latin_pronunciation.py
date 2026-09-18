"""Notas de pronúncia latina devem bater com as letras reais do termo."""

from app.services.latin_pronunciation import (
    fix_latin_usage_note,
    sanitize_latin_vocabulary_payload,
)


def test_gloria_note_does_not_claim_soft_g_before_e_i():
    bad = "G antes de e/i = /dʒ/ (como 'dj' em 'djado'); aqui g antes de l mantém /g/."
    fixed = fix_latin_usage_note("gloria", bad)
    assert fixed is not None
    assert "e/i" not in fixed.split("só ocorre")[0] or "permanece /g/" in fixed
    assert "/g/" in fixed
    assert "gloria" in fixed.casefold() or "gl" in fixed.casefold()
    # Não deve abrir afirmando que ESTE g soa /dʒ/
    assert not fixed.lower().startswith("g antes de e/i")


def test_regina_keeps_soft_g_note():
    note = "G antes de e/i = /dʒ/ (como em Regina)."
    assert fix_latin_usage_note("Regina", note) == note


def test_caelum_keeps_soft_c_note():
    note = "C antes de ae soa /tʃ/ (como 'ch' em 'chuva')."
    assert fix_latin_usage_note("caelum", note) == note


def test_sanitize_vocabulary_payload_fixes_items():
    payload = {
        "title": "Teste",
        "items": [
            {
                "term": "gloria",
                "translation": "glória",
                "usage_note": "G antes de e/i = /dʒ/; aqui g antes de l mantém /g/.",
            }
        ],
    }
    out = sanitize_latin_vocabulary_payload(payload)
    assert "permanece /g/" in out["items"][0]["usage_note"]
    assert not out["items"][0]["usage_note"].lower().startswith("g antes de e/i")
