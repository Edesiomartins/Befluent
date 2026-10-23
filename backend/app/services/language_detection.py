"""Detecção offline do idioma-alvo.

`lingua-language-detector` foi escolhido porque o projeto não tinha
detector, ele roda sem rede e devolve uma confiança por idioma. O pacote
é grande, mas cobre os oito idiomas ensinados, inclusive latim.
Confiança alta (0,80) numa língua diferente do alvo invalida o item.
Se o vencedor é o alvo, mas a confiança fica abaixo de 0,50 ou a distância
para a segunda língua é menor que 0,25, o item vai para revisão.
Textos com menos de quatro palavras ficam fora desta camada.
"""

from __future__ import annotations

from collections.abc import Mapping

from lingua import Language, LanguageDetectorBuilder

HIGH_CONFIDENCE = 0.80
_SURE_TARGET = 0.50
_SURE_GAP = 0.25
_MIN_WORDS = 4

_BY_CODE = {
    "en": Language.ENGLISH,
    "es-ES": Language.SPANISH,
    "fr": Language.FRENCH,
    "it": Language.ITALIAN,
    "de": Language.GERMAN,
    "ja": Language.JAPANESE,
    "zh-CN": Language.CHINESE,
    "la": Language.LATIN,
}

_DETECTOR = None


def _detector():
    global _DETECTOR
    if _DETECTOR is None:
        _DETECTOR = LanguageDetectorBuilder.from_languages(*_BY_CODE.values()).build()
    return _DETECTOR


def _target_texts(payload: Mapping) -> list[str]:
    texts = []
    has_prompt_target = "prompt_target" in payload
    for key, value in payload.items():
        if not isinstance(key, str) or not isinstance(value, str) or not value.strip():
            continue
        if key.endswith("_target") or (key == "prompt" and not has_prompt_target):
            texts.append(value)
    return texts


def target_field_status(payload: Mapping, target_language: str | None) -> str | None:
    """`language_invalid`, `review_required` ou None quando o detector não muda o item."""
    expected = _BY_CODE.get(target_language or "")
    if expected is None:
        return None
    uncertain = False
    for text in _target_texts(payload):
        if len(text.split()) < _MIN_WORDS:
            continue
        values = _detector().compute_language_confidence_values(text)
        if not values:
            uncertain = True
            continue
        top = values[0]
        second = values[1].value if len(values) > 1 else 0.0
        if top.language != expected:
            if top.value >= HIGH_CONFIDENCE:
                return "language_invalid"
            uncertain = True
            continue
        if top.value < _SURE_TARGET or top.value - second < _SURE_GAP:
            uncertain = True
    if uncertain:
        return "review_required"
    return None
