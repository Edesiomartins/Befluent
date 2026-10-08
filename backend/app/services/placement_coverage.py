"""Catalog capacity is independent of learner performance."""
from collections import Counter
import hashlib
import json
import re
from sqlalchemy import select
from app.models import PlacementItem
from app.services.placement_delivery import approved_active_filter
from app.services import placement_engine as engine


def evidence_fingerprint(item):
    """Identical stimuli/options do not become independent evidence via a new ID."""
    def normalize(value):
        return re.sub(r"\s+", " ", str(value or "").casefold()).strip()
    options = item.options_json or []
    option_text = sorted(normalize(option.get("text", option.get("label", "")))
                         if isinstance(option, dict) else normalize(option) for option in options)
    payload = [item.language_code, item.skill, item.item_type,
               normalize(item.prompt), normalize(item.passage), normalize(item.audio_script), option_text]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


def bank_capacity(db, language_code):
    rows = list(db.scalars(select(PlacementItem).where(
        PlacementItem.language_code == language_code, *approved_active_filter(),
        PlacementItem.skill.in_(engine.OBJECTIVE_SKILLS),
        PlacementItem.cefr_level.in_(engine.TESTABLE_LEVELS),
        PlacementItem.item_type.in_(["multiple_choice", "fill_blank", "reading_comprehension", "listening_comprehension"]))))
    unique_rows = list({evidence_fingerprint(item): item for item in rows}.values())
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
