"""Integração pedagógica: erro → 409 → retry → ERROR_REPAIRED (sem mastery automática)."""

from __future__ import annotations

from sqlalchemy import select

from app.core.teaching import AttemptResult, EvidenceType
from app.models import LearningAttempt, LearningEvidence, LearningError, Remediation
from app.services import teaching_flow, teaching_slice
from app.services.objective_seed import ensure_en_a1_can_001
from tests.test_attempt_lock import _advance_to_mcq, _ul


def test_error_retry_repaired_no_auto_mastery(db_session):
    ensure_en_a1_can_001(db_session)
    ul = _ul(db_session)
    started = teaching_slice.start_slice(db_session, user_language_id=ul.id)
    session = teaching_flow.get_flow(db_session, started["flow"]["id"])
    activity = _advance_to_mcq(db_session, session)
    texts = [
        o["text"] if isinstance(o, dict) else o for o in (activity.get("options") or [])
    ]
    wrong = next(
        (t for t in texts if t != activity.get("canonical_answer")),
        "I am a student.",
    )

    first = teaching_slice.submit_slice_answer(
        db_session, session, student_response=wrong
    )
    assert first["attempt"]["result"] == AttemptResult.INCORRECT
    assert first["answer_feedback"]["correct_option"]
    first_id = first["attempt"]["id"]
    remediation_id = first["remediation"]["id"]

    # Reenvio na mesma tentativa → 409
    from app.core.errors import APIError
    import pytest

    with pytest.raises(APIError) as exc:
        teaching_slice.submit_slice_answer(
            db_session, session, student_response=activity.get("canonical_answer")
        )
    assert exc.value.code in {"attempt_already_submitted", "use_retry_endpoint"}

    retry_activity = teaching_flow.current_activity(session) or {}
    correct = retry_activity.get("canonical_answer") or activity.get("canonical_answer")
    if retry_activity.get("type") in {"listen", "recognition", "matching"}:
        student_response = ""
    else:
        student_response = correct

    second = teaching_slice.retry_slice(
        db_session,
        session,
        remediation_id=remediation_id,
        student_response=student_response,
    )
    assert second["attempt"]["id"] != first_id
    assert second["attempt"]["result"] == AttemptResult.CORRECT

    # Histórico append-only
    assert db_session.get(LearningAttempt, first_id).result == AttemptResult.INCORRECT
    assert db_session.scalars(select(LearningError)).first() is not None
    assert db_session.scalars(select(Remediation)).first() is not None

    repaired = [
        e
        for e in db_session.scalars(select(LearningEvidence)).all()
        if e.evidence_type == EvidenceType.ERROR_REPAIRED
    ]
    strong = [
        e
        for e in db_session.scalars(select(LearningEvidence)).all()
        if e.evidence_type == EvidenceType.CORRECT_RESPONSE
        and e.attempt_id == second["attempt"]["id"]
    ]
    assert repaired, "retry pós-revelação deve gerar ERROR_REPAIRED"
    assert not strong, "não deve gerar CORRECT_RESPONSE forte no retry pós-revelação"

    # Mastery não automática só com repair
    assert second.get("mastery", {}).get("state") != "mastered"
