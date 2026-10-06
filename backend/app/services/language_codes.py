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


TARGET_LANGUAGE_CODES = tuple(_BCP47)
NATIVE_LANGUAGE_CODES = (*TARGET_LANGUAGE_CODES, "pt-BR")

def validate_native_language(value: str | None) -> str | None:
    if value is not None and value not in NATIVE_LANGUAGE_CODES:
        raise ValueError("Código de língua nativa inválido.")
    return value

def native_language_metadata(user) -> dict:
    return {"native_language": user.native_language,
            "native_language_required": user.native_language is None,
            "native_language_options": list(NATIVE_LANGUAGE_CODES)}
