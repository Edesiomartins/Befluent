"""Read-only full coverage inventory. Defaults to versioned fixtures, never seeds."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", action="store_true", help="Read configured database in verified read-only transaction")
    args = parser.parse_args()
    if args.database:
        from scripts.audit_placement_result import read_only_snapshot
        from app.core.database import engine
        from app.models import PlacementItem
        from sqlalchemy import select
        with read_only_snapshot(engine) as connection:
            rows = list(connection.execute(select(PlacementItem.__table__)).mappings())
    else:
        rows = []
        for path in sorted((Path(__file__).resolve().parents[1] / "app/data/placement_items").glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            rows.extend({**item, "language_code": data["language_code"], "is_active": True,
                         "review_status": "approved"} for item in data["items"])
    matrix = Counter((r["language_code"], r["skill"], r["cefr_level"], r["item_type"],
                      bool(r.get("is_active")), r.get("review_status")) for r in rows)
    print(json.dumps({"source": "database_read_only" if args.database else "versioned_fixtures",
        "total": len(rows), "matrix": [{"language": key[0], "skill": key[1], "cefr": key[2],
        "item_type": key[3], "active": key[4], "review_status": key[5], "count": count}
        for key, count in sorted(matrix.items(), key=lambda x: str(x[0]))]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
