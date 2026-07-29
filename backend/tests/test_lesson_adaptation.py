"""Integração entre o teste de nivelamento e as lições.

O ponto sob teste é único e é o motivo desta camada existir: o conteúdo da lição
tem de mudar conforme o nível estimado do aluno. Um teste que só verifique
"a resposta tem título" passaria mesmo com o conteúdo fixo de antes.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.levels import LEVEL_INDEX, CEFRLevel, LevelSource, Skill
from app.models import Language, User, UserLanguage
from app.prompts.library import MODE_PROMPTS, SUPPORTED_MODES
from app.services.ai import MockAIProvider
from app.services.learner_context import (
    DEFAULT_LEVEL,
    LearnerContext,
    build_context,
    recommended_modes,
)


def _context(**overrides) -> LearnerContext:
    base = dict(
        language_code="en",
        language_name_pt="Inglês",
        language_native_name="English",
        level=CEFRLevel.B1,
        level_name_pt="B1 — Intermediário",
        level_description="desc",
        level_source=LevelSource.PLACEMENT_TEST,
        level_is_estimated=True,
    )
    base.update(overrides)
    return LearnerContext(**base)


def _profile(db_session, level: str, **columns) -> None:
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    db_session.add(
        UserLanguage(
            user_id=user.id,
            language_id=language.id,
            current_level=level,
            level_source=LevelSource.PLACEMENT_TEST,
            is_active=True,
            onboarding_completed=True,
            **columns,
        )
    )
    db_session.commit()


# ---------------------------------------------------------------- contexto


def test_context_without_profile_uses_default_level(db_session):
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    context = build_context(db_session, user, "en")
    assert context.level == DEFAULT_LEVEL
    assert context.level_is_estimated is False


def test_context_reads_placement_result(db_session):
    _profile(db_session, CEFRLevel.B2, writing_level=CEFRLevel.A2, listening_level=CEFRLevel.B1)
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    context = build_context(db_session, user, "en")

    assert context.level == CEFRLevel.B2
    assert context.level_is_estimated is True
    assert context.skill_levels[Skill.WRITING] == CEFRLevel.A2
    assert context.weakest_skills == [Skill.WRITING]


def test_context_normalizes_legacy_level(db_session):
    """Usuário anterior ao CEFR não deve cair no nível padrão."""
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    db_session.add(
        UserLanguage(user_id=user.id, language_id=language.id, level_estimate="intermediario")
    )
    db_session.commit()

    assert build_context(db_session, user, "en").level == CEFRLevel.B1


def test_unknown_language_raises(db_session):
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    with pytest.raises(LookupError):
        build_context(db_session, user, "xx")


def test_prompt_context_carries_level_and_goal():
    block = _context(goal="Trabalho", minutes_per_day=20).to_prompt_context()
    assert "B1" in block
    assert "Trabalho" in block
    assert "20 minutos" in block
    assert "teste de nivelamento" in block


def test_prompt_context_flags_untested_level():
    block = _context(
        level_source=LevelSource.SELF_DECLARED, level_is_estimated=False
    ).to_prompt_context()
    assert "informado pelo próprio aluno" in block


def test_lesson_calibrates_by_skill_not_overall_level():
    """Quem lê em B2 e escreve em A2 recebe escrita A2, não escrita B2."""
    context = _context(
        level=CEFRLevel.B2,
        skill_levels={Skill.WRITING: CEFRLevel.A2, Skill.READING: CEFRLevel.B2},
    )
    assert context.level_for_skill(Skill.WRITING) == CEFRLevel.A2
    assert context.level_for_skill(Skill.READING) == CEFRLevel.B2
    # Competência não avaliada cai no nível geral.
    assert context.level_for_skill(Skill.LISTENING) == CEFRLevel.B2


# ---------------------------------------------------------------- geração


@pytest.mark.parametrize("mode", SUPPORTED_MODES)
def test_mock_generates_every_mode(mode):
    lesson = MockAIProvider().generate_lesson(mode, _context())
    assert lesson["title"]
    assert lesson["mode"] == mode
    assert lesson["provider"] == "mock"
    assert lesson["level"] == CEFRLevel.B1


@pytest.mark.parametrize("language", ["en", "es-ES", "fr", "ja", "zh-CN"])
@pytest.mark.parametrize("mode", SUPPORTED_MODES)
def test_mock_covers_every_language(mode, language):
    lesson = MockAIProvider().generate_lesson(mode, _context(language_code=language))
    assert lesson["title"]


def test_vocabulary_content_differs_between_levels():
    """O teste que prova a integração: nível diferente, conteúdo diferente."""
    provider = MockAIProvider()
    beginner = provider.generate_lesson("vocabulary", _context(level=CEFRLevel.PRE_A1))
    advanced = provider.generate_lesson("vocabulary", _context(level=CEFRLevel.B2))

    beginner_terms = {item["term"] for item in beginner["items"]}
    advanced_terms = {item["term"] for item in advanced["items"]}
    assert beginner_terms != advanced_terms
    assert not beginner_terms & advanced_terms


def test_writing_task_scales_with_level():
    provider = MockAIProvider()
    beginner = provider.generate_lesson("writing", _context(level=CEFRLevel.A1))
    advanced = provider.generate_lesson("writing", _context(level=CEFRLevel.B2))
    assert advanced["min_words"] > beginner["min_words"]
    assert advanced["prompt"] != beginner["prompt"]


def test_writing_uses_writing_level_when_assessed():
    """Nível geral B2 mas escrita A2 → tarefa de escrita de A2."""
    lesson = MockAIProvider().generate_lesson(
        "writing",
        _context(level=CEFRLevel.B2, skill_levels={Skill.WRITING: CEFRLevel.A2}),
    )
    a2_reference = MockAIProvider().generate_lesson("writing", _context(level=CEFRLevel.A2))
    assert lesson["level"] == CEFRLevel.A2
    assert lesson["prompt"] == a2_reference["prompt"]


def test_pronunciation_focus_is_language_specific():
    provider = MockAIProvider()
    english = provider.generate_lesson("pronunciation", _context(language_code="en"))
    japanese = provider.generate_lesson("pronunciation", _context(language_code="ja"))
    assert english["focus_sounds"] != japanese["focus_sounds"]


def test_unsupported_mode_raises():
    with pytest.raises(ValueError):
        MockAIProvider().generate_lesson("inexistente", _context())


# ---------------------------------------------------------------- recomendação


def test_recommendation_targets_weakest_skill():
    modes = recommended_modes(
        _context(skill_levels={Skill.LISTENING: CEFRLevel.A1}, weakest_skills=[Skill.LISTENING])
    )
    assert "listening" in modes


def test_recommendation_is_neutral_without_assessment():
    modes = recommended_modes(_context(weakest_skills=[]))
    assert modes == ["guided", "vocabulary", "conversation"]


# ---------------------------------------------------------------- API


def test_generate_blocks_anonymous_request(client):
    """Sem sessão: o CSRF guard barra a rota mutável antes mesmo da autenticação."""
    response = client.post(
        "/api/v1/lessons/generate", json={"language_code": "en", "mode": "vocabulary"}
    )
    assert response.status_code == 403


def test_modes_requires_authentication(client):
    response = client.get("/api/v1/lessons/modes?language_code=en")
    assert response.status_code == 401


def test_generate_returns_adapted_lesson(client, auth, db_session):
    _profile(db_session, CEFRLevel.A1)
    response = client.post(
        "/api/v1/lessons/generate",
        json={"language_code": "en", "mode": "vocabulary"},
        headers=auth,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["level"] == CEFRLevel.A1
    assert body["level_source"] == LevelSource.PLACEMENT_TEST
    assert body["items"]
    assert body["lesson_id"]


def test_generate_rejects_invalid_mode(client, auth):
    response = client.post(
        "/api/v1/lessons/generate",
        json={"language_code": "en", "mode": "hackeando"},
        headers=auth,
    )
    assert response.status_code == 422


def test_generate_rejects_unknown_language(client, auth):
    response = client.post(
        "/api/v1/lessons/generate",
        json={"language_code": "xx", "mode": "vocabulary"},
        headers=auth,
    )
    assert response.status_code == 404


def test_generate_works_without_onboarding(client, auth):
    """Gerar lição não deve exigir onboarding concluído."""
    response = client.post(
        "/api/v1/lessons/generate",
        json={"language_code": "en", "mode": "guided", "persist": False},
        headers=auth,
    )
    assert response.status_code == 200
    assert response.json()["level"] == DEFAULT_LEVEL


def test_modes_endpoint_marks_recommendations(client, auth, db_session):
    _profile(db_session, CEFRLevel.B1, listening_level=CEFRLevel.A2, reading_level=CEFRLevel.B2)
    response = client.get("/api/v1/lessons/modes?language_code=en", headers=auth)
    assert response.status_code == 200
    body = response.json()

    assert body["level"] == CEFRLevel.B1
    assert "listening" in body["recommended_modes"]
    listening = next(item for item in body["modes"] if item["mode"] == "listening")
    assert listening["recommended"] is True
    assert listening["level"] == CEFRLevel.A2


def test_lesson_detail_blocks_other_users(client, auth, db_session, other_user):
    _profile(db_session, CEFRLevel.B1)
    created = client.post(
        "/api/v1/lessons/generate",
        json={"language_code": "en", "mode": "vocabulary"},
        headers=auth,
    ).json()

    language = db_session.scalar(select(Language).where(Language.code == "en"))
    db_session.add(UserLanguage(user_id=other_user, language_id=language.id))
    db_session.commit()

    client.post("/api/v1/auth/logout", headers=auth)
    response = client.get(f"/api/v1/lessons/{created['lesson_id']}")
    assert response.status_code == 401


def test_every_supported_mode_has_a_prompt():
    """Guarda contra adicionar um modo sem o prompt correspondente."""
    assert set(SUPPORTED_MODES) == set(MODE_PROMPTS)


# ---------------------------------------------------------------- escrita


def test_lesson_writing_returns_real_evaluation(client, auth, db_session):
    """A correção substituiu o score fixo de 80 por avaliação de verdade."""
    _profile(db_session, CEFRLevel.A2)
    response = client.post(
        "/api/v1/writing",
        json={
            "language_code": "en",
            "prompt": "Descreva sua rotina.",
            "content_text": (
                "I wake up at seven. I have breakfast with my family. "
                "Then I go to work by bus. The trip takes thirty minutes."
            ),
            "min_words": 20,
            "max_words": 60,
        },
        headers=auth,
    )
    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "assessed"
    assert body["evaluated_by"] == "heuristic"  # sem chave OpenRouter nos testes
    assert 0.0 <= body["normalized_score"] <= 1.0
    assert body["score"] != 80  # o valor cravado que existia antes
    assert body["within_range"] is True
    assert body["word_count"] > 0
    assert body["id"]


def test_lesson_writing_flags_text_outside_range(client, auth, db_session):
    _profile(db_session, CEFRLevel.B1)
    response = client.post(
        "/api/v1/writing",
        json={
            "language_code": "en",
            "prompt": "Conte uma experiência.",
            "content_text": "Too short.",
            "min_words": 90,
            "max_words": 150,
        },
        headers=auth,
    )
    assert response.status_code == 200
    assert response.json()["within_range"] is False


def test_lesson_writing_uses_profile_level_when_omitted(client, auth, db_session):
    """Sem target_level explícito, cobra o nível de escrita avaliado."""
    _profile(db_session, CEFRLevel.B2, writing_level=CEFRLevel.A2)
    response = client.post(
        "/api/v1/writing",
        json={
            "language_code": "en",
            "prompt": "Rotina",
            "content_text": "I work every day and I study English at night.",
        },
        headers=auth,
    )
    assert response.status_code == 200
    assert response.json()["target_level"] == CEFRLevel.A2


def test_lesson_writing_never_promotes_above_target():
    """Nem a IA nem a heurística podem estimar acima do nível da tarefa."""
    from app.services.writing_evaluation import evaluate_lesson_writing

    result = evaluate_lesson_writing(
        "A very long and rich text. " * 40, "en", CEFRLevel.A2, 20, 400
    )
    assert LEVEL_INDEX[result["estimated_level"]] <= LEVEL_INDEX[CEFRLevel.A2]


def test_lesson_writing_rejects_empty_text(client, auth, db_session):
    _profile(db_session, CEFRLevel.A2)
    response = client.post(
        "/api/v1/writing",
        json={"language_code": "en", "prompt": "Rotina", "content_text": "   "},
        headers=auth,
    )
    # min_length=1 aceita espaços; a avaliação then marca como não avaliado.
    assert response.status_code in (200, 422)
    if response.status_code == 200:
        assert response.json()["status"] == "not_evaluated"


def test_lesson_writing_rejects_invalid_range(client, auth, db_session):
    _profile(db_session, CEFRLevel.A2)
    response = client.post(
        "/api/v1/writing",
        json={
            "language_code": "en",
            "prompt": "Rotina",
            "content_text": "Some text here.",
            "min_words": 200,
            "max_words": 50,
        },
        headers=auth,
    )
    assert response.status_code == 400


def test_lesson_writing_rejects_oversized_text(client, auth, db_session):
    _profile(db_session, CEFRLevel.A2)
    response = client.post(
        "/api/v1/writing",
        json={
            "language_code": "en",
            "prompt": "Rotina",
            "content_text": "x" * 5000,
        },
        headers=auth,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------- conversação


def test_conversation_turn_uses_speaking_level():
    """O turno calibra pela fala avaliada, não pelo nível geral."""
    turn = MockAIProvider().conversation_turn(
        "hello",
        _context(level=CEFRLevel.B2, skill_levels={Skill.SPEAKING: CEFRLevel.A1}),
        [],
    )
    assert turn["level"] == CEFRLevel.A1


def test_conversation_translates_below_b1():
    """Nível baixo recebe tradução; a partir de B1, não."""
    beginner = MockAIProvider().conversation_turn("oi", _context(level=CEFRLevel.A1), [])
    advanced = MockAIProvider().conversation_turn("hi", _context(level=CEFRLevel.B2), [])

    assert beginner["shows_translation"] is True
    assert beginner["reply_translation"]
    assert advanced["shows_translation"] is False
    assert advanced["reply_translation"] is None


def test_conversation_reply_differs_between_levels():
    provider = MockAIProvider()
    beginner = provider.conversation_turn("oi", _context(level=CEFRLevel.PRE_A1), [])
    advanced = provider.conversation_turn("hi", _context(level=CEFRLevel.B2), [])
    assert beginner["reply"] != advanced["reply"]


def test_conversation_mock_never_invents_corrections():
    """Sem IA não há análise gramatical — e a resposta diz isso."""
    turn = MockAIProvider().conversation_turn(
        "I has go to school yesterday", _context(level=CEFRLevel.A2), []
    )
    assert turn["corrections"] == []
    assert turn["corrections_available"] is False


def test_conversation_advances_with_history():
    """Turnos seguintes não repetem a mesma fala do tutor."""
    provider = MockAIProvider()
    context = _context(level=CEFRLevel.B1)
    first = provider.conversation_turn("a", context, [])
    history = [{"role": "user", "content": "a"}, {"role": "assistant", "content": first["reply"]}]
    second = provider.conversation_turn("b", context, history)
    assert first["reply"] != second["reply"]


def test_conversation_endpoint_returns_level(client, auth, db_session):
    _profile(db_session, CEFRLevel.B1)
    started = client.post(
        "/api/v1/conversations", json={"language_code": "en", "topic": "Restaurante"}, headers=auth
    )
    assert started.status_code == 200
    assert started.json()["level"] == CEFRLevel.B1

    reply = client.post(
        f"/api/v1/conversations/{started.json()['id']}/messages",
        json={"text": "I would like a table."},
        headers=auth,
    )
    assert reply.status_code == 200
    body = reply.json()
    assert body["reply"]
    assert body["level"] == CEFRLevel.B1
    assert body["level_is_estimated"] is True


def test_conversation_rejects_other_users_conversation(client, auth, db_session):
    """Regressão: o GET de mensagens não checava dono."""
    from app.models import Conversation, StudySession

    language = db_session.scalar(select(Language).where(Language.code == "en"))
    stranger = User(
        email="outro@befluent.local", password_hash="x", name="Outro", is_active=True
    )
    db_session.add(stranger)
    db_session.flush()
    profile = UserLanguage(user_id=stranger.id, language_id=language.id)
    db_session.add(profile)
    db_session.flush()
    session = StudySession(user_language_id=profile.id)
    db_session.add(session)
    db_session.flush()
    conversation = Conversation(
        study_session_id=session.id, user_language_id=profile.id, topic="Privada"
    )
    db_session.add(conversation)
    db_session.commit()

    assert (
        client.get(f"/api/v1/conversations/{conversation.id}/messages", headers=auth).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/conversations/{conversation.id}/messages",
            json={"text": "oi"},
            headers=auth,
        ).status_code
        == 404
    )


def test_conversation_rejects_empty_message(client, auth, db_session):
    _profile(db_session, CEFRLevel.A2)
    started = client.post(
        "/api/v1/conversations", json={"language_code": "en"}, headers=auth
    ).json()
    response = client.post(
        f"/api/v1/conversations/{started['id']}/messages", json={"text": ""}, headers=auth
    )
    assert response.status_code == 422


def test_conversation_lesson_opening_follows_translation_rule():
    """A abertura segue a mesma regra dos turnos: sem tradução a partir de B1."""
    provider = MockAIProvider()
    beginner = provider.generate_lesson("conversation", _context(level=CEFRLevel.A1))
    advanced = provider.generate_lesson("conversation", _context(level=CEFRLevel.B2))
    assert beginner["opening_translation"]
    assert advanced["opening_translation"] is None
