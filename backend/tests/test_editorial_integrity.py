"""Regressions from the multi-language editorial audit; no external calls."""
import pytest
from app.models import ContentUnit
from app.services import lesson_bank
from app.services.learner_context import LearnerContext
from app.services.lesson_envelope import apply_lesson_envelope
from app.services.content_repository import lesson_display_title
from app.services.editorial_validation import valid_generated_lesson
from app.services.speech import _piper_language, UnsupportedTTSLanguage


def context(code="fr"):
    return LearnerContext(code, "Francês", "Français", "B1", "Intermediário", "desc", "placement_test", True, native_language="pt-BR")


def test_french_starter_title_is_pedagogical():
    unit = ContentUnit(title="[starter] reading · A1", payload_json={"title": "Une matinée ordinaire · A1"})
    assert lesson_display_title(unit, "reading") == "Une matinée ordinaire · A1"
    unit.title = "Leitura editorial aprovada"
    assert lesson_display_title(unit, "reading") == unit.title


def test_content_level_not_relabelled_as_requested_level():
    payload = apply_lesson_envelope({"title": "Texto A2", "level": "A2"}, context=context(), mode="reading", provider="curated_library")
    assert payload["level"] == "B1"
    assert payload["content_level"] == "A2"


def test_french_b1_explanation_matches_existing_exercises():
    focus = lesson_bank.grammar_focus("fr", "intermediate")
    assert "imparfait" in focus["explanation"]
    assert "passé composé" in focus["explanation"]
    assert "depuis" in " ".join(focus["patterns"])
    assert focus != lesson_bank.grammar_focus("en", "intermediate")


def test_italian_open_closed_e_not_reversed():
    sound = lesson_bank.pronunciation_focus("it")[1]
    assert "pêssego, e aberto" in sound["how_to_produce"]
    assert "pesca, e fechado" in sound["how_to_produce"]


def test_english_experience_questions_state_required_structure():
    exercises = lesson_bank.grammar_exercises("en", "intermediate")
    for item in exercises:
        if item["answer"] in {"have been", "have seen"}:
            assert "present perfect" in item["prompt"].lower()
    assert "pede um momento específico" not in str(exercises)


@pytest.mark.parametrize("accessor", [*lesson_bank.SKILL_ACCESSORS.values(), lesson_bank.grammar_focus])
def test_unknown_language_cannot_teach_english(accessor):
    with pytest.raises(ValueError):
        accessor("pt-BR", "beginner")


@pytest.mark.parametrize("code,voice", [("en","en"),("es-ES","es"),("fr","fr"),("it","it"),("de","de"),("la","la-ecclesiastical")])
def test_piper_routes_target_language(code, voice):
    assert _piper_language(code) == voice


@pytest.mark.parametrize("code", ["ja", "zh-CN", "unknown"])
def test_piper_never_falls_back_to_english(code):
    with pytest.raises(UnsupportedTTSLanguage):
        _piper_language(code)


def test_generated_content_rejects_known_english_body_for_french():
    foreign = lesson_bank.reading_text("en", "beginner")
    assert not valid_generated_lesson({"title": foreign["title"], "text": foreign["text"], "questions": []}, "reading", "fr")
    french = lesson_bank.reading_text("fr", "beginner")
    assert valid_generated_lesson({"title": french["title"], "text": french["text"], "questions": []}, "reading", "fr")


@pytest.mark.parametrize("payload", [
    {"title":"Texte", "language_code":"en", "text":"Bonjour", "questions":[]},
    {"title":"Texte", "text":"Bonjour", "questions":[{"prompt":"Question", "options":["Oui","Non"], "answer":"Absent"}]},
    {"title":"Texte", "text":"Bonjour", "questions":[{"prompt":"Question", "options":["Oui"," OUI "], "answer":"Oui"}]},
    {"title":"Texte"},
    {"title":"Texte", "text":"Bonjour", "questions":[{"prompt":"Q", "answer":"Oui"}]},
    {"title":"Texte", "text":"Bonjour", "questions":["question"]},
])
def test_invalid_generated_contract_is_rejected(payload):
    assert not valid_generated_lesson(payload, "reading", "fr")


def test_short_known_english_example_is_rejected():
    payload = {"title":"Français", "items":[{"term":"bonjour", "example":"My name is Ana."}]}
    assert not valid_generated_lesson(payload, "vocabulary", "fr")


def test_french_generated_api_uses_payload_title(client, auth, db_session):
    from sqlalchemy import select
    from app.models import Language, User, UserLanguage
    from app.services.content_seed import seed_starter_content
    language = db_session.scalar(select(Language).where(Language.code == "fr"))
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    db_session.add(UserLanguage(user_id=user.id, language_id=language.id, current_level="A1", level_estimate="A1"))
    seed_starter_content(db_session, language_codes={"fr"})
    db_session.commit()
    response = client.post("/api/v1/lessons/generate", json={"language_code":"fr", "mode":"reading"}, headers=auth)
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Une matinée ordinaire · A1"
    assert body["language_code"] == "fr"
    assert body["content_level"] == "A1"
    assert "[starter]" not in body["title"]


def test_all_mock_modes_obey_guard_and_answer_invariants():
    from app.services.ai import MockAIProvider, _MOCK_BUILDERS
    from app.core.levels import LEVEL_DETAILS, LEVEL_ORDER
    for code in lesson_bank.SUPPORTED_LANGUAGES:
        for level in LEVEL_ORDER:
            ctx = LearnerContext(code, "Idioma", "Idioma", level, LEVEL_DETAILS[level]["name_pt"], "desc", "placement_test", True, native_language="pt-BR")
            for mode in _MOCK_BUILDERS:
                payload = MockAIProvider().generate_lesson(mode, ctx)
                assert valid_generated_lesson(payload, mode, code), (code, level, mode)


def test_piper_payload_preserves_french_audio_text(monkeypatch):
    from app.core.config import get_settings
    from app.services.speech import PiperAPITTSProvider
    captured = {}
    class Response:
        content = b"audio"
        headers = {"content-type":"audio/wav"}
        def raise_for_status(self):
            pass
    def post(url, **kwargs):
        captured.update(kwargs["json"])
        return Response()
    monkeypatch.setattr(get_settings(), "tts_base_url", "https://piper.test")
    monkeypatch.setattr(get_settings(), "tts_api_key", "editorial-test-key")
    monkeypatch.setattr("app.services.speech.httpx.post", post)
    text = lesson_bank.listening_script("fr", "beginner")["transcript"]
    PiperAPITTSProvider().synthesize(text, "fr")
    assert captured["text"] == text
    assert captured["language"] == "fr"


def test_generic_activity_generator_does_not_invent_english():
    from app.models import LearningObjective
    from app.services.activity_generator import generate_activities
    objective = LearningObjective(title="Apresentação em francês", can_do="Trocar informação pessoal em francês.",
        target_patterns_json=[{"canonical":"Je m'appelle Ana."}], target_expressions_json=[],
        target_vocabulary_json=[], pedagogy_json={})
    activities = generate_activities(objective)
    text = str(activities)
    for invented in ("Tell me about yourself", "My name is", "Where does your brother live", "I like coffee", "Which sentence"):
        assert invented not in text
    assert not any(a["type"] in {"guided_production", "transfer_question", "multiple_choice"} for a in activities)
    ordered = next(a for a in activities if a["type"] == "word_order")
    assert ordered["tokens"] == ["Je", "m'appelle", "Ana"]


def test_unicode_order_preserves_french_accents():
    from app.models import LearningObjective
    from app.services.activity_generator import generate_activities
    objective = LearningObjective(title="Origem", can_do="Dizer origem", target_patterns_json=["Je viens du Brésil."],
        target_expressions_json=[], target_vocabulary_json=[], pedagogy_json={})
    ordered = next(a for a in generate_activities(objective) if a["type"] == "word_order")
    assert "Brésil" in ordered["tokens"]


def test_cjk_single_expression_gap_does_not_repeat_answer():
    from app.services.activity_generator import _gap_prompt
    assert _gap_prompt("你好") == ("___", "你好")


def test_accepted_variant_never_becomes_incorrect_distractor():
    from app.models import LearningObjective
    from app.services.activity_generator import generate_activities
    objective = LearningObjective(title="Apresentar-se", can_do="Apresentar-se", target_patterns_json=[
        {"canonical":"Je suis Ana.", "accepted":["Je m'appelle Ana."]},
        "Je m'appelle Ana.", "Je travaille ici.", "Je travaille ici."],
        target_expressions_json=[], target_vocabulary_json=[], pedagogy_json={})
    question = next(a for a in generate_activities(objective) if a["type"] == "multiple_choice")
    assert [o["text"] for o in question["options"]] == ["Je suis Ana.", "Je travaille ici."]
