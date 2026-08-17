"""TTS Lab — comparação isolada de modelos de TTS via OpenRouter.

Ferramenta administrativa temporária, sem relação com o fluxo de produção de
TTS (`app/services/speech.py`, usado pelas aulas e pelo Speech Coach). Nunca
importa nem altera esse módulo: mesma `OPENROUTER_API_KEY`, chamada isolada
a `/audio/speech`, resultado só usado para comparação manual.

Capacidades por modelo (`supports_speed`/`supports_voice`) foram confirmadas
com um teste manual real contra a OpenRouter (ver `docs/TTS_LAB.md`, seção
"Teste real"), não presumidas:

- `deepgram/flux-tts:free` exige `voice` explícita (lista fixa de vozes
  `flux-*-en`) e rejeita `speed` (HTTP 400). `default_voice` usa uma dessas
  vozes confirmadas.
- `fish-audio/s2.1-pro-free:free` aceitou `speed` sem erro; `voice`
  explícita não foi testada, então `supports_voice` continua `False`.
- `hexgrad/kokoro-82m` é o modelo já validado em produção (`speech.py`):
  aceita `speed` e `voice`.
- `google/gemini-3.1-flash-tts-preview` exige `voice` explícita e só
  devolve `response_format="pcm"` — nunca mp3/wav. `speed` não foi testado
  (modelo pago; evitado excesso de chamadas), então `supports_speed`
  continua `False` por precaução.
"""

from __future__ import annotations

import io
import logging
import re
import time
import wave
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 30.0

_FORMAT_CONTENT_TYPE = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
}

TTS_LAB_MODELS: dict[str, dict] = {
    "deepgram/flux-tts:free": {
        "display_name": "Deepgram Flux",
        "provider": "deepgram",
        "supports_speed": False,
        "supports_voice": True,
        "supports_streaming": False,
        "supported_formats": ["mp3"],
        "default_voice": "flux-bree-en",
        "free": True,
    },
    "fish-audio/s2.1-pro-free:free": {
        "display_name": "Fish Audio S2.1 Pro",
        "provider": "fish-audio",
        "supports_speed": True,
        "supports_voice": False,
        "supports_streaming": False,
        "supported_formats": ["mp3"],
        "default_voice": None,
        "free": True,
    },
    "hexgrad/kokoro-82m": {
        "display_name": "Kokoro 82M",
        "provider": "hexgrad",
        "supports_speed": True,
        "supports_voice": True,
        "supports_streaming": False,
        "supported_formats": ["mp3"],
        "default_voice": "af_heart",
        "free": False,
    },
    "google/gemini-3.1-flash-tts-preview": {
        "display_name": "Gemini 3.1 Flash TTS (Preview)",
        "provider": "google",
        "supports_speed": False,
        "supports_voice": True,
        "supported_formats": ["pcm"],
        "supports_streaming": False,
        "default_voice": "Kore",
        "free": False,
    },
}


def list_models() -> list[dict]:
    return [{"id": model_id, **config} for model_id, config in TTS_LAB_MODELS.items()]


def _pcm_to_wav(pcm_bytes: bytes, content_type_header: str) -> bytes:
    """Envolve PCM cru (resposta real da Gemini TTS, ex. `google/gemini-*`)
    num contêiner WAV mínimo — o `<audio>` nativo do navegador não decodifica
    PCM sem cabeçalho. Taxa e canais vêm do `content-type` que o próprio
    provedor devolve (ex. `audio/pcm;rate=24000;channels=1`, confirmado no
    teste manual real — ver docs/TTS_LAB.md); 16 bits por amostra é assumido
    por ser o padrão de PCM de TTS (Gemini/OpenAI), já que nenhum header
    confirma profundidade de bits.
    """
    rate_match = re.search(r"rate=(\d+)", content_type_header)
    channels_match = re.search(r"channels=(\d+)", content_type_header)
    sample_rate = int(rate_match.group(1)) if rate_match else 24000
    channels = int(channels_match.group(1)) if channels_match else 1

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)
    return buffer.getvalue()


class TTSLabError(Exception):
    """Erro de geração no TTS Lab, com código/status já mapeados para a API."""

    def __init__(self, status_code: int, code: str, message: str, retryable: bool = False):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)


@dataclass
class TTSLabResult:
    model: str
    audio_bytes: bytes
    content_type: str
    latency_ms: int
    audio_size_bytes: int
    free_model: bool
    cost_available: bool = False
    estimated_cost: float | None = None


def generate(model_id: str, text: str, speed: float | None = None, voice: str | None = None) -> TTSLabResult:
    config = TTS_LAB_MODELS.get(model_id)
    if config is None:
        raise TTSLabError(400, "tts_lab_model_not_found", "Modelo não configurado no TTS Lab.")

    settings = get_settings()
    if not settings.openrouter_api_key:
        raise TTSLabError(
            503,
            "tts_lab_unconfigured",
            "OPENROUTER_API_KEY não está configurada nesta implantação.",
        )

    response_format = config["supported_formats"][0]
    payload: dict = {"model": model_id, "input": text, "response_format": response_format}
    if config["supports_voice"]:
        chosen_voice = voice or config["default_voice"]
        if chosen_voice:
            payload["voice"] = chosen_voice
    if config["supports_speed"] and speed is not None:
        payload["speed"] = speed

    started = time.monotonic()
    try:
        response = httpx.post(
            f"{settings.openrouter_base_url}/audio/speech",
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException as exc:
        logger.warning("TTS Lab request model=%s status=TIMEOUT", model_id)
        raise TTSLabError(504, "tts_lab_timeout", "O provedor demorou demais para responder.", retryable=True) from exc
    except httpx.HTTPError as exc:
        logger.warning("TTS Lab request model=%s status=ERROR error=%s", model_id, type(exc).__name__)
        raise TTSLabError(503, "tts_lab_unavailable", "Não foi possível contatar o provedor.", retryable=True) from exc

    latency_ms = int((time.monotonic() - started) * 1000)

    if response.status_code == 429:
        logger.warning("TTS Lab request model=%s status=RATE_LIMITED latency_ms=%d", model_id, latency_ms)
        raise TTSLabError(429, "tts_lab_rate_limited", "O provedor limitou as requisições (429).", retryable=True)
    if response.status_code >= 500:
        logger.warning("TTS Lab request model=%s status=ERROR http=%d latency_ms=%d", model_id, response.status_code, latency_ms)
        raise TTSLabError(503, "tts_lab_unavailable", "O provedor está temporariamente indisponível.", retryable=True)
    if response.status_code >= 400:
        logger.warning("TTS Lab request model=%s status=ERROR http=%d latency_ms=%d", model_id, response.status_code, latency_ms)
        raise TTSLabError(502, "tts_lab_provider_error", "O provedor rejeitou a requisição.", retryable=False)

    if response_format == "pcm":
        audio = _pcm_to_wav(response.content, response.headers.get("content-type", ""))
        content_type = "audio/wav"
    else:
        audio = response.content
        content_type = _FORMAT_CONTENT_TYPE.get(response_format, "audio/mpeg")
    logger.info(
        "TTS Lab request model=%s status=OK latency_ms=%d response_size=%d",
        model_id,
        latency_ms,
        len(audio),
    )
    return TTSLabResult(
        model=model_id,
        audio_bytes=audio,
        content_type=content_type,
        latency_ms=latency_ms,
        audio_size_bytes=len(audio),
        free_model=bool(config["free"]),
    )
