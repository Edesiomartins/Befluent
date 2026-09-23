"""Gera atividades a partir dos dados declarativos de um LearningObjective.

Sem IA: regras determinísticas. Português é scaffolding; a progressão tende a
menos tradução e mais produção/contexto.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from app.core.teaching import ActivityType, EvidenceType
from app.models import (
    LearningObjective,
    MemorySchedule,
    VocabularyExample,
    VocabularyItem,
)


def _patterns(objective: LearningObjective) -> list[dict[str, Any]]:
    raw = objective.target_patterns_json or []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str):
            out.append({"canonical": item, "accepted": [item]})
        elif isinstance(item, dict) and item.get("canonical"):
            accepted = list(item.get("accepted") or [])
            if item["canonical"] not in accepted:
                accepted.insert(0, item["canonical"])
            out.append({**item, "accepted": accepted})
    return out


def _expressions(objective: LearningObjective) -> list[str]:
    exprs = list(objective.target_expressions_json or [])
    if exprs:
        return [str(e) for e in exprs]
    return [p["canonical"] for p in _patterns(objective)]


def _vocabulary(objective: LearningObjective) -> list[str]:
    return [str(v) for v in (objective.target_vocabulary_json or [])]


def _pedagogy(objective: LearningObjective) -> dict:
    return dict(objective.pedagogy_json or {})


def _gap_prompt(canonical: str) -> tuple[str, str]:
    """Remove a última palavra de conteúdo para fill-gap simples."""
    tokens = canonical.split()
    if len(tokens) < 2:
        return f"{canonical} ___", canonical
    answer = tokens[-1].rstrip(".,!?")
    stem = " ".join(tokens[:-1]) + " ___."
    return stem, answer


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _deterministic_options(
    values: Sequence[str], *, correct: str, item_index: int
) -> list[str]:
    """Ordena alternativas sem aleatoriedade e sem criar conteúdo externo."""
    unique = list(dict.fromkeys(str(value) for value in values if value))
    if correct not in unique:
        unique.insert(0, correct)
    if len(unique) <= 1:
        return unique
    others = [value for value in unique if value != correct]
    position = item_index % len(unique)
    return others[:position] + [correct] + others[position:]


def generate_vocabulary_activities(
    items: Sequence[VocabularyItem],
    *,
    examples_by_item: Mapping[str, Sequence[VocabularyExample]] | None = None,
    memory_by_item: Mapping[str, MemorySchedule] | None = None,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Gera um ciclo lexical por conjunto, intercalado por modalidade.

    Itens dominados e ainda não vencidos ficam fora desta sessão. Conteúdo
    incompleto reduz as opções disponíveis; nenhum distrator ou exemplo é
    inventado.
    """
    current_time = _aware(now or datetime.now(timezone.utc))
    examples_by_item = examples_by_item or {}
    memory_by_item = memory_by_item or {}
    selected: list[VocabularyItem] = []
    for item in items:
        schedule = memory_by_item.get(item.id)
        if (
            schedule is not None
            and schedule.state == "mastered"
            and _aware(schedule.due_at) > current_time
        ):
            continue
        selected.append(item)

    meanings = [item.translation_pt for item in selected]
    terms = [item.term for item in selected]
    stages: list[list[dict[str, Any]]] = [[], [], [], [], []]

    for item_index, item in enumerate(selected):
        examples = list(examples_by_item.get(item.id) or ())
        example = examples[0] if examples else None
        audio_targets = [
            {
                "audio_target_type": "vocabulary_item",
                "audio_text": item.term,
            }
        ]
        presentation: dict[str, Any] = {
            "type": ActivityType.PRESENTATION,
            "vocabulary_item_id": item.id,
            "phase_hint": "input",
            "evidence_type": EvidenceType.EXPOSURE,
            "prompt_pt": "Conheça este item de vocabulário.",
            "term": item.term,
            "translation_pt": item.translation_pt,
            "audio_targets": audio_targets,
            "ai_required": False,
        }
        if item.reading_or_pinyin:
            presentation["reading_or_pinyin"] = item.reading_or_pinyin
        if example is not None:
            presentation["example_sentence"] = example.example_text
            presentation["example_translation_pt"] = example.translation_pt
            audio_targets.append(
                {
                    "audio_target_type": "example_sentence",
                    "audio_text": example.example_text,
                }
            )
        stages[0].append(presentation)

        meaning_options = _deterministic_options(
            meanings, correct=item.translation_pt, item_index=item_index
        )
        term_options = _deterministic_options(
            terms, correct=item.term, item_index=item_index
        )
        stages[1].append(
            {
                "type": ActivityType.RECOGNITION,
                "vocabulary_item_id": item.id,
                "phase_hint": "practicing",
                "evidence_type": EvidenceType.RECOGNITION,
                "prompt_pt": "Escolha o significado do termo.",
                "prompt": item.term,
                "show_text": True,
                "options": meaning_options,
                "canonical_answer": item.translation_pt,
                "accepted_variants": [item.translation_pt],
                "audio_targets": [],
                "ai_required": False,
            }
        )
        stages[2].append(
            {
                "type": ActivityType.REVERSE_RECOGNITION,
                "vocabulary_item_id": item.id,
                "phase_hint": "practicing",
                "evidence_type": EvidenceType.REVERSE_RECOGNITION,
                "prompt_pt": "Escolha o termo correspondente ao significado.",
                "prompt": item.translation_pt,
                "show_text": True,
                "options": term_options,
                "canonical_answer": item.term,
                "accepted_variants": [item.term],
                "audio_targets": [],
                "ai_required": False,
            }
        )
        stages[3].append(
            {
                "type": ActivityType.LISTENING_RECOGNITION,
                "vocabulary_item_id": item.id,
                "phase_hint": "practicing",
                "evidence_type": EvidenceType.LISTENING_RECOGNITION,
                "prompt_pt": "Ouça e escolha o significado.",
                "show_text": False,
                "options": meaning_options,
                "canonical_answer": item.translation_pt,
                "accepted_variants": [item.translation_pt],
                "audio_target_type": "vocabulary_item",
                "audio_text": item.term,
                "audio_targets": [
                    {
                        "audio_target_type": "vocabulary_item",
                        "audio_text": item.term,
                    }
                ],
                "ai_required": False,
            }
        )
        stages[4].append(
            {
                "type": ActivityType.LEXICAL_PRODUCTION,
                "vocabulary_item_id": item.id,
                "phase_hint": "producing",
                "evidence_type": EvidenceType.LEXICAL_PRODUCTION,
                "prompt_pt": "Recupere o termo a partir do significado.",
                "prompt": item.translation_pt,
                "canonical_answer": item.term,
                "accepted_variants": [item.term],
                "response_modes": ["typing", "speech"],
                "audio_targets": [],
                "ai_required": False,
            }
        )

    activities = [activity for stage in stages for activity in stage]
    for index, activity in enumerate(activities):
        activity["index"] = index
    return activities


def generate_activities(objective: LearningObjective) -> list[dict[str, Any]]:
    """Sequência pedagógica mínima para o vertical slice / qualquer objective."""
    patterns = _patterns(objective)
    expressions = _expressions(objective)
    vocab = _vocabulary(objective)
    pedagogy = _pedagogy(objective)
    activation = pedagogy.get("activation") or {
        "title_pt": objective.title,
        "can_do": objective.can_do,
        "support_pt": "Você vai aprender a se apresentar com frases simples.",
    }
    noticing = pedagogy.get("noticing") or {
        "prompt_pt": "Observe como essas frases se estruturam.",
        "examples": expressions[:4] or [p["canonical"] for p in patterns[:4]],
    }
    transfer_prompts = list(pedagogy.get("transfer_prompts") or [])
    if not transfer_prompts and patterns:
        transfer_prompts = [
            {
                "prompt": "Where does your brother live?",
                "prompt_pt": "Onde mora o seu irmão?",
                "expected_features": ["live", "in"],
                "scaffold_pt": "Use: He lives in…",
            }
        ]

    activities: list[dict[str, Any]] = [
        {
            "type": ActivityType.RECOGNITION,
            "phase_hint": "activating",
            "prompt_pt": activation.get("support_pt") or activation.get("can_do"),
            "title_pt": activation.get("title_pt") or objective.title,
            "can_do": objective.can_do,
            "ai_required": False,
        },
        {
            "type": ActivityType.LISTEN,
            "phase_hint": "input",
            "prompt_pt": "Ouça e leia os modelos. Não responda ainda.",
            "models": expressions[:5] or [p["canonical"] for p in patterns[:5]],
            "show_text": True,
            "ai_required": False,
        },
        {
            "type": ActivityType.RECOGNITION,
            "phase_hint": "noticing",
            "prompt_pt": noticing.get("prompt_pt"),
            "examples": noticing.get("examples") or expressions[:4],
            "ai_required": False,
        },
    ]

    if patterns:
        canonical = patterns[0]["canonical"]
        accepted = patterns[0].get("accepted") or [canonical]
        stem, gap_answer = _gap_prompt(canonical)
        activities.append(
            {
                "type": ActivityType.FILL_GAP,
                "phase_hint": "practicing",
                "prompt": stem,
                "prompt_pt": "Complete a frase.",
                "canonical_answer": gap_answer,
                "accepted_variants": [gap_answer, gap_answer.lower()],
                "ai_required": False,
            }
        )
        tokens = re.findall(r"[A-Za-z']+", canonical)
        if len(tokens) >= 3:
            activities.append(
                {
                    "type": ActivityType.WORD_ORDER,
                    "phase_hint": "practicing",
                    "prompt_pt": "Ordene as palavras para formar a frase.",
                    "tokens": tokens,
                    "canonical_answer": canonical,
                    "accepted_variants": accepted,
                    "ai_required": False,
                }
            )
        distractors = [p["canonical"] for p in patterns[1:3]] or [
            "I am a student.",
            "I like coffee.",
        ]
        option_entries = [
            {
                "id": "A",
                "text": canonical,
                "rationale": f"Esta forma expressa o padrão alvo: «{canonical}».",
            }
        ]
        for offset, distractor in enumerate(distractors[:3]):
            option_entries.append(
                {
                    "id": chr(ord("B") + offset),
                    "text": distractor,
                    "rationale": (
                        f"«{distractor}» é gramatical em outros contextos, "
                        "mas não corresponde ao padrão pedido nesta atividade."
                    ),
                }
            )
        activities.append(
            {
                "type": ActivityType.MULTIPLE_CHOICE,
                "phase_hint": "practicing",
                "prompt_pt": "Qual frase corresponde ao padrão trabalhado?",
                "prompt": "Which sentence matches the target pattern?",
                "options": option_entries,
                "canonical_answer": canonical,
                "accepted_variants": accepted,
                "correct_explanation": (
                    f"A resposta adequada é «{canonical}», que realiza o padrão "
                    "desta atividade."
                ),
                "remember_pt": "Compare a estrutura da opção com o modelo do noticing.",
                "ai_required": False,
            }
        )

    if vocab:
        activities.append(
            {
                "type": ActivityType.MATCHING,
                "phase_hint": "practicing",
                "prompt_pt": "Associe a palavra ao uso na apresentação.",
                "pairs": [
                    {"term": v, "hint_pt": f"Usar em apresentação: {v}"} for v in vocab[:4]
                ],
                "ai_required": False,
            }
        )

    guided = pedagogy.get("guided_prompt") or {
        "prompt": "Tell me about yourself.",
        "prompt_pt": "Apresente-se em 2–4 frases simples.",
        "scaffold_pt": "My name is… I'm from… I live in… I work as… I like…",
        "required_features": ["name", "from", "live", "like"],
    }
    activities.append(
        {
            "type": ActivityType.GUIDED_PRODUCTION,
            "phase_hint": "producing",
            "prompt": guided.get("prompt"),
            "prompt_pt": guided.get("prompt_pt"),
            "scaffold_pt": guided.get("scaffold_pt"),
            "required_features": guided.get("required_features") or [],
            "required_patterns": guided.get("required_patterns") or [],
            "accepted_variants": [],
            "evaluation_mode": guided.get("evaluation_mode") or "guided",
            "minimum_structure": guided.get("minimum_structure") or "clause",
            "ai_required": False,
        }
    )

    for transfer in transfer_prompts[:1]:
        activities.append(
            {
                "type": ActivityType.TRANSFER_QUESTION,
                "phase_hint": "transfer_check",
                "prompt": transfer.get("prompt"),
                "prompt_pt": transfer.get("prompt_pt"),
                "scaffold_pt": transfer.get("scaffold_pt"),
                "required_features": transfer.get("expected_features") or [],
                "required_patterns": transfer.get("required_patterns") or [],
                "accepted_variants": transfer.get("accepted_variants") or [],
                "evaluation_mode": transfer.get("evaluation_mode") or "transfer",
                "minimum_structure": transfer.get("minimum_structure") or "clause",
                "ai_required": False,
            }
        )

    # Index estável para o frontend
    for index, activity in enumerate(activities):
        activity["index"] = index
    return activities


def activity_requires_ai(activity: dict) -> bool:
    return bool(activity.get("ai_required"))
