"""Provedores de fala do BeFluent (STT/TTS) e avaliação de pronúncia.

Mesma regra do módulo de IA (`app/services/ai.py`): em produção uma falha
real de provedor nunca vira conteúdo simulado apresentado como se fosse
resultado real. Mock só roda quando explicitamente selecionado
(`STT_PROVIDER=mock` / `TTS_PROVIDER=mock`) fora de produção.

STT: Groq (`whisper-large-v3-turbo`) como primário, OpenRouter
(`input_audio` multimodal, contrato documentado pela OpenRouter) como
fallback. TTS: Piper (`TTS_PROVIDER=piper_api`) é o provedor de produção.
O frontend cai no SpeechSynthesis do navegador se a síntese de servidor falhar.
"""

import base64
import io
import logging
import os
import tempfile
import wave
from abc import ABC, abstractmethod

import httpx

from app.core.config import get_settings
from app.core.errors import APIError

logger = logging.getLogger(__name__)

_EXTENSION_BY_CONTENT_TYPE = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "m4a",
    "audio/m4a": "m4a",
    "audio/flac": "flac",
}


def _extension_for(content_type: str | None, default: str) -> str:
    return _EXTENSION_BY_CONTENT_TYPE.get((content_type or "").lower(), default)


def _language_hint(language_code: str) -> str:
    """ISO-639-1 aproximado a partir do código do projeto (ex.: `es-ES` -> `es`)."""
    return language_code.split("-", 1)[0].lower()


# --------------------------------------------------------------------- STT


class BaseSTTProvider(ABC):
    @abstractmethod
    def transcribe(self, path: str, language_code: str, content_type: str | None = None) -> dict: ...


class MockSTTProvider(BaseSTTProvider):
    """Determinístico, sem chamada externa. Só roda com `STT_PROVIDER=mock`."""

    def transcribe(self, path, language_code, content_type=None):
        return {
            "text": "[mock] Transcrição simulada — configure um provedor STT real para reconhecimento de fala.",
            "language_code": language_code,
            "provider": "mock",
            "model": None,
        }


class GroqSTTProvider(BaseSTTProvider):
    """Whisper large-v3-turbo via Groq (`POST /openai/v1/audio/transcriptions`)."""

    def __init__(self):
        self.s = get_settings()

    def transcribe(self, path, language_code, content_type=None):
        extension = _extension_for(content_type, "webm")
        with open(path, "rb") as audio_file:
            response = httpx.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.s.groq_api_key}"},
                files={
                    "file": (
                        f"audio.{extension}",
                        audio_file,
                        content_type or "application/octet-stream",
                    )
                },
                data={
                    "model": self.s.groq_stt_model,
                    "language": _language_hint(language_code),
                    "response_format": "json",
                },
                timeout=30,
            )
        response.raise_for_status()
        text = response.json()["text"]
        return {
            "text": text,
            "language_code": language_code,
            "provider": "groq",
            "model": self.s.groq_stt_model,
        }


class OpenRouterSTTProvider(BaseSTTProvider):
    """Fallback de STT via OpenRouter, usando o contrato multimodal `input_audio`
    de chat completions (documentado pela OpenRouter para modelos com áudio)."""

    def __init__(self):
        self.s = get_settings()

    def transcribe(self, path, language_code, content_type=None):
        extension = _extension_for(content_type, "wav")
        with open(path, "rb") as audio_file:
            encoded = base64.b64encode(audio_file.read()).decode("ascii")
        response = httpx.post(
            f"{self.s.openrouter_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.s.openrouter_api_key}"},
            json={
                "model": self.s.stt_fallback_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Transcreva o áudio literalmente, sem comentários "
                                    f"nem tradução, no idioma de código '{language_code}'."
                                ),
                            },
                            {
                                "type": "input_audio",
                                "input_audio": {"data": encoded, "format": extension},
                            },
                        ],
                    }
                ],
            },
            timeout=45,
        )
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]
        return {
            "text": text,
            "language_code": language_code,
            "provider": "openrouter",
            "model": self.s.stt_fallback_model,
        }


def _stt_chain(s) -> list[BaseSTTProvider]:
    providers: list[BaseSTTProvider] = []
    if s.stt_provider == "groq" and s.groq_api_key:
        providers.append(GroqSTTProvider())
    if s.stt_fallback_provider == "openrouter" and s.openrouter_api_key and s.stt_fallback_model:
        providers.append(OpenRouterSTTProvider())
    return providers


def transcribe_audio(path: str, language_code: str, content_type: str | None = None) -> dict:
    """Ponto único de transcrição: seleciona o provedor pela configuração.

    `STT_PROVIDER=mock` é um interruptor explícito (como `AI_MOCK_MODE`) e vale
    em qualquer ambiente. Fora disso, tenta a cadeia primário → fallback; se
    ambos falharem, produção recebe erro explícito (503) e nunca uma
    transcrição fabricada — só fora de produção o mock cobre a indisponibilidade.
    """
    s = get_settings()
    if s.stt_provider == "mock":
        logger.info("STT em MockSTTProvider (STT_PROVIDER=mock)")
        return MockSTTProvider().transcribe(path, language_code, content_type)

    last_error: Exception | None = None
    for provider in _stt_chain(s):
        try:
            return provider.transcribe(path, language_code, content_type)
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            logger.warning("STT provider %s falhou: %s", type(provider).__name__, exc)
            last_error = exc

    if s.environment == "production":
        raise APIError(
            503,
            "stt_unavailable",
            "O serviço de reconhecimento de fala está temporariamente indisponível.",
            retryable=True,
        ) from last_error
    logger.warning("STT indisponível fora de produção; usando MockSTTProvider (desenvolvimento)")
    return MockSTTProvider().transcribe(path, language_code, content_type)


# --------------------------------------------------------------------- TTS


class BaseTTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, language_code: str, speed: float | None = None) -> tuple[bytes, str]: ...


class MockTTSProvider(BaseTTSProvider):
    def synthesize(self, text, language_code, speed=None):
        return b"RIFF\x24\x00\x00\x00WAVEfmt ", "audio/wav"


class UnsupportedTTSLanguage(ValueError):
    """`language_code` não está no mapa do Piper.

    Não cai num idioma parecido. O `AudioPlayer` usa a voz do navegador.
    """

    def __init__(self, language_code: str):
        super().__init__(f"Nenhuma voz Piper configurada para o idioma '{language_code}'.")
        self.language_code = language_code


#: Códigos BeFluent → códigos aceitos pelo serviço Piper. Sem entrada aqui,
#: o idioma não é enviado (nunca se reduz `es-ES` por split nem se escolhe
#: uma voz parecida). `la-classical` fica de fora de propósito.
_PIPER_LANGUAGE_BY_CODE = {
    "en": "en",
    "es": "es",
    "es-ES": "es",
    "fr": "fr",
    "it": "it",
    "de": "de",
    "la": "la-ecclesiastical",
}

#: Frases curtas no Piper de produção levam cerca de 3s. 20s cobre uma
#: frase longa sem segurar o aluno num timeout de 45s ou 90s.
_PIPER_TIMEOUT_SECONDS = 20


def _piper_language(language_code: str) -> str:
    mapped = _PIPER_LANGUAGE_BY_CODE.get(language_code)
    if mapped is None:
        raise UnsupportedTTSLanguage(language_code)
    return mapped


class PiperAPITTSProvider(BaseTTSProvider):
    """Piper hospedado pelo projeto e exposto em `POST /v1/tts`.

    As vozes ficam no serviço Piper. Este cliente só traduz o código do
    BeFluent para o código de idioma que o serviço aceita.
    """

    def __init__(self):
        self.s = get_settings()

    def synthesize(self, text, language_code, speed=None):
        base_url = self.s.tts_base_url.rstrip("/")
        if not base_url or not self.s.tts_api_key:
            raise ValueError("Piper API não configurada")

        response = httpx.post(
            f"{base_url}/v1/tts",
            headers={"X-API-Key": self.s.tts_api_key},
            json={
                "text": text,
                "language": _piper_language(language_code),
                "speed": speed if speed is not None else self.s.tts_speed,
            },
            timeout=_PIPER_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "audio/wav").split(";", 1)[0]
        return response.content, content_type


def synthesize_audio(text: str, language_code: str, speed: float | None = None) -> tuple[bytes, str]:
    """Ponto único de síntese: seleciona o provedor pela configuração.

    Mesma regra do STT: `TTS_PROVIDER=mock` é um interruptor explícito que só
    vale fora de produção. `TTS_PROVIDER=piper_api` chama o Piper em
    `TTS_BASE_URL`. Se o provedor falhar, produção recebe erro explícito
    (503) e nunca áudio fabricado — só fora de produção a falha cai no mock.

    `TTS_PROVIDER=web_speech` desativa a síntese de servidor. O `AudioPlayer`
    cai no SpeechSynthesis do navegador quando este endpoint responde erro.
    """
    s = get_settings()
    if s.tts_provider == "web_speech":
        raise APIError(
            503,
            "tts_unavailable",
            "Síntese de voz em servidor desativada por configuração (TTS_PROVIDER=web_speech).",
            retryable=False,
        )

    if s.tts_provider == "mock":
        if s.environment == "production":
            raise APIError(
                503,
                "tts_unavailable",
                "Síntese de voz em servidor não está disponível nesta implantação.",
                retryable=False,
            )
        return MockTTSProvider().synthesize(text, language_code, speed)

    if s.tts_provider == "piper_api" and s.tts_base_url and s.tts_api_key:
        try:
            return PiperAPITTSProvider().synthesize(text, language_code, speed)
        except UnsupportedTTSLanguage as exc:
            logger.info("TTS sem voz Piper configurada: language_code=%s", language_code)
            raise APIError(
                400,
                "tts_unsupported_language",
                "Este idioma não tem voz configurada no TTS de servidor.",
                retryable=False,
            ) from exc
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            logger.warning("TTS provider piper_api falhou: %s", exc)
            if s.environment == "production":
                raise APIError(
                    503,
                    "tts_unavailable",
                    "O serviço de síntese de voz está temporariamente indisponível.",
                    retryable=True,
                ) from exc
            logger.warning("TTS indisponível fora de produção; usando MockTTSProvider (desenvolvimento)")
            return MockTTSProvider().synthesize(text, language_code, speed)

    raise APIError(
        503,
        "tts_unavailable",
        "Síntese de voz em servidor não está disponível nesta implantação.",
        retryable=False,
    )


# ------------------------------------------------------------- Pronúncia


def assess_pronunciation(target_text: str, transcript: str) -> dict:
    """Nenhum provedor real de avaliação fonética está integrado.

    Fabricar uma nota (`score=85.0` fixo, como antes) seria uma correção
    apresentada como real sem nenhuma análise por trás — o mesmo problema que
    a avaliação de escrita evita com `evaluated_by="heuristic"`. Aqui não há
    nem heurística objetiva disponível, então a resposta é sempre um estado
    explícito de indisponibilidade, em qualquer ambiente.
    """
    return {
        "status": "unavailable",
        "score": None,
        "provider": None,
        "feedback": {
            "message": (
                "Avaliação de pronúncia ainda não está disponível: nenhum "
                "provedor real de avaliação fonética está configurado."
            )
        },
    }


def save_temp_audio(data: bytes) -> str:
    settings = get_settings()
    if len(data) > settings.max_audio_bytes:
        raise ValueError("Arquivo de áudio excede o limite permitido.")
    try:
        with wave.open(io.BytesIO(data), "rb") as audio:
            duration = audio.getnframes() / max(audio.getframerate(), 1)
            if duration > settings.max_audio_duration_seconds:
                raise ValueError("A duração do áudio excede o limite permitido.")
    except (wave.Error, EOFError):
        # `wave` só decodifica WAV. Formatos comprimidos (webm/ogg, o que o
        # navegador grava por padrão) não têm a duração validada aqui — só o
        # tamanho em bytes protege contra áudio muito longo nesses casos.
        # Validar duração de WebM de forma confiável exigiria ffmpeg/ffprobe
        # (dependência de sistema/imagem Docker fora do escopo desta tarefa;
        # ver AGENTS.md — mudança de infraestrutura pendente de autorização).
        pass
    fd, path = tempfile.mkstemp(suffix=".audio")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return path
    except Exception:
        os.close(fd)
        os.unlink(path)
        raise