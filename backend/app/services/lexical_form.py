"""Forma contextual de um item lexical.

O card mostra o lema (`term`) e, quando o conteúdo já declara, a forma que
aparece na frase (`example_form`) com uma nota curta (`form_note`).

Este módulo não compara o lema com as palavras da frase e não conjuga nada.
Se o campo não veio preenchido, ou se a forma declarada é a mesma do lema,
a explicação não é criada.
"""

from __future__ import annotations

from typing import Any


def _clean(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _same_form(left: str, right: str) -> bool:
    return left.casefold() == right.casefold()


def normalize_lexical_item(item: dict[str, Any]) -> dict[str, Any]:
    """Conserva `example_form` e `form_note` só quando são dados úteis.

    Forma igual ao lema, string vazia ou tipo inválido são removidos.
    Uma nota sem forma distinta também sai: não há o que explicar.
    """
    out = dict(item)
    term = _clean(out.get("term"))
    form = _clean(out.get("example_form"))
    note = _clean(out.get("form_note"))
    out.pop("example_form", None)
    out.pop("form_note", None)
    if not form or _same_form(form, term):
        return out
    out["example_form"] = form
    if note:
        out["form_note"] = note
    return out


def normalize_vocabulary_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Aplica a normalização nos itens de vocabulário, sem mexer no resto."""
    out = dict(payload)
    for key in ("items", "revisited_items"):
        raw = out.get(key)
        if not isinstance(raw, list):
            continue
        out[key] = [
            normalize_lexical_item(item) if isinstance(item, dict) else item
            for item in raw
        ]
    return out
