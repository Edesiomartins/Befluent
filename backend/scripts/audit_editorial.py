"""Read-only, reproducible editorial inventory. No provider or DB writes."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3
import sys
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services import lesson_bank as bank
from app.services.content_seed import STARTER_LEVELS, STARTER_MODES, _payload_for
from app.services.seed import LANGUAGES
from app.services.ai import MockAIProvider
from app.services.learner_context import LearnerContext
from app.core.levels import LEVEL_DETAILS, LEVEL_ORDER
from app.services.curriculum_bank import themes_for
from app.services.placement_seed import load_fixture
from app.models import VocabularyItem, VocabularyExample
from app.services.activity_generator import generate_vocabulary_activities
from app.core.config import get_settings


def strings(value, path=""):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from strings(item, f"{path}.{key}".strip("."))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from strings(item, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def normalized(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def option_issues(value, path=""):
    found = []
    if isinstance(value, dict):
        options = value.get("options")
        if isinstance(options, list) and all(isinstance(o, str) for o in options):
            if len(set(map(normalized, options))) != len(options):
                found.append({"path": path, "issue": "duplicate_options"})
            answer = value.get("answer", value.get("canonical_answer"))
            if answer is not None and options.count(answer) != 1:
                found.append({"path": path, "issue": "answer_not_exactly_once"})
        for key, item in value.items():
            found += option_issues(item, f"{path}.{key}".strip("."))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found += option_issues(item, f"{path}[{index}]")
    return found


def inventory():
    result = {"catalogue": [row[0] for row in LANGUAGES], "languages": {}, "option_issues": [], "english_exact_matches": [], "placement_issues": []}
    english = dict(strings({name: getattr(bank, name)["en"] for name in (
        "VOCABULARY", "READING_TEXTS", "LISTENING_SCRIPTS", "GRAMMAR_EXAMPLES", "GRAMMAR_EXERCISES"
    )}))
    target_fields = {"term", "example", "text", "transcript", "sentence", "prompt", "answer", "title"}
    for code, name, native, *_ in LANGUAGES:
        counts = Counter()
        contents = []
        for band in bank.ALL_BANDS:
            for category, accessor in bank.SKILL_ACCESSORS.items():
                value = accessor(code, band)
                counts[category] += len(value) if isinstance(value, list) else 1
                contents.append((f"bank.{category}.{band}", value))
            counts["grammar_focus"] += 1
            contents.append((f"bank.grammar_focus.{band}", bank.grammar_focus(code, band)))
            counts["pronunciation_sounds"] = len(bank.pronunciation_focus(code))
            raw_items = bank.vocabulary(code, band)
            items = [VocabularyItem(id=f"{code}-{band}-{i}", term=raw["term"], translation_pt=raw["translation"]) for i, raw in enumerate(raw_items)]
            examples = {item.id:[VocabularyExample(example_text=raw["example"], translation_pt=raw["example_translation"])] for item, raw in zip(items, raw_items)}
            activities = generate_vocabulary_activities(items, examples_by_item=examples)
            counts["lexical_activities"] += len(activities)
            contents.append((f"lexical.{band}", activities))
        for level in LEVEL_ORDER:
            counts["curriculum_theme_entries"] += len(themes_for(code, level))
            context = LearnerContext(code, name, native, level, LEVEL_DETAILS[level]["name_pt"],
                                     LEVEL_DETAILS[level]["short_description"], "self_reported", False, native_language="pt-BR")
            for mode in ("vocabulary", "grammar", "reading", "listening", "writing", "conversation", "voice", "pronunciation", "guided", "review"):
                contents.append((f"mock.{level}.{mode}", MockAIProvider().generate_lesson(mode, context)))
                counts["mock_payloads"] += 1
        for band, level in STARTER_LEVELS:
            for mode, _ in STARTER_MODES:
                contents.append((f"starter.{level}.{mode}", _payload_for(mode, code, band, level)))
                counts["starter_payloads"] += 1
        counts["string_fields_scanned"] = sum(len(list(strings(value))) for _, value in contents)
        counts["distinct_reading_texts"] = len({bank.reading_text(code, bank.band_for(level))["text"] for level in LEVEL_ORDER})
        counts["distinct_listening_scripts"] = len({bank.listening_script(code, bank.band_for(level))["transcript"] for level in LEVEL_ORDER})
        fixture = load_fixture(code)
        counts["placement_items"] = len(fixture["items"])
        counts["placement_levels"] = dict(Counter(item["cefr_level"] for item in fixture["items"]))
        for item in fixture["items"]:
            adapted = {**item, "answer": item.get("correct_answer", {}).get("value")}
            for issue in option_issues(adapted):
                result["placement_issues"].append({"language": code, "key": item.get("external_key"), **issue})
            if item.get("cefr_level") not in LEVEL_ORDER or fixture.get("language_code") != code:
                result["placement_issues"].append({"language":code, "key": item.get("external_key"), "issue":"invalid_metadata"})
        for origin, value in contents:
            for issue in option_issues(value):
                result["option_issues"].append({"language": code, "origin": origin, **issue})
        if code != "en":
            for table in ("VOCABULARY", "READING_TEXTS", "LISTENING_SCRIPTS", "GRAMMAR_EXAMPLES", "GRAMMAR_EXERCISES"):
                for path, value in strings(getattr(bank, table)[code]):
                    if path.rsplit(".", 1)[-1] in target_fields and english.get(f"{table}.{path}") == value:
                        result["english_exact_matches"].append({"language": code, "field": f"{table}.{path}", "value": value})
        result["languages"][code] = dict(counts)
    return result


def local_database(path):
    if not path.is_file():
        return {"available": False}
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        out = {"available": True, "scope": "local SQLite only", "tables": sorted(tables)}
        if "languages" in tables:
            out["languages"] = [dict(zip(("code", "active"), row)) for row in db.execute("SELECT code, is_active FROM languages ORDER BY code")]
        if "content_units" in tables:
            out["content_counts"] = [dict(zip(("language", "mode", "level", "count"), row)) for row in db.execute("SELECT l.code,u.mode,u.cefr_level,count(*) FROM content_units u JOIN languages l ON l.id=u.language_id GROUP BY l.code,u.mode,u.cefr_level")]
            out["internal_titles"] = db.execute("SELECT count(*) FROM content_units WHERE title LIKE '[starter] %'").fetchone()[0]
        return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inventory()
    settings = get_settings()
    result["local_settings"] = {"environment": settings.environment, "database_dialect":settings.database_url.split(":",1)[0], "ai_mock_mode":settings.ai_mock_mode, "tts_provider":settings.tts_provider,"stt_provider":settings.stt_provider}
    result["database"] = local_database(Path(__file__).resolve().parents[1] / "befluent.db")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
