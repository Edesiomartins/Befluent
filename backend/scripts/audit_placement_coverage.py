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
    from app.models import PlacementItem
    from app.services.placement_coverage import catalog_matrix
    items = [PlacementItem(language_code=r["language_code"], skill=r["skill"],
        cefr_level=r["cefr_level"], item_type=r["item_type"], prompt=r["prompt"],
        instructions=r.get("instructions"), passage=r.get("passage"), audio_script=r.get("audio_script"),
        audio_url=r.get("audio_url"), options_json=r.get("options_json", r.get("options", [])),
        correct_answer_json=r.get("correct_answer_json", r.get("correct_answer", {})),
        rubric_json=r.get("rubric_json", r.get("rubric", {})), is_active=r.get("is_active"),
        review_status=r.get("review_status")) for r in rows]
    matrix = Counter((r["language_code"], r["skill"], r["cefr_level"], r["item_type"],
                      bool(r.get("is_active")), r.get("review_status")) for r in rows)
    print(json.dumps({"source": "database_read_only" if args.database else "versioned_fixtures",
        "total": len(rows), "fresh_scope": "hypothetical_unexposed_account",
        "independent_matrix": catalog_matrix(items), "matrix": [{"language": key[0], "skill": key[1], "cefr": key[2],
        "item_type": key[3], "active": key[4], "review_status": key[5], "count": count}
        for key, count in sorted(matrix.items(), key=lambda x: str(x[0]))]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
