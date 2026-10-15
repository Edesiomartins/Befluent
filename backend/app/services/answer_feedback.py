"""Feedback pedagógico pós-tentativa — sem inventar justificativa falsa.

Usado pelo Teaching Engine e, no frontend de lições, espelhado com os campos
já existentes (`rationale` / `option_rationales`).
"""

from __future__ import annotations

from typing import Any


def _option_entries(activity: dict[str, Any]) -> list[dict[str, str]]:
    """Normaliza `options` (str ou {id,text,rationale}) para entradas tipadas."""
    raw = activity.get("options") or []
    out: list[dict[str, str]] = []
    for index, item in enumerate(raw):
        if isinstance(item, str):
            out.append({"id": chr(ord("A") + index), "text": item, "rationale": ""})
        elif isinstance(item, dict) and item.get("text"):
            out.append(
                {
                    "id": str(item.get("id") or chr(ord("A") + index)),
                    "text": str(item["text"]),
                    "rationale": str(item.get("rationale") or ""),
                }
            )
    return out


def _option_rationales_map(activity: dict[str, Any]) -> dict[str, str]:
    """Mapa texto→rationale a partir de options tipadas ou `option_rationales`."""
    mapping: dict[str, str] = {}
    explicit = activity.get("option_rationales") or {}
    if isinstance(explicit, dict):
        for key, value in explicit.items():
            if value:
                mapping[str(key)] = str(value)
    for entry in _option_entries(activity):
        if entry["rationale"]:
            mapping[entry["text"]] = entry["rationale"]
    return mapping


def build_answer_feedback(
    *,
    activity: dict[str, Any],
    student_response: str,
    is_correct: bool,
) -> dict[str, Any]:
    """Monta feedback estruturado para a UI.

    Quando não há rationale do distractor, usa explicação segura baseada na
    regra da atividade (`correct_explanation` / `rationale` / contraste) —
    nunca inventa um motivo específico falso para a opção errada.
    """
    correct = str(
        activity.get("canonical_answer")
        or activity.get("answer")
        or ((activity.get("accepted_variants") or [None])[0] or "")
    )
    correct_explanation = str(
        activity.get("correct_explanation")
        or activity.get("rationale")
        or ""
    ).strip()
    if not correct_explanation and correct:
        correct_explanation = (
            f"A forma adequada nesta atividade é «{correct}», "
            "conforme o padrão trabalhado."
        )

    rationales = _option_rationales_map(activity)
    selected = student_response.strip()
    selected_rationale = rationales.get(selected, "").strip()

    if is_correct:
        return {
            "is_correct": True,
            "selected": selected,
            "correct_option": correct,
            "selected_label": selected,
            "correct_label": correct,
            "why_selected": None,
            "why_correct": correct_explanation,
            "remember": activity.get("remember_pt")
            or activity.get("scaffold_pt")
            or None,
        }

    if selected_rationale:
        why_selected = selected_rationale
    else:
        why_selected = (
            "Esta opção não aplica a regra desta atividade. "
            + (correct_explanation if correct_explanation else "")
        ).strip()

    return {
        "is_correct": False,
        "selected": selected,
        "correct_option": correct,
        "selected_label": selected,
        "correct_label": correct,
        "why_selected": why_selected,
        "why_correct": correct_explanation,
        "remember": activity.get("remember_pt")
        or activity.get("scaffold_pt")
        or None,
    }


def option_texts(activity: dict[str, Any]) -> list[str]:
    return [entry["text"] for entry in _option_entries(activity)]


def build_retry_variant(
    activity: dict[str, Any],
    patterns: list[dict] | None = None,
    *,
    seen_fingerprints: frozenset[str] | set[str] | None = None,
) -> dict[str, Any]:
    """Repete a mesma atividade depois do erro.

    O enunciado e a resposta não mudam. As alternativas podem ser
    reordenadas. `post_reveal=True` impede evidência forte de 1ª tentativa.
    `patterns` e `seen_fingerprints` permanecem na assinatura para os
    chamadores atuais; não escolhem outro objetivo.
    """
    del patterns, seen_fingerprints
    variant = dict(activity)
    options = activity.get("options")
    if isinstance(options, list) and len(options) > 1:
        variant["options"] = [*options[1:], options[0]]
    variant["post_reveal"] = True
    variant["is_retry_variant"] = True
    variant["retry_safe"] = True
    variant["retry_strategy"] = "same_activity"
    return variant
