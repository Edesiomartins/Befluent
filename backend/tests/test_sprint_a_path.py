"""Sprint A: onboarding gera cronograma; blocos usam biblioteca curada."""

from sqlalchemy import select

from app.core.curriculum import GeneratedFrom
from app.core.levels import CEFRLevel, LevelSource
from app.models import Curriculum, CurriculumBlock, CurriculumDay, CurriculumWeek, Language, User, UserLanguage
from app.services.content_repository import fetch_approved_unit
from app.services.curriculum_generator import generate_curriculum
from app.services.progression import build_block_lesson


def test_onboarding_beginner_creates_curriculum(client, auth, db_session):
    response = client.post(
        "/api/v1/onboarding/complete",
        json={
            "language_code": "en",
            "level_choice": "beginner",
            "goal": "Conversar com confiança",
            "minutes_per_day": 20,
            "skills": ["Conversação"],
        },
        headers=auth,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["curriculum_id"]
    assert body["curriculum_day_href"]
    assert body["curriculum_day_href"].startswith("/cronograma/dia/")

    curriculum = db_session.get(Curriculum, body["curriculum_id"])
    assert curriculum is not None
    assert curriculum.status == "active"
    assert curriculum.generated_from == GeneratedFrom.ONBOARDING
    assert curriculum.entry_level == CEFRLevel.PRE_A1


def test_onboarding_take_test_does_not_create_curriculum(client, auth, db_session):
    response = client.post(
        "/api/v1/onboarding/complete",
        json={
            "language_code": "en",
            "level_choice": "take_test",
            "goal": "Viajar",
            "minutes_per_day": 20,
            "skills": ["Leitura"],
        },
        headers=auth,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["should_take_test"] is True
    assert body["curriculum_id"] is None

    count = db_session.scalar(select(Curriculum.id).limit(1))
    assert count is None


def test_starter_library_feeds_block_lesson(db_session):
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    assert language is not None

    unit = fetch_approved_unit(
        db_session,
        language_id=language.id,
        level=CEFRLevel.A2,
        skill="reading",
        mode="reading",
    )
    assert unit is not None
    assert unit.validation_status == "APPROVED"

    profile = UserLanguage(
        user_id=user.id,
        language_id=language.id,
        is_active=True,
        onboarding_completed=True,
        current_level=CEFRLevel.A2,
        level_source=LevelSource.SELF_DECLARED,
        vocabulary_grammar_level=CEFRLevel.A2,
        reading_level=CEFRLevel.A2,
        listening_level=CEFRLevel.A2,
        writing_level=CEFRLevel.A2,
        speaking_level=CEFRLevel.A2,
    )
    db_session.add(profile)
    db_session.flush()
    curriculum = generate_curriculum(db_session, profile.id, 90, generated_from=GeneratedFrom.MANUAL)
    day = db_session.scalar(
        select(CurriculumDay)
        .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
        .where(CurriculumWeek.curriculum_id == curriculum.id)
        .order_by(CurriculumDay.day_number)
    )
    assert day is not None
    reading = db_session.scalar(
        select(CurriculumBlock).where(
            CurriculumBlock.day_id == day.id,
            CurriculumBlock.skill == "reading",
        )
    )
    # Domingo leve pode não ter reading no dia 1 — pega qualquer bloco não-review.
    block = reading or db_session.scalar(
        select(CurriculumBlock)
        .where(
            CurriculumBlock.day_id == day.id,
            CurriculumBlock.skill != "review",
        )
        .order_by(CurriculumBlock.position)
    )
    assert block is not None
    payload = build_block_lesson(db_session, user=user, block=block, day=day)
    assert payload.get("content_origin") == "curated_library"
    assert payload.get("provider") == "curated_library"


def test_dashboard_next_activity_is_curriculum_after_onboarding(client, auth):
    client.post(
        "/api/v1/onboarding/complete",
        json={
            "language_code": "en",
            "level_choice": "self_declared",
            "cefr_level": "A2",
            "goal": "Trabalho e carreira",
            "minutes_per_day": 30,
            "skills": ["Vocabulário", "Gramática"],
        },
        headers=auth,
    )
    dash = client.get("/api/v1/dashboard", headers=auth)
    assert dash.status_code == 200
    next_activity = dash.json()["next_activity"]
    assert next_activity["kind"] == "curriculum"
    assert next_activity["href"].startswith("/cronograma/dia/")
