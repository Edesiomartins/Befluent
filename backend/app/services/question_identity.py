"""Identidade pedagógica de questões objetivas.

Embaralhar alternativas, mudar espaços ou a caixa não cria uma questão
nova. Depois que o gabarito foi revelado, o mesmo fingerprint não pode
voltar como «Nova tentativa» na mesma sequência.

Wrappers cosméticos de retry («Nova tentativa», «New context…») também
não bastam se opções + gabarito forem os mesmos.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

_COSMETIC_PROMPT_RE = re.compile(
    r"^(nova tentativa|nova situação|new context|choose the correct|"
    r"complete a nova frase|pick the correct).*$",
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
    prompt = normalize_question_text(
        activity.get("prompt") or activity.get("prompt_pt") or ""
    )
    if not prompt or _COSMETIC_PROMPT_RE.match(prompt):
        return ""
    return prompt


def content_fingerprint(activity: dict[str, Any] | None) -> str:
    """Assinatura de gabarito + opções (ordem irrelevante)."""
    if not isinstance(activity, dict):
        return ""
    answer = _correct_answer(activity)
    options = _normalized_options(activity)
    if not answer and not options:
        return ""
    return f"{answer}|{'/'.join(options)}"


def question_fingerprint(activity: dict[str, Any] | None) -> str:
    """Assinatura estável do conteúdo pedagógico.

    Inclui prompt quando ele distingue a tarefa; wrappers cosméticos de
    retry são ignorados. Embaralhar opções não altera o fingerprint.
    """
    if not isinstance(activity, dict):
        return ""
    content = content_fingerprint(activity)
    if not content:
        # fill_gap / texto sem opções tipadas
        prompt = _prompt_for_identity(activity)
        answer = _correct_answer(activity)
        if not prompt and not answer:
            return ""
        return f"{prompt}|{answer}|"
    prompt = _prompt_for_identity(activity)
    return f"{prompt}|{content}"


def is_same_question(
    left: dict[str, Any] | None, right: dict[str, Any] | None
) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    left_content = content_fingerprint(left)
    right_content = content_fingerprint(right)
    if left_content and right_content and left_content == right_content:
        return True
    left_fp = question_fingerprint(left)
    right_fp = question_fingerprint(right)
    return bool(left_fp and right_fp and left_fp == right_fp)


def fingerprints_from_snapshots(
    snapshots: list[dict[str, Any] | None],
) -> frozenset[str]:
    out: set[str] = set()
    for snap in snapshots:
        if not isinstance(snap, dict):
            continue
        fp = question_fingerprint(snap)
        if fp:
            out.add(fp)
        content = content_fingerprint(snap)
        if content:
            out.add(content)
    return frozenset(out)
