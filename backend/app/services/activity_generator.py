"""Gera atividades a partir dos dados declarativos de um LearningObjective.

Sem IA: regras determinísticas. Português é scaffolding; a progressão tende a
menos tradução e mais produção/contexto.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.teaching import ActivityType
from app.models import LearningObjective


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
        activities.append(
            {
                "type": ActivityType.MULTIPLE_CHOICE,
                "phase_hint": "practicing",
                "prompt_pt": "Qual frase significa que você mora em Goiânia?",
                "prompt": "Which sentence means you live in Goiânia?",
                "options": [canonical, *distractors][:4],
                "canonical_answer": canonical,
                "accepted_variants": accepted,
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
