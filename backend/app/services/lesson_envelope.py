"""Contrato comum de LessonPayload — independente da origem do conteúdo.

Toda lição (curated_library, mock, OpenRouter) passa por `apply_lesson_envelope`
para expor os mesmos metadados de nível, origem e continuidade pedagógica.

Conteúdo curado **não** finge personalização por IA: `provider` /
`content_origin` ficam explícitos; campos de fio (`thread`, `apply_to_terms`,
`target_expressions`) refletem o carryover real do dia quando existir.
"""

from __future__ import annotations

from typing import Any

from app.core.levels import SKILL_LABELS
from app.prompts.library import MODE_SKILL
from app.services.learner_context import LearnerContext


def apply_lesson_envelope(
    payload: dict[str, Any],
    *,
    context: LearnerContext,
    mode: str,
    provider: str,
    content_origin: str | None = None,
    model: str | None = None,
    thread_guaranteed: bool | None = None,
) -> dict[str, Any]:
    """Normaliza metadados e overlays de continuidade sem reescrever o corpo curado."""
    skill = MODE_SKILL.get(mode)
    origin = content_origin or provider
    guaranteed = thread_guaranteed if thread_guaranteed is not None else provider == "mock"

    carried_terms = list(context.carryover_terms or [])
    base = {
        **payload,
        "mode": mode,
        "provider": provider,
        "model": model,
        "content_origin": origin,
        "language_code": context.language_code,
        "level": context.level_for_skill(skill) if skill else context.level,
        "overall_level": context.level,
        "skill": skill,
        "skill_label": SKILL_LABELS.get(skill) if skill else None,
        "level_source": context.level_source,
        "level_is_estimated": context.level_is_estimated,
        "thread": {
            "carried_terms": carried_terms,
            "carried_patterns": list(context.carryover_patterns or []),
            "sources": list(context.carryover_sources or []),
            "recycled_terms": list(context.recycled_terms or []),
            "guaranteed": guaranteed,
        },
    }

    # Continuidade pedagógica: o léxico do dia orienta prática/produção mesmo
    # quando o texto base veio da biblioteca curada (sem reescrever o conteúdo).
    if carried_terms:
        if mode == "grammar":
            base["apply_to_terms"] = carried_terms[:4]
        if mode in {"conversation", "voice"}:
            base["target_expressions"] = carried_terms[:4]
            if not base.get("thread_note"):
                base["thread_note"] = (
                    "As expressões-alvo são as do vocabulário já praticado hoje "
                    "(continuidade do path — origem do texto pode ser curada)."
                )
        if mode == "grammar" and not base.get("thread_note"):
            base["thread_note"] = (
                "Aplique os padrões às palavras do bloco de vocabulário de hoje."
            )

    # Contratos semânticos quando o campo não se aplica
    if "apply_to_terms" not in base and mode == "grammar":
        base["apply_to_terms"] = []
    if "target_expressions" not in base and mode in {"conversation", "voice"}:
        base["target_expressions"] = list(payload.get("target_expressions") or [])

    return base
