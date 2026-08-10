"""Seleção diária de vocabulário — new / revisited / SRS.

Contrato de papéis (não misturar):

- **A. new** (`items` / `new_items`): primeira exposição no percurso curricular
  (ainda não apareceu em lição aberta de jornada anterior).
- **B. revisited** (`revisited_items`): já exposto; spiral learning.
- **C. SRS**: só no bloco `review` via fila temporal — fora deste módulo.

Definição de “exposto”: termo em `items` de bloco vocabulary com `lesson_ref`
em dia anterior do mesmo currículo (ver `lesson_thread.curriculum_exposed_terms`).
Não usa SRS para decidir novidade curricular.
"""

from __future__ import annotations

from typing import Any

from app.services import lesson_bank

#: Itens novos por jornada no bloco de vocabulário (mock / fallback).
DAILY_NEW_COUNT = 5
#: Retomadas spirais mostradas junto do bloco (não são SRS).
DAILY_REVISIT_COUNT = 3


def _term_key(item: dict[str, Any]) -> str:
    return str(item.get("term") or "").casefold()


def _stable_pool(
    language_code: str,
    band: str,
    week_theme: str | None,
) -> list[dict[str, str]]:
    """Pool da semana: preferir itens etiquetados com o tema; senão banda inteira."""
    all_items = lesson_bank.vocabulary(language_code, band)
    theme = (week_theme or "").strip()
    if theme:
        themed = [
            item
            for item in all_items
            if theme in (item.get("themes") or [])
        ]
        if len(themed) >= DAILY_NEW_COUNT:
            pool = themed
        else:
            pool = all_items
    else:
        pool = all_items
    return sorted(pool, key=_term_key)


def _slice_for_day(pool: list[dict[str, str]], *, day_number: int, count: int) -> list[dict[str, str]]:
    """Fatia estável e quase disjunta por dia dentro da semana."""
    if not pool:
        return []
    count = min(count, len(pool))
    day_in_week = max(0, (day_number or 1) - 1) % 7
    start = (day_in_week * count) % len(pool)
    out: list[dict[str, str]] = []
    for offset in range(len(pool)):
        item = pool[(start + offset) % len(pool)]
        if item not in out:
            out.append(item)
        if len(out) >= count:
            break
    return out


def select_daily_vocabulary(
    language_code: str,
    band: str,
    *,
    day_number: int | None,
    week_theme: str | None = None,
    recycled_items: list[dict[str, str]] | None = None,
    exposed_items: list[dict[str, str]] | None = None,
    count: int = DAILY_NEW_COUNT,
) -> dict[str, Any]:
    """Seleciona léxico do dia com papéis explícitos por histórico curricular.

    `exposed_items`: já apresentados ao aluno em jornadas anteriores.
    `recycled_items`: candidatos preferenciais à spiral da semana (subconjunto
    tipicamente recente); também contam como expostos se ainda não estiverem.
    """
    recycled = [item for item in (recycled_items or []) if item.get("term")]
    exposed = [item for item in (exposed_items or []) if item.get("term")]

    exposed_keys = {_term_key(item) for item in exposed}
    exposed_keys.update(_term_key(item) for item in recycled)

    # Índice por termo para montar payloads revisitados com metadados.
    by_key: dict[str, dict[str, str]] = {}
    for item in [*exposed, *recycled]:
        key = _term_key(item)
        if key and key not in by_key:
            by_key[key] = item

    pool = _stable_pool(language_code, band, week_theme)
    day_n = day_number or 1

    candidates = _slice_for_day(pool, day_number=day_n, count=count)
    fresh = [item for item in candidates if _term_key(item) not in exposed_keys]
    if len(fresh) < count:
        for item in pool:
            key = _term_key(item)
            if key in exposed_keys:
                continue
            if item in fresh:
                continue
            fresh.append(item)
            if len(fresh) >= count:
                break

    # Nunca marcar como novo um termo já exposto — mesmo se o pool esgotar.
    new_items = [item for item in fresh[:count] if _term_key(item) not in exposed_keys]

    # Spiral: preferir recycled da semana; completar com outros já expostos.
    revisited: list[dict[str, str]] = []
    seen_rev: set[str] = set()
    for item in recycled:
        key = _term_key(item)
        if not key or key in seen_rev:
            continue
        # Não misturar com os new do dia.
        if any(_term_key(n) == key for n in new_items):
            continue
        revisited.append(item)
        seen_rev.add(key)
        if len(revisited) >= DAILY_REVISIT_COUNT:
            break
    if len(revisited) < DAILY_REVISIT_COUNT:
        for key, item in by_key.items():
            if key in seen_rev:
                continue
            if any(_term_key(n) == key for n in new_items):
                continue
            revisited.append(item)
            seen_rev.add(key)
            if len(revisited) >= DAILY_REVISIT_COUNT:
                break

    violations = [
        _term_key(item)
        for item in new_items
        if _term_key(item) in exposed_keys
    ]

    return {
        "new_items": list(new_items),
        "revisited_items": list(revisited),
        "pool_size": len(pool),
        "exposed_count": len(exposed_keys),
        "selection_policy": "curriculum_history_first_exposure",
        "content_roles": {
            "items": "new_first_exposure",
            "revisited_items": "spiral_curriculum",
            "srs": "review_block_only",
        },
        "new_as_exposed_violations": violations,
    }
