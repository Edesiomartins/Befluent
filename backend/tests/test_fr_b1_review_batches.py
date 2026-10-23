"""Lotes FR B1 ficam em revisão e não entram como aprovados."""

from scripts.generate_fr_b1_review_batches import main


def test_fr_b1_review_batches_are_not_approved():
    report = main()
    assert report["ai_generation"] == "blocked"
    assert report["database"] == "sqlite-memory"
    assert report["generated"] == 10
    assert report["accepted_for_review"] == 9
    assert report["rejected"] == 1
    assert report["rejection_reasons"] == {"review_required": 1}
    assert report["accepted"]
    assert all(item["quality_status"] == "review_required" for item in report["accepted"])
    assert all(item["target_language"] == "fr" for item in report["accepted"])
    assert all(item["native_language"] == "pt-BR" for item in report["accepted"])
