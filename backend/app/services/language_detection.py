"""Detecção offline do idioma-alvo.

`lingua-language-detector` foi escolhido porque o projeto não tinha
detector, ele roda sem rede e devolve uma confiança por idioma. O pacote
é grande, mas cobre os oito idiomas ensinados, inclusive latim.
O texto-alvo usa só esses oito. O classificador de papéis acrescenta
o português, para reconhecer o apoio sem recalibrar o limiar do alvo.
Confiança alta (0,80) numa língua diferente do alvo invalida o item.
Se o vencedor é o alvo, mas a confiança fica abaixo de 0,50 ou a distância
para a segunda língua é menor que 0,25, o item vai para revisão.
Textos com menos de quatro palavras ficam fora desta camada.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from lingua import Language, LanguageDetectorBuilder

HIGH_CONFIDENCE = 0.80
_SURE_TARGET = 0.50
_SURE_GAP = 0.25
_MIN_WORDS = 4
_MIN_CJK = 8
_CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")


def has_enough_signal(text: str) -> bool:
    """Texto curto demais não entra no detector.

    Japonês e mandarim não se medem por palavras separadas por espaço.
    Um termo isolado continua fora; uma frase nesses sistemas entra.
    """
    if _CJK.search(text):
        return len(_CJK.findall(text)) >= _MIN_CJK
    return len(text.split()) >= _MIN_WORDS

_TARGET_BY_CODE = {
    "en": Language.ENGLISH,
    "es-ES": Language.SPANISH,
    "fr": Language.FRENCH,
    "it": Language.ITALIAN,
    "de": Language.GERMAN,
    "ja": Language.JAPANESE,
    "zh-CN": Language.CHINESE,
    "la": Language.LATIN,
}
# O português entra só na classificação de papéis. No detector do texto-alvo
# ele rebaixa frases francesas que já passavam no limiar de 0,50.
_ROLE_BY_CODE = {**_TARGET_BY_CODE, "pt": Language.PORTUGUESE}

_TARGET_DETECTOR = None
_ROLE_DETECTOR = None
_CODE_BY_LANGUAGE = {language: code for code, language in _ROLE_BY_CODE.items()}


def _build(codes: dict[str, Language]):
    return LanguageDetectorBuilder.from_languages(*codes.values()).build()


def _target_detector():
    global _TARGET_DETECTOR
    if _TARGET_DETECTOR is None:
        _TARGET_DETECTOR = _build(_TARGET_BY_CODE)
    return _TARGET_DETECTOR


def _role_detector():
    global _ROLE_DETECTOR
    if _ROLE_DETECTOR is None:
        _ROLE_DETECTOR = _build(_ROLE_BY_CODE)
    return _ROLE_DETECTOR


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
    expected = _TARGET_BY_CODE.get(target_language or "")
    if expected is None:
        return None
    uncertain = False
    for text in _target_texts(payload):
        if not has_enough_signal(text):
            continue
        values = _target_detector().compute_language_confidence_values(text)
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


def top_language(text: str) -> tuple[str | None, float]:
    """Idioma vencedor entre os idiomas ensinados, mais o português de apoio."""
    values = _role_detector().compute_language_confidence_values(text)
    if not values:
        return None, 0.0
    top = values[0]
    return _CODE_BY_LANGUAGE.get(top.language), float(top.value)
