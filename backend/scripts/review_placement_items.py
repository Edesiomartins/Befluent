"""CLI de revisão de itens de nivelamento (PlacementItem)."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.core.levels import ReviewStatus  # noqa: E402
from app.models import AuditLog, PlacementItem  # noqa: E402


def _now() -> datetime:
    return datetime.now(timezone.utc)


def cmd_list(db, args) -> int:
    query = select(PlacementItem)
    if args.language:
        query = query.where(PlacementItem.language_code == args.language)
    if args.status:
        query = query.where(PlacementItem.review_status == args.status)
    items = list(db.scalars(query.order_by(PlacementItem.language_code, PlacementItem.external_key)))
    for item in items:
        print(
            f"{item.id}\t{item.language_code}\t{item.review_status or 'null'}\t"
            f"{item.skill}\t{item.external_key}\t{item.is_active}"
        )
    print(f"Total: {len(items)}")
    return 0


def cmd_show(db, args) -> int:
    item = db.get(PlacementItem, args.id) or db.scalar(
        select(PlacementItem).where(PlacementItem.external_key == args.id)
    )
    if not item:
        print("Item não encontrado.", file=sys.stderr)
        return 1
    payload = {
        "id": item.id,
        "external_key": item.external_key,
        "language_code": item.language_code,
        "cefr_level": item.cefr_level,
        "skill": item.skill,
        "item_type": item.item_type,
        "prompt": item.prompt,
        "review_status": item.review_status,
        "source": item.source,
        "license": item.license,
        "is_active": item.is_active,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _audit(db, *, action: str, item: PlacementItem, metadata: dict) -> None:
    db.add(
        AuditLog(
            action=action,
            resource_type="placement_item",
            resource_id=item.id,
            metadata_json=metadata,
        )
    )


def cmd_approve(db, args) -> int:
    item = db.get(PlacementItem, args.id)
    if not item:
        print("Item não encontrado.", file=sys.stderr)
        return 1
    item.review_status = ReviewStatus.APPROVED
    item.is_active = True
    item.updated_at = _now()
    _audit(
        db,
        action="placement_item_approved",
        item=item,
        metadata={"reason": args.reason or "manual_review"},
    )
    db.commit()
    print(f"Aprovado: {item.id} ({item.external_key})")
    return 0


def cmd_reject(db, args) -> int:
    if not args.reason or not args.reason.strip():
        print("Rejeição exige --reason.", file=sys.stderr)
        return 2
    item = db.get(PlacementItem, args.id)
    if not item:
        print("Item não encontrado.", file=sys.stderr)
        return 1
    item.review_status = ReviewStatus.REJECTED
    item.is_active = False
    item.updated_at = _now()
    _audit(
        db,
        action="placement_item_rejected",
        item=item,
        metadata={"reason": args.reason.strip()},
    )
    db.commit()
    print(f"Rejeitado: {item.id} ({item.external_key})")
    return 0


def cmd_report(db, _args) -> int:
    rows = db.execute(
        select(PlacementItem.review_status, func.count())
        .group_by(PlacementItem.review_status)
        .order_by(PlacementItem.review_status)
    ).all()
    print("Relatório de revisão — placement_items")
    for status, count in rows:
        print(f"  {status or 'null'}: {count}")
    inactive = db.scalar(
        select(func.count()).where(
            PlacementItem.is_active.is_(False),
            PlacementItem.review_status == ReviewStatus.APPROVED,
        )
    )
    print(f"  approved_inactive: {inactive or 0}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Revisão de itens de nivelamento BeFluent")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="Lista itens")
    p_list.add_argument("--language", help="Filtra por idioma")
    p_list.add_argument("--status", help="Filtra por review_status")

    p_show = sub.add_parser("show", help="Mostra um item")
    p_show.add_argument("id", help="ID ou external_key")

    p_approve = sub.add_parser("approve", help="Aprova item (nunca automático em import)")
    p_approve.add_argument("id")
    p_approve.add_argument("--reason", default="manual_review")

    p_reject = sub.add_parser("reject", help="Rejeita item")
    p_reject.add_argument("id")
    p_reject.add_argument("--reason", required=True)

    sub.add_parser("report", help="Resumo por status")

    args = parser.parse_args(argv)
    with SessionLocal() as db:
        if args.command == "list":
            return cmd_list(db, args)
        if args.command == "show":
            return cmd_show(db, args)
        if args.command == "approve":
            return cmd_approve(db, args)
        if args.command == "reject":
            return cmd_reject(db, args)
        if args.command == "report":
            return cmd_report(db, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
