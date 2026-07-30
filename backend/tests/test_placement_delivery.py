"""Testes de entrega/consumo de itens de nivelamento."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.levels import ReviewStatus
from app.models import PlacementItem, PlacementItemDelivery, PlacementTest, User
from app.services.placement_delivery import (
    consume_delivery_for_answer,
    deliver_item,
    get_open_delivery,
)
from app.core.errors import APIError


def _item(db, **overrides):
    base = dict(
        external_key=f"test-{overrides.get('language_code', 'en')}-x",
        language_code="en",
        cefr_level="A2",
        skill="vocabulary_grammar",
        item_type="multiple_choice",
        prompt="Test?",
        options_json=["a", "b"],
        correct_answer_json={"value": "a"},
        review_status=ReviewStatus.APPROVED,
        is_active=True,
    )
    base.update(overrides)
    if "external_key" not in overrides:
        base["external_key"] = f"key-{id(base)}"
    item = PlacementItem(**base)
    db.add(item)
    db.flush()
    return item


def _test(db, user_id):
    test = PlacementTest(user_id=user_id, language_code="en", status="in_progress")
    db.add(test)
    db.flush()
    return test


class TestApprovedFilter:
    def test_pending_not_consumed(self, db_session):
        user = db_session.scalar(select(User).limit(1))
        test = _test(db_session, user.id)
        item = _item(db_session, review_status=ReviewStatus.PENDING_REVIEW)
        deliver_item(db_session, test, item)
        db_session.commit()
        with pytest.raises(APIError) as exc:
            consume_delivery_for_answer(db_session, test=test, item_id=item.id)
        assert exc.value.code == "placement_item_not_found"

    def test_rejected_not_consumed(self, db_session):
        user = db_session.scalar(select(User).limit(1))
        test = _test(db_session, user.id)
        item = _item(db_session, review_status=ReviewStatus.REJECTED, is_active=False)
        deliver_item(db_session, test, item)
        db_session.commit()
        with pytest.raises(APIError) as exc:
            consume_delivery_for_answer(db_session, test=test, item_id=item.id)
        assert exc.value.code == "placement_item_not_found"

    def test_null_review_not_consumed(self, db_session):
        user = db_session.scalar(select(User).limit(1))
        test = _test(db_session, user.id)
        item = _item(db_session, review_status=None)
        deliver_item(db_session, test, item)
        db_session.commit()
        with pytest.raises(APIError) as exc:
            consume_delivery_for_answer(db_session, test=test, item_id=item.id)
        assert exc.value.code == "placement_item_not_found"

    def test_inactive_not_consumed(self, db_session):
        user = db_session.scalar(select(User).limit(1))
        test = _test(db_session, user.id)
        item = _item(db_session, is_active=False)
        deliver_item(db_session, test, item)
        db_session.commit()
        with pytest.raises(APIError) as exc:
            consume_delivery_for_answer(db_session, test=test, item_id=item.id)
        assert exc.value.code == "placement_item_not_found"


class TestDeliveryLifecycle:
    def test_not_delivered_blocks_answer(self, db_session):
        user = db_session.scalar(select(User).limit(1))
        test = _test(db_session, user.id)
        item = _item(db_session)
        with pytest.raises(APIError) as exc:
            consume_delivery_for_answer(db_session, test=test, item_id=item.id)
        assert exc.value.code == "placement_item_not_delivered"

    def test_expired_delivery(self, db_session):
        user = db_session.scalar(select(User).limit(1))
        test = _test(db_session, user.id)
        item = _item(db_session)
        delivery = PlacementItemDelivery(
            test_id=test.id,
            item_id=item.id,
            delivered_at=datetime.now(timezone.utc) - timedelta(hours=2),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        db_session.add(delivery)
        db_session.commit()
        with pytest.raises(APIError) as exc:
            consume_delivery_for_answer(db_session, test=test, item_id=item.id)
        assert exc.value.code == "placement_item_delivery_expired"

    def test_consumed_blocks_reanswer(self, db_session):
        user = db_session.scalar(select(User).limit(1))
        test = _test(db_session, user.id)
        item = _item(db_session)
        deliver_item(db_session, test, item)
        consume_delivery_for_answer(db_session, test=test, item_id=item.id)
        db_session.commit()
        with pytest.raises(APIError) as exc:
            consume_delivery_for_answer(db_session, test=test, item_id=item.id)
        assert exc.value.code == "placement_item_already_consumed"

    def test_other_test_cannot_consume(self, db_session, other_user):
        user = db_session.scalar(select(User).limit(1))
        test_a = _test(db_session, user.id)
        test_b = _test(db_session, other_user)
        item = _item(db_session)
        deliver_item(db_session, test_a, item)
        db_session.commit()
        with pytest.raises(APIError) as exc:
            consume_delivery_for_answer(db_session, test=test_b, item_id=item.id)
        assert exc.value.code == "placement_item_not_delivered"

    def test_resume_open_delivery(self, db_session):
        user = db_session.scalar(select(User).limit(1))
        test = _test(db_session, user.id)
        item = _item(db_session)
        first = deliver_item(db_session, test, item)
        second = deliver_item(db_session, test, item)
        assert first.id == second.id
        open_d = get_open_delivery(db_session, test.id)
        assert open_d is not None
        assert open_d.item_id == item.id
