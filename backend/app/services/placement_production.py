"""Production evidence. Transcript analysis never represents acoustic assessment."""
from app.core.levels import LEVEL_INDEX
from app.services.writing_evaluation import evaluate_writing


def production_result(answer):
    feedback = answer.feedback_json or {}
    level = feedback.get("estimated_level")
    linguistic = answer.evaluated_by == "ai" and level in LEVEL_INDEX and feedback.get("level_origin") != "unavailable"
    if feedback.get("exposure", {}).get("reused"):
        linguistic = False
    score = answer.normalized_score
    status = "provisional" if linguistic else "insufficient_evidence"
    if feedback.get("status") == "skipped":
        status = "not_collected"
    return {
        "skill": answer.skill, "estimated_level": level if linguistic else None,
        "score": score, "max_score": 1.0 if score is not None else None,
        "status": status, "eligible_for_overall": False,
        "evidence_counts": {"answered": 1, "valid": int(linguistic), "excluded": int(not linguistic),
                            "by_cefr": {answer.cefr_level: 1}},
        "skill_confidence": {"basis": "single_linguistic_sample", "label": "provisional" if linguistic else "insufficient",
                             "reasons": feedback.get("limitations", ["production_policy_not_validated"])},
        "provenance": {"evaluated_by": answer.evaluated_by, **feedback.get("provenance", {})},
        "feedback": feedback.get("feedback"), "criteria": feedback.get("criteria", {}),
        "reported_level": feedback.get("reported_level", level if linguistic else None),
    }


def evaluate_speaking(transcription, language_code, target_level, native_language, prompt):
    provenance = {"stt_provider": transcription.get("provider"), "stt_model": transcription.get("model"),
                  "assessment_scope": "transcript_linguistic_content", "rubric_version": "speaking-transcript-v1"}
    if transcription.get("provider") == "mock":
        return {"status": "not_evaluated", "evaluated_by": "unavailable", "eligible_for_overall": False,
                "reason": "stt_mock", "provenance": provenance, "limitations": ["stt_mock"]}
    # Existing configured evaluator. No provider/model is selected here.
    result = evaluate_writing(transcription.get("text", ""), language_code, target_level,
                              min_chars=60, native_language=native_language, task=prompt,
                              assessment_scope="speaking_transcript")
    result["provenance"] = {**result.get("provenance", {}), **provenance}
    result["eligible_for_overall"] = False
    result["limitations"] = list(dict.fromkeys(result.get("limitations", []) + ["single_sample", "pronunciation_not_measured", "fluency_not_measured",
                             "transcription_may_normalize_errors"]))
    return result
