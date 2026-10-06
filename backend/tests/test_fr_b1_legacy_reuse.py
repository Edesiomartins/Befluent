from copy import deepcopy
from datetime import date

import pytest
from sqlalchemy import select
from app.core.errors import APIError
from app.models import (
    Curriculum, CurriculumBlock, CurriculumDay, CurriculumWeek, Language, Lesson,
    LessonActivityAttempt, StudySession, User, UserLanguage,
)
from app.services.language_policy import ensure_stored_content_language
from tests.test_fr_b1_incident_diagnostic import TITLE, EXPLANATION

CONFIRMED_ID = "f2ab192f-36ef-42d0-b7aa-1038c8d230d2"
MODEL = "nvidia/nemotron-3.5-lightning"
TOPIC = "Opinião e justificativa — estruturas-chave"


def legacy_payload():
    # PostgreSQL ->> NULL does not distinguish missing from JSON null.
    return {"mode":"grammar", "target_language":"fr", "level":"B1",
            "provider":"openrouter", "content_origin":"openrouter", "model":MODEL,
            "title":TITLE, "explanation":EXPLANATION, "examples":[], "exercises":[]}


def french_payload():
    return {"mode":"grammar", "title":"Structurer une opinion et sa justification",
            "explanation":"On donne son avis avec « je pense que ». On ajoute une raison avec « parce que » et un résultat avec « donc ».",
            "explanation_native":"Apresente a opinião, depois o motivo e a consequência.",
            "examples":[{"sentence":"Je pense que ce projet est utile parce qu'il aide les élèves."}],
            "exercises":[], "level":"B1"}


@pytest.fixture
def confirmed_lesson(db_session):
    user = db_session.scalar(select(User))
    language = db_session.scalar(select(Language).where(Language.code == "fr"))
    owner = UserLanguage(user_id=user.id, language_id=language.id, current_level="B1",
                         vocabulary_grammar_level="B1", onboarding_completed=True)
    db_session.add(owner); db_session.flush()
    curriculum = Curriculum(user_language_id=owner.id, start_date=date(2026,10,6),
                            entry_level="B1", target_level="B2")
    db_session.add(curriculum); db_session.flush()
    week = CurriculumWeek(curriculum_id=curriculum.id, week_number=1,
                          theme="Opinião e justificativa", cefr_focus="B1")
    db_session.add(week); db_session.flush()
    day = CurriculumDay(week_id=week.id,day_number=1,scheduled_date=date(2026,10,6))
    session = StudySession(user_language_id=owner.id)
    db_session.add_all([day,session]); db_session.flush()
    lesson = Lesson(id=CONFIRMED_ID, user_language_id=owner.id, study_session_id=session.id,
                    title=TITLE, objective=TOPIC, content_json=legacy_payload(), status="active")
    db_session.add(lesson); db_session.flush()
    block = CurriculumBlock(day_id=day.id,skill="grammar",position=1,cefr_level="B1",
                            topic=TOPIC,lesson_ref=lesson.id,status="pending")
    answer = LessonActivityAttempt(lesson_id=lesson.id,user_language_id=owner.id,
                                  activity_key="exercise:0",answer_json={"response":"Parce que"})
    db_session.add_all([block,answer]); db_session.commit()
    return user, owner, curriculum, day, block, lesson, answer


@pytest.mark.parametrize("native_value", ["missing", None])
def test_legacy_openrouter_without_native_snapshot_is_not_certified(native_value):
    payload = {**french_payload(), "target_language":"fr", "provider":"openrouter"}
    if native_value != "missing":
        payload["native_language"] = native_value
    before = deepcopy(payload)
    with pytest.raises(APIError):
        ensure_stored_content_language(payload,"pt-BR")
    assert payload == before


def test_legacy_curated_pt_support_remains_compatible_without_relabelling():
    payload = {"target_language":"fr", "provider":"curated_library", "title":"Exprimer son avis",
               "explanation":"Apresente sua opinião e explique o motivo.", "support_language":"pt-BR"}
    before = deepcopy(payload)
    ensure_stored_content_language(payload,"pt-BR")
    assert payload == before and "native_language" not in payload


@pytest.mark.parametrize("mode, allowed", [("review",True),("grammar",False)])
def test_only_declared_internal_srs_queue_has_static_legacy_compatibility(mode,allowed):
    payload = {"provider":"srs","mode":mode,"source":"srs_queue","language_code":"fr","items":[]}
    if allowed:
        ensure_stored_content_language(payload,"pt-BR")
    else:
        with pytest.raises(APIError):
            ensure_stored_content_language(payload,"pt-BR")


@pytest.mark.parametrize("field", ["title", "logic_title", "explanation", "explanation_native", "objective"])
def test_known_third_language_is_blocked_even_with_current_snapshot(field):
    payload = {**french_payload(), "target_language":"fr", "native_language":"pt-BR"}
    payload[field] = TITLE if field in {"title","logic_title"} else EXPLANATION
    with pytest.raises(APIError) as error:
        ensure_stored_content_language(payload,"pt-BR")
    assert error.value.code == "lesson_language_invalid"
    from app.services.editorial_validation import valid_generated_lesson
    assert not valid_generated_lesson(payload,"grammar","fr",native_language="pt-BR")


def test_malformed_target_metadata_fails_closed():
    with pytest.raises(APIError):
        ensure_stored_content_language({"target_language":{"code":"fr"}, "native_language":"pt-BR"},"pt-BR")


def test_confirmed_old_lesson_is_not_delivered_or_mutated(client,auth,db_session,confirmed_lesson):
    user, owner, curriculum, day, block, lesson, answer = confirmed_lesson
    original = deepcopy(lesson.content_json)
    response = client.post(f"/api/v1/curriculum/block/{block.id}/start",headers=auth)
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "lesson_language_invalid"
    assert client.get(f"/api/v1/lessons/{lesson.id}").status_code == 409
    db_session.expire_all()
    assert lesson.content_json == original and lesson.status == "active"
    assert block.lesson_ref == lesson.id and block.status == "pending"
    assert curriculum.status == "active" and owner.current_level == "B1"
    assert answer.answer_json == {"response":"Parce que"}


def test_stored_title_is_checked_separately_from_json_title(client,auth,db_session,confirmed_lesson):
    *_, block, lesson, answer = confirmed_lesson
    lesson.content_json = {**french_payload(), "target_language":"fr", "native_language":"pt-BR"}
    db_session.commit()
    assert client.get(f"/api/v1/lessons/{lesson.id}").status_code == 409
    assert client.post(f"/api/v1/curriculum/block/{block.id}/start",headers=auth).status_code == 409


def test_new_openrouter_generation_rejects_incident_and_keeps_fr_pt(monkeypatch):
    from app.core.config import get_settings
    from app.services.ai import OpenRouterProvider
    from app.services.learner_context import LearnerContext
    monkeypatch.setattr(get_settings(),"openrouter_api_key","test-key")
    monkeypatch.setattr(get_settings(),"openrouter_model",MODEL)
    def generate(settings,messages,validator,**kwargs):
        assert not validator(legacy_payload())
        valid = french_payload()
        assert validator(valid)
        return valid, MODEL
    monkeypatch.setattr("app.services.ai.openrouter_chat_with_fallback",generate)
    context = LearnerContext("fr","Francês","Français","B1","B1","desc","self_declared",False,native_language="pt-BR")
    payload = OpenRouterProvider().generate_lesson("grammar",context)
    assert payload["target_language"] == "fr" and payload["native_language"] == "pt-BR"
    assert payload["explanation"] == french_payload()["explanation"]
    assert payload["explanation_native"] == french_payload()["explanation_native"]
    assert TITLE not in str(payload) and "Logic: In French" not in str(payload)
