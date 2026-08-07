"""Seed da biblioteca pedagógica inicial (unidades aprovadas para o path).

O cronograma já prioriza `fetch_approved_unit`. Sem unidades aprovadas, os
blocos caem em IA/mock. Este seed materializa o `lesson_bank` como ContentUnit
aprovado — conteúdo de desenvolvimento, não validação pedagógica definitiva.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.content_policy import OriginType, UsagePolicy, ValidationStatus
from app.core.levels import CEFRLevel, Skill
from app.models import ContentSource, ContentUnit, Language
from app.services import lesson_bank

#: Modos do path diário (sem guided/review — review usa a fila SRS).
STARTER_MODES: tuple[tuple[str, str], ...] = (
    ("vocabulary", Skill.VOCABULARY_GRAMMAR),
    ("grammar", Skill.VOCABULARY_GRAMMAR),
    ("reading", Skill.READING),
    ("listening", Skill.LISTENING),
    ("writing", Skill.WRITING),
    ("conversation", Skill.SPEAKING),
    ("pronunciation", Skill.SPEAKING),
)

#: Faixa do lesson_bank → nível CEFR gravado na unidade.
STARTER_LEVELS: tuple[tuple[str, str], ...] = (
    (lesson_bank.BAND_BEGINNER, CEFRLevel.A1),
    (lesson_bank.BAND_ELEMENTARY, CEFRLevel.A2),
    (lesson_bank.BAND_INTERMEDIATE, CEFRLevel.B1),
)

SOURCE_TITLE = "BeFluent · biblioteca inicial"


def _payload_for(mode: str, language_code: str, band: str, level: str) -> dict:
    """Monta payload no mesmo formato que o MockAIProvider / study UI espera."""
    if mode == "vocabulary":
        items = lesson_bank.vocabulary(language_code, band)
        return {
            "title": f"Vocabulário essencial · {level}",
            "objective": "Ampliar o vocabulário de alta frequência do seu nível.",
            "items": list(items),
        }
    if mode == "grammar":
        focus = lesson_bank.grammar_focus(language_code, band)
        return {
            "title": f"{focus['title']} · {level}",
            "objective": focus["objective"],
            "explanation": focus["explanation"],
            "patterns": list(focus["patterns"]),
            "examples": lesson_bank.grammar_examples(language_code, band),
            "exercises": lesson_bank.grammar_exercises(language_code, band),
        }
    if mode == "reading":
        text = lesson_bank.reading_text(language_code, band)
        return {
            "title": f"{text['title']} · {level}",
            "objective": "Ler um texto calibrado e verificar a compreensão.",
            "text": text["text"],
            "note": text["note"],
            "glossary": [],
            "questions": [
                {
                    "prompt": "Qual é a ideia principal do texto?",
                    "options": [
                        "Uma descrição de rotina ou situação concreta.",
                        "Uma lista de instruções técnicas.",
                        "Um diálogo entre duas pessoas.",
                    ],
                    "answer": "Uma descrição de rotina ou situação concreta.",
                }
            ],
        }
    if mode == "listening":
        script = lesson_bank.listening_script(language_code, band)
        return {
            "title": f"Compreensão auditiva · {level}",
            "objective": "Treinar escuta ativa com um objetivo definido.",
            "transcript": script["transcript"],
            "speaking_rate": script["speaking_rate"],
            "note": script["note"],
            "questions": [
                {
                    "prompt": "Qual é a informação central do áudio?",
                    "options": [
                        "Uma informação prática sobre uma situação concreta.",
                        "Uma opinião sobre política internacional.",
                        "Uma receita de cozinha.",
                    ],
                    "answer": "Uma informação prática sobre uma situação concreta.",
                }
            ],
        }
    if mode == "writing":
        task = lesson_bank.writing_task(language_code, band)
        return {
            "title": f"Produção escrita · {level}",
            "objective": "Produzir um texto no seu nível.",
            "prompt": task["prompt"],
            "min_words": task["min_words"],
            "max_words": task["max_words"],
            "rubric_hints": list(task["rubric_hints"]),
            "useful_expressions": [],
        }
    if mode == "conversation":
        situation = lesson_bank.conversation_situation(language_code, band)
        items = lesson_bank.vocabulary(language_code, band)
        return {
            "title": f"Conversação · {level}",
            "objective": f"Praticar {situation['focus']} em uma situação realista.",
            "situation": situation["situation"],
            "opening": items[0]["example"],
            "opening_translation": items[0]["example_translation"],
            "suggested_replies": [item["example"] for item in items[1:4]],
            "target_expressions": [item["term"] for item in items[:4]],
        }
    if mode == "pronunciation":
        sounds = lesson_bank.pronunciation_focus(language_code)
        items = lesson_bank.vocabulary(language_code, band)
        return {
            "title": f"Pronúncia · {level}",
            "objective": "Treinar os sons que mais comprometem a compreensão.",
            "focus_sounds": list(sounds),
            "target_phrases": [
                {
                    "phrase": item["example"],
                    "translation": item["example_translation"],
                    "focus": item["term"],
                }
                for item in items[:4]
            ],
        }
    raise ValueError(mode)


def _ensure_source(db: Session, language: Language) -> ContentSource:
    source = db.scalar(
        select(ContentSource).where(
            ContentSource.language_id == language.id,
            ContentSource.title == SOURCE_TITLE,
        )
    )
    if source is not None:
        source.review_status = ValidationStatus.APPROVED
        source.usage_policy = UsagePolicy.OPEN_LICENSE
        return source
    source = ContentSource(
        title=SOURCE_TITLE,
        language_id=language.id,
        usage_policy=UsagePolicy.OPEN_LICENSE,
        review_status=ValidationStatus.APPROVED,
        allow_excerpt=False,
        allow_concept_extraction=True,
        commercial_use_reviewed=True,
        notes_json={"origin": "lesson_bank_seed", "disclaimer": "dev_starter"},
    )
    db.add(source)
    db.flush()
    return source


def seed_starter_content(
    db: Session,
    *,
    language_codes: set[str] | None = None,
) -> int:
    """Insere/atualiza unidades aprovadas. Retorna quantas unidades tocou."""
    touched = 0
    query = select(Language).where(Language.is_active.is_(True))
    languages = list(db.scalars(query))
    if language_codes is not None:
        languages = [lang for lang in languages if lang.code in language_codes]
    for language in languages:
        source = _ensure_source(db, language)
        for band, cefr in STARTER_LEVELS:
            for mode, skill in STARTER_MODES:
                title_key = f"[starter] {mode} · {cefr}"
                existing = db.scalar(
                    select(ContentUnit).where(
                        ContentUnit.source_id == source.id,
                        ContentUnit.mode == mode,
                        ContentUnit.cefr_level == cefr,
                        ContentUnit.title == title_key,
                    )
                )
                try:
                    payload = _payload_for(mode, language.code, band, cefr)
                except (KeyError, IndexError, TypeError):
                    continue
                if existing is None:
                    existing = ContentUnit(
                        source_id=source.id,
                        language_id=language.id,
                        title=title_key,
                        mode=mode,
                        skill=skill,
                        cefr_level=cefr,
                    )
                    db.add(existing)
                existing.language_id = language.id
                existing.cefr_level = cefr
                existing.skill = skill
                existing.mode = mode
                existing.topic = payload.get("title") or mode
                existing.payload_json = payload
                existing.origin_type = OriginType.ORIGINAL
                existing.attribution_text = "BeFluent · material inicial de desenvolvimento"
                existing.validation_status = ValidationStatus.APPROVED
                existing.is_active = True
                existing.content_type = "lesson_unit"
                touched += 1
        # PRE_A1 reutiliza o pacote beginner (A1) — entry comum do onboarding.
        for mode, skill in STARTER_MODES:
            title_key = f"[starter] {mode} · {CEFRLevel.PRE_A1}"
            donor = db.scalar(
                select(ContentUnit).where(
                    ContentUnit.source_id == source.id,
                    ContentUnit.mode == mode,
                    ContentUnit.cefr_level == CEFRLevel.A1,
                    ContentUnit.title == f"[starter] {mode} · {CEFRLevel.A1}",
                )
            )
            if donor is None:
                continue
            existing = db.scalar(
                select(ContentUnit).where(
                    ContentUnit.source_id == source.id,
                    ContentUnit.mode == mode,
                    ContentUnit.cefr_level == CEFRLevel.PRE_A1,
                    ContentUnit.title == title_key,
                )
            )
            payload = dict(donor.payload_json or {})
            payload["title"] = (payload.get("title") or mode).replace("A1", "PRE_A1")
            if existing is None:
                existing = ContentUnit(
                    source_id=source.id,
                    language_id=language.id,
                    title=title_key,
                    mode=mode,
                    skill=skill,
                    cefr_level=CEFRLevel.PRE_A1,
                )
                db.add(existing)
            existing.payload_json = payload
            existing.topic = payload.get("title") or mode
            existing.origin_type = OriginType.ORIGINAL
            existing.attribution_text = "BeFluent · material inicial de desenvolvimento"
            existing.validation_status = ValidationStatus.APPROVED
            existing.is_active = True
            existing.content_type = "lesson_unit"
            touched += 1
    db.flush()
    return touched
