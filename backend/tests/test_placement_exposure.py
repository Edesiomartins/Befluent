import pytest
from sqlalchemy import create_engine
from sqlalchemy import select
from app.models import PlacementItem, PlacementTest, User
from app.services import placement_engine as engine


@pytest.mark.parametrize("environment,database,allowed", [
    ("development", "placement_dev.db", True),
    ("staging", "placement_test.db", True),
    ("production", "placement_test.db", False),
    ("development", "placement.db", False),
])
def test_clear_exposure_requires_nonproduction_and_marked_database(environment, database, allowed):
    from scripts.reset_test_user_learning import validate_exposure_clear
    engine_ = create_engine(f"sqlite:///{database}")
    if allowed:
        validate_exposure_clear(engine_, environment)
    else:
        with pytest.raises(ValueError):
            validate_exposure_clear(engine_, environment)
    engine_.dispose()


def test_cooldown_is_versioned_policy_configuration(client, auth, db_session):
    from app.services.placement_exposure import EXPOSURE_POLICY
    from tests.test_placement_api import create_test
    assert EXPOSURE_POLICY["cooldown_days"] == 30
    result = create_test(client, auth).json()
    assert db_session.get(PlacementTest, result["id"]).result_json["exposure_policy"] == EXPOSURE_POLICY


def test_unseen_band_fallback_beats_seen_preferred_band(db_session):
    from app.services.placement_exposure import exposure_history, exposure_metadata
    from app.services.placement_delivery import deliver_item
    from app.api.placement_tests import _pick_objective_item
    user = db_session.scalar(select(User))
    item = db_session.scalar(select(PlacementItem).where(PlacementItem.language_code == "en", PlacementItem.skill == "vocabulary_grammar", PlacementItem.cefr_level == "A2"))
    old = PlacementTest(user_id=user.id, language_code="en")
    db_session.add(old); db_session.flush()
    from datetime import datetime, timezone
    for current in db_session.scalars(select(PlacementItem).where(PlacementItem.language_code == "en", PlacementItem.skill == "vocabulary_grammar", PlacementItem.cefr_level == "A2")):
        delivery = deliver_item(db_session, old, current)
        delivery.consumed_at = datetime.now(timezone.utc)
        db_session.flush()
    db_session.commit()
    history = exposure_history(db_session, user.id, "en", exclude_test_id="next")
    assert exposure_metadata(item, history)["reused"]
    picked = _pick_objective_item(db_session, "en", engine.TestState(), set(), user_id=user.id, test_id="next")
    assert picked.id != item.id
    assert picked.cefr_level != "A2"


def test_reused_response_cannot_support_level():
    from app.api.placement_tests import _records
    from app.models import PlacementTestAnswer
    answer = PlacementTestAnswer(skill="reading", cefr_level="B1", normalized_score=1,
        feedback_json={"exposure": {"reused": True, "evidence_eligible": False}})
    assert _records([answer]) == []


def test_shared_passage_is_seen_even_with_new_question():
    from app.services.placement_exposure import semantic_keys, exposure_metadata
    original = PlacementItem(language_code="en", skill="reading", item_type="reading_comprehension",
        prompt="What happened?", passage="A substantial independent story about a train.", options_json=["a", "b"], correct_answer_json={"value": "a"})
    clone = PlacementItem(language_code="en", skill="reading", item_type="reading_comprehension",
        prompt="Where did it happen?", passage=original.passage, options_json=["c", "d"], correct_answer_json={"value": "c"})
    meta = exposure_metadata(clone, [{"keys": semantic_keys(original), "answered": True, "revealed": True}])
    assert meta["reused"] and meta["stimulus_reused"]
    assert meta["exposure_status"] == "feedback_revealed"


def test_reset_preserves_exposure_and_technical_clear_is_guarded(db_session):
    from app.services.placement_delivery import deliver_item
    from app.models import PlacementItemExposure
    from scripts.reset_test_user_learning import run_reset
    user = db_session.scalar(select(User))
    item = db_session.scalar(select(PlacementItem).where(PlacementItem.language_code == "en"))
    test = PlacementTest(user_id=user.id, language_code="en")
    db_session.add(test); db_session.flush(); deliver_item(db_session, test, item); db_session.commit()
    engine_db = db_session.get_bind()
    run_reset(engine_db, user_id=user.id, apply=True)
    db_session.expire_all()
    assert db_session.scalar(select(PlacementItemExposure.id).where(PlacementItemExposure.user_id == user.id))
    import pytest
    with pytest.raises(ValueError, match="test"):
        run_reset(engine_db, user_id=user.id, clear_placement_exposure=True, environment="production")


def test_accounts_and_languages_are_isolated(db_session):
    from app.services.placement_exposure import exposure_history
    from app.services.placement_delivery import deliver_item
    users = list(db_session.scalars(select(User)))
    user = users[0]
    other = User(email="other-exposure@example.org", password_hash="unused", name="Other")
    db_session.add(other); db_session.flush()
    item = db_session.scalar(select(PlacementItem).where(PlacementItem.language_code == "en"))
    test = PlacementTest(user_id=user.id, language_code="en")
    db_session.add(test); db_session.flush(); deliver_item(db_session, test, item); db_session.commit()
    assert exposure_history(db_session, user.id, "en")
    assert not exposure_history(db_session, other.id, "en")
    assert not exposure_history(db_session, user.id, "fr")


def test_first_and_second_session_exposure_and_resume(client, auth, db_session):
    from tests.test_placement_api import create_test
    from app.models import PlacementItemExposure
    first = create_test(client, auth).json()
    one = client.post(f'/api/v1/placement-tests/{first["id"]}/next-item', headers=auth).json()
    assert one["item"]["exposure"]["exposure_status"] == "fresh"
    again = client.post(f'/api/v1/placement-tests/{first["id"]}/next-item', headers=auth).json()
    assert again["item"]["id"] == one["item"]["id"]
    assert len(list(db_session.scalars(select(PlacementItemExposure)))) == 1
    test = db_session.get(PlacementTest, first["id"])
    test.status = "abandoned"; db_session.commit()
    second = create_test(client, auth).json()
    two = client.post(f'/api/v1/placement-tests/{second["id"]}/next-item', headers=auth).json()
    assert two["item"]["id"] != one["item"]["id"]
    assert two["item"]["exposure"]["previous_exposure_count"] == 0


def test_reuse_only_after_fresh_exhaustion_and_revealed_is_last(db_session):
    from app.services.placement_delivery import deliver_item
    from app.services.placement_exposure import mark_feedback_revealed, record_delivery
    from app.api.placement_tests import _pick_objective_item
    from datetime import datetime, timezone
    user = db_session.scalar(select(User))
    old = PlacementTest(user_id=user.id, language_code="en")
    db_session.add(old); db_session.flush()
    items = list(db_session.scalars(select(PlacementItem).where(PlacementItem.language_code == "en", PlacementItem.skill.in_(engine.OBJECTIVE_SKILLS))))
    for item in items:
        delivery = deliver_item(db_session, old, item)
        delivery.consumed_at = datetime.now(timezone.utc)
        db_session.flush()
    mark_feedback_revealed(db_session, old, items[0]); db_session.commit()
    assert _pick_objective_item(db_session, "en", engine.TestState(), set(), user_id=user.id, test_id="new") is None
    reused = _pick_objective_item(db_session, "en", engine.TestState(), set(), user_id=user.id, test_id="new", allow_reuse=True)
    assert reused and reused.id != items[0].id
    test = PlacementTest(user_id=user.id, language_code="en")
    db_session.add(test); db_session.flush()
    delivery = deliver_item(db_session, test, reused)
    row = record_delivery(db_session, test, reused, delivery)
    assert row.snapshot_json["exposure"]["reused"]
    assert row.snapshot_json["exposure"]["previous_exposure_count"] == 1
    assert not row.snapshot_json["exposure"]["evidence_eligible"]


def test_option_order_and_version_do_not_create_independent_items():
    from app.services.placement_exposure import semantic_keys
    first = PlacementItem(language_code="en", skill="vocabulary_grammar", item_type="multiple_choice",
        prompt="Choose a greeting", options_json=["hello", "bye"], correct_answer_json={"value": "hello"}, version=1)
    clone = PlacementItem(language_code="en", skill=first.skill, item_type=first.item_type,
        prompt=first.prompt, options_json=["bye", "hello"], correct_answer_json=first.correct_answer_json, version=2)
    assert semantic_keys(first) == semantic_keys(clone)
    clone.prompt = "Choose a farewell"
    assert semantic_keys(first) != semantic_keys(clone)


def test_technical_clear_dry_run_and_rollback_preserve_ledger(db_session):
    from app.services.placement_delivery import deliver_item
    from app.models import PlacementItemExposure
    from scripts.reset_test_user_learning import run_reset
    user = db_session.scalar(select(User))
    item = db_session.scalar(select(PlacementItem).where(PlacementItem.language_code == "en"))
    test = PlacementTest(user_id=user.id, language_code="en")
    db_session.add(test); db_session.flush(); deliver_item(db_session, test, item); db_session.commit()
    uid = user.id
    db_session.rollback()
    report = run_reset(db_session.get_bind(), user_id=uid, clear_placement_exposure=True, environment="test")
    assert not report["write_committed"]
    report = run_reset(db_session.get_bind(), user_id=uid, apply=True, rollback=True, clear_placement_exposure=True, environment="test")
    assert report["rollback_verified"]
    assert db_session.scalar(select(PlacementItemExposure.id))
    db_session.rollback()
    run_reset(db_session.get_bind(), user_id=uid, apply=True, clear_placement_exposure=True, environment="test")
    assert db_session.scalar(select(PlacementItemExposure.id)) is None


def test_changed_item_cannot_be_graded_against_new_content(client, auth, db_session):
    from tests.test_placement_api import create_test
    test = create_test(client, auth).json()
    item = client.post(f'/api/v1/placement-tests/{test["id"]}/next-item', headers=auth).json()["item"]
    stored = db_session.get(PlacementItem, item["id"])
    stored.prompt = "A different question edited after delivery"
    db_session.commit()
    response = client.post(f'/api/v1/placement-tests/{test["id"]}/answers', headers=auth,
        json={"item_id": stored.id, "answer": "anything"})
    assert response.status_code == 409
    next_ = client.post(f'/api/v1/placement-tests/{test["id"]}/next-item', headers=auth).json()
    assert next_["item"]["id"] != stored.id
    submitted = client.post(f'/api/v1/placement-tests/{test["id"]}/answers', headers=auth,
        json={"item_id": next_["item"]["id"], "answer": "anything"})
    assert submitted.status_code == 200


@pytest.mark.parametrize("field", ["options_json", "cefr_level", "version"])
def test_delivery_rejects_changed_grading_contract(client, auth, db_session, field):
    from tests.test_placement_api import create_test
    test = create_test(client, auth).json()
    item = client.post(f'/api/v1/placement-tests/{test["id"]}/next-item', headers=auth).json()["item"]
    stored = db_session.get(PlacementItem, item["id"])
    if field == "options_json":
        stored.options_json = list(reversed(stored.options_json))
    elif field == "cefr_level":
        stored.cefr_level = "B1" if stored.cefr_level != "B1" else "A2"
    else:
        stored.version += 1
    db_session.commit()
    response = client.post(f'/api/v1/placement-tests/{test["id"]}/answers', headers=auth,
        json={"item_id": stored.id, "answer": "anything"})
    assert response.status_code == 409


def test_invalid_forms_are_not_activated(db_session):
    from app.services.placement_exposure import rotation_metadata
    user = db_session.scalar(select(User))
    for item in db_session.scalars(select(PlacementItem).where(PlacementItem.language_code == "en", PlacementItem.skill == "vocabulary_grammar")):
        item.rubric_json = {**(item.rubric_json or {}), "form_id": "A"}
    db_session.commit()
    policy = rotation_metadata(db_session, user.id, "en")
    assert policy["selected_form"] is None
    assert policy["unusable_forms"] == ["A"]
    assert policy["psychometric_equivalence"] is False


def test_snapshot_survives_item_edits_and_reset(db_session):
    from app.services.placement_delivery import deliver_item
    from app.services.placement_exposure import exposure_history, semantic_keys
    from scripts.reset_test_user_learning import run_reset
    user = db_session.scalar(select(User))
    item = db_session.scalar(select(PlacementItem).where(PlacementItem.language_code == "en", PlacementItem.skill == "reading"))
    keys = semantic_keys(item)
    test = PlacementTest(user_id=user.id, language_code="en")
    db_session.add(test); db_session.flush(); deliver_item(db_session, test, item); db_session.commit()
    uid = user.id
    item.passage = "Different edited passage"; db_session.commit()
    assert exposure_history(db_session, uid, "en")[0]["keys"] == keys
    db_session.rollback()
    run_reset(db_session.get_bind(), user_id=uid, apply=True)
    assert exposure_history(db_session, uid, "en")[0]["keys"] == keys


def test_reset_preserves_legacy_feedback_revelation(db_session):
    from app.models import PlacementTestAnswer
    from app.services.placement_exposure import exposure_history
    from scripts.reset_test_user_learning import run_reset
    user = db_session.scalar(select(User))
    item = db_session.scalar(select(PlacementItem).where(PlacementItem.language_code == "en"))
    test = PlacementTest(user_id=user.id, language_code="en")
    db_session.add(test); db_session.flush()
    db_session.add(PlacementTestAnswer(test_id=test.id, item_id=item.id, skill=item.skill,
        cefr_level=item.cefr_level, feedback_json={"feedback_revealed": True}))
    db_session.commit()
    uid = user.id
    assert exposure_history(db_session, uid, "en")[0]["revealed"]
    db_session.rollback()
    run_reset(db_session.get_bind(), user_id=uid, apply=True)
    assert exposure_history(db_session, uid, "en")[0]["revealed"]
