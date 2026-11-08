"""O diagnóstico aponta objetivo misto e não grava."""

from sqlalchemy import select

from app.core.levels import CEFRLevel, LevelSource
from app.models import Language, Lesson, User, UserLanguage
from scripts.diagnose_mixed_objectives import assert_safe_database_url, diagnose

MIXED = "Praticar opinion, raison et concession em uma situação realista."


def test_dry_run_flags_a_stored_mixed_objective_without_writing(db_session):
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db_session.scalar(select(Language).where(Language.code == "fr"))
    profile = UserLanguage(
        user_id=user.id,
        language_id=language.id,
        current_level=CEFRLevel.B1,
        level_source=LevelSource.PLACEMENT_TEST,
        is_active=True,
    )
    db_session.add(profile)
    db_session.flush()
    lesson = Lesson(
        user_language_id=profile.id,
        title="Conversação antiga",
        objective=MIXED,
        content_json={"objective": MIXED, "opening": "Bonjour."},
        status="active",
    )
    db_session.add(lesson)
    db_session.commit()
    lesson_id = lesson.id

    report = diagnose(db_session.connection())

    assert report["mode"] == "dry_run"
    assert report["writes"] == 0
    assert report["production"] is False
    languages = {row["language"] for row in report["static_inventory"]}
    assert {"en", "fr", "es-ES", "it", "de", "ja", "zh-CN", "la"} <= languages
    assert all(row["vocabulary"] > 0 for row in report["static_inventory"])
    mixed = report["historical_lessons"]["mixed"]
    assert any(item["lesson_id"] == lesson_id and item["reason"] == "mixed_target_span" for item in mixed)
    assert all("opinion" not in item["reason"] for item in mixed)
    db_session.expire_all()
    stored = db_session.get(Lesson, lesson_id)
    assert stored.objective == MIXED
    assert stored.content_json["objective"] == MIXED
    assert stored.status == "active"


def test_postgres_without_test_suffix_is_refused():
    try:
        assert_safe_database_url("postgresql+psycopg://localhost/fluentia")
    except ValueError as error:
        assert "_test" in str(error)
    else:
        raise AssertionError("banco sem sufixo _test deveria ser recusado")
    assert_safe_database_url("sqlite://")
    assert_safe_database_url("postgresql+psycopg://localhost/befluent_test")
