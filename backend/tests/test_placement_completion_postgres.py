"""Real concurrent finalization, opt-in dedicated PostgreSQL 18 *_test only."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.placement_tests import complete_test
from app.models import Base, Curriculum, PlacementTest, PlacementTestSection, User, UserLanguage
from app.services.placement_seed import seed_placement_items
from app.services.seed import seed_languages
from test_placement_completion import prepared_test
from test_reset_test_user_learning_postgres import postgres_reset_database


def test_parallel_completion_refreshes_stale_status_and_preserves_downstream(postgres_reset_database):
    engine, _, _ = postgres_reset_database
    with Session(engine, autoflush=False, expire_on_commit=False) as db:
        seed_languages(db)
        seed_placement_items(db)
        db.add(User(email="admin@befluent.local", name="Test", password_hash="unused", native_language="pt-BR"))
        db.commit()
        user, test = prepared_test(db)
        user_id, test_id = user.id, test.id

    barrier = Barrier(2)
    def finish():
        with Session(engine, autoflush=False, expire_on_commit=False) as db:
            user = db.get(User, user_id)
            # Both requests deliberately cache the old status before locking.
            cached_test = db.get(PlacementTest, test_id)
            assert cached_test.status == "in_progress"
            barrier.wait(timeout=15)
            result = complete_test(test_id, db, user)
            assert cached_test.status == "completed"
            return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(finish) for _ in range(2)]
        results = [future.result(timeout=45) for future in futures]
    assert results[0] == results[1]
    assert results[0]["status"] == "completed"
    with Session(engine, autoflush=False) as db:
        profile = db.scalar(select(UserLanguage).where(UserLanguage.user_id == user_id))
        assert db.scalar(select(func.count()).select_from(UserLanguage).where(UserLanguage.user_id == user_id)) == 1
        assert db.scalar(select(func.count()).select_from(Curriculum).where(Curriculum.user_language_id == profile.id)) == 1
        assert db.scalar(select(func.count()).select_from(PlacementTestSection).where(PlacementTestSection.test_id == test_id)) == 5
        def snapshot():
            return {table.name: list(db.execute(select(table)).mappings()) for table in Base.metadata.sorted_tables}
        before = snapshot()
        assert complete_test(test_id, db, db.get(User, user_id)) == results[0]
        assert snapshot() == before
