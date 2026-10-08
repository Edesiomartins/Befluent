"""Read-only diagnostic contracts; no production database used."""
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.models import Base, PlacementTestAnswer, PlacementItemDelivery
from test_placement_completion import prepared_test


def test_report_preserves_rows_and_explains_exclusions(db_session):
    from scripts.audit_placement_result import collect_report
    _, test = prepared_test(db_session)
    answers = list(db_session.scalars(select(PlacementTestAnswer).where(
        PlacementTestAnswer.test_id == test.id)))
    for answer in answers:
        db_session.add(PlacementItemDelivery(test_id=test.id, item_id=answer.item_id,
                                            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
    db_session.commit()
    def snapshot():
        return {t.name: list(db_session.execute(select(t)).mappings()) for t in Base.metadata.sorted_tables}
    before = snapshot()
    report = collect_report(db_session.connection(), test.id)
    assert snapshot() == before
    assert len(report["activities"]) == 13
    assert report["counts_by_skill"]["writing"]["records"] == 0
    assert report["counts_by_skill"]["reading"]["records"] == 4
    assert report["recomputed_result"]["overall_level"] == "A2"
    assert report["overall_calculation"]["weighted_index"] == 2.0
    assert report["overall_calculation"]["weights"] == {
        "vocabulary_grammar": 1 / 3, "reading": 1 / 3, "listening": 1 / 3}
    # 40 base + 15 volume + 12 three skills - 7 absent speaking = 60.
    assert report["confidence_calculation"]["final"] == 60.0
    writing = next(row for row in report["activities"] if row["answer"]["skill"] == "writing")
    assert writing["records_exclusion_reason"] == "production_skill_excluded_by_records"
    assert writing["has_voice_recording"] is False
    assert report["counts_by_skill"]["speaking"]["answered"] == 0


def test_read_only_snapshot_rejects_writes_and_restores_connection(db_session):
    from scripts.audit_placement_result import read_only_snapshot
    engine = db_session.get_bind()
    with read_only_snapshot(engine) as conn:
        assert conn.exec_driver_sql("PRAGMA query_only").scalar() == 1
        with pytest.raises(DBAPIError):
            conn.execute(text("UPDATE placement_tests SET status='completed'"))
    with engine.connect() as conn:
        assert conn.exec_driver_sql("PRAGMA query_only").scalar() == 0


def test_unknown_test_fails_closed(db_session):
    from scripts.audit_placement_result import collect_report
    with pytest.raises(ValueError, match="placement_test_not_found"):
        collect_report(db_session.connection(), "missing")


def test_unanswered_deliveries_and_answers_without_delivery_are_retained(db_session):
    from scripts.audit_placement_result import collect_report
    from app.models import PlacementItem
    _, test = prepared_test(db_session)
    used = list(db_session.scalars(select(PlacementTestAnswer.item_id).where(PlacementTestAnswer.test_id == test.id)))
    item = db_session.scalar(select(PlacementItem).where(PlacementItem.id.not_in(used)))
    db_session.add(PlacementItemDelivery(test_id=test.id, item_id=item.id,
                                        expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
    db_session.commit()
    report = collect_report(db_session.connection(), test.id)
    assert len(report["activities"]) == 14
    assert sum(row["answer"] is None for row in report["activities"]) == 1
    assert sum(row["delivery"] is None for row in report["activities"]) == 13


def test_diagnostic_distinguishes_missing_score_from_band_coverage(db_session):
    from scripts.audit_placement_result import collect_report
    _, test = prepared_test(db_session)
    answers = list(db_session.scalars(select(PlacementTestAnswer).where(PlacementTestAnswer.test_id == test.id)))
    reading = [answer for answer in answers if answer.skill == "reading"]
    reading[0].normalized_score = None
    listening = [answer for answer in answers if answer.skill == "listening"]
    for answer, band in zip(listening, ["A1", "A2", "B1", "B2"]):
        answer.cefr_level = band
    db_session.commit()
    report = collect_report(db_session.connection(), test.id)
    assert report["counts_by_skill"]["reading"]["records"] == 3
    assert report["skill_evidence"]["reading"]["no_cefr_reason"] == "fewer_than_min_items_per_skill"
    assert report["skill_evidence"]["listening"]["records"] == 4
    assert report["skill_evidence"]["listening"]["no_cefr_reason"] == "no_band_meets_minimum_count_and_accuracy"
    assert report["recomputed_result"]["weights_used"] == {"vocabulary_grammar": 1.0}


def test_calibrating_comparison_uses_final_api_contract(db_session):
    from scripts.audit_placement_result import collect_report
    _, test = prepared_test(db_session)
    for answer in db_session.scalars(select(PlacementTestAnswer).where(PlacementTestAnswer.test_id == test.id)):
        answer.normalized_score = 0.0
    test.confidence_score = None
    test.result_json = {"diagnostic_status": "calibrating", "confidence_score": None}
    db_session.commit()
    report = collect_report(db_session.connection(), test.id)
    assert report["raw_engine_result"]["confidence_score"] == 0.0
    assert report["recomputed_result"]["confidence_score"] is None
    assert report["stored_vs_recomputed"]["confidence_score"]["matches"] is True
