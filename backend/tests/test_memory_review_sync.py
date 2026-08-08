"""MemorySchedule = SoT; ReviewItem = projeção — sync legado ↔ V2."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models import (
    Language,
    MemoryReviewEvent,
    MemorySchedule,
    User,
    UserLanguage,
)
from app.services import memory_engine
from app.services.objective_seed import ensure_en_a1_can_001


def _ul(db_session, email="admin@befluent.local") -> UserLanguage:
    user = db_session.scalar(select(User).where(User.email == email))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    existing = db_session.scalar(
        select(UserLanguage).where(
            UserLanguage.user_id == user.id, UserLanguage.language_id == language.id
        )
    )
    if existing:
        return existing
    ul = UserLanguage(user_id=user.id, language_id=language.id, is_active=True)
    db_session.add(ul)
    db_session.commit()
    return ul


def test_v2_and_legacy_answer_keep_due_at_consistent(client, auth, db_session):
    ul = _ul(db_session)
    objective = ensure_en_a1_can_001(db_session)
    schedule = memory_engine.schedule_objective_review(
        db_session, user_language_id=ul.id, objective=objective
    )
    db_session.commit()
    assert schedule.review_item_id

    # Via V2
    resp_v2 = client.post(
        f"/api/v1/teaching/memory/{schedule.id}/review",
        json={"rating": "good"},
        headers=auth,
    )
    assert resp_v2.status_code == 200
    db_session.refresh(schedule)
    due_v2 = schedule.due_at
    from app.models import ReviewItem

    review = db_session.get(ReviewItem, schedule.review_item_id)
    assert review is not None
    assert review.next_review_at == due_v2

    events_after_v2 = db_session.scalar(
        select(func.count()).select_from(MemoryReviewEvent).where(
            MemoryReviewEvent.memory_schedule_id == schedule.id
        )
    )

    # Via legado — não deve divergir nem duplicar evento (idempotência se mesma janela;
    # aqui rating diferente força novo evento, mas due_at permanece alinhado).
    resp_legacy = client.post(
        f"/api/v1/reviews/{schedule.review_item_id}/answer",
        json={"rating": "easy"},
        headers=auth,
    )
    assert resp_legacy.status_code == 200
    db_session.refresh(schedule)
    db_session.refresh(review)
    assert review.next_review_at == schedule.due_at

    events_after_legacy = db_session.scalar(
        select(func.count()).select_from(MemoryReviewEvent).where(
            MemoryReviewEvent.memory_schedule_id == schedule.id
        )
    )
    assert events_after_legacy == events_after_v2 + 1


def test_legacy_answer_does_not_double_write_same_rating(client, auth, db_session):
    ul = _ul(db_session)
    objective = ensure_en_a1_can_001(db_session)
    schedule = memory_engine.schedule_objective_review(
        db_session, user_language_id=ul.id, objective=objective
    )
    db_session.commit()

    r1 = client.post(
        f"/api/v1/reviews/{schedule.review_item_id}/answer",
        json={"rating": "good"},
        headers=auth,
    )
    assert r1.status_code == 200
    r2 = client.post(
        f"/api/v1/reviews/{schedule.review_item_id}/answer",
        json={"rating": "good"},
        headers=auth,
    )
    assert r2.status_code == 200
    count = db_session.scalar(
        select(func.count()).select_from(MemoryReviewEvent).where(
            MemoryReviewEvent.memory_schedule_id == schedule.id
        )
    )
    assert count == 1


def test_flow_restore_preserves_phase_and_remediation(client, auth, db_session):
    _ul(db_session)
    start = client.post(
        "/api/v1/teaching/slice/en-a1-can-001/start", json={}, headers=auth
    )
    assert start.status_code == 200
    flow_id = start.json()["flow"]["id"]
    phase = start.json()["flow"]["phase"]

    # Avança ack até practice (ou até erro)
    session = start.json()
    for _ in range(8):
        activity = session.get("current_activity") or {}
        if activity.get("type") in {"fill_gap", "word_order", "multiple_choice", "guided_production"}:
            break
        resp = client.post(
            f"/api/v1/teaching/slice/flows/{flow_id}/answer",
            json={"student_response": ""},
            headers=auth,
        )
        assert resp.status_code == 200
        session = resp.json()

    # Força remediação
    bad = client.post(
        f"/api/v1/teaching/slice/flows/{flow_id}/answer",
        json={"student_response": "zzz totally wrong"},
        headers=auth,
    )
    assert bad.status_code == 200
    body = bad.json()
    assert body["flow"]["phase"] == "needs_remediation"
    assert body["remediation"]
    rem_id = body["remediation"]["id"]
    cursor = body["flow"]["activity_cursor"]

    restored = client.get(
        "/api/v1/teaching/slice/en-a1-can-001/active", headers=auth
    )
    assert restored.status_code == 200
    again = restored.json()
    assert again["flow"]["id"] == flow_id
    assert again["flow"]["phase"] == "needs_remediation"
    assert again["flow"]["activity_cursor"] == cursor
    assert again["remediation"]["id"] == rem_id

    # Restore não cria segundo flow
    start2 = client.post(
        "/api/v1/teaching/slice/en-a1-can-001/start", json={}, headers=auth
    )
    assert start2.json()["flow"]["id"] == flow_id
    assert phase  # sanity: havia fase inicial
