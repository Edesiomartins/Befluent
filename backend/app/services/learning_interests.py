"""Interesses do aluno mudam o contexto, não o curso nem o domínio.

Os objetivos já gravados em `LearningGoal` (onboarding) viram chaves de
contexto. Sem interesse, sem variante ou com conteúdo legado, a frase geral
do nível permanece. O termo e a tradução não saem da seleção.
"""

from __future__ import annotations

from app.models import LearningGoal

#: Trechos dos objetivos atuais do onboarding. A correspondência é por
#: conteúdo, não por um segundo cadastro.
_GOAL_MARKERS: tuple[tuple[str, str], ...] = (
    ("viaj", "travel"),
    ("trabalho", "work"),
    ("carreira", "work"),
    ("estudo", "study"),
    ("prova", "study"),
    ("cultura", "culture"),
    ("convers", "general"),
)

#: Variantes de frase para termos que já existem no banco geral.
#: A ausência de uma chave cai no exemplo original.
EXAMPLE_VARIANTS: dict[str, dict[str, dict[str, tuple[str, str]]]] = {
    "en": {
        "how much": {
            "travel": (
                "How much is the train ticket?",
                "Quanto custa a passagem de trem?",
            ),
            "work": (
                "How much is the project budget?",
                "Quanto é o orçamento do projeto?",
            ),
            "study": (
                "How much time does this assignment take?",
                "Quanto tempo esta tarefa leva?",
            ),
        },
        "water": {
            "travel": (
                "Can I have some water on the train, please?",
                "Pode me trazer água no trem, por favor?",
            ),
            "work": (
                "Could I have some water before the meeting?",
                "Pode me trazer água antes da reunião?",
            ),
        },
    },
    "de": {
        "können": {
            "travel": (
                "Kann ich hier mit Karte bezahlen?",
                "Posso pagar com cartão aqui?",
            ),
            "work": (
                "Kann ich morgen von zu Hause arbeiten?",
                "Posso trabalhar de casa amanhã?",
            ),
            "study": (
                "Kann ich diese Aufgabe später abgeben?",
                "Posso entregar esta tarefa depois?",
            ),
        },
    },
}


def context_key_for_goal(text: str) -> str:
    folded = " ".join((text or "").casefold().split())
    for marker, key in _GOAL_MARKERS:
        if marker in folded:
            return key
    return "general"


def context_keys(interests: list[str]) -> list[str]:
    if not interests:
        return ["general"]
    keys: list[str] = []
    for interest in interests:
        key = context_key_for_goal(interest)
        if key not in keys:
            keys.append(key)
    return keys or ["general"]


def load_personal_interests(db, user_language_id: str) -> list[str]:
    from sqlalchemy import select

    return list(
        db.scalars(
            select(LearningGoal.description)
            .where(
                LearningGoal.user_language_id == user_language_id,
                LearningGoal.goal_type == "personal",
                LearningGoal.status == "active",
            )
            .order_by(LearningGoal.priority, LearningGoal.id)
        )
    )


def apply_interest_context(
    items: list[dict],
    *,
    language_code: str,
    interests: list[str] | None,
) -> list[dict]:
    """Devolve os mesmos itens, com exemplo contextual só quando ele existe."""
    keys = [key for key in context_keys(list(interests or [])) if key != "general"]
    language_variants = EXAMPLE_VARIANTS.get(language_code, {})
    personalized: list[dict] = []
    for item in items:
        copy = dict(item)
        term = str(copy.get("term") or "").casefold()
        variants = language_variants.get(term, {})
        applied = None
        for key in keys:
            variant = variants.get(key)
            if variant is None:
                continue
            example, translation = variant
            copy["example"] = example
            copy["example_translation"] = translation
            copy["learning_context"] = key
            applied = key
            break
        if applied is None:
            copy["learning_context"] = "general"
        personalized.append(copy)
    return personalized


def personalize_conversation_item(
    items: list[dict],
    *,
    language_code: str,
    interests: list[str] | None,
    recent_terms: list[str] | None,
    turn: int,
) -> dict | None:
    """Escolhe um item real do nível. Interesse e vocabulário recente só reordenam."""
    contextual = apply_interest_context(
        items, language_code=language_code, interests=interests
    )
    if not contextual:
        return None
    recent = {term.casefold() for term in (recent_terms or []) if term}
    preferred = [
        item
        for item in contextual
        if str(item.get("term") or "").casefold() in recent
    ]
    pool = preferred or contextual
    return pool[turn % len(pool)]
