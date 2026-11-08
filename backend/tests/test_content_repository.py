"""Repositório de conteúdo — apenas unidades aprovadas."""

from sqlalchemy import select

from app.core.content_policy import ValidationStatus
from app.models import ContentSource, ContentUnit, Language, Lesson, LessonContentUsage, User, UserLanguage
from app.services.content_repository import (
    fetch_approved_unit,
    practiced_content_unit_ids,
    public_unit_or_none,
)


def _seed(db, *, unit_status=ValidationStatus.APPROVED, source_status=ValidationStatus.APPROVED):
    lang = db.scalar(select(Language).where(Language.code == "en"))
    source = ContentSource(
        title="Fonte teste",
        language_id=lang.id,
        review_status=source_status,
        usage_policy="OPEN_LICENSE",
    )
    db.add(source)
    db.flush()
    # mode "guided" não faz parte do seed starter — evita falso positivo.
    unit = ContentUnit(
        source_id=source.id,
        language_id=lang.id,
        cefr_level="A2",
        skill="vocabulary_grammar",
        mode="guided",
        title="Unidade guiada de teste",
        payload_json={"text": "Hello world", "internal_notes": "privado"},
        validation_status=unit_status,
        is_active=True,
    )
    db.add(unit)
    db.flush()
    return unit


def test_fetch_approved_unit(db_session):
    unit = _seed(db_session)
    db_session.commit()
    found = fetch_approved_unit(
        db_session,
        language_id=unit.language_id,
        level="A2",
        skill="vocabulary_grammar",
        mode="guided",
    )
    assert found is not None
    assert found.id == unit.id
    public = public_unit_or_none(found)
    assert public is not None
    assert "internal_notes" not in public["payload"]


def test_pending_blocked(db_session):
    unit = _seed(db_session, unit_status=ValidationStatus.PENDING_REVIEW)
    db_session.commit()
    found = fetch_approved_unit(
        db_session,
        language_id=unit.language_id,
        level="A2",
        skill="vocabulary_grammar",
        mode="guided",
    )
    assert found is None


def test_rejected_source_blocked(db_session):
    unit = _seed(db_session, source_status=ValidationStatus.REJECTED)
    db_session.commit()
    found = fetch_approved_unit(
        db_session,
        language_id=unit.language_id,
        level="A2",
        skill="vocabulary_grammar",
        mode="guided",
    )
    assert found is None


def test_practiced_units_are_excluded_from_the_next_selection(db_session):
    first = _seed(db_session)
    second = ContentUnit(
        source_id=first.source_id,
        language_id=first.language_id,
        cefr_level="A2",
        skill="vocabulary_grammar",
        mode="guided",
        title="Segunda unidade guiada",
        payload_json={"text": "Another approved unit"},
        validation_status=ValidationStatus.APPROVED,
        is_active=True,
    )
    db_session.add(second)
    db_session.flush()
    user = User(email="selection-scope@befluent.local", password_hash="x", name="Seleção")
    other = User(email="selection-other@befluent.local", password_hash="x", name="Outro")
    db_session.add_all([user, other])
    db_session.flush()
    profile = UserLanguage(user_id=user.id, language_id=first.language_id, is_active=True)
    other_profile = UserLanguage(user_id=other.id, language_id=first.language_id, is_active=True)
    db_session.add_all([profile, other_profile])
    db_session.flush()
    lesson = Lesson(
        user_language_id=profile.id,
        title="Já feita",
        objective="objetivo",
        content_json={},
        status="active",
    )
    db_session.add(lesson)
    db_session.flush()
    db_session.add(LessonContentUsage(lesson_id=lesson.id, content_unit_id=first.id))
    db_session.commit()

    excluded = practiced_content_unit_ids(db_session, profile.id)
    found = fetch_approved_unit(
        db_session,
        language_id=first.language_id,
        level="A2",
        skill="vocabulary_grammar",
        mode="guided",
        exclude_ids=excluded,
    )
    assert first.id in excluded
    assert found is not None
    assert found.id == second.id
    assert practiced_content_unit_ids(db_session, other_profile.id) == set()


def test_exhausted_curated_pool_is_explicit_and_not_persisted(client, auth, db_session):
    from app.core.levels import CEFRLevel, LevelSource

    unit = _seed(db_session)
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    profile = UserLanguage(
        user_id=user.id,
        language_id=unit.language_id,
        current_level=CEFRLevel.A2,
        level_source=LevelSource.PLACEMENT_TEST,
        assessment_summary_json={"global_estimate_status": "sufficient"},
        is_active=True,
        onboarding_completed=True,
    )
    db_session.add(profile)
    db_session.flush()
    lesson = Lesson(
        user_language_id=profile.id,
        title="Já feita",
        objective="objetivo",
        content_json={},
        status="active",
    )
    db_session.add(lesson)
    db_session.flush()
    db_session.add(LessonContentUsage(lesson_id=lesson.id, content_unit_id=unit.id))
    db_session.commit()

    response = client.post(
        "/api/v1/lessons/generate",
        json={"language_code": "en", "mode": "guided", "persist": True},
        headers=auth,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["exhausted"] is True
    assert "lesson_id" not in body
    assert body["selection_trace"]["reason"] == "curated_pool_exhausted"
    assert body["selection_trace"]["exhaustion"] == "curated_pool_exhausted"
    stored = db_session.scalars(select(Lesson).where(Lesson.user_language_id == profile.id)).all()
    assert [item.id for item in stored] == [lesson.id]
