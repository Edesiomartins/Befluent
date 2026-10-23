"""Banco curado endereçado por metadados.

Um idioma novo entra como mais um pacote nesta lista. O seletor não
conhece o idioma: filtra alvo, nativo e CEFR.
"""

from __future__ import annotations

from collections.abc import Callable

from app.services.fr_b1_slice import activities as french_b1_activities
from app.services.learner_language_contract import interaction_family

_PACKS: tuple[dict, ...] = (
    {
        "learning_objective_id": "curated:fr:B1:pt-BR",
        "target_language": "fr",
        "native_language": "pt-BR",
        "cefr_level": "B1",
        "activities": french_b1_activities,
    },
)


def candidates_for(
    *,
    target_language: str | None,
    native_language: str | None,
    cefr_level: str | None,
) -> list[dict]:
    selected: list[dict] = []
    for pack in _PACKS:
        if (
            pack["target_language"] != target_language
            or pack["native_language"] != native_language
            or pack["cefr_level"] != cefr_level
        ):
            continue
        loader: Callable[[], list[dict]] = pack["activities"]
        for activity in loader():
            item = dict(activity)
            item["learning_objective_id"] = pack["learning_objective_id"]
            item["target_language"] = pack["target_language"]
            item["native_language"] = pack["native_language"]
            item["cefr_level"] = pack["cefr_level"]
            item["quality_status"] = item.get("quality_status") or "approved"
            item["interaction_family"] = item.get("interaction_family") or interaction_family(item.get("type"))
            selected.append(item)
    return selected
