"""Catalog capacity is independent of learner performance."""
from collections import Counter
from sqlalchemy import select
from app.models import PlacementItem
from app.services.placement_delivery import approved_active_filter
from app.services import placement_engine as engine


def evidence_fingerprint(item):
    """Identical stimuli/options do not become independent evidence via a new ID."""
    from app.services.placement_exposure import semantic_keys
    keys = semantic_keys(item)
    return keys.get("family") or keys.get("passage") or keys.get("audio") or keys.get("prompt") or keys["exact"]


def independent_item_groups(items):
    """Connected semantic identities, including overlapping passage/family keys."""
    from app.services.placement_exposure import semantic_keys
    groups = []
    for item in items:
        keys = {f"{k}:{v}" for k, v in semantic_keys(item).items()}
        matches = [i for i, (_, seen) in enumerate(groups) if keys & seen]
        if not matches:
            groups.append(([item], keys))
        else:
            first = matches[0]
            groups[first][0].append(item)
            groups[first][1].update(keys)
            for i in reversed(matches[1:]):
                groups[first][0].extend(groups[i][0])
                groups[first][1].update(groups[i][1])
                groups.pop(i)
    return [rows for rows, _ in groups]


def catalog_matrix(items):
    """Static bank inventory; fresh means unexposed hypothetical new account.

    Existing-account availability must be audited with its exposure ledger.
    Shared components are counted once per matrix cell, never merely by ID.
    """
    items = list(items)
    counts = Counter((x.language_code, x.skill, x.cefr_level, x.item_type) for x in items)
    independent = Counter()
    eligible = [x for x in items if x.is_active and x.review_status == "approved"]
    for group in independent_item_groups(eligible):
        independent.update(set((x.language_code, x.skill, x.cefr_level, x.item_type) for x in group))
    for code in {x.language_code for x in items}:
        for skill in ("reading", "listening"):
            for band in engine.TESTABLE_LEVELS:
                counts.setdefault((code, skill, band, f"{skill}_comprehension"), 0)
    return [{"language_code": code, "skill": skill, "cefr": band, "item_type": kind,
             "fresh_independent_stimulus_groups": independent[code, skill, band, kind],
             "total_items": total}
            for (code, skill, band, kind), total in sorted(counts.items())]


def bank_capacity(db, language_code):
    rows = list(db.scalars(select(PlacementItem).where(
        PlacementItem.language_code == language_code, *approved_active_filter(),
        PlacementItem.skill.in_(engine.OBJECTIVE_SKILLS),
        PlacementItem.cefr_level.in_(engine.TESTABLE_LEVELS),
        PlacementItem.item_type.in_(["multiple_choice", "fill_blank", "reading_comprehension", "listening_comprehension"]))))
    unique_rows = [group[0] for group in independent_item_groups(rows)]
    counts = Counter((item.skill, item.cefr_level) for item in unique_rows)
    deficits = []
    for skill in engine.OBJECTIVE_SKILLS:
        total = sum(count for (s, band), count in counts.items() if s == skill)
        if total < engine.MIN_ITEMS_PER_SKILL or not any(count >= 2 for (s, _), count in counts.items() if s == skill):
            deficits.append(skill)
    return {"objective_capacity": len(unique_rows), "duplicate_items_excluded": len(rows) - len(unique_rows), "target": min(len(unique_rows), engine.RECOMMENDED_OBJECTIVE_ITEMS),
            "bank_feasibility": "insufficient" if deficits else "possible",
            "bank_deficits": deficits,
            "by_skill_cefr": {skill: {band: counts[skill, band] for band in engine.TESTABLE_LEVELS}
                               for skill in engine.OBJECTIVE_SKILLS}}
