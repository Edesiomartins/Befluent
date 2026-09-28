"""Cache de áudio do TTS.

O mesmo texto era sintetizado de novo a cada toque no botão Ouvir — custo e
espera repetidos por um áudio idêntico. As regras que os testes travam: mesmo
pedido não vai ao provedor duas vezes; velocidade diferente é outro áudio;
falha nunca é cacheada; e o cache tem teto (não cresce sem limite).
"""

import pytest

from app.services import speech


@pytest.fixture(autouse=True)
def clean_cache():
    speech.clear_tts_cache()
    yield
    speech.clear_tts_cache()


@pytest.fixture
def counting_provider(monkeypatch):
    """Substitui a síntese real por um contador determinístico."""
    calls: list[tuple[str, str, float | None]] = []

    def fake(text: str, language_code: str, speed: float | None):
        calls.append((text, language_code, speed))
        return b"audio-" + text.encode(), "audio/wav"

    monkeypatch.setattr(speech, "_synthesize_uncached", fake)
    return calls


def test_mesmo_pedido_sintetiza_uma_vez(counting_provider):
    first = speech.synthesize_audio_cached("Hello", "en", 1.0)
    second = speech.synthesize_audio_cached("Hello", "en", 1.0)

    assert first == second
    assert len(counting_provider) == 1


def test_velocidade_diferente_e_outro_audio(counting_provider):
    speech.synthesize_audio_cached("Hello", "en", 1.0)
    speech.synthesize_audio_cached("Hello", "en", 0.75)

    assert len(counting_provider) == 2


def test_idioma_diferente_e_outro_audio(counting_provider):
    speech.synthesize_audio_cached("Hello", "en", 1.0)
    speech.synthesize_audio_cached("Hello", "fr", 1.0)

    assert len(counting_provider) == 2


def test_falha_do_provedor_nao_e_cacheada(monkeypatch):
    from app.core.errors import APIError

    attempts = {"n": 0}

    def flaky(text: str, language_code: str, speed: float | None):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise APIError(503, "tts_unavailable", "fora do ar")
        return b"audio", "audio/wav"

    monkeypatch.setattr(speech, "_synthesize_uncached", flaky)

    with pytest.raises(APIError):
        speech.synthesize_audio_cached("Hello", "en", 1.0)
    audio, _content_type = speech.synthesize_audio_cached("Hello", "en", 1.0)

    assert audio == b"audio"
    assert attempts["n"] == 2


def test_cache_tem_teto_de_entradas(counting_provider, monkeypatch):
    monkeypatch.setattr(speech, "TTS_CACHE_MAX_ENTRIES", 3)

    for index in range(5):
        speech.synthesize_audio_cached(f"frase {index}", "en", 1.0)

    assert speech.tts_cache_size() <= 3
    # A entrada mais antiga saiu: pedi-la de novo volta ao provedor.
    speech.synthesize_audio_cached("frase 0", "en", 1.0)
    assert len(counting_provider) == 6
