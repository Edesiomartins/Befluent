"""Real account serialization; opt-in dedicated PostgreSQL 18 *_test only."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models import PlacementItemExposure, User
from app.schemas import PlacementTestCreate
from app.services.seed import seed_languages
from app.services.placement_seed import seed_placement_items
from app.api.placement_tests import create_test, next_item
from test_reset_test_user_learning_postgres import postgres_reset_database


def test_parallel_session_creation_and_delivery_are_one_logical_exposure(postgres_reset_database):
    engine, _, _ = postgres_reset_database
    with Session(engine) as db:
        seed_languages(db); seed_placement_items(db); db.commit()
    barrier = Barrier(2)
    def start():
        with Session(engine, autoflush=False, expire_on_commit=False) as db:
            user = db.get(User, "target")
            barrier.wait(timeout=15)
            test = create_test(PlacementTestCreate(language_code="en"), db, user)
            item = next_item(test["id"], db, user)
            return test["id"], item["item"]["id"], item["item"]["exposure"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(start) for _ in range(2)]
        results = [f.result(timeout=45) for f in futures]
    assert results[0] == results[1]
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(PlacementItemExposure)) == 1
