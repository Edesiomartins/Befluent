"""Língua nativa não é inferida do alvo, navegador ou interface."""
import pytest
from sqlalchemy import select
from app.models import User

@pytest.fixture(autouse=True)
def legacy_native_null(db_session):
    user = db_session.scalar(select(User))
    user.native_language = None
    db_session.commit()


def test_profile_exposes_legacy_null(client, auth):
    body = client.get("/api/v1/profile").json()
    assert body["native_language"] is None
    assert body["native_language_required"] is True
    assert "pt-BR" in body["native_language_options"]
    assert client.get("/api/v1/auth/me").json()["native_language"] is None


def test_native_language_patch_persists_without_name(client, auth, db_session):
    response = client.patch("/api/v1/profile", json={"native_language":"en"}, headers=auth)
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Admin"
    assert body["native_language"] == "en"
    assert body["native_language_required"] is False
    db_session.expire_all()
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    assert user.native_language == "en"
    assert client.get("/api/v1/auth/me").json()["native_language"] == "en"


def test_omitted_native_preserved_explicit_null_clears(client, auth):
    assert client.patch("/api/v1/profile", json={"native_language":"pt-BR"}, headers=auth).status_code == 200
    body = client.patch("/api/v1/profile", json={"name":"Nome atualizado"}, headers=auth).json()
    assert body["native_language"] == "pt-BR"
    body = client.patch("/api/v1/profile", json={"native_language":None}, headers=auth).json()
    assert body["native_language"] is None
    assert body["native_language_required"] is True


@pytest.mark.parametrize("code", ["xx", "en-US", "pt", "la-classical", "", 123])
def test_invalid_native_code_rejected(client, auth, code):
    response = client.patch("/api/v1/profile", json={"native_language":code}, headers=auth)
    assert response.status_code == 422
    assert client.get("/api/v1/profile").json()["native_language"] is None


def test_onboarding_collects_native_and_preserves_it_when_omitted(client, auth):
    data = {"language_code":"fr", "level_choice":"later", "goals":["Viajar"], "native_language":"pt-BR"}
    response = client.post("/api/v1/onboarding/complete", json=data, headers=auth)
    assert response.status_code == 200, response.text
    assert response.json()["native_language"] == "pt-BR"
    data.pop("native_language")
    data["language_code"] = "de"
    assert client.post("/api/v1/onboarding/complete", json=data, headers=auth).json()["native_language"] == "pt-BR"


def test_context_carries_explicit_pair_and_level(db_session):
    from app.services.learner_context import build_context
    user = db_session.scalar(select(User))
    user.native_language = "en"
    db_session.commit()
    context = build_context(db_session, user, "de")
    text = context.to_prompt_context()
    assert context.native_language == "en"
    assert "target_language=de" in text
    assert "native_language=en" in text
    assert "CEFR=A2" in text
    assert "Idioma nativo do aluno: português do Brasil" not in text


@pytest.mark.parametrize("level,explanation", [("PRE_A1","pt-BR"),("A1","pt-BR"),("A2","pt-BR"),("B1","fr"),("B2","fr"),("C1","fr"),("C2","fr")])
def test_cefr_language_policy(level, explanation):
    from app.services.language_policy import language_policy
    policy = language_policy("fr", "pt-BR", level)
    assert policy["explanation_language"] == explanation
    assert policy["allowed_languages"] == ["fr","pt-BR"]
    assert "percent" not in str(policy)


def test_missing_native_policy_never_guesses():
    from app.services.language_policy import language_policy
    policy = language_policy("fr", None, "A1")
    assert policy["native_language_required"] is True
    assert policy["explanation_language"] == "fr"
    assert policy["allowed_languages"] == ["fr"]


def test_guard_checks_logic_and_allows_english_only_as_native_support():
    from app.services.editorial_validation import valid_generated_lesson
    payload = {"title":"Grammaire", "explanation":"We use the present simple to describe habits.", "examples":[], "exercises":[]}
    assert not valid_generated_lesson(payload, "grammar", "fr", native_language="pt-BR")
    assert valid_generated_lesson(payload, "grammar", "de", native_language="en")
    assert not valid_generated_lesson(payload, "grammar", "fr", native_language=None)


def test_primary_german_body_not_replaced_by_native_english():
    from app.services.editorial_validation import valid_generated_lesson
    from app.services import lesson_bank
    english = lesson_bank.reading_text("en","beginner")
    payload = {"title":"Lesen", "text":english["text"], "questions":[]}
    assert not valid_generated_lesson(payload,"reading","de",native_language="en")


def test_static_mock_refuses_unavailable_native_support():
    from app.services.ai import MockAIProvider
    from app.services.learner_context import LearnerContext
    from app.core.errors import APIError
    context = LearnerContext("de","Alemão","Deutsch","A1","A1","desc","self_declared",False,native_language="en")
    with pytest.raises(APIError) as error:
        MockAIProvider().generate_lesson("grammar",context)
    assert error.value.code == "native_support_unavailable"


@pytest.mark.parametrize("target,native", [("fr","pt-BR"),("de","en"),("en","pt-BR")])
def test_all_mode_prompts_receive_pair_cefr_and_third_language_rule(target, native):
    from app.services.learner_context import LearnerContext
    from app.prompts.library import MODE_PROMPTS, get_output_contract
    context = LearnerContext(target,"Idioma","Idioma","A2","A2","desc","self_declared",False,native_language=native)
    for mode, template in MODE_PROMPTS.items():
        prompt = template.render(context.to_prompt_context(), get_output_contract(mode))
        assert f"target_language={target}" in prompt
        assert f"native_language={native}" in prompt
        assert "CEFR=A2" in prompt
        assert "Do not use any third language in learner-facing content unless the activity explicitly requires it." in prompt
        assert "Português é permitido" not in prompt


def test_missing_native_mock_does_not_guess():
    from app.services.ai import MockAIProvider
    from app.services.learner_context import LearnerContext
    from app.core.errors import APIError
    context = LearnerContext("fr","Francês","Français","A1","A1","desc","self_declared",False)
    with pytest.raises(APIError) as error:
        MockAIProvider().generate_lesson("grammar", context)
    assert error.value.code == "native_language_required"


def test_stored_known_english_logic_rejected_and_history_not_relabelled():
    from app.services.language_policy import ensure_stored_content_language
    from app.core.errors import APIError
    with pytest.raises(APIError) as error:
        ensure_stored_content_language({"language_code":"fr","explanation":"We use the present simple to describe habits."}, "pt-BR")
    assert error.value.code == "lesson_language_invalid"
    with pytest.raises(APIError) as error:
        ensure_stored_content_language({"native_language":"pt-BR","language_code":"de"}, "en")
    assert error.value.code == "lesson_native_language_mismatch"


def test_native_is_part_of_cache_identity():
    from app.services.ai_cache import build_cache_key
    assert build_cache_key(capability="grammar", language_code="de", native_language="en") != build_cache_key(capability="grammar",language_code="de",native_language="pt-BR")


def test_migration_native_null_roundtrip(tmp_path, monkeypatch):
    from pathlib import Path
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect, text
    from app.core.config import get_settings
    url = f"sqlite:///{(tmp_path / 'native.db').as_posix()}"
    monkeypatch.setattr(get_settings(), "database_url", url)
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    command.upgrade(cfg, "0015_lesson_report")
    engine = create_engine(url)
    # Older revisions use current metadata: restore the actual legacy shape.
    with engine.begin() as conn:
        if "native_language" in {c["name"] for c in inspect(conn).get_columns("users")}:
            conn.execute(text("ALTER TABLE users DROP COLUMN native_language"))
        conn.execute(text("INSERT INTO users (id,email,password_hash,name,is_active,created_at,updated_at) VALUES ('legacy','legacy@example.test','hash','Legacy',1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        col = next(c for c in inspect(conn).get_columns("users") if c["name"] == "native_language")
        assert col["nullable"] and col["default"] is None
        assert conn.execute(text("SELECT native_language FROM users WHERE id='legacy'")).scalar() is None
    command.downgrade(cfg, "0015_lesson_report")
    with engine.connect() as conn:
        assert "native_language" not in {c["name"] for c in inspect(conn).get_columns("users")}
    command.upgrade(cfg, "head")
    engine.dispose()


@pytest.mark.parametrize("native", ["pt-BR", "en", None])
def test_audio_main_keeps_target_language(client, auth, monkeypatch, native):
    if native is not None:
        assert client.patch("/api/v1/profile", json={"native_language":native}, headers=auth).status_code == 200
    captured = {}
    def synthesize(text, language_code, speed):
        captured.update(text=text, language_code=language_code)
        return b"audio", "audio/wav"
    monkeypatch.setattr("app.api.speech.synthesize_audio", synthesize)
    response = client.post("/api/v1/speech/synthesize", json={"text":"Bonjour.","language_code":"fr"}, headers=auth)
    assert response.status_code == 200
    assert captured == {"text":"Bonjour.", "language_code":"fr"}


def test_vocabulary_legacy_not_delivered_as_english_support(client, auth):
    client.patch("/api/v1/profile", json={"native_language":"en"}, headers=auth)
    response = client.get("/api/v1/vocabulary")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "native_support_unavailable"


def test_conversation_history_native_snapshot_blocks_reuse(db_session):
    from app.api.conversations import _ensure_history_native
    from app.models import Language, UserLanguage, StudySession, Conversation, ConversationMessage
    from app.core.errors import APIError
    user = db_session.scalar(select(User))
    lang = db_session.scalar(select(Language).where(Language.code == "fr"))
    owner = UserLanguage(user_id=user.id, language_id=lang.id)
    db_session.add(owner); db_session.flush()
    session = StudySession(user_language_id=owner.id)
    db_session.add(session); db_session.flush()
    conversation = Conversation(user_language_id=owner.id, study_session_id=session.id, topic="Voyage")
    db_session.add(conversation); db_session.flush()
    db_session.add(ConversationMessage(conversation_id=conversation.id, role="assistant", content_text="Bonjour", source="native:pt-BR"))
    db_session.flush()
    user.native_language = "pt-BR"
    _ensure_history_native(db_session, conversation, user)
    user.native_language = "en"
    with pytest.raises(APIError) as error:
        _ensure_history_native(db_session, conversation, user)
    assert error.value.code == "conversation_native_language_mismatch"


@pytest.mark.parametrize("target,native,text,support", [("fr","pt-BR","Le présent décrit une habitude.","O presente descreve um hábito."),("de","en","Das Präsens beschreibt Gewohnheiten.","The present tense describes habits."),("en","pt-BR","The present tense describes habits.","O presente descreve um hábito.")])
def test_generated_bilingual_grammar_keeps_pair_separate(monkeypatch, target, native, text, support):
    from app.services.ai import OpenRouterProvider
    from app.services.learner_context import LearnerContext
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "openrouter_api_key", "test-key")
    monkeypatch.setattr(get_settings(), "openrouter_model", "test-model")
    payload = {"title":"Grammaire", "explanation":text, "explanation_native":support, "examples":[],"exercises":[]}
    def generate(settings, messages, validator, **kwargs):
        assert validator(payload)
        assert f"native_language={native}" in messages[0]["content"]
        return payload, "test-model"
    monkeypatch.setattr("app.services.ai.openrouter_chat_with_fallback", generate)
    context = LearnerContext(target,"Idioma","Idioma","A1","A1","desc","self_declared",False,native_language=native)
    result = OpenRouterProvider().generate_lesson("grammar", context)
    assert result["target_language"] == target
    assert result["native_language"] == native
    assert result["explanation"] == text
    assert result["explanation_native"] == support


@pytest.mark.parametrize("native", [None,"en"])
def test_review_queue_does_not_expose_portuguese_support(client, auth, db_session, native):
    from app.models import Language, UserLanguage
    user = db_session.scalar(select(User))
    lang = db_session.scalar(select(Language).where(Language.code == "en"))
    db_session.add(UserLanguage(user_id=user.id, language_id=lang.id))
    db_session.commit()
    if native:
        client.patch("/api/v1/profile", json={"native_language":native}, headers=auth)
    response = client.get("/api/v1/reviews/due", params={"language_code":"en"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] in {"native_support_unavailable","native_language_required"}


@pytest.mark.parametrize("action", ["start","restore","answer"])
def test_vocabulary_cycle_checks_inverse_native_change(client, auth, db_session, action):
    from app.models import Language, UserLanguage, Lesson
    user = db_session.scalar(select(User))
    user.native_language = "pt-BR"
    lang = db_session.scalar(select(Language).where(Language.code == "de"))
    owner = UserLanguage(user_id=user.id, language_id=lang.id)
    db_session.add(owner); db_session.flush()
    lesson = Lesson(user_language_id=owner.id, title="Wörter", objective="Wörter", content_json={"mode":"vocabulary", "language_code":"de", "native_language":"en", "items":[]})
    db_session.add(lesson); db_session.commit()
    path = f"/api/v1/lessons/{lesson.id}/vocabulary-cycle"
    if action == "restore":
        response = client.get(path)
    elif action == "start":
        response = client.post(path + "/start", json={}, headers=auth)
    else:
        response = client.post(path + "/answer", json={"student_response":"x", "activity_index":0}, headers=auth)
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "lesson_native_language_mismatch"


def test_curated_new_delivery_rejects_known_third_language_logic():
    from app.services.lesson_envelope import apply_lesson_envelope
    from app.services.learner_context import LearnerContext
    from app.core.errors import APIError
    context = LearnerContext("fr","Francês","Français","A1","A1","desc","self_declared",False,native_language="pt-BR")
    with pytest.raises(APIError) as error:
        apply_lesson_envelope({"title":"Grammaire", "explanation":"We use the present simple to describe habits."},context=context,mode="grammar",provider="curated_library")
    assert error.value.code == "lesson_language_invalid"
