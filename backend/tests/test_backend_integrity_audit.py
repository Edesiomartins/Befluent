"""Regressões de integridade observadas na auditoria de 2026-10-05."""

import pytest
from sqlalchemy import select

from app.core.errors import APIError
from app.core.teaching import FlowPhase
from app.models import (
    Conversation, ConversationMessage, LearningAttempt, LearningEvidence,
    Language, LearningProgressEvent, StudySession, TeachingFlowSession, User, UserLanguage,
)
from app.services import teaching_flow, teaching_slice
from app.services.objective_seed import ensure_en_a1_can_001


def _ul(db, email="admin@befluent.local"):
    user_id = db.scalar(select(User.id).where(User.email == email))
    language_id = db.scalar(select(Language.id).where(Language.code == "en"))
    ul = db.scalar(select(UserLanguage).where(UserLanguage.user_id == user_id,
                                             UserLanguage.language_id == language_id))
    if ul is None:
        ul = UserLanguage(user_id=user_id, language_id=language_id, is_active=True)
        db.add(ul)
        db.flush()
    return ul


def _flow(db, activities, phase=FlowPhase.PRACTICING):
    ul = _ul(db)
    objective = ensure_en_a1_can_001(db)
    flow = TeachingFlowSession(
        user_language_id=ul.id, objective_id=objective.id, status="active",
        phase=phase, activity_cursor=0, payload_json={"activities": activities},
    )
    db.add(flow)
    db.commit()
    return flow


@pytest.mark.parametrize("kind", ["fill_gap", "multiple_choice", "guided_production"])
def test_ack_cannot_bypass_assessed_activity(db_session, kind):
    flow = _flow(db_session, [{"type": kind, "phase_hint": "practicing",
                              "canonical_answer": "hello", "options": ["hello", "bye"]}])
    with pytest.raises(APIError) as exc:
        teaching_slice.submit_slice_answer(db_session, flow, student_response="__ack__", activity_index=0)
    assert exc.value.code == "invalid_acknowledgement"
    assert not list(db_session.scalars(select(LearningAttempt)))
    assert flow.activity_cursor == 0


@pytest.mark.parametrize("kind", ["listen", "matching", "presentation", "recognition", "conversation_prompt"])
@pytest.mark.parametrize("response", ["", "__ack__", "texto legado"])
def test_passive_continue_does_not_demonstrate_comprehension(db_session, kind, response):
    flow = _flow(db_session, [{"type": kind, "phase_hint": "practicing"}])
    teaching_slice.submit_slice_answer(db_session, flow, student_response=response, activity_index=0)
    assert not list(db_session.scalars(select(LearningEvidence)))
    assert flow.activity_cursor == 1
    assert flow.status == "closed"
    assert flow.phase == "needs_review"


def test_transfer_advances_and_closes_without_fabricating_mastery(db_session):
    flow = _flow(db_session, [{"type": "transfer_question", "phase_hint": "transfer_check",
                              "canonical_answer": "hello"}], FlowPhase.TRANSFER_CHECK)
    teaching_slice.submit_slice_answer(db_session, flow, student_response="hello", activity_index=0)
    assert flow.activity_cursor == 1
    assert flow.status == "closed"
    assert flow.phase == "needs_review"
    with pytest.raises(APIError):
        teaching_slice.submit_slice_answer(db_session, flow, student_response="hello", activity_index=0)
    assert len(list(db_session.scalars(select(LearningEvidence)))) == 1


def _conversation(db):
    ul = _ul(db)
    session = StudySession(user_language_id=ul.id, status="active")
    db.add(session)
    db.flush()
    conversation = Conversation(user_language_id=ul.id, study_session_id=session.id,
                                topic="Missão de viagem", status="active")
    db.add(conversation)
    db.commit()
    return conversation, session


@pytest.mark.parametrize("abandon_conversation", [False, True])
def test_complete_rejects_abandoned_state(client, auth, db_session, abandon_conversation):
    conversation, session = _conversation(db_session)
    if abandon_conversation:
        response = client.post(f"/api/v1/conversations/{conversation.id}/abandon", headers=auth)
    else:
        response = client.post(f"/api/v1/study-sessions/{session.id}/abandon", headers=auth)
    assert response.status_code == 200
    response = client.post(f"/api/v1/conversations/{conversation.id}/complete", headers=auth)
    assert response.status_code == 409
    db_session.expire_all()
    assert session.status == "abandoned"
    assert conversation.status == ("abandoned" if abandon_conversation else "active")
    assert not list(db_session.scalars(select(LearningProgressEvent).where(
        LearningProgressEvent.event_type == "conversation_completed")))


def test_message_rejects_closed_study_session(client, auth, db_session):
    conversation, session = _conversation(db_session)
    client.post(f"/api/v1/study-sessions/{session.id}/complete", headers=auth)
    response = client.post(f"/api/v1/conversations/{conversation.id}/messages",
                           json={"text": "hello"}, headers=auth)
    assert response.status_code == 409
    assert not list(db_session.scalars(select(ConversationMessage)))


def test_conversation_completion_is_idempotent(client, auth, db_session):
    conversation, session = _conversation(db_session)
    first = client.post(f"/api/v1/conversations/{conversation.id}/complete", headers=auth)
    assert first.status_code == 200
    db_session.expire_all()
    ended = (conversation.ended_at, session.ended_at)
    second = client.post(f"/api/v1/conversations/{conversation.id}/complete", headers=auth)
    assert second.status_code == 200
    db_session.expire_all()
    assert (conversation.ended_at, session.ended_at) == ended
    assert len(list(db_session.scalars(select(LearningProgressEvent).where(
        LearningProgressEvent.event_type == "conversation_completed")))) == 1


def test_conversation_missing_session_rejects_completion(db_session):
    from app.services.study_sessions import validate_study_session_for_user
    conversation, session = _conversation(db_session)
    user = db_session.get(User, _ul(db_session).user_id)
    # Production FK prevents creating this orphan; exercise the shared guard
    # without disabling database integrity for the rest of the suite.
    with pytest.raises(APIError) as exc:
        validate_study_session_for_user(db_session, user, "missing-session", conversation.user_language_id,
                                        require_active=False)
    assert exc.value.status_code == 404
    db_session.refresh(conversation)
    assert conversation.status == "active"


def test_retry_cannot_use_other_flows_remediation(db_session, other_user):
    owner_flow = _flow(db_session, [{"type": "fill_gap", "phase_hint": "practicing",
                                    "canonical_answer": "hello"}])
    answer = teaching_slice.submit_slice_answer(db_session, owner_flow, student_response="wrong", activity_index=0)
    remediation_id = answer["remediation"]["id"]
    db_session.commit()
    other_ul = _ul(db_session, email="outro@befluent.local")
    foreign_flow = TeachingFlowSession(user_language_id=other_ul.id,
        objective_id=owner_flow.objective_id, status="active", phase=FlowPhase.NEEDS_REMEDIATION,
        activity_cursor=0, payload_json={"activities": [{"type": "fill_gap", "canonical_answer": "hello"}]})
    db_session.add(foreign_flow)
    db_session.commit()
    with pytest.raises(APIError) as exc:
        teaching_slice.retry_slice(db_session, foreign_flow, remediation_id=remediation_id, student_response="hello")
    assert exc.value.code == "remediation_flow_mismatch"
    assert len(list(db_session.scalars(select(LearningAttempt)))) == 1


def test_failed_conversation_commit_rolls_back_all_completion(client, auth, db_session, monkeypatch):
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import OperationalError

    conversation, session = _conversation(db_session)
    def fail_commit(self):
        raise OperationalError("commit", {}, RuntimeError("database unavailable"))
    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", fail_commit)
        with pytest.raises(OperationalError):
            client.post(f"/api/v1/conversations/{conversation.id}/complete", headers=auth)
    db_session.expire_all()
    assert conversation.status == session.status == "active"
    assert conversation.ended_at is session.ended_at is None
    assert not list(db_session.scalars(select(LearningProgressEvent).where(
        LearningProgressEvent.event_type == "conversation_completed")))


def test_abandon_cannot_contradict_completed_study_session(client, auth, db_session):
    conversation, session = _conversation(db_session)
    client.post(f"/api/v1/study-sessions/{session.id}/complete", headers=auth)
    response = client.post(f"/api/v1/conversations/{conversation.id}/abandon", headers=auth)
    assert response.status_code == 409
    db_session.expire_all()
    assert conversation.status == "active"
    assert session.status == "completed"


def test_retry_ack_cannot_bypass_real_question(db_session):
    flow = _flow(db_session, [{"type": "fill_gap", "phase_hint": "practicing", "canonical_answer": "hello"}])
    out = teaching_slice.submit_slice_answer(db_session, flow, student_response="wrong", activity_index=0)
    payload = dict(flow.payload_json)
    payload["retry_activity"] = {"type": "fill_gap", "canonical_answer": "goodbye", "retry_safe": True}
    flow.payload_json = payload
    db_session.commit()
    with pytest.raises(APIError) as exc:
        teaching_slice.retry_slice(db_session, flow, remediation_id=out["remediation"]["id"], student_response="__ack__")
    assert exc.value.code == "invalid_acknowledgement"
    assert len(list(db_session.scalars(select(LearningAttempt)))) == 1


def test_lexical_presentation_preserves_exposure_and_repeat_is_rejected(db_session):
    from app.models import VocabularyItem
    ul = _ul(db_session)
    item = VocabularyItem(user_language_id=ul.id, term="hello", translation_pt="olá")
    db_session.add(item)
    db_session.flush()
    flow = _flow(db_session, [{"type": "presentation", "phase_hint": "input",
                              "vocabulary_item_id": item.id, "evidence_type": "exposure"}], FlowPhase.INPUT)
    flow.payload_json = {**flow.payload_json, "lexical_cycle": True}
    db_session.commit()
    teaching_slice.submit_slice_answer(db_session, flow, student_response="", activity_index=0)
    evidence = list(db_session.scalars(select(LearningEvidence)))
    assert len(evidence) == 1
    assert evidence[0].evidence_type == "exposure"
    with pytest.raises(APIError):
        teaching_slice.submit_slice_answer(db_session, flow, student_response="", activity_index=0)
    assert len(list(db_session.scalars(select(LearningAttempt)))) == 1


@pytest.mark.parametrize("endpoint", ["speech/synthesize", "speech/transcribe", "conversation", "teaching"])
def test_locked_language_cannot_continue_via_existing_ids_or_speech(client, auth, db_session, monkeypatch, endpoint):
    from app.core.config import get_settings
    conversation, session = _conversation(db_session)
    flow = _flow(db_session, [{"type": "fill_gap", "canonical_answer": "hello", "phase_hint": "practicing"}])
    monkeypatch.setattr(get_settings(), "language_entitlements_enabled", True)
    if endpoint == "conversation":
        response = client.post(f"/api/v1/conversations/{conversation.id}/messages", json={"text": "hello"}, headers=auth)
    elif endpoint == "teaching":
        response = client.post(f"/api/v1/teaching/slice/flows/{flow.id}/answer",
                               json={"student_response": "hello", "activity_index": 0}, headers=auth)
    elif endpoint.endswith("transcribe"):
        response = client.post("/api/v1/speech/transcribe", data={"language_code": "en"},
                               files={"file": ("audio.webm", b"audio", "audio/webm")}, headers=auth)
    else:
        response = client.post("/api/v1/speech/synthesize", json={"language_code": "en", "text": "hello"}, headers=auth)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "language_locked"
    assert not list(db_session.scalars(select(LearningAttempt)))
    assert not list(db_session.scalars(select(ConversationMessage)))


def test_exposure_only_keeps_mastery_progress_calibrating(db_session):
    from app.models import VocabularyItem
    from app.services.progress import aggregate_mastery_progress
    from zoneinfo import ZoneInfo
    ul = _ul(db_session)
    item = VocabularyItem(user_language_id=ul.id, term="hello", translation_pt="olá")
    db_session.add(item)
    db_session.flush()
    flow = _flow(db_session, [{"type": "presentation", "vocabulary_item_id": item.id,
                              "phase_hint": "input", "evidence_type": "exposure"}], FlowPhase.INPUT)
    flow.payload_json = {**flow.payload_json, "lexical_cycle": True}
    db_session.commit()
    teaching_slice.submit_slice_answer(db_session, flow, student_response="", activity_index=0)
    progress = aggregate_mastery_progress(db_session, ul.id, tz=ZoneInfo("America/Sao_Paulo"), days=7)
    assert progress["status"] == "calibrating"
    assert progress["overall_percent"] is None
    assert all(day["percent"] is None for day in progress["timeline"])


def test_wrong_answer_returns_mastery_after_recording_error(db_session):
    from app.models import UserObjectiveProgress
    flow = _flow(db_session, [{"type": "fill_gap", "phase_hint": "practicing", "canonical_answer": "hello"}])
    out = teaching_slice.submit_slice_answer(db_session, flow, student_response="wrong", activity_index=0)
    progress = db_session.scalar(select(UserObjectiveProgress).where(
        UserObjectiveProgress.objective_id == flow.objective_id,
        UserObjectiveProgress.user_language_id == flow.user_language_id))
    assert out["mastery"]["state"] == progress.state == "needs_remediation"


def test_retry_limit_closes_instead_of_leaving_unfinishable_flow(db_session):
    flow = _flow(db_session, [{"type": "fill_gap", "phase_hint": "practicing", "canonical_answer": "hello"}])
    out = teaching_slice.submit_slice_answer(db_session, flow, student_response="wrong", activity_index=0)
    payload = dict(flow.payload_json)
    payload["retry_activity"] = {"type": "fill_gap", "canonical_answer": "bye", "retry_safe": True}
    flow.payload_json = payload
    flow.remediation_cycles = 2
    db_session.commit()
    out = teaching_slice.retry_slice(db_session, flow, remediation_id=out["remediation"]["id"], student_response="wrong")
    assert out["attempt"]["result"] == "incorrect"
    assert flow.status == "closed"
    assert flow.phase == "needs_review"
    with pytest.raises(APIError) as exc:
        teaching_slice.retry_slice(db_session, flow, remediation_id=out["remediation"]["id"], student_response="bye")
    assert exc.value.code == "flow_closed"


def test_stale_study_session_cannot_overwrite_completed_state(db_session):
    from sqlalchemy.orm import Session
    from app.services.study_sessions import abandon_session, complete_session
    conversation, session = _conversation(db_session)
    with Session(bind=db_session.get_bind()) as other:
        complete_session(other, other.get(StudySession, session.id))
        other.commit()
    # The first identity map still contains the earlier active state.
    assert session.status == "active"
    with pytest.raises(APIError) as exc:
        abandon_session(db_session, session)
    assert exc.value.code == "session_already_completed"
    db_session.rollback()
    assert session.status == "completed"


@pytest.mark.parametrize("safe", [True, False])
def test_passive_retry_defers_without_repairing_critical_error(db_session, safe):
    from app.models import LearningError
    flow = _flow(db_session, [{"type": "guided_production", "phase_hint": "producing", "canonical_answer": "hello"}])
    out = teaching_slice.submit_slice_answer(db_session, flow, student_response="wrong", activity_index=0)
    error_id = out["remediation"]["error_id"]
    payload = dict(flow.payload_json)
    payload["retry_activity"] = {"type": "recognition", "retry_safe": safe,
                                  "retry_strategy": "fallback_continue", "models": ["hello"]}
    flow.payload_json = payload
    db_session.commit()
    out = teaching_slice.retry_slice(db_session, flow, remediation_id=out["remediation"]["id"], student_response="__ack__")
    assert out["attempt"]["result"] == "partial"
    assert db_session.get(LearningError, error_id).resolved is False
    assert not list(db_session.scalars(select(LearningEvidence)))
    assert flow.activity_cursor == 1
    assert flow.status == "closed"


def test_event_integrity_failure_is_not_silently_committed(client, auth, db_session, monkeypatch):
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import IntegrityError
    conversation, session = _conversation(db_session)
    original_flush = Session.flush
    def fail_event_flush(self, *args, **kwargs):
        if any(isinstance(row, LearningProgressEvent) for row in self.new):
            raise IntegrityError("insert event", {}, RuntimeError("invalid event data"))
        return original_flush(self, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Session, "flush", fail_event_flush)
        with pytest.raises(IntegrityError):
            client.post(f"/api/v1/conversations/{conversation.id}/complete", headers=auth)
    db_session.expire_all()
    assert conversation.status == session.status == "active"
    assert not list(db_session.scalars(select(LearningProgressEvent)))
