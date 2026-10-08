import pytest
from app.services import placement_engine as e

@pytest.mark.parametrize("skill", ["reading", "listening"])
def test_candidate_then_confirmation(skill):
    answers = [e.AnswerRecord(skill, band, 1) for band in ("A1", "A2", "B1", "B2")]
    data = e.skill_results(answers)[skill]
    assert data["candidate_level"] == "B2"
    assert data["estimated_level"] is None
    assert data["confirmation_required"]
    assert data["confirmation_count"] == 1
    assert data["confirmation_needed"] == 2
    assert e.build_result(answers)["overall_level"] is None
    answers.append(e.AnswerRecord(skill, "B2", 1))
    data = e.skill_results(answers)[skill]
    assert data["estimated_level"] == "B2"
    assert not data["confirmation_required"]

@pytest.mark.parametrize("skill", ["reading", "listening"])
def test_failed_confirmation_keeps_candidate_and_requires_conflict_resolution(skill):
    answers = [e.AnswerRecord(skill, band, 1) for band in ("A1", "A2", "B1", "B2")]
    answers.append(e.AnswerRecord(skill, "B2", 0))
    data = e.skill_results(answers)[skill]
    assert data["candidate_level"] == "B2"
    assert data["estimated_level"] is None
    assert data["candidate_reason"] == "conflicting_band_evidence"
    assert data["confirmation_needed"] == 3
    answers.append(e.AnswerRecord(skill, "B2", 1))
    assert e.skill_results(answers)[skill]["estimated_level"] == "B2"

@pytest.mark.parametrize("keys", [("same-passage",), ("same-audio",), ("same-family",)])
def test_shared_stimulus_cannot_confirm(keys):
    answers = [e.AnswerRecord("reading", band, 1) for band in ("A1", "A2", "B1")]
    answers += [e.AnswerRecord("reading", "B2", 1, evidence_keys=keys) for _ in range(2)]
    data = e.skill_results(answers)["reading"]
    assert data["estimated_level"] is None
    assert data["confirmation_count"] == 1
    assert data["evidence_counts"]["by_cefr"]["B2"] == 2
    assert data["independent_evidence_counts"]["by_cefr"]["B2"] == 1

@pytest.mark.parametrize("reason", ["reused", "feedback_revealed"])
def test_ineligible_item_cannot_confirm(reason):
    answers = [e.AnswerRecord("reading", band, 1) for band in ("A1", "A2", "B1", "B2")]
    answers.append(e.AnswerRecord("reading", "B2", 1, eligible=False))
    data = e.skill_results(answers)["reading"]
    assert data["estimated_level"] is None
    assert data["confirmation_count"] == 1

from sqlalchemy import select
from app.models import PlacementItem, PlacementTest, PlacementTestAnswer
from app.api import placement_tests as api


def test_selector_prioritizes_candidate_skill(db_session):
    state = e.TestState()
    state.answers = [e.AnswerRecord("reading", band, 1) for band in ("A1", "A2", "B1", "B2")]
    selected = api._pick_objective_item(db_session, "en", state, set())
    assert selected.skill == "reading"
    assert selected.cefr_level == "B2"


def test_candidate_planning_trace_preserves_measured_fields():
    from app.services.placement_planning import planning_decision
    answers = [e.AnswerRecord(skill, band, 1) for skill in ("reading", "listening")
               for band in ("A1", "A2", "B1", "B2")]
    result = e.build_result(answers)
    planning = planning_decision(result)
    assert planning["planning_level"] == "A1"
    assert all(x["candidate_influenced_planning"] for x in planning["planning_level_trace"]["signals"])
    assert result["overall_level"] is None
    assert all(x["estimated_level"] is None for x in result["skills"].values())


@pytest.mark.parametrize("field", ["passage", "audio_script", "stimulus_family_key"])
def test_api_records_exclude_shared_stimulus(db_session, field):
    from app.models import User
    user = db_session.scalar(select(User))
    test = PlacementTest(user_id=user.id, language_code="en", status="in_progress", current_level_band="A2")
    db_session.add(test); db_session.flush()
    rows = []
    for i, band in enumerate(("A1", "A2", "B1", "B2", "B2")):
        item = PlacementItem(external_key=f"confirmation-test-{field}-{i}", language_code="en", cefr_level=band, skill="reading", item_type="reading_comprehension",
            prompt=f"Question {i}", options_json=["yes", "no"], correct_answer_json={"value":"yes"},
            review_status="approved", is_active=True, passage=f"Unique passage {i}")
        if i >= 3:
            if field == "stimulus_family_key":
                item.rubric_json = {field: "shared-family"}
            else:
                setattr(item, field, "shared stimulus")
        db_session.add(item); db_session.flush()
        row = PlacementTestAnswer(test_id=test.id, item_id=item.id, skill="reading", cefr_level=band,
            normalized_score=1, feedback_json={})
        db_session.add(row); rows.append(row)
    db_session.flush()
    data = e.skill_results(api._records(rows))["reading"]
    assert data["confirmation_count"] == 1
    assert data["estimated_level"] is None


def test_stimulus_bridge_collapses_connected_groups():
    rows = [e.AnswerRecord("reading", "B2", 1, evidence_keys=("passage:a",)),
            e.AnswerRecord("reading", "B2", 1, evidence_keys=("family:b",)),
            e.AnswerRecord("reading", "B2", 1, evidence_keys=("passage:a", "family:b"))]
    assert len(e.independent_answers(rows)) == 1

@pytest.mark.parametrize("code", ["en", "es-ES", "fr", "it", "de", "ja", "zh-CN", "la"])
def test_catalog_floor_for_every_testable_reading_listening_band(db_session, code):
    from app.services.placement_coverage import catalog_matrix
    rows = catalog_matrix(db_session.scalars(select(PlacementItem).where(PlacementItem.language_code == code)))
    for skill in ("reading", "listening"):
        for band in e.TESTABLE_LEVELS:
            cell = next(x for x in rows if x["skill"] == skill and x["cefr"] == band)
            assert cell["fresh_independent_stimulus_groups"] >= 2


def test_selector_uses_adjacent_band_before_another_skill(db_session):
    state = e.TestState()
    state.answers = [e.AnswerRecord("reading", band, 1) for band in ("A1", "A2", "B1", "B2")]
    ids = set(db_session.scalars(select(PlacementItem.id).where(PlacementItem.language_code == "en",
        PlacementItem.skill == "reading", PlacementItem.cefr_level == "B2")))
    selected = api._pick_objective_item(db_session, "en", state, ids)
    assert selected.skill == "reading"
    assert selected.cefr_level == "B1"


def test_cannot_stop_with_useful_unconfirmed_higher_candidate():
    state = e.TestState()
    for skill in e.OBJECTIVE_SKILLS:
        state.answers += [e.AnswerRecord(skill, "A2", 1) for _ in range(4)]
    state.answers.append(e.AnswerRecord("reading", "B2", 1))
    assert not e.should_stop(state)


def test_catalogue_seed_is_idempotent(db_session):
    from app.services.placement_seed import seed_placement_items
    before = [(x.id, x.external_key, x.version) for x in db_session.scalars(select(PlacementItem))]
    seed_placement_items(db_session); db_session.flush()
    after = [(x.id, x.external_key, x.version) for x in db_session.scalars(select(PlacementItem))]
    assert before == after


def test_bank_exhaustion_preserves_candidate_partial_and_trace(client, auth, db_session):
    from tests.test_placement_api import create_test
    from app.services.placement_delivery import deliver_item
    test_id = create_test(client, auth).json()["id"]
    test = db_session.get(PlacementTest, test_id)
    # Replay the real four-band evidence without changing production or weakening policy.
    for band in ("A1", "A2", "B1", "B2"):
        item = db_session.scalar(select(PlacementItem).where(PlacementItem.language_code == "en",
            PlacementItem.skill == "reading", PlacementItem.cefr_level == band,
            ~PlacementItem.external_key.contains("confirmation")))
        deliver_item(db_session, test, item); db_session.commit()
        response = client.post(f"/api/v1/placement-tests/{test_id}/answers", headers=auth,
            json={"item_id": item.id, "answer": item.correct_answer_json["value"]})
        assert response.status_code == 200
    for item in db_session.scalars(select(PlacementItem).where(PlacementItem.language_code == "en")):
        item.is_active = False
    db_session.commit()
    response = client.post(f"/api/v1/placement-tests/{test_id}/next-item", headers=auth)
    assert response.status_code == 200
    assert response.json()["progress"]["stop_reason"] == "bank_exhausted"
    result = client.post(f"/api/v1/placement-tests/{test_id}/complete", headers=auth).json()
    reading = next(x for x in result["skills"] if x["skill"] == "reading")
    assert reading["candidate_level"] == "B2"
    assert reading["estimated_level"] is None
    assert result["profile_status"] == "partial"
    assert result["stop_detail"] == "confirmation_bank_exhausted"
    assert result["overall_level"] is None


def test_selector_persists_confirmation_reason(client, auth, db_session):
    from tests.test_placement_api import create_test
    test_id = create_test(client, auth).json()["id"]
    state = e.TestState()
    state.answers = [e.AnswerRecord("reading", band, 1) for band in ("A1", "A2", "B1", "B2")]
    item = api._pick_objective_item(db_session, "en", state, set(), test_id=test_id)
    db_session.flush()
    trace = db_session.get(PlacementTest, test_id).result_json["selection_trace"][-1]
    assert trace["item_id"] == item.id
    assert trace["phase"] == "confirmation"
    assert trace["reason"] == "candidate_band_confirmation"


def test_authoring_policy_has_target_stimulus_and_native_instructions():
    from app.services.placement_seed import available_languages, load_fixture
    for code in available_languages():
        for item in load_fixture(code)["items"]:
            if "-confirmation-" not in item["external_key"]:
                continue
            assert item["rubric"]["native_language"] == "pt-BR"
            assert item["rubric"]["target_language"] == code
            assert item.get("passage") or item.get("audio_script")
            assert item["correct_answer"]["value"] in item["options"]
            assert item["prompt"] not in (item.get("passage"), item.get("audio_script"))


def test_selector_uses_immutable_within_session_stimulus(db_session):
    from app.models import User
    from app.services.placement_delivery import deliver_item
    original = db_session.scalar(select(PlacementItem).where(PlacementItem.language_code == "en",
        PlacementItem.skill == "reading", PlacementItem.cefr_level == "B2"))
    user = db_session.scalar(select(User))
    test = PlacementTest(user_id=user.id, language_code="en")
    db_session.add(test); db_session.flush()
    deliver_item(db_session, test, original)
    clone = PlacementItem(external_key="aaa-snapshot-clone", language_code="en", skill="reading", cefr_level="B2",
        item_type="reading_comprehension", prompt="different question", passage=original.passage,
        options_json=["different", "options"], review_status="approved", is_active=True)
    db_session.add(clone)
    original.passage = "Changed after answering"
    db_session.flush()
    state = e.TestState()
    state.answers = [e.AnswerRecord("reading", band, 1) for band in ("A1", "A2", "B1", "B2")]
    selected = api._pick_objective_item(db_session, "en", state, {original.id}, user_id=user.id, test_id=test.id)
    assert selected.id != clone.id


def test_new_static_support_is_not_served_as_third_language(db_session):
    from app.models import User
    user = db_session.scalar(select(User))
    user.native_language = "en"
    for item in db_session.scalars(select(PlacementItem).where(PlacementItem.language_code == "fr")):
        if "-confirmation-" not in item.external_key:
            item.is_active = False
    db_session.flush()
    assert api._pick_objective_item(db_session, "fr", e.TestState(), set(), user_id=user.id) is None


def test_raw_hard_cap_has_correct_reason_and_keeps_candidate(client, auth, db_session):
    from tests.test_placement_api import create_test
    test_id = create_test(client, auth).json()["id"]
    items = list(db_session.scalars(select(PlacementItem).where(PlacementItem.language_code == "en",
        PlacementItem.skill.in_(e.OBJECTIVE_SKILLS))))
    # Only one item is eligible, but all raw responses consume session budget.
    for i,item in enumerate(items):
        db_session.add(PlacementTestAnswer(test_id=test_id,item_id=item.id,skill=item.skill,cefr_level=item.cefr_level,
            normalized_score=1,feedback_json={"exposure":{"reused":i>0}}))
    # Add enough excluded observations to reach the hard cap.
    for i in range(e.MAX_OBJECTIVE_ITEMS-len(items)):
        item=PlacementItem(external_key=f"budget-test-{i}",language_code="en",skill="reading",cefr_level="B2",
            item_type="reading_comprehension",prompt=f"budget {i}",review_status="approved",is_active=True)
        db_session.add(item); db_session.flush()
        db_session.add(PlacementTestAnswer(test_id=test_id,item_id=item.id,skill="reading",cefr_level="B2",
            normalized_score=1,feedback_json={"exposure":{"reused":True}}))
    db_session.commit()
    response=client.post(f"/api/v1/placement-tests/{test_id}/next-item",headers=auth)
    assert response.json()["progress"]["stop_reason"] == "maximum_reached"
    stored=db_session.get(PlacementTest,test_id)
    db_session.refresh(stored)
    assert stored.result_json["confirmation_deficits"]


@pytest.mark.parametrize("skill", ["reading", "listening"])
@pytest.mark.parametrize("correct", [True, False])
def test_http_confirmation_contract_and_profile_boundary(client, auth, db_session, skill, correct):
    from tests.test_placement_api import create_test
    from app.services.placement_delivery import deliver_item
    from app.models import UserLanguage
    test_id = create_test(client, auth).json()["id"]
    test = db_session.get(PlacementTest, test_id)
    for band in ("A1", "A2", "B1", "B2"):
        item = db_session.scalar(select(PlacementItem).where(PlacementItem.language_code == "en",
            PlacementItem.skill == skill, PlacementItem.cefr_level == band,
            ~PlacementItem.external_key.contains("confirmation")))
        deliver_item(db_session, test, item); db_session.commit()
        assert client.post(f"/api/v1/placement-tests/{test_id}/answers", headers=auth,
            json={"item_id":item.id,"answer":item.correct_answer_json["value"]}).status_code == 200
    selected = client.post(f"/api/v1/placement-tests/{test_id}/next-item", headers=auth).json()
    assert selected["item"]["skill"] == skill
    assert db_session.get(PlacementItem, selected["item"]["id"]).cefr_level == "B2"
    assert selected["progress"]["selection"]["phase"] == "confirmation"
    item = db_session.get(PlacementItem, selected["item"]["id"])
    assert client.post(f"/api/v1/placement-tests/{test_id}/answers", headers=auth,
        json={"item_id":item.id,"answer":item.correct_answer_json["value"] if correct else "wrong"}).status_code == 200
    result = client.post(f"/api/v1/placement-tests/{test_id}/complete", headers=auth).json()
    data = next(x for x in result["skills"] if x["skill"] == skill)
    assert data["candidate_level"] == "B2"
    assert data["estimated_level"] == ("B2" if correct else None)
    assert data["confirmation_required"] == (not correct)
    assert result["overall_level"] is None
    assert db_session.scalar(select(UserLanguage)).current_level is None
    assert client.get(f"/api/v1/placement-tests/{test_id}/result",headers=auth).json() == result


def test_native_change_blocks_resume_and_submission_of_declared_support(client, auth, db_session):
    from tests.test_placement_api import create_test
    from app.models import User
    for item in db_session.scalars(select(PlacementItem).where(PlacementItem.language_code == "fr")):
        if "-confirmation-" not in item.external_key:
            item.is_active = False
    db_session.commit()
    test_id = create_test(client, auth, language="fr").json()["id"]
    payload = client.post(f"/api/v1/placement-tests/{test_id}/next-item",headers=auth).json()
    db_session.scalar(select(User)).native_language="en"
    db_session.commit()
    response=client.post(f"/api/v1/placement-tests/{test_id}/next-item",headers=auth)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "native_support_unavailable"
    item=db_session.get(PlacementItem,payload["item"]["id"])
    submitted=client.post(f"/api/v1/placement-tests/{test_id}/answers",headers=auth,
        json={"item_id":item.id,"answer":item.correct_answer_json["value"]})
    assert submitted.status_code == 409
    assert not list(db_session.scalars(select(PlacementTestAnswer).where(PlacementTestAnswer.test_id==test_id)))


def test_forms_cannot_treat_shared_passages_with_different_families_as_independent(db_session):
    from app.models import User
    from app.services.placement_exposure import rotation_metadata
    user = db_session.scalar(select(User))
    for i,item in enumerate(db_session.scalars(select(PlacementItem).where(PlacementItem.language_code == "en"))):
        item.rubric_json={**(item.rubric_json or {}),"form_id":"A"}
        if item.skill == "reading":
            item.passage="shared form stimulus"
            item.rubric_json={**item.rubric_json,"stimulus_family_key":f"fake independent family {i}"}
    db_session.flush()
    assert rotation_metadata(db_session,user.id,"en")["selected_form"] is None


def test_raw_by_cefr_and_independent_by_cefr_do_not_confuse_reused_evidence():
    from app.services.placement_exposure import adjust_result
    answer=PlacementTestAnswer(skill="reading",cefr_level="B2",normalized_score=1,
        feedback_json={"exposure":{"reused":True}})
    result=e.build_result([])
    adjust_result(result,[answer])
    data=result["skills"]["reading"]
    assert data["evidence_counts"]["by_cefr"] == {"B2":1}
    assert data["independent_evidence_counts"]["by_cefr"] == {}
    assert data["candidate_level"] is None
