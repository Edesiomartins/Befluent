from app.services import placement_engine as engine
from sqlalchemy import select
from app.models import PlacementItem, PlacementTestAnswer, UserLanguage


def test_single_skill_never_produces_global_level():
    result = engine.build_result([
        engine.AnswerRecord("vocabulary_grammar", "B1", 1.0) for _ in range(4)
    ])
    assert result["overall_level"] is None
    assert result["weights_used"] == {}
    assert result["overall_estimate_status"] == "partial"


def test_collected_reading_keeps_score_without_deciding_band():
    result = engine.build_result([
        engine.AnswerRecord("reading", level, 1.0) for level in ("A1", "A2", "B1", "B2")
    ])
    skill = result["skills"]["reading"]
    assert skill["score"] == 4
    assert skill["max_score"] == 4
    assert skill["estimated_level"] is None
    assert skill["status"] == "insufficient_evidence"
    assert skill["evidence_counts"]["valid"] == 4


def test_fallback_correct_answers_do_not_promote_current_band():
    state = engine.TestState()
    for _ in range(3):
        engine.register_answer(state, engine.AnswerRecord("reading", "B1", 1.0))
    assert state.skill_states["reading"].current_band == "A2"


def test_stop_requires_coverage_of_each_objective_skill():
    state = engine.TestState()
    for _ in range(20):
        engine.register_answer(state, engine.AnswerRecord("vocabulary_grammar", "A2", 1.0))
    assert not engine.should_stop(state)


def test_conflicting_lower_band_does_not_emit_unconfirmed_higher_level():
    answers = [engine.AnswerRecord("reading", "A2", 0.0) for _ in range(2)]
    answers += [engine.AnswerRecord("reading", "B1", 1.0) for _ in range(2)]
    assert engine.estimate_skill_level(answers) is None


def test_partial_completion_keeps_reading_scores_and_is_idempotent(client, auth, db_session):
    from tests.test_placement_api import answer_all, create_test
    test = create_test(client, auth).json()
    answer_all(client, auth, test["id"], db_session)
    response = client.post(f'/api/v1/placement-tests/{test["id"]}/complete', headers=auth)
    assert response.status_code == 200
    result = response.json()
    assert result["overall_level"] is None
    assert result["overall_estimate_status"] == "partial"
    reading = next(s for s in result["skills"] if s["skill"] == "reading")
    assert reading["score"] == 4
    assert reading["evidence_counts"]["valid"] == 4
    assert client.post(f'/api/v1/placement-tests/{test["id"]}/complete', headers=auth).json() == result


def test_speaking_receives_server_transcribed_audio(client, auth, db_session, monkeypatch):
    from app.api import placement_tests as api
    from tests.test_placement_api import create_test
    from app.services.placement_delivery import deliver_item
    from app.models import PlacementTest
    test = create_test(client, auth).json()
    item = db_session.scalar(select(PlacementItem).where(
        PlacementItem.language_code == "en", PlacementItem.skill == "speaking"))
    assert item is not None
    deliver_item(db_session, db_session.get(PlacementTest, test["id"]), item)
    db_session.commit()
    monkeypatch.setattr(api, "transcribe_audio", lambda *args: {
        "text": "I would like to describe my daily work and explain what I enjoy about it.",
        "provider": "groq", "model": "test-stt"})
    response = client.post(f'/api/v1/placement-tests/{test["id"]}/speaking', headers=auth,
        data={"item_id": item.id}, files={"file": ("voice.webm", b"audio", "audio/webm")})
    assert response.status_code == 200
    answer = db_session.scalar(select(PlacementTestAnswer).where(
        PlacementTestAnswer.test_id == test["id"], PlacementTestAnswer.skill == "speaking"))
    assert answer.answer_json["transcript"].startswith("I would like")
    assert answer.feedback_json["provenance"]["stt_model"] == "test-stt"
    assert not answer.feedback_json["eligible_for_overall"]


def test_speaking_rejects_client_only_transcript(client, auth):
    from tests.test_placement_api import create_test
    test = create_test(client, auth).json()
    response = client.post(f'/api/v1/placement-tests/{test["id"]}/speaking', headers=auth,
                           json={"transcript": "A forged transcript"})
    assert response.status_code == 422


def test_ai_payload_nonfinite_or_boolean_is_not_a_measurement():
    from app.services.writing_evaluation import _validate_ai_payload
    for score in (True, float("nan"), float("inf")):
        assert _validate_ai_payload({"normalized_score": score, "estimated_level": "B1"}, "B1") is None


def test_partial_profile_records_latest_assessment_without_erasing_level(client, auth, db_session):
    from tests.test_placement_api import answer_all, create_test
    from app.models import User, Language
    user = db_session.scalar(select(User))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    profile = UserLanguage(user_id=user.id, language_id=language.id, current_level="A2", level_source="admin")
    db_session.add(profile); db_session.commit()
    test = create_test(client, auth).json()
    answer_all(client, auth, test["id"], db_session)
    response = client.post(f'/api/v1/placement-tests/{test["id"]}/complete', headers=auth)
    assert response.status_code == 200
    db_session.refresh(profile)
    assert profile.current_level == "A2"
    assert profile.level_source == "admin"
    assert profile.last_assessment_id == test["id"]
    assert profile.assessment_summary_json["overall_estimate_status"] == "partial"


def test_speaking_cannot_enter_objective_endpoint(client, auth, db_session):
    from tests.test_placement_api import create_test
    from app.services.placement_delivery import deliver_item
    from app.models import PlacementTest
    test = create_test(client, auth).json()
    item = db_session.scalar(select(PlacementItem).where(PlacementItem.language_code == "en", PlacementItem.skill == "speaking"))
    deliver_item(db_session, db_session.get(PlacementTest, test["id"]), item); db_session.commit()
    result = client.post(f'/api/v1/placement-tests/{test["id"]}/answers', headers=auth,
                         json={"item_id": item.id, "answer": "anything"})
    assert result.status_code == 400


def test_progress_target_is_possible_in_current_bank(client, auth):
    from tests.test_placement_api import create_test
    test = create_test(client, auth).json()
    assert test["progress"]["target"] == 16
    assert test["progress"]["bank_feasibility"] == "insufficient"


def test_duplicate_stimulus_does_not_increase_capacity_or_repeat_selection(db_session):
    from app.services.placement_coverage import bank_capacity
    from app.api.placement_tests import _pick_objective_item
    original = db_session.scalar(select(PlacementItem).where(PlacementItem.language_code == "en", PlacementItem.skill == "reading"))
    before = bank_capacity(db_session, "en")["objective_capacity"]
    clone = PlacementItem(language_code=original.language_code, skill=original.skill,
        cefr_level=original.cefr_level, item_type=original.item_type, prompt=original.prompt,
        passage=original.passage, audio_script=original.audio_script, options_json=original.options_json,
        external_key="clone", review_status="approved", is_active=True)
    db_session.add(clone); db_session.commit()
    assert bank_capacity(db_session, "en")["objective_capacity"] == before
    state = engine.TestState()
    selected = _pick_objective_item(db_session, "en", state, {original.id})
    assert selected.id != clone.id


def test_ai_writing_level_is_preserved_as_provisional(db_session):
    from app.services.placement_production import production_result
    from app.models import PlacementTestAnswer
    answer = PlacementTestAnswer(skill="writing", cefr_level="B1", normalized_score=0.96,
        evaluated_by="ai", feedback_json={"estimated_level": "B1", "criteria": {"clareza": 0.96}})
    result = production_result(answer)
    assert result["estimated_level"] == "B1"
    assert result["status"] == "provisional"
    assert not result["eligible_for_overall"]


def test_profile_partial_avoids_dashboard_retake_loop(db_session):
    from app.api.dashboard import _level_block
    profile = UserLanguage(current_level=None, level_source="pending", last_assessment_id="partial",
        assessment_summary_json={"overall_estimate_status": "partial", "skills": {}})
    assert not _level_block(profile)["needs_placement_test"]


def test_legacy_placement_level_is_not_presented_as_verified_global():
    from app.api.dashboard import _level_block
    profile = UserLanguage(current_level="B1", level_source="placement_test")
    assert _level_block(profile)["current_level"] is None
    assert _level_block(profile)["legacy_overall_level"] == "B1"


def test_partial_retest_keeps_previous_verified_global():
    from app.services.assessment_level import verified_current_level
    profile = UserLanguage(current_level="A2", level_source="placement_test",
        assessment_summary_json={"overall_estimate_status": "partial", "global_estimate_status": "sufficient"})
    assert verified_current_level(profile) == "A2"


def test_speaking_mock_cannot_produce_evidence(client, auth, db_session, monkeypatch):
    from app.api import placement_tests as api
    from tests.test_placement_api import create_test
    from app.services.placement_delivery import deliver_item
    from app.models import PlacementTest
    test = create_test(client, auth).json()
    item = db_session.scalar(select(PlacementItem).where(PlacementItem.language_code == "en", PlacementItem.skill == "speaking"))
    deliver_item(db_session, db_session.get(PlacementTest, test["id"]), item)
    db_session.commit()
    monkeypatch.setattr(api, "transcribe_audio", lambda *args: {"text": "fabricated", "provider": "mock"})
    response = client.post(f'/api/v1/placement-tests/{test["id"]}/speaking', headers=auth,
        data={"item_id": item.id}, files={"file": ("voice.webm", b"audio", "audio/webm")})
    assert response.status_code == 503
    assert not list(db_session.scalars(select(PlacementTestAnswer).where(PlacementTestAnswer.test_id == test["id"])))
    next_ = client.post(f'/api/v1/placement-tests/{test["id"]}/next-item', headers=auth)
    assert next_.json()["item"]["id"] == item.id


def test_invalid_ai_level_is_not_derived_from_task_score():
    from app.services.writing_evaluation import _validate_ai_payload
    result = _validate_ai_payload({"normalized_score": 0.96}, "B1")
    assert result["estimated_level"] is None
    assert result["level_origin"] == "unavailable"


def test_exhaustion_is_recorded_and_empty_bank_can_finish_partial(client, auth, db_session):
    from tests.test_placement_api import create_test
    items = db_session.scalars(select(PlacementItem).where(PlacementItem.language_code == "en"))
    for item in items:
        item.is_active = False
    db_session.commit()
    test = create_test(client, auth).json()
    next_ = client.post(f'/api/v1/placement-tests/{test["id"]}/next-item', headers=auth)
    assert next_.json()["stage"] == "ready_to_complete"
    response = client.post(f'/api/v1/placement-tests/{test["id"]}/complete', headers=auth)
    assert response.status_code == 200
    assert response.json()["assessment_coverage"]["stop_reason"] == "bank_exhausted"
