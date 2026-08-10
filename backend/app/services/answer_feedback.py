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


def build_retry_variant(activity: dict[str, Any], patterns: list[dict] | None = None) -> dict[str, Any]:
    """Variante da mesma distinção para retry pós-revelação.

    Hierarquia:
    1. Outro padrão do objetivo (variante determinística)
    2. Mesmo padrão com prompt/contexto reformulado (ainda post_reveal)
    3. Fallback seguro: marca `retry_safe=False` — UI deve oferecer Continuar,
       não desbloquear a questão revelada nem fabricar falso acerto.

    Em todos os casos com conteúdo reapresentado, `post_reveal=True` impede
    CORRECT_RESPONSE forte (só ERROR_REPAIRED no TE V2).
    """
    patterns = patterns or []
    base_meta = {
        "post_reveal": True,
        "is_retry_variant": True,
        "retry_safe": True,
        "retry_strategy": "none",
    }

    if activity.get("type") == "multiple_choice":
        if len(patterns) >= 2:
            alt = patterns[1]
            canonical = alt.get("canonical") or activity.get("canonical_answer")
            accepted = list(alt.get("accepted") or [canonical])
            distractors = [
                p.get("canonical")
                for p in patterns
                if p.get("canonical") and p.get("canonical") != canonical
            ][:3]
            options = [canonical, *[d for d in distractors if d]]
            return {
                **dict(activity),
                **base_meta,
                "retry_strategy": "deterministic_variant",
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

        # Um único pattern: reformular apresentação sem revelar pela forma idêntica.
        canonical = activity.get("canonical_answer") or (
            (activity.get("accepted_variants") or [None])[0]
        )
        if canonical:
            opts = option_texts(activity)
            # Reordenar opções para reduzir “mesma posição = resposta”.
            rotated = list(reversed(opts)) if len(opts) > 1 else opts
            return {
                **dict(activity),
                **base_meta,
                "retry_strategy": "recontextualized_same_skill",
                "prompt_pt": (
                    "Nova tentativa do mesmo objetivo — escolha a forma adequada "
                    "(a questão anterior permanece fechada)."
                ),
                "prompt": activity.get("prompt") or "Choose the correct form.",
                "options": rotated,
                "canonical_answer": canonical,
                "correct_explanation": activity.get("correct_explanation")
                or f"A forma adequada continua sendo «{canonical}».",
                "remember_pt": activity.get("remember_pt")
                or activity.get("scaffold_pt")
                or "Foque na estrutura, não na posição da opção.",
            }

        # Continuar sem reabrir MCQ revelada (reconhecimento / ack).
        return {
            "type": "recognition",
            "phase_hint": activity.get("phase_hint") or "practicing",
            "prompt_pt": (
                "Não há variante segura agora. Leia a correção acima e continue — "
                "a questão anterior permanece fechada."
            ),
            "title_pt": "Continuar após o feedback",
            "examples": [],
            "ai_required": False,
            **base_meta,
            "retry_strategy": "fallback_continue",
        }

    if activity.get("type") == "fill_gap" and patterns:
        alt = patterns[min(1, len(patterns) - 1)]
        canonical = str(alt.get("canonical") or activity.get("canonical_answer") or "")
        tokens = canonical.split()
        if len(tokens) >= 2:
            answer = tokens[-1].rstrip(".,!?")
            stem = " ".join(tokens[:-1]) + " ___."
            return {
                **dict(activity),
                **base_meta,
                "retry_strategy": "deterministic_variant"
                if len(patterns) >= 2
                else "recontextualized_same_skill",
                "prompt": stem,
                "prompt_pt": "Complete a nova frase (mesmo padrão).",
                "canonical_answer": answer,
                "accepted_variants": [answer, answer.lower()],
                "correct_explanation": f"A lacuna pede «{answer}» neste padrão.",
            }

    # Fallback pedagógico seguro: ack de continuidade, sem reabrir item revelado.
    return {
        "type": "recognition",
        "phase_hint": activity.get("phase_hint") or "practicing",
        "prompt_pt": (
            "Não há variante segura para nova tentativa agora. "
            "Continue; o erro fica registrado para revisão futura."
        ),
        "title_pt": "Continuar após o feedback",
        "examples": [],
        "ai_required": False,
        **base_meta,
        "retry_strategy": "fallback_continue",
    }
