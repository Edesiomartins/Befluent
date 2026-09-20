"""Latim clássico (`la-classical`) — isolamento vs. eclesiástico (`la`)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models import Language, PlacementItem, UserLanguage
from app.services import lesson_bank


def test_seed_includes_la_and_la_classical_as_distinct(db_session):
    codes = {row.code for row in db_session.scalars(select(Language)).all()}
    assert "la" in codes
    assert "la-classical" in codes

    la = db_session.scalar(select(Language).where(Language.code == "la"))
    classical = db_session.scalar(select(Language).where(Language.code == "la-classical"))
    assert la is not None and classical is not None
    assert la.id != classical.id
    assert "eclesiástico" in la.name_pt.lower()
    assert "clássico" in classical.name_pt.lower()


def test_activate_la_classical(client, auth):
    response = client.post(
        "/api/v1/languages/activate", json={"code": "la-classical"}, headers=auth
    )
    assert response.status_code == 200
    assert response.json()["code"] == "la-classical"


def test_progress_la_does_not_affect_la_classical(client, auth):
    assert client.post("/api/v1/languages/activate", json={"code": "la"}, headers=auth).status_code == 200
    la_vocab = client.post(
        "/api/v1/vocabulary",
        json={"language_code": "la", "term": "caelum", "translation_pt": "céu"},
        headers=auth,
    )
    assert la_vocab.status_code == 200

    assert (
        client.post(
            "/api/v1/languages/activate", json={"code": "la-classical"}, headers=auth
        ).status_code
        == 200
    )
    classical_vocab = client.post(
        "/api/v1/vocabulary",
        json={"language_code": "la-classical", "term": "rosa", "translation_pt": "rosa"},
        headers=auth,
    )
    assert classical_vocab.status_code == 200

    due_classical = client.get(
        "/api/v1/reviews/due?language_code=la-classical", headers=auth
    )
    assert due_classical.status_code == 200
    terms_classical = {item["payload"]["term"] for item in due_classical.json()}
    assert "rosa" in terms_classical
    assert "caelum" not in terms_classical

    due_la = client.get("/api/v1/reviews/due?language_code=la", headers=auth)
    assert due_la.status_code == 200
    terms_la = {item["payload"]["term"] for item in due_la.json()}
    assert "caelum" in terms_la
    assert "rosa" not in terms_la


def test_placement_level_isolated_between_latin_modalities(client, auth, db_session):
    """Nível em `la` não classifica `la-classical` (UserLanguage distintos)."""
    assert client.post("/api/v1/languages/activate", json={"code": "la"}, headers=auth).status_code == 200
    assert (
        client.post(
            "/api/v1/languages/activate", json={"code": "la-classical"}, headers=auth
        ).status_code
        == 200
    )

    la = db_session.scalar(select(Language).where(Language.code == "la"))
    classical = db_session.scalar(select(Language).where(Language.code == "la-classical"))
    assert la and classical

    ul_la = db_session.scalar(select(UserLanguage).where(UserLanguage.language_id == la.id))
    ul_classical = db_session.scalar(
        select(UserLanguage).where(UserLanguage.language_id == classical.id)
    )
    assert ul_la is not None and ul_classical is not None
    assert ul_la.id != ul_classical.id

    ul_la.current_level = "B1"
    ul_la.level_source = "placement_test"
    db_session.commit()

    db_session.refresh(ul_classical)
    assert ul_classical.current_level != "B1"


def test_placement_items_exist_for_la_classical(db_session):
    items = list(
        db_session.scalars(
            select(PlacementItem).where(PlacementItem.language_code == "la-classical")
        ).all()
    )
    assert len(items) >= 10
    prompts = " ".join((item.prompt or "") for item in items).lower()
    assert "clássica" in prompts or "classica" in prompts or "clássico" in prompts


def test_lesson_bank_supports_la_classical():
    assert "la-classical" in lesson_bank.SUPPORTED_LANGUAGES
    for band in (
        lesson_bank.BAND_BEGINNER,
        lesson_bank.BAND_ELEMENTARY,
        lesson_bank.BAND_INTERMEDIATE,
        lesson_bank.BAND_UPPER,
    ):
        vocab = lesson_bank.vocabulary("la-classical", band)
        assert vocab, f"vocabulário vazio em {band}"
        notes = " ".join(str(item.get("usage_note") or "") for item in vocab).lower()
        assert "/tʃ/" not in notes


def test_pronunciation_focus_classical_not_ecclesiastical():
    focus = lesson_bank.pronunciation_focus("la-classical")
    joined = " ".join(
        f"{x.get('sound', '')} {x.get('how_to_produce', '')}" for x in focus
    ).lower()
    assert "/k/" in joined
    assert "/tʃ/" not in joined


def test_kokoro_voice_rejects_la_classical():
    from app.services.speech import UnsupportedTTSLanguage, _voice_for_language

    class _S:
        tts_voice = None

    with pytest.raises(UnsupportedTTSLanguage) as exc:
        _voice_for_language("la-classical", _S())
    assert exc.value.language_code == "la-classical"


def test_bcp47_mapping_for_classical():
    from app.services.language_codes import to_bcp47

    assert to_bcp47("la-classical") in {"la", "la-x-classical"}
    assert to_bcp47("la") == "la"
