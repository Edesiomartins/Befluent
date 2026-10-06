"""Small deterministic guard; does not certify language or CEFR correctness."""
from __future__ import annotations
import unicodedata
from functools import lru_cache
from app.core.levels import LEVEL_ORDER
from app.services import lesson_bank

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


def valid_generated_lesson(payload, mode: str, language_code: str, native_language: str | None = None) -> bool:
    if not isinstance(payload, dict) or not isinstance(payload.get("title"), str) or not payload["title"].strip():
        return False
    if language_code not in lesson_bank.SUPPORTED_LANGUAGES or mode not in _FIELDS:
        return False
    if payload.get("language_code", language_code) != language_code:
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
    english = _english_targets() if language_code != "en" else set()

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
            if key in {"explanation", "explanation_native", "logic", "hint", "feedback", "instruction", "subtitle", "logic_title_native"} and isinstance(item, str) and "en" not in {language_code, native_language}:
                normalized = _normal(item)
                if normalized in _english_targets() or normalized.startswith(("we use the ", "use the present ", "the present simple ", "the past simple ")):
                    return False
            # Only target fields; Portuguese scaffolding/translation is allowed.
            if key in {"title", "text", "transcript", "sentence", "example", "opening", "phrase"} and isinstance(item, str) and _normal(item) in english:
                return False
            if not valid(item):
                return False
        return True
    return valid(payload)
