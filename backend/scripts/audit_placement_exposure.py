"""Read-only exposure inventory for one account/language. Never seeds or calls AI."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--language-code", required=True)
    args = parser.parse_args()
    from scripts.audit_placement_result import read_only_snapshot
    from app.core.database import engine
    from app.services.placement_exposure import exposure_history, bank_freshness
    from sqlalchemy.orm import Session
    with read_only_snapshot(engine) as connection:
        with Session(bind=connection) as db:
            history = exposure_history(db, args.user_id, args.language_code)
            print(json.dumps({"user_id": args.user_id, "language": args.language_code,
                "seen_events": len(history), "answered_events": sum(bool(e.get("answered")) for e in history),
                "revealed_events": sum(bool(e.get("revealed")) for e in history),
                "legacy_events": sum(e.get("origin") == "legacy_current_item" for e in history),
                "bank_freshness": bank_freshness(db, args.user_id, args.language_code)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
