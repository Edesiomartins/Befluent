"""Operational entry policy, deliberately separate from measured CEFR."""
from app.core.levels import LEVEL_INDEX, normalize_level

PLANNING_POLICY = {"version": "placement-planning-v1", "partial_ceiling": "A1",
                   "entry_signal_minimum": 2, "performance_minimum_items": 4,
                   "performance_minimum_accuracy": 0.75}


def planning_decision(result):
    trace = {"policy": dict(PLANNING_POLICY), "signals": [], "excluded": []}
    overall = normalize_level(result.get("overall_level"))
    if result.get("overall_estimate_status") == "sufficient" and overall:
        level, source, reason = overall, "sufficient_overall", "Entrada baseada no nível global sustentado por cobertura suficiente."
    else:
        levels = []
        entry_signals = set()
        for skill, data in result.get("skills", {}).items():
            if skill not in {"vocabulary_grammar", "reading", "listening", "writing", "speaking"}:
                trace["excluded"].append({"skill": skill, "reason": "unsupported_skill"})
                continue
            status = data.get("status")
            counts = data.get("evidence_counts") or {}
            valid = counts.get("independent", counts.get("valid", 0))
            if not valid:
                trace["excluded"].append({"skill": skill, "reason": "no_independent_eligible_evidence"})
                continue
            estimated = normalize_level(data.get("estimated_level"))
            if status in {"estimated", "provisional"} and estimated:
                levels.append(estimated)
                trace["signals"].append({"skill": skill, "status": status, "kind": "level_for_planning", "level": estimated})
                if LEVEL_INDEX[estimated] >= LEVEL_INDEX["A1"]:
                    entry_signals.add(skill)
            elif status == "insufficient_evidence" and skill in {"vocabulary_grammar", "reading", "listening"}:
                # Use eligible performance only: observed raw score may include reused items.
                accuracy = data.get("accuracy") if not counts.get("reused") else None
                total = data.get("max_score") or 0
                if accuracy is None and not counts.get("reused") and total:
                    accuracy = (data.get("score") or 0) / total
                supports_entry = valid >= PLANNING_POLICY["performance_minimum_items"] and accuracy is not None and accuracy >= PLANNING_POLICY["performance_minimum_accuracy"]
                trace["signals"].append({"skill": skill, "status": status, "kind": "performance_only",
                    "eligible_items": valid, "accuracy": accuracy, "supports_entry": supports_entry})
                if supports_entry:
                    entry_signals.add(skill)
            else:
                trace["excluded"].append({"skill": skill, "reason": "unknown_or_unavailable"})
        ordered = sorted(levels, key=LEVEL_INDEX.__getitem__)
        median = ordered[(len(ordered) - 1) // 2] if ordered else "PRE_A1"
        corroborated = len(entry_signals) >= PLANNING_POLICY["entry_signal_minimum"]
        candidate = max((median, "A1" if corroborated else "PRE_A1"), key=LEVEL_INDEX.__getitem__)
        level = min((candidate, PLANNING_POLICY["partial_ceiling"]), key=LEVEL_INDEX.__getitem__) if corroborated else "PRE_A1"
        trace.update(lower_median=median, candidate=candidate, entry_supporting_skills=sorted(entry_signals),
                     ceiling_applied=PLANNING_POLICY["partial_ceiling"], corroborated=corroborated)
        source = "partial_evidence"
        reason = ("Entrada operacional A1 apoiada por pelo menos duas competências; perfil parcial e teto conservador A1."
                  if corroborated else "Entrada operacional PRE_A1: faltam sinais independentes em duas competências para iniciar em A1.")
    return {"planning_level": level, "planning_level_source": source,
            "planning_level_reason": reason, "planning_level_trace": trace}


def planning_payload(profile):
    summary = profile.assessment_summary_json or {}
    planning = summary.get("planning") or {}
    return {"planning_level": profile.planning_level, "planning_level_source": profile.planning_level_source,
            "planning_level_reason": planning.get("planning_level_reason"),
            "planning_level_trace": planning.get("planning_level_trace")}


def assessment_payload(profile):
    summary = profile.assessment_summary_json or {}
    return {**planning_payload(profile), "overall_level": summary.get("overall_level"),
            "overall_estimate_status": summary.get("overall_estimate_status"),
            "profile_status": summary.get("profile_status"), "assessment_skills": summary.get("skills", {})}
