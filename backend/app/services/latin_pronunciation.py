"""Correções de notas de pronúncia do latim eclesiástico.

A IA às vezes cola a regra genérica «g/c ante e/i» em palavras onde a letra
seguinte é outra (ex.: gloria → g+l). Isso confunde o aluno. Estas funções
reescrevem a nota quando o contexto da palavra não bate com a regra citada.
"""

from __future__ import annotations

import re
from typing import Any

_SOFT_G_MENTION = re.compile(
    r"g\s*antes\s*de\s*e\s*/\s*i|g\s*\+\s*e\s*/\s*i|/dʒ/|djado|dj['']",
    re.IGNORECASE,
)
_SOFT_C_MENTION = re.compile(
    r"c\s*antes\s*de\s*e\s*/\s*i|c\s*\+\s*e\s*/\s*i|/tʃ/|tché|chuva",
    re.IGNORECASE,
)
_HAS_SOFT_G = re.compile(r"g[eéiíy]", re.IGNORECASE)
_HAS_SOFT_C = re.compile(r"c[eéiíyæ]|cae|coe", re.IGNORECASE)


def fix_latin_usage_note(term: str, usage_note: str | None) -> str | None:
    """Reescreve nota enganosa; devolve a original se estiver coerente."""
    if not usage_note or not term:
        return usage_note
    folded = term.casefold()
    note = usage_note

    if _SOFT_G_MENTION.search(note) and not _HAS_SOFT_G.search(folded):
        if "gl" in folded:
            return (
                "Em «gloria», o g ante l permanece /g/ (duro). "
                "O /dʒ/ eclesiástico só ocorre com g ante e/i (ex.: Regina, angelus)."
            )
        if re.search(r"g[aou]", folded):
            return (
                f"Em «{term}», o g ante a/o/u permanece /g/ (duro). "
                "O /dʒ/ eclesiástico só ocorre com g ante e/i (ex.: Regina)."
            )
        return (
            f"Em «{term}», o g não está ante e/i — permanece /g/ (duro). "
            "O /dʒ/ eclesiástico só ocorre com g ante e/i (ex.: Regina, angelus)."
        )

    if _SOFT_C_MENTION.search(note) and not _HAS_SOFT_C.search(folded):
        if re.search(r"c[aoulr]", folded) or "ch" in folded:
            return (
                f"Em «{term}», o c não está ante e/i/ae/oe — permanece /k/. "
                "O /tʃ/ eclesiástico só ocorre com c ante e/i/ae/oe (ex.: caelum, Cecilia)."
            )

    return note


def sanitize_latin_vocabulary_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Aplica a correção em `items` (e revisitados) de uma lição de vocabulário."""
    out = dict(payload)
    for key in ("items", "revisited_items"):
        raw = out.get(key)
        if not isinstance(raw, list):
            continue
        fixed: list[Any] = []
        for item in raw:
            if not isinstance(item, dict):
                fixed.append(item)
                continue
            copy = dict(item)
            term = str(copy.get("term") or copy.get("word") or "")
            note = copy.get("usage_note")
            if isinstance(note, str):
                copy["usage_note"] = fix_latin_usage_note(term, note)
            fixed.append(copy)
        out[key] = fixed
    return out
