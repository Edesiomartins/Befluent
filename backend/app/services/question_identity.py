"""Identidade pedagógica de questões objetivas.

Embaralhar alternativas, mudar espaços ou a caixa não cria uma questão
nova. Prefixo cosmético de retry («Nova tentativa», «New context…») é
removido do prompt, mas o contexto semântico restante continua a distinguir
duas questões — mesmo que opções e gabarito coincidam.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# Prefixo/decoração de retry — remove só a embalagem, não o enunciado.
_COSMETIC_PREFIX_RE = re.compile(
    r"^(?:"
    r"nova tentativa|"
    r"nova situação|"
    r"new context|"
    r"retry"
    r")(?:\s*[—\-–:]+\s*|\s+)",
    re.IGNORECASE,
)


def normalize_question_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKC", text)
    text = text.casefold().strip()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalized_options(activity: dict[str, Any]) -> tuple[str, ...]:
    raw = activity.get("options") or []
    texts: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            texts.append(normalize_question_text(item.get("text")))
        else:
            texts.append(normalize_question_text(item))
    return tuple(sorted(t for t in texts if t))


def _correct_answer(activity: dict[str, Any]) -> str:
    if activity.get("answer") is not None:
        return normalize_question_text(activity.get("answer"))
    if activity.get("canonical_answer") is not None:
        return normalize_question_text(activity.get("canonical_answer"))
    accepted = activity.get("accepted_variants") or []
    if accepted:
        return normalize_question_text(accepted[0])
    return ""


def _prompt_for_identity(activity: dict[str, Any]) -> str:
    """Prompt semântico: remove prefixos cosméticos de retry, mantém o contexto."""
    raw = str(activity.get("prompt") or activity.get("prompt_pt") or "").strip()
    if not raw:
        return ""
    # Remover um ou mais prefixos empilhados ("Nova tentativa — New context — …").
    while True:
        stripped = _COSMETIC_PREFIX_RE.sub("", raw, count=1).strip()
        if stripped == raw:
            break
        raw = stripped
    return normalize_question_text(raw)


def question_fingerprint(activity: dict[str, Any] | None) -> str:
    """Assinatura estável: prompt semântico + gabarito + opções (ordem irrelevante).

    Duas questões com enunciados diferentes e as mesmas alternativas/gabarito
    produzem fingerprints distintos. Embaralhar opções ou mudar só caixa/
    espaços/pontuação/prefixo de retry não altera o fingerprint.
    """
    if not isinstance(activity, dict):
        return ""
    prompt = _prompt_for_identity(activity)
    answer = _correct_answer(activity)
    options = _normalized_options(activity)
    if not prompt and not answer and not options:
        return ""
    return f"{prompt}|{answer}|{'/'.join(options)}"


def is_same_question(
    left: dict[str, Any] | None, right: dict[str, Any] | None
) -> bool:
    left_fp = question_fingerprint(left)
    right_fp = question_fingerprint(right)
    return bool(left_fp and right_fp and left_fp == right_fp)


def fingerprints_from_snapshots(
    snapshots: list[dict[str, Any] | None],
) -> frozenset[str]:
    return frozenset(
        fp
        for snap in snapshots
        if isinstance(snap, dict) and (fp := question_fingerprint(snap))
    )
