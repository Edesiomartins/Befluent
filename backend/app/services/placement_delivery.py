"""Entrega e consumo de itens do teste de nivelamento."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import APIError
from app.core.levels import ReviewStatus
from app.models import PlacementItem, PlacementItemDelivery, PlacementTest


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def approved_active_filter():
    """Somente itens explicitamente aprovados e ativos (NULL nunca é aprovado)."""
    return (
        PlacementItem.review_status == ReviewStatus.APPROVED,
        PlacementItem.is_active.is_(True),
    )


def get_open_delivery(db: Session, test_id: str) -> PlacementItemDelivery | None:
    delivery = db.scalar(
        select(PlacementItemDelivery)
        .where(
            PlacementItemDelivery.test_id == test_id,
            PlacementItemDelivery.consumed_at.is_(None),
        )
        .order_by(PlacementItemDelivery.delivered_at.desc())
    )
    if delivery and _as_utc(delivery.expires_at) <= _now():
        return None
    return delivery


def deliver_item(db: Session, test: PlacementTest, item: PlacementItem) -> PlacementItemDelivery:
    open_delivery = get_open_delivery(db, test.id)
    if open_delivery and open_delivery.item_id == item.id:
        return open_delivery
    if open_delivery:
        # Retoma o mesmo item ainda não respondido.
        return open_delivery

    minutes = get_settings().placement_item_delivery_minutes
    delivery = PlacementItemDelivery(
        test_id=test.id,
        item_id=item.id,
        delivered_at=_now(),
        expires_at=_now() + timedelta(minutes=minutes),
    )
    db.add(delivery)
    db.flush()
    return delivery


def consume_delivery_for_answer(
    db: Session,
    *,
    test: PlacementTest,
    item_id: str,
) -> PlacementItem:
    """Valida entrega + item aprovado/ativo/idioma e marca consumo."""
    delivery = db.scalar(
        select(PlacementItemDelivery).where(
            PlacementItemDelivery.test_id == test.id,
            PlacementItemDelivery.item_id == item_id,
        )
    )
    if not delivery:
        raise APIError(
            403,
            "placement_item_not_delivered",
            "Este item não foi entregue para o teste atual.",
        )
    if delivery.consumed_at is not None:
        raise APIError(
            409,
            "placement_item_already_consumed",
            "Este item já foi respondido.",
        )
    if _as_utc(delivery.expires_at) <= _now():
        raise APIError(
            410,
            "placement_item_delivery_expired",
            "A entrega deste item expirou. Solicite o próximo item novamente.",
        )

    item = db.get(PlacementItem, item_id)
    if not item or item.language_code != test.language_code:
        raise APIError(404, "placement_item_not_found", "Item não encontrado.")
    if not item.is_active:
        raise APIError(404, "placement_item_not_found", "Item não encontrado.")
    if item.review_status != ReviewStatus.APPROVED:
        raise APIError(404, "placement_item_not_found", "Item não encontrado.")

    delivery.consumed_at = _now()
    db.flush()
    return item
