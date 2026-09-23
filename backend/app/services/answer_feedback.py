"""Feedback pedagógico pós-tentativa — sem inventar justificativa falsa.

Usado pelo Teaching Engine e, no frontend de lições, espelhado com os campos
já existentes (`rationale` / `option_rationales`).
"""

from __future__ import annotations

from typing import Any

from app.services.question_identity import (
    is_same_question,
    normalize_question_text,
    question_fingerprint,
)


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


def _fallback_continue(activity: dict[str, Any], *, message: str | None = None) -> dict[str, Any]:
    """Ack de continuidade — não reabre item já revelado."""
    return {
        "type": "recognition",
        "phase_hint": activity.get("phase_hint") or "practicing",
        "prompt_pt": message
        or (
            "Continue o percurso; este ponto ficará marcado para revisão futura."
        ),
        "title_pt": "Continuar após o feedback",
        "examples": [],
        "ai_required": False,
        "post_reveal": True,
        "is_retry_variant": True,
        "retry_safe": False,
        "retry_strategy": "fallback_continue",
    }


def _mcq_from_pattern(
    activity: dict[str, Any],
    pattern: dict[str, Any],
    patterns: list[dict],
    *,
    strategy: str,
) -> dict[str, Any]:
    canonical = pattern.get("canonical") or activity.get("canonical_answer")
    accepted = list(pattern.get("accepted") or [canonical])
    distractors = [
        p.get("canonical")
        for p in patterns
        if p.get("canonical") and p.get("canonical") != canonical
    ][:3]
    options = [canonical, *[d for d in distractors if d]]
    return {
        **dict(activity),
        "post_reveal": True,
        "is_retry_variant": True,
        "retry_safe": True,
        "retry_strategy": strategy,
        "prompt_pt": "Nova situação — escolha a frase correta para o mesmo objetivo.",
        "prompt": "New context — choose the correct sentence for the same skill.",
        "options": options[:4],
        "canonical_answer": canonical,
        "accepted_variants": accepted,
        "correct_explanation": (
            f"O padrão alvo continua o mesmo; a forma adequada é «{canonical}»."
        ),
        "remember_pt": activity.get("scaffold_pt")
        or activity.get("remember_pt")
        or "Aplique a mesma estrutura em um contexto novo.",
    }


def build_retry_variant(
    activity: dict[str, Any],
    patterns: list[dict] | None = None,
    *,
    seen_fingerprints: frozenset[str] | set[str] | None = None,
) -> dict[str, Any]:
    """Variante da mesma distinção para retry pós-revelação.

    Hierarquia:
    1. Outro padrão do objetivo ainda não visto (variante determinística)
    2. Fallback seguro: `retry_safe=False` + `fallback_continue`

    Embaralhar alternativas ou repetir o mesmo prompt/gabarito NÃO conta
    como questão nova. `post_reveal=True` impede evidência forte de 1ª tentativa.
    """
    patterns = patterns or []
    seen = set(seen_fingerprints or ())
    current_fp = question_fingerprint(activity)
    if current_fp:
        seen.add(current_fp)

    def _is_fresh(candidate: dict[str, Any]) -> bool:
        if is_same_question(candidate, activity):
            return False
        fp = question_fingerprint(candidate)
        return bool(fp) and fp not in seen

    if activity.get("type") == "multiple_choice":
        current_answer = normalize_question_text(
            activity.get("canonical_answer")
            or ((activity.get("accepted_variants") or [None])[0])
        )
        # Tentar cada padrão alternativo — nunca o gabarito já revelado.
        if len(patterns) >= 2:
            for alt in patterns:
                alt_canonical = normalize_question_text(alt.get("canonical"))
                if not alt_canonical or alt_canonical == current_answer:
                    continue
                candidate = _mcq_from_pattern(
                    activity,
                    alt,
                    patterns,
                    strategy="deterministic_variant",
                )
                if _is_fresh(candidate):
                    return candidate

        # Um único pattern (ou todos esgotados): NÃO embaralhar a mesma MCQ.
        return _fallback_continue(activity)

    if activity.get("type") == "fill_gap" and patterns:
        for index, alt in enumerate(patterns):
            canonical = str(alt.get("canonical") or "")
            tokens = canonical.split()
            if len(tokens) < 2:
                continue
            answer = tokens[-1].rstrip(".,!?")
            stem = " ".join(tokens[:-1]) + " ___."
            candidate = {
                **dict(activity),
                "post_reveal": True,
                "is_retry_variant": True,
                "retry_safe": True,
                "retry_strategy": (
                    "deterministic_variant"
                    if len(patterns) >= 2
                    else "recontextualized_same_skill"
                ),
                "prompt": stem,
                "prompt_pt": "Complete a nova frase (mesmo padrão).",
                "canonical_answer": answer,
                "accepted_variants": [answer, answer.lower()],
                "correct_explanation": f"A lacuna pede «{answer}» neste padrão.",
            }
            if index == 0 and is_same_question(candidate, activity):
                continue
            if _is_fresh(candidate):
                return candidate
        return _fallback_continue(activity)

    return _fallback_continue(activity)
