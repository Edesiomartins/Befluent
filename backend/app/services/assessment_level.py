"""Read-only qualification of placement-derived global claims."""
def verified_current_level(profile):
    if profile is None:
        return None
    if profile.level_source in {"placement_test", "checkpoint"}:
        summary = profile.assessment_summary_json or {}
        if summary.get("global_estimate_status", summary.get("overall_estimate_status")) != "sufficient":
            return None
    return profile.current_level
