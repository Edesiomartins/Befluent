"""Antirrepetição pedagógica no retry legado e Teaching Engine V2."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.teaching import AttemptResult, EvidenceType
from app.models import Language, LearningEvidence, Lesson, User, UserLanguage
from app.services import lesson_attempts, teaching_flow, teaching_slice
from app.services.answer_feedback import build_retry_variant
from app.services.objective_seed import ensure_en_a1_can_001
from app.services.question_identity import (
    is_same_question,
    normalize_question_text,
    question_fingerprint,
)


def _admin(db):
    return db.scalar(select(User).where(User.email == "admin@befluent.local"))


def _owner(db, user: User) -> UserLanguage:
    language = db.scalar(select(Language).where(Language.code == "en"))
    ul = db.scalar(
        select(UserLanguage).where(
            UserLanguage.user_id == user.id,
            UserLanguage.language_id == language.id,
        )
    )
    if ul is None:
        ul = UserLanguage(
            user_id=user.id,
            language_id=language.id,
            is_active=True,
            onboarding_completed=True,
        )
        db.add(ul)
        db.flush()
    return ul


def _lesson_with_questions(db, user: User, questions: list[dict]) -> Lesson:
    ul = _owner(db, user)
    lesson = Lesson(
        user_language_id=ul.id,
        title="Reading retry antirrepetição",
        objective="Compreensão",
        status="active",
        content_json={
            "language_code": "fr",
            "mode": "reading",
            "band": "beginner",
            "questions": questions,
            "exercises": [],
        },
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


FR_QUESTIONS = [
    {
        "prompt": "Selon le texte, pourquoi le vélo peut-il être plus rapide en ville ?",
        "options": [
            "Parce qu'il évite les embouteillages",
            "Parce qu'il est plus cher",
            "Parce qu'il consomme plus d'essence",
        ],
        "answer": "Parce qu'il évite les embouteillages",
        "rationale": "Le texte lie vitesse urbaine à l'absence d'embouteillages.",
    },
    {
        "prompt": "D'après le texte, quel avantage principal le vélo offre-t-il en ville ?",
        "options": [
            "Il contourne les bouchons",
            "Il coûte plus cher",
            "Il pollue davantage",
        ],
        "answer": "Il contourne les bouchons",
        "rationale": "Avantage = éviter les embouteillages.",
    },
    {
        "prompt": "Pourquoi le texte recommande-t-il le vélo pour les trajets urbains ?",
        "options": [
            "Parce qu'il permet de gagner du temps dans le trafic",
            "Parce qu'il remplace tous les bus",
            "Parce qu'il est obligatoire",
        ],
        "answer": "Parce qu'il permet de gagner du temps dans le trafic",
        "rationale": "Gain de temps lié au trafic.",
    },
]


def test_fingerprint_ignores_shuffle_case_and_punctuation():
    a = {
        "prompt": "  Pourquoi le vélo ? ",
        "options": ["Oui!", "Non"],
        "answer": "Oui!",
    }
    b = {
        "prompt": "pourquoi le vélo?",
        "options": ["Non", "oui"],
        "answer": "oui",
    }
    assert question_fingerprint(a) == question_fingerprint(b)
    assert is_same_question(a, b)
    assert normalize_question_text("  A  B ") == "a b"


def test_legacy_retry_not_same_as_a(db_session):
    admin = _admin(db_session)
    lesson = _lesson_with_questions(db_session, admin, FR_QUESTIONS[:2])
    owner = db_session.get(UserLanguage, lesson.user_language_id)
    first = lesson_attempts.submit_objective_answer(
        db_session,
        lesson=lesson,
        owner=owner,
        activity_key="reading:question:0",
        selected_answer=FR_QUESTIONS[0]["options"][1],
    )
    db_session.commit()
    assert first["retry"]["available"] is True
    retry_prompt = first["retry"]["activity"]["prompt"]
    assert retry_prompt != FR_QUESTIONS[0]["prompt"]
    assert not is_same_question(
        {"prompt": retry_prompt, "options": first["retry"]["activity"]["options"], "answer": FR_QUESTIONS[1]["answer"]},
        FR_QUESTIONS[0],
    )


def test_legacy_no_a_b_a_cycle(db_session):
    admin = _admin(db_session)
    lesson = _lesson_with_questions(db_session, admin, FR_QUESTIONS[:2])
    owner = db_session.get(UserLanguage, lesson.user_language_id)
    key = "reading:question:0"

    first = lesson_attempts.submit_objective_answer(
        db_session,
        lesson=lesson,
        owner=owner,
        activity_key=key,
        selected_answer=FR_QUESTIONS[0]["options"][1],
    )
    db_session.commit()
    assert first["retry"]["available"] is True
    assert first["retry"]["activity"]["prompt"] == FR_QUESTIONS[1]["prompt"]

    second = lesson_attempts.submit_objective_answer(
        db_session,
        lesson=lesson,
        owner=owner,
        activity_key=key,
        selected_answer=FR_QUESTIONS[1]["options"][1],
        request_retry=True,
    )
    db_session.commit()
    # Só havia A e B — após ambas, sem variante segura (não voltar para A).
    assert second["retry"]["available"] is False
    assert second["retry"]["strategy"] == "fallback_continue"


def test_legacy_three_variants_no_repeat(db_session):
    admin = _admin(db_session)
    lesson = _lesson_with_questions(db_session, admin, FR_QUESTIONS)
    owner = db_session.get(UserLanguage, lesson.user_language_id)
    key = "reading:question:0"
    seen_prompts: list[str] = [FR_QUESTIONS[0]["prompt"]]

    first = lesson_attempts.submit_objective_answer(
        db_session,
        lesson=lesson,
        owner=owner,
        activity_key=key,
        selected_answer=FR_QUESTIONS[0]["options"][1],
    )
    db_session.commit()
    assert first["retry"]["available"] is True
    seen_prompts.append(first["retry"]["activity"]["prompt"])

    second = lesson_attempts.submit_objective_answer(
        db_session,
        lesson=lesson,
        owner=owner,
        activity_key=key,
        selected_answer=FR_QUESTIONS[1]["options"][1],
        request_retry=True,
    )
    db_session.commit()
    assert second["retry"]["available"] is True
    seen_prompts.append(second["retry"]["activity"]["prompt"])

    third = lesson_attempts.submit_objective_answer(
        db_session,
        lesson=lesson,
        owner=owner,
        activity_key=key,
        selected_answer=FR_QUESTIONS[2]["options"][1],
        request_retry=True,
    )
    db_session.commit()
    assert len(seen_prompts) == len(set(seen_prompts))
    assert third["retry"]["available"] is False
    assert third["retry"]["strategy"] == "fallback_continue"


def test_legacy_regression_three_retries_never_repeat(db_session):
    """Regressão: A → erro → retry ×3 nunca reapresenta questão já vista."""
    from app.models import LessonActivityAttempt

    admin = _admin(db_session)
    lesson = _lesson_with_questions(db_session, admin, FR_QUESTIONS)
    owner = db_session.get(UserLanguage, lesson.user_language_id)
    key = "reading:question:0"
    fingerprints: list[str] = []

    result = lesson_attempts.submit_objective_answer(
        db_session,
        lesson=lesson,
        owner=owner,
        activity_key=key,
        selected_answer=FR_QUESTIONS[0]["options"][1],
    )
    db_session.commit()
    row = db_session.get(LessonActivityAttempt, result["attempt_id"])
    fingerprints.append(question_fingerprint(row.question_snapshot_json))

    for _ in range(3):
        if not result["retry"]["available"]:
            break
        prompt = result["retry"]["activity"]["prompt"]
        options = result["retry"]["activity"]["options"]
        correct = next(q["answer"] for q in FR_QUESTIONS if q["prompt"] == prompt)
        wrong = next(o for o in options if o != correct)
        result = lesson_attempts.submit_objective_answer(
            db_session,
            lesson=lesson,
            owner=owner,
            activity_key=key,
            selected_answer=wrong,
            request_retry=True,
        )
        db_session.commit()
        row = db_session.get(LessonActivityAttempt, result["attempt_id"])
        fingerprints.append(question_fingerprint(row.question_snapshot_json))

    assert len(fingerprints) == len(set(fingerprints))
    assert len(fingerprints) >= 2
    # Com 3 questões, o 3º erro esgota variantes.
    assert result["retry"]["available"] is False or len(fingerprints) == 3


def test_shuffle_not_new_question(db_session):
    admin = _admin(db_session)
    q = dict(FR_QUESTIONS[0])
    shuffled = {
        **q,
        "options": list(reversed(q["options"])),
    }
    lesson = _lesson_with_questions(db_session, admin, [q, shuffled])
    owner = db_session.get(UserLanguage, lesson.user_language_id)
    first = lesson_attempts.submit_objective_answer(
        db_session,
        lesson=lesson,
        owner=owner,
        activity_key="reading:question:0",
        selected_answer=q["options"][1],
    )
    db_session.commit()
    assert first["retry"]["available"] is False
    assert first["retry"]["strategy"] == "fallback_continue"


def test_whitespace_duplicate_not_new(db_session):
    admin = _admin(db_session)
    q = FR_QUESTIONS[0]
    twin = {
        **q,
        "prompt": f"  {q['prompt']}  ",
        "options": [f" {o} " for o in q["options"]],
        "answer": f"  {q['answer']}  ",
    }
    lesson = _lesson_with_questions(db_session, admin, [q, twin])
    owner = db_session.get(UserLanguage, lesson.user_language_id)
    first = lesson_attempts.submit_objective_answer(
        db_session,
        lesson=lesson,
        owner=owner,
        activity_key="reading:question:0",
        selected_answer=q["options"][1],
    )
    db_session.commit()
    assert first["retry"]["available"] is False


def test_legacy_snapshots_intact_and_new_attempt_ids(db_session):
    admin = _admin(db_session)
    lesson = _lesson_with_questions(db_session, admin, FR_QUESTIONS[:2])
    owner = db_session.get(UserLanguage, lesson.user_language_id)
    key = "reading:question:0"
    first = lesson_attempts.submit_objective_answer(
        db_session,
        lesson=lesson,
        owner=owner,
        activity_key=key,
        selected_answer=FR_QUESTIONS[0]["options"][1],
    )
    db_session.commit()
    second = lesson_attempts.submit_objective_answer(
        db_session,
        lesson=lesson,
        owner=owner,
        activity_key=key,
        selected_answer=FR_QUESTIONS[1]["options"][1],
        request_retry=True,
    )
    db_session.commit()
    from app.models import LessonActivityAttempt

    old = db_session.get(LessonActivityAttempt, first["attempt_id"])
    assert old.question_snapshot_json["prompt"] == FR_QUESTIONS[0]["prompt"]
    assert old.is_correct is False
    assert second["attempt_id"] != first["attempt_id"]
    assert second["attempt_number"] == 2


def test_te_retry_never_same_prompt_answer_combo():
    activity = {
        "type": "multiple_choice",
        "prompt": "Pick the correct form",
        "options": ["I live in Goiânia.", "I am a student."],
        "canonical_answer": "I live in Goiânia.",
    }
    # Um só pattern → não pode devolver a mesma MCQ embaralhada.
    variant = build_retry_variant(activity, patterns=[{"canonical": "I live in Goiânia."}])
    assert variant["retry_strategy"] == "fallback_continue"
    assert variant["retry_safe"] is False
    assert not is_same_question(variant, activity)


def test_te_recontextualized_must_change_or_fallback():
    activity = {
        "type": "multiple_choice",
        "prompt": "Choose",
        "options": ["A", "B"],
        "canonical_answer": "A",
    }
    variant = build_retry_variant(
        activity,
        patterns=[{"canonical": "A"}],
        seen_fingerprints={question_fingerprint(activity)},
    )
    assert variant["retry_strategy"] == "fallback_continue"


def test_te_multi_retry_no_cycle(db_session):
    ensure_en_a1_can_001(db_session)
    ul = _owner(db_session, _admin(db_session))
    started = teaching_slice.start_slice(db_session, user_language_id=ul.id)
    session = teaching_flow.get_flow(db_session, started["flow"]["id"])

    # Avançar até MCQ
    for _ in range(12):
        activity = teaching_flow.current_activity(session) or {}
        if activity.get("type") == "multiple_choice":
            break
        teaching_slice.submit_slice_answer(
            db_session, session, student_response="__ack__"
        )
        session = teaching_flow.get_flow(db_session, session.id)
    else:
        pytest.skip("MCQ não encontrada no slice")

    activity = teaching_flow.current_activity(session) or {}
    texts = [
        o["text"] if isinstance(o, dict) else o for o in (activity.get("options") or [])
    ]
    wrong = next(t for t in texts if t != activity.get("canonical_answer"))
    seen = {question_fingerprint(activity)}

    out = teaching_slice.submit_slice_answer(db_session, session, student_response=wrong)
    rem_id = out["remediation"]["id"]
    session = teaching_flow.get_flow(db_session, session.id)

    for _ in range(5):
        session = teaching_flow.get_flow(db_session, session.id)
        if session.status != "active" or session.phase in {
            "needs_review",
            "completed",
            "abandoned",
        }:
            break
        retry_act = (session.payload_json or {}).get("retry_activity") or {}
        if retry_act.get("retry_safe") is False:
            assert retry_act.get("retry_strategy") == "fallback_continue"
            break
        fp = question_fingerprint(retry_act)
        content = fp  # já inclui conteúdo; garantir unicidade
        assert content not in seen
        seen.add(content)
        texts = [
            o["text"] if isinstance(o, dict) else o
            for o in (retry_act.get("options") or [])
        ]
        if not texts:
            break
        wrong = next(
            (t for t in texts if t != retry_act.get("canonical_answer")),
            texts[0],
        )
        try:
            out = teaching_slice.retry_slice(
                db_session,
                session,
                remediation_id=rem_id,
                student_response=wrong,
            )
        except Exception as exc:
            # Esgotamento pedagógico (needs_review) encerra retries — ok.
            if getattr(exc, "code", None) in {"flow_closed", "retry_not_available"}:
                break
            raise
        rem_id = (out.get("remediation") or {}).get("id") or rem_id
    assert len(seen) == len(set(seen))
    assert len(seen) >= 1


def test_te_retry_correct_is_error_repaired(db_session):
    ensure_en_a1_can_001(db_session)
    ul = _owner(db_session, _admin(db_session))
    started = teaching_slice.start_slice(db_session, user_language_id=ul.id)
    session = teaching_flow.get_flow(db_session, started["flow"]["id"])
    for _ in range(12):
        activity = teaching_flow.current_activity(session) or {}
        if activity.get("type") == "multiple_choice":
            break
        teaching_slice.submit_slice_answer(
            db_session, session, student_response="__ack__"
        )
        session = teaching_flow.get_flow(db_session, session.id)
    else:
        pytest.skip("MCQ não encontrada")

    activity = teaching_flow.current_activity(session) or {}
    texts = [
        o["text"] if isinstance(o, dict) else o for o in (activity.get("options") or [])
    ]
    wrong = next(t for t in texts if t != activity.get("canonical_answer"))
    first = teaching_slice.submit_slice_answer(
        db_session, session, student_response=wrong
    )
    rem_id = first["remediation"]["id"]
    session = teaching_flow.get_flow(db_session, session.id)
    retry_act = teaching_flow.current_activity(session) or {}
    if retry_act.get("retry_safe") is False or retry_act.get("type") == "recognition":
        pytest.skip("Sem variante segura para exercitar ERROR_REPAIRED")
    correct = retry_act.get("canonical_answer")
    second = teaching_slice.retry_slice(
        db_session,
        session,
        remediation_id=rem_id,
        student_response=correct,
    )
    assert second["attempt"]["result"] == AttemptResult.CORRECT
    evidences = list(
        db_session.scalars(
            select(LearningEvidence).where(
                LearningEvidence.attempt_id == second["attempt"]["id"]
            )
        )
    )
    assert evidences
    assert all(e.evidence_type == EvidenceType.ERROR_REPAIRED for e in evidences)
    assert not any(e.evidence_type == EvidenceType.CORRECT_RESPONSE for e in evidences)
