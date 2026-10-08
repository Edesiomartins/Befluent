from copy import deepcopy
from datetime import datetime, timezone
import pytest
from sqlalchemy import event, select
from app.models import Language, PlacementItem, PlacementTest, PlacementTestAnswer, User, UserLanguage
from tests.test_placement_planning import french_partial


def legacy_test(db, *, schema=2, planning=None, qualified=False):
    user = db.scalar(select(User))
    language = db.scalar(select(Language).where(Language.code == "fr"))
    profile = UserLanguage(user_id=user.id, language_id=language.id, planning_level=planning,
        planning_level_source="sufficient_overall" if qualified else "partial_evidence",
        current_level="B2" if qualified else None, level_source="placement_test" if qualified else "pending",
        assessment_summary_json={"global_estimate_status": "sufficient"} if qualified else {})
    db.add(profile)
    result = french_partial()
    result.update(result_schema_version=schema, confidence_score=None, items_answered=16)
    test = PlacementTest(user_id=user.id, language_code="fr", status="completed", overall_level="B1",
        completed_at=datetime.now(timezone.utc), result_json=result)
    db.add(test); db.commit()
    if schema == 1:
        for item in db.scalars(select(PlacementItem).where(PlacementItem.language_code == "fr",
                PlacementItem.skill.in_(["reading", "listening"]))):
            db.add(PlacementTestAnswer(test_id=test.id, item_id=item.id, skill=item.skill,
                cefr_level=item.cefr_level, raw_score=1, normalized_score=1, is_correct=True, evaluated_by="automatic"))
        db.commit()
    return test, profile


@pytest.mark.parametrize("schema", [1, 2])
def test_missing_planning_is_unknown_not_reconstructed_as_applied(client, auth, db_session, schema):
    test, _ = legacy_test(db_session, schema=schema)
    response = client.get(f'/api/v1/placement-tests/{test.id}/result', headers=auth)
    assert response.status_code == 200
    data = response.json()
    assert data["planning_level"] is None
    assert data["planning_level_source"] == "legacy_planning_unknown"
    assert data["assessment_proposed_level"] in {"PRE_A1", "A1"}
    assert data["overall_level"] is None


@pytest.mark.parametrize("qualified", [False, True])
@pytest.mark.parametrize("schema", [1, 2])
def test_legacy_uses_current_applied_profile_with_provenance(client, auth, db_session, qualified, schema):
    test, profile = legacy_test(db_session, planning="B2", qualified=qualified, schema=schema)
    response = client.get(f'/api/v1/placement-tests/{test.id}/result', headers=auth)
    data = response.json()
    assert response.status_code == 200
    assert data["planning_level"] == "B2"
    assert data["planning_level_source"] == "legacy_current_profile"
    assert data["assessment_proposed_level"] == "A1"
    assert data["planning_level_trace"]["assessment_proposed_level"] == "A1"
    assert data["planning_level_trace"]["action"] == "retained_prior_planning"
    assert data["planning_level_trace"]["historical_application_known"] is False
    assert data["planning_level_trace"]["profile_id"] == profile.id
    assert data["overall_level"] is None
    fallback = client.get('/api/v1/language-profiles/fr', headers=auth)
    assert fallback.status_code == 200
    assert fallback.json()["planning_level"] == data["planning_level"]
    if qualified:
        assert fallback.json()["current_level"] == "B2"


def test_qualified_global_without_applied_planning_is_not_invented(client, auth, db_session):
    test, _ = legacy_test(db_session, qualified=True)
    data = client.get(f'/api/v1/placement-tests/{test.id}/result', headers=auth).json()
    assert data["planning_level"] is None
    assert data["planning_level_source"] == "legacy_planning_unknown"
    assert data["overall_level"] is None


@pytest.mark.parametrize("schema", [1, 2])
def test_get_is_read_only_and_deterministic(client, auth, db_session, schema):
    test, profile = legacy_test(db_session, planning="B2", qualified=True, schema=schema)
    before = (deepcopy(test.result_json), profile.planning_level, deepcopy(profile.assessment_summary_json))
    writes = []
    def detect(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().split()[0].upper() in {"INSERT", "UPDATE", "DELETE"}:
            writes.append(statement)
    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", detect)
    try:
        first = client.get(f'/api/v1/placement-tests/{test.id}/result', headers=auth)
        second = client.get(f'/api/v1/placement-tests/{test.id}/result', headers=auth)
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()
        assert writes == []
    finally:
        event.remove(engine, "before_cursor_execute", detect)
    db_session.refresh(test); db_session.refresh(profile)
    assert (test.result_json, profile.planning_level, profile.assessment_summary_json) == before


def test_persisted_v2_planning_is_not_replaced_by_current_profile(client, auth, db_session):
    test, _ = legacy_test(db_session, planning="B2", qualified=True)
    snapshot = {"planning_level": "A1", "planning_level_source": "partial_evidence",
        "planning_level_reason": "Persisted decision", "planning_level_trace": {"policy_version": "historical", "assessment_proposed_level": "A1"}}
    test.result_json = {**test.result_json, **snapshot}
    db_session.commit()
    data = client.get(f'/api/v1/placement-tests/{test.id}/result', headers=auth).json()
    for key, value in snapshot.items():
        assert data[key] == value


def test_no_profile_leaves_applied_planning_unknown(client, auth, db_session):
    test, profile = legacy_test(db_session)
    db_session.delete(profile); db_session.commit()
    response = client.get(f'/api/v1/placement-tests/{test.id}/result', headers=auth)
    assert response.status_code == 200
    data = response.json()
    assert data["planning_level"] is None
    assert data["planning_level_source"] == "legacy_planning_unknown"
    assert data["assessment_proposed_level"] == "A1"
