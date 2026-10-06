"""Small deterministic guard; does not certify language or CEFR correctness."""
from __future__ import annotations
import unicodedata
from functools import lru_cache
from app.core.levels import LEVEL_ORDER
from app.services import lesson_bank
from collections.abc import Mapping

_FIELDS = {
    "vocabulary": {"items": list}, "grammar": {"explanation": str, "examples": list, "exercises": list},
    "reading": {"text": str, "questions": list}, "listening": {"transcript": str, "questions": list},
    "writing": {"prompt": str}, "conversation": {"situation": str, "opening": str},
    "voice": {"situation": str, "opening": str}, "pronunciation": {"focus_sounds": list, "target_phrases": list},
    "guided": {"steps": list}, "review": {"items": list},
}


def _normal(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


@lru_cache(maxsize=1)
def _english_targets():
    texts = set()
    for band in lesson_bank.ALL_BANDS:
        for value in (lesson_bank.reading_text("en", band), lesson_bank.listening_script("en", band)):
            texts.update(_normal(v) for k, v in value.items() if k in {"title", "text", "transcript"})
        for item in lesson_bank.vocabulary("en", band):
            texts.add(_normal(item["example"]))
        for item in lesson_bank.grammar_examples("en", band):
            texts.add(_normal(item["sentence"]))
    return texts


def has_known_incompatible_english(payload, target_language, native_language):
    """Finite known markers, shared by generation and historical delivery.

    Does not certify arbitrary language/CEFR. Metadata is not learner text.
    English native support remains allowed; primary English clones do not.
    """
    primary = {"title", "logic_title", "text", "transcript", "sentence", "example", "opening", "phrase"}
    support = {"explanation", "explanation_native", "logic", "hint", "feedback", "instruction",
               "subtitle", "logic_title_native", "title_native", "objective", "prompt", "patterns", "options", "answer"}
    english = _english_targets()
    old_prefixes = ("we use the ", "use the present ", "the present simple ", "the past simple ")
    incident_markers = ("logical structure for opinion & justification in french",
                        "logic: in french", "we create a chain", "connectors have fixed roles")

    def incompatible(value, field=None):
        if isinstance(value, Mapping):
            return any(incompatible(item, key) for key, item in value.items())
        if isinstance(value, list):
            return any(incompatible(item, field) for item in value)
        if not isinstance(value, str) or field not in primary | support:
            return False
        normalized = _normal(value)
        known_incident = any(marker in normalized for marker in incident_markers)
        if field in primary and target_language != "en" and (normalized in english or known_incident):
            return True
        return "en" not in {target_language, native_language} and (
            normalized in english or normalized.startswith(old_prefixes) or known_incident
        )

    return incompatible(payload)


def valid_generated_lesson(payload, mode: str, language_code: str, native_language: str | None = None) -> bool:
    if not isinstance(payload, dict) or not isinstance(payload.get("title"), str) or not payload["title"].strip():
        return False
    if language_code not in lesson_bank.SUPPORTED_LANGUAGES or mode not in _FIELDS:
        return False
    if payload.get("language_code", language_code) != language_code:
        return False
    if payload.get("target_language", language_code) != language_code:
        return False
    if native_language is not None and "native_language" in payload and payload["native_language"] != native_language:
        return False
    if "level" in payload and payload["level"] not in LEVEL_ORDER:
        return False
    for key, kind in _FIELDS[mode].items():
        if not isinstance(payload.get(key), kind) or (kind is str and not payload[key].strip()):
            return False
    for key in ("questions", "exercises"):
        if key in payload:
            if not isinstance(payload[key], list) or not all(
                isinstance(item, dict) and isinstance(item.get("prompt"), str)
                and isinstance(item.get("options"), list) and isinstance(item.get("answer"), str)
                for item in payload[key]
            ):
                return False
    if has_known_incompatible_english(payload, language_code, native_language):
        return False

    def valid(value):
        if isinstance(value, list):
            return all(valid(item) for item in value)
        if not isinstance(value, dict):
            return True
        options = value.get("options")
        if options is not None:
            if not isinstance(options, list) or not all(isinstance(o, str) for o in options):
                return False
            if len(set(map(_normal, options))) != len(options) or options.count(value.get("answer")) != 1:
                return False
        for key, item in value.items():
            if not valid(item):
                return False
        return True
    return valid(payload)
