"""Mapeamento explícito de códigos internos → BCP 47.

`la-classical` não é um tag BCP 47 padrão. Integrações externas (STT/TTS
de terceiros, metadados) devem usar `to_bcp47` em vez de passar o código
interno cru — e nunca tratar `la-classical` como voz Piper suportada.
"""

from __future__ import annotations

# Preferência documentada: variante privada `la-x-classical`.
# Alternativa aceitável em APIs que só aceitam ISO 639-1: `la`.
_BCP47: dict[str, str] = {
    "en": "en",
    "es-ES": "es-ES",
    "fr": "fr",
    "it": "it",
    "de": "de",
    "ja": "ja",
    "zh-CN": "zh-CN",
    "la": "la",
    "la-classical": "la-x-classical",
}


def to_bcp47(language_code: str) -> str:
    """Converte código interno BeFluent para tag BCP 47 / aproximação."""
    return _BCP47.get(language_code, language_code)


def is_latin_modality(language_code: str) -> bool:
    return language_code in {"la", "la-classical"}
