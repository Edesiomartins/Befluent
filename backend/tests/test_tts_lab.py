"""TTS Lab — acesso restrito por allow-list, isolamento por modelo, sem
segredos vazando e sem alterar o fluxo de TTS de produção (`speech.py`).
"""

from __future__ import annotations

import base64

import httpx
import pytest

from app.core.config import get_settings
from app.services import tts_lab as service


class FakeAudioResponse:
    def __init__(self, status_code: int, content: bytes = b"fake-mp3-bytes", headers: dict | None = None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}


@pytest.fixture(autouse=True)
def _allow_admin_email(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "tts_lab_allowed_emails", "admin@befluent.local")
    monkeypatch.setattr(settings, "openrouter_api_key", "sk-secret-key")
    yield settings


# --------------------------------------------------------------- Acesso


def test_models_endpoint_requires_auth(client):
    response = client.get("/api/v1/tts-lab/models")
    assert response.status_code == 401


def test_models_endpoint_denies_non_allowlisted_user(client, auth, db_session):
    from app.core.security import hash_password
    from app.models import User, UserPreference

    user = User(email="outro@befluent.local", name="Outro", password_hash=hash_password("senha-segura"))
    db_session.add(user)
    db_session.flush()
    db_session.add(UserPreference(user_id=user.id))
    db_session.commit()

    other_client_response = client.post(
        "/api/v1/auth/login",
        json={"email": "outro@befluent.local", "password": "senha-segura"},
    )
    assert other_client_response.status_code == 200
    headers = {"X-CSRF-Token": client.cookies.get("csrf_token")}

    response = client.get("/api/v1/tts-lab/models", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "tts_lab_forbidden"


def test_models_endpoint_allows_allowlisted_user(client, auth):
    response = client.get("/api/v1/tts-lab/models", headers=auth)
    assert response.status_code == 200
    models = response.json()["models"]
    assert {m["id"] for m in models} == set(service.TTS_LAB_MODELS)
    assert "sk-secret-key" not in response.text


# ------------------------------------------------------------- Geração


def test_generate_unknown_model_returns_400(client, auth):
    response = client.post(
        "/api/v1/tts-lab/generate",
        json={"model": "not/a-real-model", "text": "Hello"},
        headers=auth,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "tts_lab_model_not_found"


def test_generate_missing_api_key_returns_503(client, auth, monkeypatch):
    monkeypatch.setattr(get_settings(), "openrouter_api_key", "")
    response = client.post(
        "/api/v1/tts-lab/generate",
        json={"model": "hexgrad/kokoro-82m", "text": "Hello"},
        headers=auth,
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "tts_lab_unconfigured"


def test_generate_success_returns_audio_and_latency(client, auth, monkeypatch):
    def fake_post(url, **kwargs):
        assert url == "https://openrouter.ai/api/v1/audio/speech"
        assert kwargs["headers"]["Authorization"] == "Bearer sk-secret-key"
        body = kwargs["json"]
        assert body["model"] == "hexgrad/kokoro-82m"
        assert body["voice"] == "af_heart"
        return FakeAudioResponse(200)

    monkeypatch.setattr(httpx, "post", fake_post)

    response = client.post(
        "/api/v1/tts-lab/generate",
        json={"model": "hexgrad/kokoro-82m", "text": "Hello there"},
        headers=auth,
    )
    assert response.status_code == 200
    payload = response.json()
    assert base64.b64decode(payload["audio_base64"]) == b"fake-mp3-bytes"
    assert payload["content_type"] == "audio/mpeg"
    assert isinstance(payload["latency_ms"], int)
    assert payload["audio_size_bytes"] == len(b"fake-mp3-bytes")
    assert payload["free_model"] is False
    assert payload["cost_available"] is False
    assert payload["estimated_cost"] is None


def test_generate_does_not_send_unsupported_params(client, auth, monkeypatch):
    """`fish-audio/s2.1-pro-free:free` aceita `speed` mas não tem `voice`
    explícita confirmada (ver docs/TTS_LAB.md) — só `speed` deve ir no corpo."""
    captured = {}

    def fake_post(url, **kwargs):
        captured["body"] = kwargs["json"]
        return FakeAudioResponse(200)

    monkeypatch.setattr(httpx, "post", fake_post)

    client.post(
        "/api/v1/tts-lab/generate",
        json={"model": "fish-audio/s2.1-pro-free:free", "text": "Hello", "speed": 1.5, "voice": "custom"},
        headers=auth,
    )
    assert captured["body"]["speed"] == 1.5
    assert "voice" not in captured["body"]


def test_generate_sends_default_voice_for_deepgram(client, auth, monkeypatch):
    """Confirmado em teste manual real: Deepgram Flux exige `voice` explícita
    (lista fixa `flux-*-en`) e rejeita `speed` — ver docs/TTS_LAB.md."""
    captured = {}

    def fake_post(url, **kwargs):
        captured["body"] = kwargs["json"]
        return FakeAudioResponse(200)

    monkeypatch.setattr(httpx, "post", fake_post)

    client.post(
        "/api/v1/tts-lab/generate",
        json={"model": "deepgram/flux-tts:free", "text": "Hello", "speed": 1.5},
        headers=auth,
    )
    assert captured["body"]["voice"] == "flux-bree-en"
    assert "speed" not in captured["body"]


def test_generate_wraps_gemini_pcm_response_as_playable_wav(client, auth, monkeypatch):
    """Confirmado em teste manual real: `google/gemini-3.1-flash-tts-preview`
    só devolve PCM cru (`content-type: audio/pcm;rate=24000;channels=1`) — o
    `<audio>` nativo não decodifica isso sem um cabeçalho WAV."""
    import wave

    raw_pcm = b"\x00\x01" * 500

    def fake_post(url, **kwargs):
        return FakeAudioResponse(200, content=raw_pcm, headers={"content-type": "audio/pcm;rate=24000;channels=1"})

    monkeypatch.setattr(httpx, "post", fake_post)

    response = client.post(
        "/api/v1/tts-lab/generate",
        json={"model": "google/gemini-3.1-flash-tts-preview", "text": "Hello"},
        headers=auth,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["content_type"] == "audio/wav"

    import io

    wav_bytes = base64.b64decode(payload["audio_base64"])
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
        assert wav_file.getframerate() == 24000
        assert wav_file.getnchannels() == 1
        assert wav_file.readframes(wav_file.getnframes()) == raw_pcm


def test_generate_provider_timeout_returns_504(client, auth, monkeypatch):
    def fake_post(url, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "post", fake_post)

    response = client.post(
        "/api/v1/tts-lab/generate",
        json={"model": "hexgrad/kokoro-82m", "text": "Hello"},
        headers=auth,
    )
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "tts_lab_timeout"


def test_generate_provider_rate_limited_returns_429(client, auth, monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda url, **kwargs: FakeAudioResponse(429, b""))

    response = client.post(
        "/api/v1/tts-lab/generate",
        json={"model": "hexgrad/kokoro-82m", "text": "Hello"},
        headers=auth,
    )
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "tts_lab_rate_limited"


def test_generate_provider_5xx_returns_503(client, auth, monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda url, **kwargs: FakeAudioResponse(500, b""))

    response = client.post(
        "/api/v1/tts-lab/generate",
        json={"model": "hexgrad/kokoro-82m", "text": "Hello"},
        headers=auth,
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "tts_lab_unavailable"


def test_generate_one_model_failure_does_not_affect_another(client, auth, monkeypatch):
    def fake_post(url, **kwargs):
        if kwargs["json"]["model"] == "hexgrad/kokoro-82m":
            raise httpx.HTTPError("falha simulada")
        return FakeAudioResponse(200)

    monkeypatch.setattr(httpx, "post", fake_post)

    failing = client.post(
        "/api/v1/tts-lab/generate",
        json={"model": "hexgrad/kokoro-82m", "text": "Hello"},
        headers=auth,
    )
    assert failing.status_code == 503

    working = client.post(
        "/api/v1/tts-lab/generate",
        json={"model": "deepgram/flux-tts:free", "text": "Hello"},
        headers=auth,
    )
    assert working.status_code == 200


def test_no_response_or_log_leaks_api_key(client, auth, monkeypatch, caplog):
    import logging

    secret = "sk-super-secret-tts-lab-key-should-never-leak"
    monkeypatch.setattr(get_settings(), "openrouter_api_key", secret)

    def fake_post(url, **kwargs):
        assert kwargs["headers"]["Authorization"] == f"Bearer {secret}"
        raise httpx.HTTPError("falha simulada")

    monkeypatch.setattr(httpx, "post", fake_post)

    with caplog.at_level(logging.DEBUG):
        response = client.post(
            "/api/v1/tts-lab/generate",
            json={"model": "hexgrad/kokoro-82m", "text": "Hello"},
            headers=auth,
        )
    assert secret not in response.text
    assert secret not in caplog.text


# ----------------------------------------------------- Kokoro Voice Lab


def test_kokoro_voices_endpoint_requires_auth(client):
    response = client.get("/api/v1/tts-lab/kokoro/voices")
    assert response.status_code == 401


def test_kokoro_voices_endpoint_lists_languages_and_voices(client, auth):
    response = client.get("/api/v1/tts-lab/kokoro/voices", headers=auth)
    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "hexgrad/kokoro-82m"
    codes = {lang["code"] for lang in payload["languages"]}
    assert {"en-US", "en-GB", "es-ES", "fr-FR", "ja-JP", "zh-CN"} <= codes

    en_us = next(lang for lang in payload["languages"] if lang["code"] == "en-US")
    voice_ids = {v["id"] for v in en_us["voices"]}
    assert "af_heart" in voice_ids
    assert "bf_alice" not in voice_ids  # voz britânica não pode aparecer em en-US
    assert all({"id", "name", "gender"} <= v.keys() for v in en_us["voices"])


def test_kokoro_generate_rejects_invalid_language(client, auth):
    response = client.post(
        "/api/v1/tts-lab/kokoro/generate",
        json={"language": "xx-XX", "voice": "af_heart", "text": "Hello"},
        headers=auth,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "tts_lab_kokoro_invalid_language"


def test_kokoro_generate_rejects_invalid_voice(client, auth):
    response = client.post(
        "/api/v1/tts-lab/kokoro/generate",
        json={"language": "en-US", "voice": "not-a-real-voice", "text": "Hello"},
        headers=auth,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "tts_lab_kokoro_invalid_voice"


def test_kokoro_generate_rejects_voice_from_another_language(client, auth):
    """`bf_alice` é uma voz britânica válida, mas não pertence a `en-US`."""
    response = client.post(
        "/api/v1/tts-lab/kokoro/generate",
        json={"language": "en-US", "voice": "bf_alice", "text": "Hello"},
        headers=auth,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "tts_lab_kokoro_invalid_voice"


def test_kokoro_generate_success_sends_model_voice_and_text(client, auth, monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["body"] = kwargs["json"]
        return FakeAudioResponse(200)

    monkeypatch.setattr(httpx, "post", fake_post)

    response = client.post(
        "/api/v1/tts-lab/kokoro/generate",
        json={"language": "es-ES", "voice": "ef_dora", "text": "Hola", "speed": 1.1},
        headers=auth,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "hexgrad/kokoro-82m"
    assert payload["language"] == "es-ES"
    assert payload["voice"] == "ef_dora"
    assert captured["body"]["voice"] == "ef_dora"
    assert captured["body"]["speed"] == 1.1
    assert captured["body"]["input"] == "Hola"


def test_kokoro_generate_provider_timeout_returns_504(client, auth, monkeypatch):
    def fake_post(url, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "post", fake_post)

    response = client.post(
        "/api/v1/tts-lab/kokoro/generate",
        json={"language": "en-US", "voice": "af_heart", "text": "Hello"},
        headers=auth,
    )
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "tts_lab_timeout"


def test_kokoro_generate_provider_rate_limited_returns_429(client, auth, monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda url, **kwargs: FakeAudioResponse(429, b""))

    response = client.post(
        "/api/v1/tts-lab/kokoro/generate",
        json={"language": "en-US", "voice": "af_heart", "text": "Hello"},
        headers=auth,
    )
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "tts_lab_rate_limited"


def test_kokoro_generate_one_voice_failure_does_not_affect_another(client, auth, monkeypatch):
    def fake_post(url, **kwargs):
        if kwargs["json"]["voice"] == "af_heart":
            raise httpx.HTTPError("falha simulada")
        return FakeAudioResponse(200)

    monkeypatch.setattr(httpx, "post", fake_post)

    failing = client.post(
        "/api/v1/tts-lab/kokoro/generate",
        json={"language": "en-US", "voice": "af_heart", "text": "Hello"},
        headers=auth,
    )
    assert failing.status_code == 503

    working = client.post(
        "/api/v1/tts-lab/kokoro/generate",
        json={"language": "en-US", "voice": "af_bella", "text": "Hello"},
        headers=auth,
    )
    assert working.status_code == 200


def test_kokoro_generate_denies_non_allowlisted_user(client, auth, db_session):
    from app.core.security import hash_password
    from app.models import User, UserPreference

    user = User(email="outro2@befluent.local", name="Outro", password_hash=hash_password("senha-segura"))
    db_session.add(user)
    db_session.flush()
    db_session.add(UserPreference(user_id=user.id))
    db_session.commit()

    other_client_response = client.post(
        "/api/v1/auth/login",
        json={"email": "outro2@befluent.local", "password": "senha-segura"},
    )
    assert other_client_response.status_code == 200
    headers = {"X-CSRF-Token": client.cookies.get("csrf_token")}

    response = client.post(
        "/api/v1/tts-lab/kokoro/generate",
        json={"language": "en-US", "voice": "af_heart", "text": "Hello"},
        headers=headers,
    )
    assert response.status_code == 403


def test_kokoro_generate_does_not_leak_api_key(client, auth, monkeypatch, caplog):
    import logging

    secret = "sk-super-secret-kokoro-lab-key-should-never-leak"
    monkeypatch.setattr(get_settings(), "openrouter_api_key", secret)

    def fake_post(url, **kwargs):
        assert kwargs["headers"]["Authorization"] == f"Bearer {secret}"
        raise httpx.HTTPError("falha simulada")

    monkeypatch.setattr(httpx, "post", fake_post)

    with caplog.at_level(logging.DEBUG):
        response = client.post(
            "/api/v1/tts-lab/kokoro/generate",
            json={"language": "en-US", "voice": "af_heart", "text": "Hello"},
            headers=auth,
        )
    assert secret not in response.text
    assert secret not in caplog.text


def test_kokoro_voice_lab_does_not_change_production_tts_config():
    """`_KOKORO_VOICE_BY_LANGUAGE` (voz padrão de produção por idioma, em
    `app/services/speech.py`) não é lida nem importada por `kokoro_voices.py`
    — o Voice Lab não influencia nem depende da configuração de produção."""
    import app.services.kokoro_voices as kv_module

    assert "speech" not in dir(kv_module) or not hasattr(kv_module, "_KOKORO_VOICE_BY_LANGUAGE")
    from app.services.speech import _KOKORO_VOICE_BY_LANGUAGE

    assert _KOKORO_VOICE_BY_LANGUAGE == {
        "en": "af_heart",
        "es": "ef_dora",
        "fr": "ff_siwis",
        "ja": "jf_alpha",
        "zh": "zf_xiaoxiao",
    }
