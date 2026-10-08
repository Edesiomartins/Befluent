"""Release gates: contracts and concrete regressions, no new policy."""
from sqlalchemy import select
from app.models import PlacementTestAnswer, User


def test_native_en_fr_static_pt_bank_is_explicitly_unavailable(client, auth, db_session):
    from tests.test_placement_api import create_test
    db_session.scalar(select(User)).native_language = "en"
    db_session.commit()
    created = create_test(client, auth, language="fr")
    assert created.status_code == 200
    test_id = created.json()["id"]
    response = client.post(f"/api/v1/placement-tests/{test_id}/next-item", headers=auth)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "native_support_unavailable"
    assert not list(db_session.scalars(select(PlacementTestAnswer).where(PlacementTestAnswer.test_id == test_id)))


def test_valid_ai_reported_and_accepted_level_are_preserved():
    from app.services.writing_evaluation import _validate_ai_payload
    from app.services.placement_production import production_result
    feedback = _validate_ai_payload({"normalized_score":.9,"estimated_level":"B2"}, "B1")
    feedback["provenance"]={"provider":"configured","model":"existing-model"}
    answer = PlacementTestAnswer(skill="writing",cefr_level="B1",normalized_score=.9,
        evaluated_by="ai",feedback_json=feedback)
    result=production_result(answer)
    assert result["reported_level"] == "B2"
    assert result["accepted_level"] == "B1"
    assert result["estimated_level"] == "B1"
    assert result["status"] == "provisional"
    assert result["provenance"]["model"] == "existing-model"
    assert not result["eligible_for_overall"]


import pytest

@pytest.mark.parametrize("level", [{}, [], True, None, "INVALID"])
def test_invalid_ai_level_has_no_accepted_cefr(level):
    from app.services.writing_evaluation import _validate_ai_payload
    result = _validate_ai_payload({"normalized_score":.95,"estimated_level":level},"B1")
    assert result["estimated_level"] is None
    assert result["accepted_level"] is None
    assert result["reported_level"] is None


def test_speaking_metadata_cleanup_retry_and_skip(client, auth, db_session, monkeypatch, tmp_path):
    import hashlib
    from app.api import placement_tests as api
    from app.models import PlacementItem, PlacementTest, PlacementItemDelivery
    from app.services.placement_delivery import deliver_item
    from tests.test_placement_api import create_test
    test_id=create_test(client,auth).json()["id"]
    item=db_session.scalar(select(PlacementItem).where(PlacementItem.language_code=="en",PlacementItem.skill=="speaking"))
    deliver_item(db_session,db_session.get(PlacementTest,test_id),item);db_session.commit()
    audio=b"controlled-audio-test"
    path=tmp_path/"speech.webm"
    def save(data):
        path.write_bytes(data)
        return str(path)
    monkeypatch.setattr(api,"save_temp_audio",save)
    monkeypatch.setattr(api,"transcribe_audio",lambda *args:{"text":"Server transcript","provider":"configured-stt","model":"existing"})
    monkeypatch.setattr(api,"evaluate_speaking",lambda *args:{"status":"assessed","evaluated_by":"ai","estimated_level":"A1",
        "normalized_score":.8,"reported_level":"A1","accepted_level":"A1","limitations":["pronunciation_not_measured","fluency_not_measured"],
        "provenance":{"stt_provider":"configured-stt","assessment_scope":"transcript_linguistic_content"}})
    response=client.post(f"/api/v1/placement-tests/{test_id}/speaking",headers=auth,
        data={"item_id":item.id,"transcript":"CLIENT FORGED"},files={"file":("speech.webm",audio,"audio/webm")})
    assert response.status_code==200
    assert response.json()["status"]=="provisional"
    assert not path.exists()
    row=db_session.scalar(select(PlacementTestAnswer).where(PlacementTestAnswer.test_id==test_id))
    assert row.answer_json["transcript"]=="Server transcript"
    assert row.answer_json["audio_metadata"]=={"received":True,"sha256":hashlib.sha256(audio).hexdigest(),
        "bytes":len(audio),"mime_type":"audio/webm","retained":False}
    again=client.post(f"/api/v1/placement-tests/{test_id}/speaking",headers=auth,
        data={"item_id":item.id},files={"file":("speech.webm",audio,"audio/webm")})
    assert again.status_code==409
    assert len(list(db_session.scalars(select(PlacementTestAnswer).where(PlacementTestAnswer.test_id==test_id))))==1


def test_speaking_failure_cleans_temp_and_allows_retry_then_skip(client, auth, db_session, monkeypatch, tmp_path):
    from app.api import placement_tests as api
    from app.models import PlacementItem, PlacementTest, PlacementItemDelivery
    from app.services.placement_delivery import deliver_item
    from tests.test_placement_api import create_test
    test_id=create_test(client,auth).json()["id"]
    item=db_session.scalar(select(PlacementItem).where(PlacementItem.language_code=="en",PlacementItem.skill=="speaking"))
    deliver_item(db_session,db_session.get(PlacementTest,test_id),item);db_session.commit()
    path=tmp_path/"speech-error.webm"
    def save(data):
        path.write_bytes(data)
        return str(path)
    monkeypatch.setattr(api,"save_temp_audio",save)
    monkeypatch.setattr(api,"transcribe_audio",lambda *args:{"text":"","provider":"configured-stt"})
    response=client.post(f"/api/v1/placement-tests/{test_id}/speaking",headers=auth,
        data={"item_id":item.id},files={"file":("speech.webm",b"audio","audio/webm")})
    assert response.status_code==422
    assert not path.exists()
    assert not list(db_session.scalars(select(PlacementTestAnswer).where(PlacementTestAnswer.test_id==test_id)))
    delivery=db_session.scalar(select(PlacementItemDelivery).where(PlacementItemDelivery.test_id==test_id))
    db_session.refresh(delivery)
    assert delivery.consumed_at is None
    skipped=client.post(f"/api/v1/placement-tests/{test_id}/skip-production",headers=auth,json={"item_id":item.id,"text":"skip"})
    assert skipped.status_code==200
    result=client.post(f"/api/v1/placement-tests/{test_id}/complete",headers=auth).json()
    speaking=next(x for x in result["skills"] if x["skill"]=="speaking")
    assert speaking["status"]=="not_collected"
    assert speaking["score"] is None
    assert speaking["estimated_level"] is None

