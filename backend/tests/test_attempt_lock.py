"""Tentativa imutável + feedback pedagógico + retry como nova tentativa."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.errors import APIError
from app.core.teaching import AttemptResult
from app.models import LearningAttempt, LearningError, Remediation, User, UserLanguage, Language
from app.core.levels import CEFRLevel, LevelSource
from app.services import teaching_flow, teaching_slice
from app.services.answer_feedback import build_answer_feedback, build_retry_variant
from app.services.objective_seed import ensure_en_a1_can_001


def _ul(db):
    user = db.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db.scalar(select(Language).where(Language.code == "en"))
    existing = db.scalar(
        select(UserLanguage).where(
            UserLanguage.user_id == user.id,
            UserLanguage.language_id == language.id,
        )
    )
    if existing:
        return existing
    ul = UserLanguage(
        user_id=user.id,
        language_id=language.id,
        is_active=True,
        onboarding_completed=True,
        diagnostic_completed=True,
        current_level=CEFRLevel.A1,
        level_source=LevelSource.PLACEMENT_TEST,
        vocabulary_grammar_level=CEFRLevel.A1,
        reading_level=CEFRLevel.A1,
        listening_level=CEFRLevel.A1,
        writing_level=CEFRLevel.A1,
        speaking_level=CEFRLevel.A1,
    )
    db.add(ul)
    db.commit()
    return ul


def _advance_to_mcq(db, session):
    """Avança corretamente até a primeira multiple_choice."""
    for _ in range(20):
        activity = teaching_flow.current_activity(session) or {}
        kind = activity.get("type")
        if kind == "multiple_choice":
            return activity
        if kind in {"listen", "recognition", "matching"}:
            ans = ""
        elif kind == "fill_gap":
            ans = activity.get("canonical_answer") or ""
        elif kind == "word_order":
            ans = " ".join(activity.get("tokens") or [])
        else:
            ans = activity.get("canonical_answer") or ""
        teaching_slice.submit_slice_answer(db, session, student_response=ans)
        db.refresh(session)
    raise AssertionError("multiple_choice não encontrada no fluxo")


def test_feedback_wrong_includes_selected_and_correct():
    activity = {
        "type": "multiple_choice",
        "options": [
            {"id": "A", "text": "I live in Goiânia.", "rationale": "Correto: morar + in."},
            {
                "id": "B",
                "text": "I am a student.",
                "rationale": "Fala de profissão/estudo, não de moradia.",
            },
        ],
        "canonical_answer": "I live in Goiânia.",
        "correct_explanation": "Use live + in + cidade.",
    }
    fb = build_answer_feedback(
        activity=activity, student_response="I am a student.", is_correct=False
    )
    assert fb["is_correct"] is False
    assert fb["selected"] == "I am a student."
    assert fb["correct_option"] == "I live in Goiânia."
    assert "profissão" in (fb["why_selected"] or "")
    assert "live" in (fb["why_correct"] or "").lower() or "Use live" in (fb["why_correct"] or "")


def test_retry_variant_is_marked_post_reveal():
    activity = {
        "type": "multiple_choice",
        "canonical_answer": "I live in Goiânia.",
        "options": ["I live in Goiânia.", "I am a student."],
    }
    patterns = [
        {"canonical": "I live in Goiânia.", "accepted": ["I live in Goiânia."]},
        {"canonical": "I'm from Brazil.", "accepted": ["I'm from Brazil."]},
    ]
    variant = build_retry_variant(activity, patterns)
    assert variant["post_reveal"] is True
    assert variant["is_retry_variant"] is True
    assert variant["canonical_answer"] == "I'm from Brazil."


def test_mcq_second_submit_rejected(db_session):
    ensure_en_a1_can_001(db_session)
    ul = _ul(db_session)
    started = teaching_slice.start_slice(db_session, user_language_id=ul.id)
    session = teaching_flow.get_flow(db_session, started["flow"]["id"])
    activity = _advance_to_mcq(db_session, session)
    options = activity.get("options") or []
    # options podem ser str após normalização no payload; na activity bruta são dicts
    wrong = "I am a student."
    texts = [
        o["text"] if isinstance(o, dict) else o for o in options
    ]
    if wrong not in texts and texts:
        wrong = next(t for t in texts if t != activity.get("canonical_answer"))

    out = teaching_slice.submit_slice_answer(
        db_session, session, student_response=wrong
    )
    assert out["attempt"]["result"] == AttemptResult.INCORRECT
    assert out["answer_feedback"]["is_correct"] is False

    with pytest.raises(APIError) as exc:
        teaching_slice.submit_slice_answer(
            db_session, session, student_response=activity.get("canonical_answer")
        )
    assert exc.value.code in {"attempt_already_submitted", "use_retry_endpoint"}


def test_retry_creates_new_attempt_and_keeps_history(db_session):
    ensure_en_a1_can_001(db_session)
    ul = _ul(db_session)
    started = teaching_slice.start_slice(db_session, user_language_id=ul.id)
    session = teaching_flow.get_flow(db_session, started["flow"]["id"])
    activity = _advance_to_mcq(db_session, session)
    options = activity.get("options") or []
    texts = [o["text"] if isinstance(o, dict) else o for o in options]
    wrong = next(
        (t for t in texts if t != activity.get("canonical_answer")),
        "I am a student.",
    )
    first = teaching_slice.submit_slice_answer(
        db_session, session, student_response=wrong
    )
    first_id = first["attempt"]["id"]
    remediation_id = first["remediation"]["id"]

    # Retry na variante (não na questão já revelada)
    retry_activity = teaching_flow.current_activity(session) or {}
    correct = retry_activity.get("canonical_answer") or activity.get("canonical_answer")
    second = teaching_slice.retry_slice(
        db_session,
        session,
        remediation_id=remediation_id,
        student_response=correct,
    )
    assert second["attempt"]["id"] != first_id
    assert second["attempt"]["result"] == AttemptResult.CORRECT

    attempts = list(
        db_session.scalars(
            select(LearningAttempt).where(LearningAttempt.user_language_id == ul.id)
        )
    )
    assert len(attempts) >= 2
    assert any(a.id == first_id and a.result == AttemptResult.INCORRECT for a in attempts)


def test_evaluate_attempt_immutable(db_session):
    ensure_en_a1_can_001(db_session)
    ul = _ul(db_session)
    objective = ensure_en_a1_can_001(db_session)
    from app.services import teaching_engine

    attempt = teaching_engine.record_attempt(
        db_session,
        user_language_id=ul.id,
        objective_id=objective.id,
        activity_type="multiple_choice",
        student_response="x",
    )
    teaching_engine.evaluate_attempt(
        db_session, attempt, result=AttemptResult.INCORRECT, provider="test"
    )
    with pytest.raises(APIError) as exc:
        teaching_engine.evaluate_attempt(
            db_session, attempt, result=AttemptResult.CORRECT, provider="test"
        )
    assert exc.value.code == "attempt_already_submitted"
