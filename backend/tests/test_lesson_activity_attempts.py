"""Tentativas autoritativas de lições legadas (LessonActivityAttempt)."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text

from app.core.errors import APIError
from app.models import (
    Language,
    Lesson,
    LessonActivityAttempt,
    LearningEvidence,
    User,
    UserLanguage,
)
from app.services import lesson_attempts
from app.services.answer_feedback import build_retry_variant
from app.services.lesson_bank import GRAMMAR_EXERCISES


def _lesson_with_grammar(db, user: User) -> Lesson:
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
    lesson = Lesson(
        user_language_id=ul.id,
        title="Grammar test",
        objective="Test",
        status="active",
        content_json={
            "language_code": "en",
            "mode": "grammar",
            "band": "beginner",
            "exercises": [
                {
                    "prompt": "____ is your name?",
                    "options": ["What", "Where", "Who"],
                    "answer": "What",
                    "rationale": "'What' pergunta pelo nome.",
                    "option_rationales": {
                        "Where": "'Where' pergunta por lugar.",
                        "Who": "'Who' pergunta por pessoa.",
                    },
                },
                {
                    "prompt": "____ are you from?",
                    "options": ["Where", "What", "Who"],
                    "answer": "Where",
                    "rationale": "'Where' pergunta origem/lugar.",
                    "option_rationales": {
                        "What": "Não pergunta lugar.",
                        "Who": "Não pergunta lugar.",
                    },
                },
            ],
            "questions": [
                {
                    "prompt": "Ideia principal?",
                    "options": ["Rotina", "Manual", "Diálogo"],
                    "answer": "Rotina",
                    "rationale": "Texto de rotina.",
                    "option_rationales": {
                        "Manual": "Não é manual.",
                        "Diálogo": "Não é diálogo.",
                    },
                }
            ],
        },
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@pytest.fixture
def admin(db_session):
    return db_session.scalar(select(User).where(User.email == "admin@befluent.local"))


def test_first_submit_accepted(db_session, admin):
    lesson = _lesson_with_grammar(db_session, admin)
    owner = db_session.get(UserLanguage, lesson.user_language_id)
    result = lesson_attempts.submit_objective_answer(
        db_session,
        lesson=lesson,
        owner=owner,
        activity_key="grammar:exercise:0",
        selected_answer="What",
    )
    db_session.commit()
    assert result["submitted"] is True
    assert result["correct"] is True
    assert result["attempt_number"] == 1
    assert result["pedagogical_effect"] == "correct_first_try"
    assert result["feedback"]["is_correct"] is True


def test_second_submit_rejected(db_session, admin):
    lesson = _lesson_with_grammar(db_session, admin)
    owner = db_session.get(UserLanguage, lesson.user_language_id)
    lesson_attempts.submit_objective_answer(
        db_session,
        lesson=lesson,
        owner=owner,
        activity_key="grammar:exercise:0",
        selected_answer="Where",
    )
    db_session.commit()
    with pytest.raises(APIError) as exc:
        lesson_attempts.submit_objective_answer(
            db_session,
            lesson=lesson,
            owner=owner,
            activity_key="grammar:exercise:0",
            selected_answer="What",
        )
    assert exc.value.status_code == 409
    assert exc.value.code == "attempt_already_submitted"


def test_wrong_and_correct_persisted(db_session, admin):
    lesson = _lesson_with_grammar(db_session, admin)
    owner = db_session.get(UserLanguage, lesson.user_language_id)
    wrong = lesson_attempts.submit_objective_answer(
        db_session,
        lesson=lesson,
        owner=owner,
        activity_key="grammar:exercise:0",
        selected_answer="Where",
    )
    db_session.commit()
    assert wrong["correct"] is False
    assert wrong["selected_answer"] == "Where"
    assert wrong["correct_answer"] == "What"
    assert "lugar" in (wrong["feedback"].get("why_selected") or "").lower()

    # Restore
    listed = lesson_attempts.list_attempts_for_lesson(db_session, lesson_id=lesson.id)
    assert len(listed) == 1
    assert listed[0].is_correct is False


def test_client_correct_flag_ignored(db_session, admin, client, auth):
    lesson = _lesson_with_grammar(db_session, admin)
    response = client.post(
        f"/api/v1/lessons/{lesson.id}/objective-answers",
        headers=auth,
        json={
            "activity_key": "grammar:exercise:0",
            "selected_answer": "Where",
            "correct": True,
            "is_correct": True,
            "correct_answer": "Where",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is False
    assert body["correct_answer"] == "What"


def test_restore_via_api(db_session, admin, client, auth):
    lesson = _lesson_with_grammar(db_session, admin)
    owner = db_session.get(UserLanguage, lesson.user_language_id)
    lesson_attempts.submit_objective_answer(
        db_session,
        lesson=lesson,
        owner=owner,
        activity_key="reading:question:0",
        selected_answer="Rotina",
    )
    db_session.commit()
    restored = client.get(
        f"/api/v1/lessons/{lesson.id}/objective-attempts", headers=auth
    )
    assert restored.status_code == 200
    attempts = restored.json()["attempts"]
    assert len(attempts) == 1
    assert attempts[0]["activity_key"] == "reading:question:0"
    assert attempts[0]["selected_answer"] == "Rotina"


def test_legacy_does_not_create_learning_evidence(db_session, admin):
    lesson = _lesson_with_grammar(db_session, admin)
    owner = db_session.get(UserLanguage, lesson.user_language_id)
    lesson_attempts.submit_objective_answer(
        db_session,
        lesson=lesson,
        owner=owner,
        activity_key="grammar:exercise:0",
        selected_answer="What",
    )
    db_session.commit()
    evidence = db_session.scalars(select(LearningEvidence)).all()
    assert evidence == []
    assert db_session.scalars(select(LessonActivityAttempt)).first() is not None


def test_retry_creates_new_id(db_session, admin):
    lesson = _lesson_with_grammar(db_session, admin)
    owner = db_session.get(UserLanguage, lesson.user_language_id)
    first = lesson_attempts.submit_objective_answer(
        db_session,
        lesson=lesson,
        owner=owner,
        activity_key="grammar:exercise:0",
        selected_answer="Where",
    )
    db_session.commit()
    assert first["retry"]["available"] is True
    second = lesson_attempts.submit_objective_answer(
        db_session,
        lesson=lesson,
        owner=owner,
        activity_key="grammar:exercise:0",
        selected_answer="Where",
        request_retry=True,
    )
    db_session.commit()
    assert second["attempt_id"] != first["attempt_id"]
    assert second["attempt_number"] == 2
    assert second["retry_of_id"] == first["attempt_id"]
    # Tentativa antiga intacta
    old = db_session.get(LessonActivityAttempt, first["attempt_id"])
    assert old is not None
    assert old.answer_json["selected_answer"] == "Where"
    assert old.is_correct is False


def test_retry_without_variant_safe(db_session, admin):
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    ul = db_session.scalar(
        select(UserLanguage).where(
            UserLanguage.user_id == admin.id,
            UserLanguage.language_id == language.id,
        )
    )
    if ul is None:
        ul = UserLanguage(
            user_id=admin.id,
            language_id=language.id,
            is_active=True,
            onboarding_completed=True,
        )
        db_session.add(ul)
        db_session.flush()
    lesson = Lesson(
        user_language_id=ul.id,
        title="Single",
        objective="x",
        status="active",
        content_json={
            "language_code": "zz",
            "exercises": [
                {
                    "prompt": "Only one",
                    "options": ["A", "B"],
                    "answer": "A",
                    "rationale": "A é a regra.",
                }
            ],
        },
    )
    db_session.add(lesson)
    db_session.commit()
    first = lesson_attempts.submit_objective_answer(
        db_session,
        lesson=lesson,
        owner=ul,
        activity_key="grammar:exercise:0",
        selected_answer="B",
    )
    db_session.commit()
    assert first["retry"]["available"] is False
    assert first["retry"]["strategy"] == "fallback_continue"
    with pytest.raises(APIError) as exc:
        lesson_attempts.submit_objective_answer(
            db_session,
            lesson=lesson,
            owner=ul,
            activity_key="grammar:exercise:0",
            selected_answer="A",
            request_retry=True,
        )
    assert exc.value.code == "retry_variant_unavailable"


def test_foreign_lesson_rejected(db_session, admin, other_user, client, auth):
    lesson = _lesson_with_grammar(db_session, admin)
    # Login as other user
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "outro@befluent.local", "password": "senha-segura"},
    )
    assert login.status_code == 200
    other_auth = {"X-CSRF-Token": client.cookies.get("csrf_token")}
    denied = client.post(
        f"/api/v1/lessons/{lesson.id}/objective-answers",
        headers=other_auth,
        json={
            "activity_key": "grammar:exercise:0",
            "selected_answer": "What",
        },
    )
    assert denied.status_code == 404


def test_concurrent_submits_only_one_wins(db_session, admin):
    lesson = _lesson_with_grammar(db_session, admin)
    owner = db_session.get(UserLanguage, lesson.user_language_id)

    results = []
    errors = []

    def once(answer: str):
        try:
            out = lesson_attempts.submit_objective_answer(
                db_session,
                lesson=lesson,
                owner=owner,
                activity_key="grammar:exercise:0",
                selected_answer=answer,
            )
            db_session.commit()
            results.append(out)
        except APIError as exc:
            db_session.rollback()
            errors.append(exc.code)
        except Exception:
            db_session.rollback()
            raise

    once("Where")
    once("What")
    assert len(results) == 1
    assert "attempt_already_submitted" in errors
    rows = db_session.scalars(
        select(LessonActivityAttempt).where(
            LessonActivityAttempt.lesson_id == lesson.id,
            LessonActivityAttempt.activity_key == "grammar:exercise:0",
        )
    ).all()
    assert len(rows) == 1


def test_retry_variant_without_two_patterns():
    activity = {
        "type": "multiple_choice",
        "prompt": "Pick",
        "options": ["A", "B"],
        "canonical_answer": "A",
        "correct_explanation": "A é a forma.",
    }
    variant = build_retry_variant(activity, patterns=[{"canonical": "A"}])
    assert variant.get("post_reveal") is True
    assert variant.get("retry_strategy") in {
        "recontextualized_same_skill",
        "fallback_continue",
    }
    assert variant.get("retry_safe") is not False or variant.get("type") == "recognition"


def test_grammar_bank_has_option_rationales():
    missing = []
    total = 0
    with_rationales = 0
    for lang, bands in GRAMMAR_EXERCISES.items():
        for band, items in bands.items():
            for item in items:
                total += 1
                opts = item.get("options") or []
                rats = item.get("option_rationales") or {}
                if all(o in rats and rats[o] for o in opts):
                    with_rationales += 1
                else:
                    missing.append(f"{lang}/{band}/{item.get('prompt')}")
    assert total > 0
    assert with_rationales == total, f"Sem rationales: {missing}"


def test_migration_0009_upgrade_downgrade(tmp_path: Path, monkeypatch):
    import os

    from app.core.config import get_settings

    db_path = tmp_path / "mig.db"
    url = f"sqlite:///{db_path.as_posix()}"
    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()

    command.upgrade(cfg, "0009_lesson_activity_attempts")
    eng = create_engine(url)
    with eng.connect() as conn:
        tables = {
            r[0]
            for r in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        assert "lesson_activity_attempts" in tables
    command.downgrade(cfg, "0008_teaching_engine_v2")
    with eng.connect() as conn:
        tables = {
            r[0]
            for r in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        assert "lesson_activity_attempts" not in tables
    command.upgrade(cfg, "0009_lesson_activity_attempts")
    get_settings.cache_clear()
