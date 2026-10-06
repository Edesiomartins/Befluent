from copy import deepcopy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest
from sqlalchemy import select, update
from app.models import Base, CurriculumBlock, Lesson, LessonActivityAttempt, UserLanguage
from tests.test_fr_b1_legacy_reuse import (
    CONFIRMED_ID, MODEL, confirmed_lesson, french_payload,
)


def snapshot(db):
    return {table.name: [tuple(row) for row in db.execute(select(table).order_by(table.c.id))]
            for table in Base.metadata.sorted_tables if "id" in table.c}


def test_repair_default_dry_run_is_read_only_and_binds_confirmed_id(db_session,confirmed_lesson):
    from scripts.repair_fr_b1_incident import repair
    *_, block, lesson, answer = confirmed_lesson
    before = deepcopy(snapshot(db_session))
    plan = repair(db_session)
    assert plan["lesson_id"] == CONFIRMED_ID
    assert plan["write_performed"] is False
    assert plan["curriculum_blocks"][0]["id"] == block.id
    assert plan["current_status"] == "active"
    assert plan["proposed_action"] == "invalidate_lesson_pending_regeneration"
    assert snapshot(db_session) == before


def test_refusal_identifies_raw_target_missing_despite_diagnostic_fallback(db_session, confirmed_lesson):
    from scripts.repair_fr_b1_incident import repair
    from scripts.diagnose_fr_b1_content import describe_payload
    *_, block, lesson, answer = confirmed_lesson
    payload = dict(lesson.content_json)
    del payload["target_language"]
    payload["language_code"] = "fr"
    lesson.content_json = payload
    db_session.commit()
    assert describe_payload(payload)["payload_target_language"] == "fr"
    before = deepcopy(snapshot(db_session))
    with pytest.raises(ValueError, match=r"target_language.*expected.*fr.*actual.*missing"):
        repair(db_session)
    assert snapshot(db_session) == before


def test_repair_refuses_unconfirmed_block_even_if_it_is_the_only_reference(db_session, confirmed_lesson):
    from scripts.repair_fr_b1_incident import repair
    *_, block, lesson, answer = confirmed_lesson
    block.id = "00000000-0000-0000-0000-000000000001"
    db_session.commit()
    before = deepcopy(snapshot(db_session))
    with pytest.raises(ValueError, match="block"):
        repair(db_session)
    assert snapshot(db_session) == before


def test_apply_requires_explicit_reviewed_block_id(db_session,confirmed_lesson):
    from scripts.repair_fr_b1_incident import repair
    with pytest.raises(ValueError,match="block-id"):
        repair(db_session,apply=True)
    with pytest.raises(ValueError,match="block"):
        repair(db_session,apply=True,block_id="unconfirmed-id")


def test_apply_changes_only_lesson_status_and_preserves_pending_reference(db_session,confirmed_lesson):
    from scripts.repair_fr_b1_incident import repair
    *_, block, lesson, answer = confirmed_lesson
    before = deepcopy(snapshot(db_session))
    result = repair(db_session,apply=True,block_id=block.id)
    assert result["write_performed"] is True
    after = snapshot(db_session)
    assert lesson.status == "language_invalid" and block.lesson_ref == lesson.id
    for table_name in before:
        if table_name != "lessons":
            assert after[table_name] == before[table_name], table_name
    for table, changed_column in ((Lesson.__table__,"status"),(CurriculumBlock.__table__,"lesson_ref")):
        before_rows = [dict(zip(table.c.keys(),row)) for row in before[table.name]]
        after_rows = [dict(zip(table.c.keys(),row)) for row in after[table.name]]
        for old,new in zip(before_rows,after_rows):
            assert {k:v for k,v in old.items() if k != changed_column} == {k:v for k,v in new.items() if k != changed_column}
    again = repair(db_session,apply=True,block_id=block.id)
    assert again["proposed_action"] == "already_applied" and not again["write_performed"]


def test_transaction_rollback_restores_both_changes(db_session,confirmed_lesson):
    from scripts.repair_fr_b1_incident import repair
    *_, block, lesson, answer = confirmed_lesson
    repair(db_session,apply=True,block_id=block.id)
    db_session.rollback(); db_session.expire_all()
    assert lesson.status == "active" and block.lesson_ref == CONFIRMED_ID
    assert answer.answer_json == {"response":"Parce que"}


@pytest.mark.parametrize("changed", ["block_completed","lesson_completed","native_changed","wrong_owner","topic_changed"])
def test_repair_refuses_changed_preconditions(db_session,confirmed_lesson,changed,other_user):
    from scripts.repair_fr_b1_incident import repair
    user, owner, curriculum, day, block, lesson, answer = confirmed_lesson
    if changed == "block_completed": block.status = "completed"
    if changed == "lesson_completed": lesson.status = "completed"
    if changed == "native_changed": user.native_language = "en"
    if changed == "wrong_owner":
        other_owner = UserLanguage(user_id=other_user,language_id=owner.language_id)
        db_session.add(other_owner); db_session.flush()
        curriculum.user_language_id = other_owner.id
    if changed == "topic_changed": block.topic = "Autre sujet"
    db_session.commit()
    before = deepcopy(snapshot(db_session))
    with pytest.raises(ValueError):
        repair(db_session,apply=True,block_id=block.id)
    assert snapshot(db_session) == before


def test_after_repair_normal_generation_replaces_pointer_and_preserves_history(db_session,confirmed_lesson,monkeypatch):
    from scripts.repair_fr_b1_incident import repair
    from app.services.progression import build_block_lesson
    from app.services.ai import OpenRouterProvider
    from app.core.config import get_settings
    user, owner, curriculum, day, block, old, answer = confirmed_lesson
    original = deepcopy(old.content_json)
    repair(db_session,apply=True,block_id=block.id)
    db_session.commit()
    monkeypatch.setattr(get_settings(),"openrouter_api_key","test-key")
    monkeypatch.setattr(get_settings(),"openrouter_model",MODEL)
    def generate(settings,messages,validator,**kwargs):
        payload = french_payload()
        assert validator(payload)
        return payload, MODEL
    monkeypatch.setattr("app.services.ai.openrouter_chat_with_fallback",generate)
    monkeypatch.setattr("app.services.progression.get_ai_provider",lambda: OpenRouterProvider())
    result = build_block_lesson(db_session,user=user,block=block,day=day)
    db_session.commit()
    new = db_session.get(Lesson,result["lesson_id"])
    assert new.id != old.id and block.lesson_ref == new.id
    assert new.content_json["native_language"] == "pt-BR"
    assert new.content_json["target_language"] == "fr"
    assert new.content_json["explanation"] == french_payload()["explanation"]
    assert new.content_json["explanation_native"] == french_payload()["explanation_native"]
    assert old.content_json == original and old.status == "language_invalid"
    assert db_session.get(LessonActivityAttempt,answer.id).answer_json == {"response":"Parce que"}
    assert owner.current_level == "B1" and curriculum.status == "active" and block.status == "pending"


@pytest.mark.parametrize("mode", ["dry_run","rollback","apply","missing_block_flag"])
def test_cli_commit_is_explicit_and_rollback_is_real(db_session,confirmed_lesson,tmp_path,mode):
    *_, block, lesson, answer = confirmed_lesson
    database = tmp_path / "production_simulation.db"
    with sqlite3.connect(database) as target:
        db_session.connection().connection.driver_connection.backup(target)
    original_bytes = database.read_bytes()
    args = [sys.executable,"scripts/repair_fr_b1_incident.py"]
    if mode != "dry_run": args.append("--apply")
    if mode in {"rollback","apply"}: args.extend(["--block-id",block.id])
    if mode == "rollback": args.append("--rollback")
    result = subprocess.run(args,cwd=Path(__file__).resolve().parents[1],
                            env={**os.environ,"DATABASE_URL":f"sqlite:///{database.as_posix()}"},
                            capture_output=True,encoding="utf-8",timeout=30)
    if mode == "missing_block_flag":
        assert result.returncode == 2 and "--block-id" in result.stderr
    else:
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert report["write_committed"] == (mode == "apply")
        assert report["transaction"] == {"apply":"committed","rollback":"rolled_back","dry_run":"read_only_dry_run"}[mode]
    with sqlite3.connect(f"{database.as_uri()}?mode=ro",uri=True) as conn:
        stored = conn.execute("SELECT status,content_json FROM lessons WHERE id=?",(CONFIRMED_ID,)).fetchone()
        reference = conn.execute("SELECT lesson_ref FROM curriculum_blocks WHERE id=?",(block.id,)).fetchone()[0]
    assert stored[0] == ("language_invalid" if mode == "apply" else "active")
    assert reference == CONFIRMED_ID
    assert json.loads(stored[1]) == lesson.content_json
    if mode in {"dry_run","missing_block_flag"}: assert database.read_bytes() == original_bytes


@pytest.mark.parametrize("action", ["lesson_complete","lesson_abandon","block_complete"])
def test_stale_page_cannot_complete_or_mutate_invalid_lesson(db_session,confirmed_lesson,client,auth,action):
    *_, block, lesson, answer = confirmed_lesson
    # State after the revised repair: preserve the reference until replacement.
    lesson.status = "language_invalid"
    db_session.commit()
    before = deepcopy(snapshot(db_session))
    path = f"/api/v1/curriculum/block/{block.id}/complete" if action == "block_complete" else f"/api/v1/lessons/{lesson.id}/{'complete' if action == 'lesson_complete' else 'abandon'}"
    response = client.post(path,json={},headers=auth)
    assert response.status_code == 409, response.text
    db_session.expire_all()
    assert snapshot(db_session) == before


def test_failed_replacement_preserves_invalid_pointer_and_history(db_session,confirmed_lesson,monkeypatch):
    from app.core.errors import APIError
    from app.services.progression import build_block_lesson
    user, owner, curriculum, day, block, old, answer = confirmed_lesson
    old.status = "language_invalid"
    db_session.commit()
    before = deepcopy(snapshot(db_session))
    def fail(*args,**kwargs):
        raise APIError(503,"ai_unavailable","IA indisponível.")
    monkeypatch.setattr("app.services.progression._generate_payload",fail)
    with pytest.raises(APIError) as error:
        build_block_lesson(db_session,user=user,block=block,day=day)
    assert error.value.code == "ai_unavailable"
    assert block.lesson_ref == old.id
    assert snapshot(db_session) == before


def test_abandon_refreshes_quarantine_status_before_mutation(db_session,confirmed_lesson,client,auth,monkeypatch):
    user, owner, curriculum, day, block, lesson, answer = confirmed_lesson
    db_session.execute(update(Lesson).where(Lesson.id==lesson.id).values(status="language_invalid").execution_options(synchronize_session=False))
    db_session.commit()
    assert lesson.status == "active"  # Simulates a pre-repair MVCC read.
    monkeypatch.setattr("app.api.lessons._owned_lesson",lambda *args:(lesson,owner))
    response = client.post(f"/api/v1/lessons/{lesson.id}/abandon",json={},headers=auth)
    assert response.status_code == 409, response.text
    db_session.expire_all()
    assert lesson.status == "language_invalid"


def test_regeneration_refreshes_pointer_after_another_request_replaced_it(db_session,confirmed_lesson,monkeypatch):
    from app.services.progression import build_block_lesson
    user, owner, curriculum, day, block, old, answer = confirmed_lesson
    old.status = "language_invalid"
    new = Lesson(user_language_id=owner.id,title=french_payload()["title"],objective="Avis",
                 content_json={**french_payload(),"target_language":"fr","native_language":"pt-BR"},status="active")
    db_session.add(new); db_session.flush()
    db_session.execute(update(CurriculumBlock).where(CurriculumBlock.id==block.id).values(lesson_ref=new.id).execution_options(synchronize_session=False))
    db_session.commit()
    assert block.lesson_ref == old.id
    def must_not_generate(*args,**kwargs):
        pytest.fail("A validated replacement already exists; reuse it after refreshing the pointer")
    monkeypatch.setattr("app.services.progression._generate_payload",must_not_generate)
    result = build_block_lesson(db_session,user=user,block=block,day=day)
    assert result["lesson_id"] == new.id and block.lesson_ref == new.id
