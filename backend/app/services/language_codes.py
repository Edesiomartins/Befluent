"""Mapeamento explícito de códigos internos → BCP 47."""

from __future__ import annotations

_BCP47: dict[str, str] = {
    "en": "en",
    "es-ES": "es-ES",
    "fr": "fr",
    "it": "it",
    "de": "de",
    "ja": "ja",
    "zh-CN": "zh-CN",
    "la": "la",
}


def to_bcp47(language_code: str) -> str:
    """Converte código interno BeFluent para tag BCP 47 / aproximação."""
    return _BCP47.get(language_code, language_code)


def is_latin_modality(language_code: str) -> bool:
    return language_code == "la"
