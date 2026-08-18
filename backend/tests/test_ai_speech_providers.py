"""Cadeia de fallback de IA/STT/TTS e proibição de mock silencioso em produção.

Nenhuma chamada externa real é feita: `httpx.post` é substituído por um dublê
em cada teste. Os testes cobrem o contrato exigido pela tarefa de remoção de
mocks de produção — ver AGENTS.md e o histórico da conversa que motivou este
arquivo.
"""

from __future__ import annotations

import json
import logging

import httpx
import pytest

from app.core.config import get_settings
from app.core.errors import APIError
from app.core.levels import CEFRLevel, LevelSource
from app.services import speech as speech_service
from app.services.ai import MockAIProvider, OpenRouterProvider, get_ai_provider
from app.services.learner_context import LearnerContext
from app.services.writing_evaluation import evaluate_writing


class FakeResponse:
    """Dublê mínimo de `httpx.Response` para os pontos usados pelo código."""

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeBinaryResponse:
    """Dublê de `httpx.Response` para respostas binárias (síntese de TTS)."""

    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        return None


def _chat_payload(url: str, kwargs: dict) -> dict:
    return kwargs.get("json") or {}


def _context() -> LearnerContext:
    return LearnerContext(
        language_code="en",
        language_name_pt="Inglês",
        language_native_name="English",
        level=CEFRLevel.A2,
        level_name_pt="A2 — Básico",
        level_description="desc",
        level_source=LevelSource.PLACEMENT_TEST,
        level_is_estimated=True,
    )


@pytest.fixture(autouse=True)
def _settings():
    """Configuração base isolada por teste; cada teste ajusta o que precisa."""
    settings = get_settings()
    yield settings


# --------------------------------------------------------------------- IA


def test_ai_mock_mode_true_in_development_uses_mock(monkeypatch, _settings):
    monkeypatch.setattr(_settings, "environment", "development")
    monkeypatch.setattr(_settings, "ai_mock_mode", True)
    assert isinstance(get_ai_provider(), MockAIProvider)


def test_production_ai_mock_false_uses_openrouter_primary(monkeypatch, _settings):
    monkeypatch.setattr(_settings, "environment", "production")
    monkeypatch.setattr(_settings, "ai_mock_mode", False)
    monkeypatch.setattr(_settings, "openrouter_api_key", "sk-secret-key")
    monkeypatch.setattr(_settings, "openrouter_model", "nvidia/nemotron-3-ultra-550b-a55b:free")
    monkeypatch.setattr(_settings, "openrouter_fallback_model", "google/gemma-4-31b-it:free")

    def fake_post(url, **kwargs):
        model = _chat_payload(url, kwargs)["model"]
        assert model == "nvidia/nemotron-3-ultra-550b-a55b:free"
        content = json.dumps({"reply": "Hi!", "suggestions": []})
        return FakeResponse({"choices": [{"message": {"content": content}}]})

    monkeypatch.setattr(httpx, "post", fake_post)

    provider = get_ai_provider()
    assert isinstance(provider, OpenRouterProvider)
    result = provider.conversation_turn("Hello", _context(), [])
    assert result["provider"] == "openrouter"
    assert result["model"] == "nvidia/nemotron-3-ultra-550b-a55b:free"
    assert result["reply"] == "Hi!"


def test_primary_model_failure_calls_fallback_model(monkeypatch, _settings):
    monkeypatch.setattr(_settings, "environment", "production")
    monkeypatch.setattr(_settings, "ai_mock_mode", False)
    monkeypatch.setattr(_settings, "openrouter_api_key", "sk-secret-key")
    monkeypatch.setattr(_settings, "openrouter_model", "primary-model")
    monkeypatch.setattr(_settings, "openrouter_fallback_model", "fallback-model")

    calls = []

    def fake_post(url, **kwargs):
        model = _chat_payload(url, kwargs)["model"]
        calls.append(model)
        if model == "primary-model":
            raise httpx.HTTPError("falha simulada do modelo primário")
        content = json.dumps({"reply": "Resposta do fallback"})
        return FakeResponse({"choices": [{"message": {"content": content}}]})

    monkeypatch.setattr(httpx, "post", fake_post)

    result = OpenRouterProvider().conversation_turn("Hello", _context(), [])
    assert calls == ["primary-model", "fallback-model"]
    assert result["provider"] == "openrouter"
    assert result["model"] == "fallback-model"
    assert result["reply"] == "Resposta do fallback"


def test_both_models_failing_never_falls_back_to_mock_in_production(monkeypatch, _settings):
    monkeypatch.setattr(_settings, "environment", "production")
    monkeypatch.setattr(_settings, "ai_mock_mode", False)
    monkeypatch.setattr(_settings, "openrouter_api_key", "sk-secret-key")
    monkeypatch.setattr(_settings, "openrouter_model", "primary-model")
    monkeypatch.setattr(_settings, "openrouter_fallback_model", "fallback-model")

    def fake_post(url, **kwargs):
        raise httpx.HTTPError("falha simulada")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(APIError) as exc_info:
        OpenRouterProvider().conversation_turn("Hello", _context(), [])
    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "ai_unavailable"
    assert exc_info.value.retryable is True


def test_both_models_failing_falls_back_to_mock_outside_production(monkeypatch, _settings):
    monkeypatch.setattr(_settings, "environment", "development")
    monkeypatch.setattr(_settings, "ai_mock_mode", False)
    monkeypatch.setattr(_settings, "openrouter_api_key", "sk-secret-key")
    monkeypatch.setattr(_settings, "openrouter_model", "primary-model")
    monkeypatch.setattr(_settings, "openrouter_fallback_model", "fallback-model")

    def fake_post(url, **kwargs):
        raise httpx.HTTPError("falha simulada")

    monkeypatch.setattr(httpx, "post", fake_post)

    result = OpenRouterProvider().conversation_turn("Hello", _context(), [])
    assert result["provider"] == "mock"


# -------------------------------------------------------------------- STT


def test_stt_provider_groq_uses_groq(monkeypatch, _settings, tmp_path):
    monkeypatch.setattr(_settings, "environment", "production")
    monkeypatch.setattr(_settings, "stt_provider", "groq")
    monkeypatch.setattr(_settings, "groq_api_key", "gsk-secret-key")
    monkeypatch.setattr(_settings, "groq_stt_model", "whisper-large-v3-turbo")

    audio_path = tmp_path / "audio.webm"
    audio_path.write_bytes(b"fake-audio-bytes")

    def fake_post(url, **kwargs):
        assert url == "https://api.groq.com/openai/v1/audio/transcriptions"
        assert kwargs["data"]["model"] == "whisper-large-v3-turbo"
        return FakeResponse({"text": "olá mundo"})

    monkeypatch.setattr(httpx, "post", fake_post)

    result = speech_service.transcribe_audio(str(audio_path), "pt", "audio/webm")
    assert result["provider"] == "groq"
    assert result["model"] == "whisper-large-v3-turbo"
    assert result["text"] == "olá mundo"


def test_groq_failure_calls_openrouter_fallback(monkeypatch, _settings, tmp_path):
    monkeypatch.setattr(_settings, "environment", "production")
    monkeypatch.setattr(_settings, "stt_provider", "groq")
    monkeypatch.setattr(_settings, "groq_api_key", "gsk-secret-key")
    monkeypatch.setattr(_settings, "stt_fallback_provider", "openrouter")
    monkeypatch.setattr(_settings, "openrouter_api_key", "sk-secret-key")
    monkeypatch.setattr(_settings, "stt_fallback_model", "qwen/qwen3-asr-flash-2026-02-10")

    audio_path = tmp_path / "audio.webm"
    audio_path.write_bytes(b"fake-audio-bytes")

    def fake_post(url, **kwargs):
        if "groq.com" in url:
            raise httpx.HTTPError("groq indisponível")
        assert url.endswith("/chat/completions")
        return FakeResponse({"choices": [{"message": {"content": "transcrição via fallback"}}]})

    monkeypatch.setattr(httpx, "post", fake_post)

    result = speech_service.transcribe_audio(str(audio_path), "en", "audio/webm")
    assert result["provider"] == "openrouter"
    assert result["model"] == "qwen/qwen3-asr-flash-2026-02-10"
    assert result["text"] == "transcrição via fallback"


def test_stt_both_providers_failing_no_mock_transcript_in_production(monkeypatch, _settings, tmp_path):
    monkeypatch.setattr(_settings, "environment", "production")
    monkeypatch.setattr(_settings, "stt_provider", "groq")
    monkeypatch.setattr(_settings, "groq_api_key", "gsk-secret-key")
    monkeypatch.setattr(_settings, "stt_fallback_provider", "openrouter")
    monkeypatch.setattr(_settings, "openrouter_api_key", "sk-secret-key")
    monkeypatch.setattr(_settings, "stt_fallback_model", "qwen/qwen3-asr-flash-2026-02-10")

    audio_path = tmp_path / "audio.webm"
    audio_path.write_bytes(b"fake-audio-bytes")

    def fake_post(url, **kwargs):
        raise httpx.HTTPError("indisponível")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(APIError) as exc_info:
        speech_service.transcribe_audio(str(audio_path), "en", "audio/webm")
    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "stt_unavailable"


def test_unknown_stt_provider_in_production_fails_explicitly_not_silently(monkeypatch, _settings, tmp_path):
    """Configuração desconhecida (typo, provider não suportado) não deve
    mascarar o erro fingindo sucesso nem caindo num mock silencioso."""
    monkeypatch.setattr(_settings, "environment", "production")
    monkeypatch.setattr(_settings, "stt_provider", "azure-nao-implementado")
    monkeypatch.setattr(_settings, "stt_fallback_provider", "")

    audio_path = tmp_path / "audio.webm"
    audio_path.write_bytes(b"fake-audio-bytes")

    with pytest.raises(APIError) as exc_info:
        speech_service.transcribe_audio(str(audio_path), "en", "audio/webm")
    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "stt_unavailable"


# -------------------------------------------------------------------- TTS


def test_tts_mock_provider_never_returns_fake_riff_in_production(monkeypatch, _settings):
    monkeypatch.setattr(_settings, "environment", "production")
    monkeypatch.setattr(_settings, "tts_provider", "mock")
    with pytest.raises(APIError) as exc_info:
        speech_service.synthesize_audio("Hello", "en")
    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "tts_unavailable"


def test_tts_mock_provider_allowed_outside_production(monkeypatch, _settings):
    monkeypatch.setattr(_settings, "environment", "development")
    monkeypatch.setattr(_settings, "tts_provider", "mock")
    audio, content_type = speech_service.synthesize_audio("Hello", "en")
    assert audio.startswith(b"RIFF")
    assert content_type == "audio/wav"


def test_tts_provider_openrouter_uses_kokoro(monkeypatch, _settings):
    monkeypatch.setattr(_settings, "environment", "production")
    monkeypatch.setattr(_settings, "tts_provider", "openrouter")
    monkeypatch.setattr(_settings, "openrouter_api_key", "sk-secret-key")
    monkeypatch.setattr(_settings, "tts_model", "hexgrad/kokoro-82m")
    monkeypatch.setattr(_settings, "tts_voice", "")
    monkeypatch.setattr(_settings, "tts_speed", 1.0)

    def fake_post(url, **kwargs):
        assert url == "https://openrouter.ai/api/v1/audio/speech"
        assert kwargs["headers"]["Authorization"] == "Bearer sk-secret-key"
        body = kwargs["json"]
        assert body["model"] == "hexgrad/kokoro-82m"
        assert body["input"] == "Hello there"
        assert body["voice"] == "af_sky"
        assert body["response_format"] == "mp3"
        assert body["speed"] == 1.0
        return FakeBinaryResponse(b"fake-mp3-bytes")

    monkeypatch.setattr(httpx, "post", fake_post)

    audio, content_type = speech_service.synthesize_audio("Hello there", "en")
    assert audio == b"fake-mp3-bytes"
    assert content_type == "audio/mpeg"


@pytest.mark.parametrize(
    "language_code,expected_voice",
    [
        ("en", "af_sky"),
        ("en-US", "af_sky"),  # alias válido: prefixo ISO-639-1 antes do "-"
        ("es-ES", "em_alex"),
        ("fr", "ff_siwis"),
        ("fr-FR", "ff_siwis"),
        ("ja", "jf_nezumi"),
        ("ja-JP", "jf_nezumi"),
        ("zh-CN", "zf_xiaoxiao"),
    ],
)
def test_tts_openrouter_picks_voice_by_language(monkeypatch, _settings, language_code, expected_voice):
    """Mapeamento oficial das vozes Kokoro escolhidas no Kokoro Voice Lab —
    ver docs/TTS.md. Cobre também aliases de locale (`en-US`, `fr-FR`,
    `ja-JP`) resolvidos pelo mesmo `_language_hint` (split em "-", sem
    `startsWith`/substring matching que pudesse casar idioma errado)."""
    monkeypatch.setattr(_settings, "environment", "production")
    monkeypatch.setattr(_settings, "tts_provider", "openrouter")
    monkeypatch.setattr(_settings, "openrouter_api_key", "sk-secret-key")
    monkeypatch.setattr(_settings, "tts_voice", "")

    captured = {}

    def fake_post(url, **kwargs):
        captured["voice"] = kwargs["json"]["voice"]
        return FakeBinaryResponse(b"audio")

    monkeypatch.setattr(httpx, "post", fake_post)

    speech_service.synthesize_audio("texto de teste", language_code)
    assert captured["voice"] == expected_voice


def test_tts_openrouter_unsupported_language_never_guesses_a_voice(monkeypatch, _settings):
    """Idioma sem entrada no mapa (ex. alemão, fora dos 5 idiomas do
    BeFluent) nunca cai numa voz "parecida" nem na voz default — mandar
    texto de idioma desconhecido para af_sky (voz de inglês) produziria
    fala errada. Devolve erro explícito (400) para o frontend cair no
    SpeechSynthesis do navegador, sem sequer chamar a OpenRouter."""
    monkeypatch.setattr(_settings, "environment", "production")
    monkeypatch.setattr(_settings, "tts_provider", "openrouter")
    monkeypatch.setattr(_settings, "openrouter_api_key", "sk-secret-key")
    monkeypatch.setattr(_settings, "tts_voice", "")

    def fake_post(url, **kwargs):
        raise AssertionError("idioma sem voz Kokoro não deve chegar a chamar a OpenRouter")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(APIError) as exc_info:
        speech_service.synthesize_audio("some text", "de")  # alemão: sem voz Kokoro mapeada
    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "tts_unsupported_language"


def test_tts_voice_override_bypasses_language_allowlist(monkeypatch, _settings):
    """`TTS_VOICE` é uma escolha explícita do operador — continua valendo
    mesmo para um idioma fora do allowlist, porque não é mais uma decisão
    automática por idioma."""
    monkeypatch.setattr(_settings, "environment", "production")
    monkeypatch.setattr(_settings, "tts_provider", "openrouter")
    monkeypatch.setattr(_settings, "openrouter_api_key", "sk-secret-key")
    monkeypatch.setattr(_settings, "tts_voice", "am_michael")

    captured = {}

    def fake_post(url, **kwargs):
        captured["voice"] = kwargs["json"]["voice"]
        return FakeBinaryResponse(b"audio")

    monkeypatch.setattr(httpx, "post", fake_post)

    speech_service.synthesize_audio("some text", "de")
    assert captured["voice"] == "am_michael"


def test_tts_openrouter_voice_override(monkeypatch, _settings):
    monkeypatch.setattr(_settings, "environment", "production")
    monkeypatch.setattr(_settings, "tts_provider", "openrouter")
    monkeypatch.setattr(_settings, "openrouter_api_key", "sk-secret-key")
    monkeypatch.setattr(_settings, "tts_voice", "am_michael")

    captured = {}

    def fake_post(url, **kwargs):
        captured["voice"] = kwargs["json"]["voice"]
        return FakeBinaryResponse(b"audio")

    monkeypatch.setattr(httpx, "post", fake_post)

    speech_service.synthesize_audio("Hi", "en")
    assert captured["voice"] == "am_michael"


def test_tts_openrouter_failure_in_production_returns_503(monkeypatch, _settings):
    monkeypatch.setattr(_settings, "environment", "production")
    monkeypatch.setattr(_settings, "tts_provider", "openrouter")
    monkeypatch.setattr(_settings, "openrouter_api_key", "sk-secret-key")

    def fake_post(url, **kwargs):
        raise httpx.HTTPError("falha simulada")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(APIError) as exc_info:
        speech_service.synthesize_audio("Hello", "en")
    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "tts_unavailable"
    assert exc_info.value.retryable is True


def test_tts_openrouter_failure_outside_production_falls_back_to_mock(monkeypatch, _settings):
    monkeypatch.setattr(_settings, "environment", "development")
    monkeypatch.setattr(_settings, "tts_provider", "openrouter")
    monkeypatch.setattr(_settings, "openrouter_api_key", "sk-secret-key")

    def fake_post(url, **kwargs):
        raise httpx.HTTPError("falha simulada")

    monkeypatch.setattr(httpx, "post", fake_post)

    audio, content_type = speech_service.synthesize_audio("Hello", "en")
    assert audio.startswith(b"RIFF")
    assert content_type == "audio/wav"


def test_tts_provider_web_speech_forces_unavailable_without_calling_openrouter(monkeypatch, _settings):
    """Rollback por configuração (seção "Rollback" de docs/TTS.md): setar
    `TTS_PROVIDER=web_speech` desativa o Kokoro de servidor sem remover
    código — o endpoint sempre falha, e o `AudioPlayer` do frontend já cai
    no SpeechSynthesis do navegador nesse caso."""
    monkeypatch.setattr(_settings, "environment", "production")
    monkeypatch.setattr(_settings, "tts_provider", "web_speech")
    monkeypatch.setattr(_settings, "openrouter_api_key", "sk-secret-key")  # mesmo com chave válida

    def fake_post(url, **kwargs):
        raise AssertionError("web_speech não deve chamar a OpenRouter")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(APIError) as exc_info:
        speech_service.synthesize_audio("Hello", "en")
    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "tts_unavailable"


def test_tts_no_response_or_log_leaks_api_keys(monkeypatch, _settings, caplog):
    secret = "sk-super-secret-tts-key-should-never-leak"
    monkeypatch.setattr(_settings, "environment", "production")
    monkeypatch.setattr(_settings, "tts_provider", "openrouter")
    monkeypatch.setattr(_settings, "openrouter_api_key", secret)

    def fake_post(url, **kwargs):
        assert kwargs["headers"]["Authorization"] == f"Bearer {secret}"
        raise httpx.HTTPError("falha simulada")

    monkeypatch.setattr(httpx, "post", fake_post)

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(APIError) as exc_info:
            speech_service.synthesize_audio("Hello", "en")

    assert secret not in str(exc_info.value.message)
    assert secret not in caplog.text


# ------------------------------------------------------------- Pronúncia


def test_pronunciation_never_returns_fabricated_score_in_production(_settings, monkeypatch):
    monkeypatch.setattr(_settings, "environment", "production")
    result = speech_service.assess_pronunciation("hello there", "hello there")
    assert result["status"] == "unavailable"
    assert result["score"] is None
    assert "85" not in json.dumps(result)


# ------------------------------------------------------------ Segurança


def test_no_response_or_log_leaks_api_keys(monkeypatch, _settings, caplog):
    secret = "sk-super-secret-openrouter-key-should-never-leak"
    monkeypatch.setattr(_settings, "environment", "production")
    monkeypatch.setattr(_settings, "ai_mock_mode", False)
    monkeypatch.setattr(_settings, "openrouter_api_key", secret)
    monkeypatch.setattr(_settings, "openrouter_model", "primary-model")
    monkeypatch.setattr(_settings, "openrouter_fallback_model", "fallback-model")

    def fake_post(url, **kwargs):
        assert kwargs["headers"]["Authorization"] == f"Bearer {secret}"
        raise httpx.HTTPError("falha simulada")

    monkeypatch.setattr(httpx, "post", fake_post)

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(APIError) as exc_info:
            OpenRouterProvider().conversation_turn("Hello", _context(), [])

    assert secret not in str(exc_info.value.message)
    assert secret not in caplog.text


# ------------------------------------------------------------ Escrita


def test_writing_heuristic_stays_labeled_as_heuristic(monkeypatch, _settings):
    monkeypatch.setattr(_settings, "ai_mock_mode", True)
    result = evaluate_writing("This is a short but valid test sentence.", "en", "A2")
    assert result["evaluated_by"] == "heuristic"
    assert "notice" in result
