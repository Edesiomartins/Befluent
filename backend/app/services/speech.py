"""Provedores de fala do BeFluent (STT/TTS) e avaliação de pronúncia.

Mesma regra do módulo de IA (`app/services/ai.py`): em produção uma falha
real de provedor nunca vira conteúdo simulado apresentado como se fosse
resultado real. Mock só roda quando explicitamente selecionado
(`STT_PROVIDER=mock` / `TTS_PROVIDER=mock`) fora de produção.

STT: Groq (`whisper-large-v3-turbo`) como primário, OpenRouter
(`input_audio` multimodal, contrato documentado pela OpenRouter) como
fallback. TTS: Kokoro-82M (`hexgrad/kokoro-82m`) via `/audio/speech` da
OpenRouter (`TTS_PROVIDER=openrouter`), com a mesma `OPENROUTER_API_KEY`;
o frontend cai no SpeechSynthesis do navegador só se essa chamada falhar.
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


# Voz padrão de produção por idioma ISO-639-1, escolhida manualmente por
# escuta comparativa no Kokoro Voice Lab (`/admin/tts-lab`, seção "Kokoro
# Voice Lab") — não é um ranking automático nem derivado de nenhuma
# heurística. Trocar uma voz aqui é a única forma de mudar a voz de
# produção; ver docs/TTS.md ("Como trocar uma voz") antes de editar.
# `_language_hint` reduz o código do projeto (ex. "es-ES", "zh-CN") ao
# prefixo ISO-639-1 antes do lookup — sem `startsWith`/substring matching
# que pudesse casar um idioma errado.
_KOKORO_VOICE_BY_LANGUAGE = {
    "en": "af_sky",
    "es": "em_alex",
    "fr": "ff_siwis",
    "ja": "jf_nezumi",
    "zh": "zf_xiaoxiao",
}


class UnsupportedTTSLanguage(ValueError):
    """`language_code` não tem voz Kokoro configurada (fora do allowlist de
    `_KOKORO_VOICE_BY_LANGUAGE`, sem `TTS_VOICE` forçando uma voz única).

    Propositalmente NÃO cai num idioma "parecido" nem numa voz default — ver
    seção "Idioma" de docs/TTS.md: mandar texto de um idioma desconhecido
    para a voz de outro idioma produziria fala errada, não uma rede de
    segurança. É melhor devolver esse erro (o `AudioPlayer` do frontend cai
    no SpeechSynthesis do navegador, que lê qualquer idioma do BCP-47) do
    que arriscar uma leitura incorreta.
    """

    def __init__(self, language_code: str):
        super().__init__(f"Nenhuma voz Kokoro configurada para o idioma '{language_code}'.")
        self.language_code = language_code


def _voice_for_language(language_code: str, s) -> str:
    if s.tts_voice:
        return s.tts_voice
    voice = _KOKORO_VOICE_BY_LANGUAGE.get(_language_hint(language_code))
    if voice is None:
        raise UnsupportedTTSLanguage(language_code)
    return voice


class OpenRouterTTSProvider(BaseTTSProvider):
    """Kokoro-82M (`hexgrad/kokoro-82m`) via `/audio/speech` da OpenRouter."""

    def __init__(self):
        self.s = get_settings()

    def synthesize(self, text, language_code, speed=None):
        response = httpx.post(
            f"{self.s.openrouter_base_url}/audio/speech",
            headers={"Authorization": f"Bearer {self.s.openrouter_api_key}"},
            json={
                "model": self.s.tts_model,
                "input": text,
                "voice": _voice_for_language(language_code, self.s),
                "response_format": "mp3",
                "speed": speed if speed is not None else self.s.tts_speed,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.content, "audio/mpeg"


def synthesize_audio(text: str, language_code: str, speed: float | None = None) -> tuple[bytes, str]:
    """Ponto único de síntese: seleciona o provedor pela configuração.

    Mesma regra do STT: `TTS_PROVIDER=mock` é um interruptor explícito que só
    vale fora de produção. Com `TTS_PROVIDER=openrouter`, tenta o Kokoro-82M
    (mesma `OPENROUTER_API_KEY` já usada por IA/STT); se falhar, produção
    recebe erro explícito (503) e nunca áudio fabricado — só fora de produção
    a falha cai no mock.

    `TTS_PROVIDER=web_speech` é o interruptor de rollback: desativa o Kokoro
    de servidor sem remover código nenhum. Devolve o mesmo 503 que qualquer
    valor de `TTS_PROVIDER` não reconhecido já devolveria (ver o `raise` no
    fim da função) — só existe como ramo explícito para não depender de um
    comportamento acidental de fallthrough; ver docs/TTS.md ("Rollback").
    O `AudioPlayer` do frontend já cai no SpeechSynthesis do navegador
    sempre que este endpoint responde erro, então esse único valor de env
    var é suficiente para o rollback — não é necessário um `TTS_FALLBACK_
    PROVIDER` separado, porque o fallback roda inteiramente no navegador.
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

    if s.tts_provider == "openrouter" and s.openrouter_api_key:
        try:
            return OpenRouterTTSProvider().synthesize(text, language_code, speed)
        except UnsupportedTTSLanguage as exc:
            # Erro de entrada (idioma sem voz configurada), não indisponibilidade
            # do provedor — vale em qualquer ambiente, nunca cai no mock.
            logger.info("TTS sem voz Kokoro configurada: language_code=%s", language_code)
            raise APIError(
                400,
                "tts_unsupported_language",
                "Este idioma não tem voz configurada no TTS de servidor.",
                retryable=False,
            ) from exc
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            logger.warning("TTS provider openrouter falhou: %s", exc)
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
