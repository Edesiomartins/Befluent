from copy import deepcopy
from sqlalchemy import select
from app.models import User, Language, UserLanguage, PlacementTest, Curriculum


def french_partial():
    skills = {
        "vocabulary_grammar": {"status": "estimated", "estimated_level": "PRE_A1", "score": 5, "max_score": 8},
        "reading": {"status": "insufficient_evidence", "estimated_level": None, "score": 4, "max_score": 4},
        "listening": {"status": "insufficient_evidence", "estimated_level": None, "score": 4, "max_score": 4},
        "writing": {"status": "provisional", "estimated_level": "B1"},
        "speaking": {"status": "provisional", "estimated_level": "A1"},
    }
    for skill in skills.values():
        skill["evidence_counts"] = {"valid": int(skill.get("max_score", 1)), "independent": int(skill.get("max_score", 1)), "reused": 0}
    return {"overall_level": None, "overall_estimate_status": "partial", "profile_status": "partial", "skills": skills}


def test_french_partial_uses_correlated_planning_without_measuring_skills():
    from app.services.placement_planning import planning_decision
    result = french_partial()
    original = deepcopy(result)
    decision = planning_decision(result)
    assert decision["planning_level"] == "A1"
    assert decision["planning_level_source"] == "partial_evidence"
    assert decision["planning_level_reason"]
    assert len(decision["planning_level_trace"]["signals"]) == 5
    assert result == original


def test_sufficient_uses_overall_for_planning():
    from app.services.placement_planning import planning_decision
    result = french_partial()
    result.update(overall_level="B2", overall_estimate_status="sufficient", profile_status="complete")
    for skill in result["skills"].values():
        skill.update(status="estimated", estimated_level="B2", eligible_for_overall=True)
    assert planning_decision(result)["planning_level"] == "B2"
    assert planning_decision(result)["planning_level_source"] == "sufficient_overall"


def test_missing_and_reused_skills_cannot_raise_planning():
    from app.services.placement_planning import planning_decision
    result = french_partial()
    result["skills"] = {"writing": result["skills"]["writing"]}
    assert planning_decision(result)["planning_level"] == "PRE_A1"
    result["skills"]["unknown_skill"] = deepcopy(result["skills"]["writing"])
    assert planning_decision(result)["planning_level"] == "PRE_A1"
    for skill in french_partial()["skills"].values():
        skill["evidence_counts"] = {"valid": 0, "independent": 0, "reused": 4}
        result["skills"][str(len(result["skills"]))] = skill
    assert planning_decision(result)["planning_level"] == "PRE_A1"


def test_partial_completion_opens_journey_and_repeat_is_stable(client, auth, db_session):
    from tests.test_placement_api import create_test, answer_all
    test = create_test(client, auth).json()
    answer_all(client, auth, test["id"], db_session)
    response = client.post(f'/api/v1/placement-tests/{test["id"]}/complete', headers=auth)
    assert response.status_code == 200
    result = response.json()
    assert result["overall_level"] is None
    assert result["planning_level"] in {"PRE_A1", "A1"}
    assert result["planning_level_source"] == "partial_evidence"
    profile = db_session.scalar(select(UserLanguage))
    assert profile.current_level is None
    assert profile.reading_level is None
    assert profile.writing_level is None
    curriculum = db_session.scalar(select(Curriculum).where(Curriculum.user_language_id == profile.id))
    assert curriculum.generated_from == "planning"
    assert curriculum.entry_level == profile.planning_level
    before = (profile.planning_level, deepcopy(profile.assessment_summary_json))
    assert client.post(f'/api/v1/placement-tests/{test["id"]}/complete', headers=auth).json() == result
    db_session.refresh(profile)
    assert (profile.planning_level, profile.assessment_summary_json) == before
    journey = client.get('/api/v1/curriculum/active?language_code=en', headers=auth)
    assert journey.status_code == 200
    assert journey.json()["generated_from"] == "planning"
    assert journey.json()["entry_is_measured_global"] is False
    public = client.get('/api/v1/language-profiles/en', headers=auth).json()
    assert public["overall_level"] is None
    assert public["planning_level_reason"]
    reading = next(skill for skill in public["skills"] if skill["skill"] == "reading")
    assert reading["status"] == "insufficient_evidence"
    assert reading["score"] == 4


def test_prior_sufficient_global_survives_partial_and_checkpoint(db_session):
    from app.api.placement_tests import _apply_to_profile, CHECKPOINT_SOURCE
    from app.services.placement_planning import planning_decision
    user = db_session.scalar(select(User))
    language = db_session.scalar(select(Language).where(Language.code == "fr"))
    profile = UserLanguage(user_id=user.id, language_id=language.id, current_level="B2", level_source="placement_test",
        planning_level="B2", planning_level_source="sufficient_overall", assessment_summary_json={"global_estimate_status": "sufficient"})
    db_session.add(profile); db_session.flush()
    for source in ("placement", CHECKPOINT_SOURCE):
        result = french_partial()
        result.update(planning_decision(result), assessment_coverage={}, policy_version="test", priority_focus=[])
        test = PlacementTest(user_id=user.id, language_code="fr", source=source)
        db_session.add(test); db_session.flush()
        _apply_to_profile(db_session, test, result, user)
        assert profile.current_level == "B2"
        assert profile.planning_level == "B2"
        assert result["planning_level"] == "B2"
        assert result["planning_level_trace"]["action"] == "retained_prior_planning"
        assert profile.assessment_summary_json["global_estimate_status"] == "sufficient"


def test_context_uses_planning_with_explicit_origin(db_session):
    from app.services.learner_context import build_context
    user = db_session.scalar(select(User))
    language = db_session.scalar(select(Language).where(Language.code == "fr"))
    profile = UserLanguage(user_id=user.id, language_id=language.id, planning_level="A1", planning_level_source="partial_evidence")
    db_session.add(profile); db_session.flush()
    context = build_context(db_session, user, "fr")
    assert context.level == "A1"
    assert context.level_source == "planning"
    assert all(value is None for value in context.skill_levels.values())
    prompt = context.to_prompt_context()
    assert "não CEFR global medido" in prompt
    assert "informado pelo próprio aluno" not in prompt


def test_real_french_result_persists_planning_only(db_session):
    from app.api.placement_tests import _apply_to_profile
    user = db_session.scalar(select(User))
    result = french_partial()
    result.update(assessment_coverage={}, policy_version="test", priority_focus=[])
    test = PlacementTest(user_id=user.id, language_code="fr")
    db_session.add(test); db_session.flush()
    _apply_to_profile(db_session, test, result, user)
    profile = db_session.scalar(select(UserLanguage))
    assert profile.planning_level == "A1"
    assert profile.current_level is None
    assert profile.level_estimate is None
    assert profile.reading_level is None
    assert profile.listening_level is None
    assert profile.writing_level is None
    assert profile.speaking_level is None
    assert profile.assessment_summary_json["planning"]["planning_level_reason"]


def test_sufficient_profile_updates_both_distinct_fields(db_session):
    from app.api.placement_tests import _apply_to_profile
    user = db_session.scalar(select(User))
    result = french_partial()
    result.update(overall_level="B1", overall_estimate_status="sufficient", profile_status="complete",
                  assessment_coverage={}, policy_version="test", priority_focus=[])
    for skill in result["skills"].values():
        skill.update(status="estimated", estimated_level="B1", eligible_for_overall=True)
    test = PlacementTest(user_id=user.id, language_code="fr")
    db_session.add(test); db_session.flush()
    _apply_to_profile(db_session, test, result, user)
    profile = db_session.scalar(select(UserLanguage))
    assert profile.current_level == "B1"
    assert profile.planning_level == "B1"
    assert profile.planning_level_source == "sufficient_overall"


def test_partial_blocks_skill_hydration_and_isolated_performance_can_support_entry():
    from app.services.curriculum_generator import hydrate_skill_levels
    from app.services.placement_planning import planning_decision
    profile = UserLanguage(assessment_summary_json={"overall_estimate_status": "partial"})
    assert not hydrate_skill_levels(profile, "A1")
    assert profile.current_level is None
    assert profile.reading_level is None
    result = french_partial()
    del result["skills"]["writing"]
    del result["skills"]["speaking"]
    assert planning_decision(result)["planning_level"] == "A1"
    assert result["skills"]["reading"]["estimated_level"] is None
