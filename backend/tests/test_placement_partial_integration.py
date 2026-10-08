"""HTTP integration audit: real local endpoints, no mocked planning/complete."""
import json
import os
from pathlib import Path

from sqlalchemy import func, select
from app.main import app
from app.models import Curriculum, Language, PlacementTest, UserLanguage
from tests.test_placement_api import answer_all, create_test

PLANNING_KEYS = ("planning_level", "planning_level_source", "planning_level_reason", "planning_level_trace")


def capture(name, responses):
    directory = os.environ.get("PLACEMENT_CAPTURE_DIR")
    if not directory:
        return
    schemas = {}
    for path, method in (("/api/v1/placement-tests/{test_id}/complete", "post"),
                         ("/api/v1/placement-tests/{test_id}/result", "get")):
        schemas[f"{method.upper()} {path}"] = app.openapi()["paths"][path][method]["responses"]["200"]["content"]["application/json"]["schema"]
    payload = {"environment": "Local TestClient; isolated SQLite; deployed API not tested",
               "openapi_response_schemas": schemas, "responses": responses}
    destination = Path(directory) / f"{name}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_new_account_partial_a1_has_result_snapshot_and_navigable_journey(client, other_user, db_session):
    from tests.test_placement_api import use_legacy_catalog
    use_legacy_catalog(db_session)
    assert db_session.scalar(select(func.count()).select_from(UserLanguage).where(UserLanguage.user_id == other_user)) == 0
    assert db_session.scalar(select(func.count()).select_from(PlacementTest).where(PlacementTest.user_id == other_user)) == 0
    login = client.post('/api/v1/auth/login', json={"email": "outro@befluent.local", "password": "senha-segura"})
    assert login.status_code == 200
    headers = {"X-CSRF-Token": client.cookies.get("csrf_token")}
    created = create_test(client, headers, language="fr")
    assert created.status_code == 200
    test_id = created.json()["id"]
    answer_all(client, headers, test_id, db_session)
    completed = client.post(f'/api/v1/placement-tests/{test_id}/complete', headers=headers)
    assert completed.status_code == 200
    result = completed.json()
    assert result["overall_level"] is None
    assert result["profile_status"] == "partial"
    assert result["planning_level"] == "A1"
    assert result["planning_level_source"] == "partial_evidence"
    assert result["planning_level_reason"]
    assert result["planning_level_trace"]["policy"]["version"] == "placement-planning-v1"
    fetched = client.get(f'/api/v1/placement-tests/{test_id}/result', headers=headers)
    assert fetched.status_code == 200
    assert fetched.json() == result
    stored = db_session.get(PlacementTest, test_id)
    for key in PLANNING_KEYS:
        assert stored.result_json[key] == result[key]
    profile = db_session.scalar(select(UserLanguage).where(UserLanguage.user_id == other_user))
    assert profile.current_level is None
    assert profile.planning_level == "A1"
    assert profile.reading_level is None
    assert profile.listening_level is None
    assert profile.diagnostic_completed is False
    curriculum = db_session.scalar(select(Curriculum).where(Curriculum.user_language_id == profile.id))
    assert curriculum.generated_from == "planning"
    assert curriculum.entry_level == "A1"
    active = client.get('/api/v1/curriculum/active?language_code=fr', headers=headers)
    assert active.status_code == 200
    assert active.json()["id"] == curriculum.id == result["curriculum"]["id"]
    assert active.json()["generated_from"] == "planning"
    today = client.get('/api/v1/curriculum/day/today?language_code=fr', headers=headers)
    assert today.status_code == 200
    first_id = today.json()["day"]["id"]
    assert today.json()["day"]["day_number"] == 1
    assert result["curriculum"]["day_href"] == f"/cronograma/dia/{first_id}"
    day = client.get(f'/api/v1/curriculum/day/{first_id}', headers=headers)
    assert day.status_code == 200
    assert day.json()["day"]["blocks_total"] > 0
    assert day.json()["day"]["blocks"][0]["locked"] is False
    repeat = client.post(f'/api/v1/placement-tests/{test_id}/complete', headers=headers)
    assert repeat.json() == result
    assert db_session.scalar(select(func.count()).select_from(Curriculum).where(Curriculum.user_language_id == profile.id)) == 1
    generated = client.post('/api/v1/curriculum', headers=headers,
        json={"language_code": "fr", "duration_days": 180})
    assert generated.status_code == 200
    assert generated.json()["generated_from"] == "planning"
    assert generated.json()["entry_level"] == "A1"
    db_session.refresh(profile)
    assert profile.diagnostic_completed is False
    assert profile.current_level is None
    assert profile.reading_level is None
    capture("new-account-partial-a1", {"complete": result, "get_result": fetched.json(),
        "active_curriculum": active.json(), "today": today.json(), "first_day": day.json(),
        "post_curriculum_180_with_partial": generated.json()})


def test_result_preserves_applied_planning_and_keeps_assessment_proposal(client, auth, db_session):
    from app.models import User
    user = db_session.scalar(select(User))
    language = db_session.scalar(select(Language).where(Language.code == "fr"))
    profile = UserLanguage(user_id=user.id, language_id=language.id, current_level="B2", level_estimate="B2",
        level_source="placement_test", planning_level="B2", planning_level_source="sufficient_overall",
        assessment_summary_json={"global_estimate_status": "sufficient"})
    db_session.add(profile); db_session.commit()
    test_id = create_test(client, auth, language="fr").json()["id"]
    answer_all(client, auth, test_id, db_session)
    response = client.post(f'/api/v1/placement-tests/{test_id}/complete', headers=auth)
    assert response.status_code == 200
    result = response.json()
    assert result["overall_level"] is None
    assert result["planning_level"] == "B2"
    assert result["planning_level_trace"]["assessment_proposed_level"] == "A1"
    assert result["planning_level_trace"]["action"] == "retained_prior_planning"
    fetched = client.get(f'/api/v1/placement-tests/{test_id}/result', headers=auth)
    assert fetched.status_code == 200
    assert fetched.json() == result
    # A result snapshot must not silently follow the current aggregated profile.
    db_session.refresh(profile)
    profile.planning_level = "A2"
    db_session.commit()
    after_profile_change = client.get(f'/api/v1/placement-tests/{test_id}/result', headers=auth)
    assert after_profile_change.status_code == 200
    for key in PLANNING_KEYS:
        assert after_profile_change.json()[key] == result[key]
    capture("retained-planning", {"complete": result, "get_result": fetched.json(),
        "get_result_after_profile_change": after_profile_change.json()})
