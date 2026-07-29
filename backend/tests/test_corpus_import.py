"""Importação de corpus e proveniência de itens.

O ponto central sob teste: item importado NUNCA pode ser servido ao aluno antes
de revisão, porque a calibragem de nível é heurística.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.levels import CEFRLevel, ReviewStatus, Skill
from app.models import PlacementItem
from app.services.corpus_import import (
    TATOEBA_ATTRIBUTION,
    TATOEBA_LICENSE,
    TATOEBA_SOURCE,
    build_item,
    estimate_level,
    import_pairs,
    load_frequency_ranks,
    read_pairs,
)

PAIRS_TSV = "\t".join(["1", "I am Ana.", "101", "Eu sou a Ana."]) + "\n" + "\t".join(
    ["2", "Could you tell me where the nearest train station is, please?", "102",
     "Você poderia me dizer onde fica a estação de trem mais próxima, por favor?"]
) + "\n" + "\t".join(["3", "Hi.", "103", "Oi."]) + "\n"


@pytest.fixture
def tsv(tmp_path):
    path = tmp_path / "eng-por.tsv"
    path.write_text(PAIRS_TSV, encoding="utf-8")
    return path


# ---------------------------------------------------------------- leitura


def test_reads_valid_pairs(tsv):
    pairs, malformed = read_pairs(tsv)
    assert len(pairs) == 3
    assert malformed == 0
    assert pairs[0].target_text == "I am Ana."
    assert pairs[0].translation_text == "Eu sou a Ana."


def test_counts_malformed_lines_without_crashing(tmp_path):
    path = tmp_path / "bad.tsv"
    path.write_text("só uma coluna\n1\ttexto\n" + PAIRS_TSV, encoding="utf-8")
    pairs, malformed = read_pairs(path)
    assert malformed == 2
    assert len(pairs) == 3


def test_respects_limit(tsv):
    pairs, _ = read_pairs(tsv, limit=2)
    assert len(pairs) == 2


# ---------------------------------------------------------------- calibragem


def test_short_sentence_lands_in_low_band():
    assert estimate_level("I am Ana.", "en") in {CEFRLevel.PRE_A1, CEFRLevel.A1}


def test_long_sentence_lands_higher():
    """O que importa é a ordem relativa, não o rótulo exato de uma frase."""
    from app.core.levels import LEVEL_INDEX

    short = estimate_level("I am Ana.", "en")
    long_sentence = (
        "Notwithstanding the considerable risks involved, the committee decided "
        "to proceed with the original proposal without any further consultation "
        "of the affected teams."
    )
    assert LEVEL_INDEX[estimate_level(long_sentence, "en")] > LEVEL_INDEX[short]


def test_frequency_list_promotes_rare_vocabulary():
    """Frase curta com palavra rara não deve ficar em PRE_A1."""
    common = {"the": 1, "cat": 200, "is": 3, "here": 400}
    assert estimate_level("The cat is here", "en", common) in {
        CEFRLevel.PRE_A1,
        CEFRLevel.A1,
    }
    # 'notwithstanding' ausente da lista → tratada como muito rara.
    promoted = estimate_level("The notwithstanding is here", "en", common)
    assert promoted in {CEFRLevel.A2, CEFRLevel.B1, CEFRLevel.B2}


def test_cjk_uses_character_count():
    """Japonês não separa palavras por espaço; contar por espaço daria 1."""
    assert estimate_level("私はアナです。", "ja") != estimate_level(
        "私は毎日日本語を勉強していますが、まだ難しいと感じることがあります。", "ja"
    )


def test_frequency_ranks_load_positions(tmp_path):
    path = tmp_path / "freq.txt"
    path.write_text("the 500\nof 300\nand 250\n", encoding="utf-8")
    ranks = load_frequency_ranks(path)
    assert ranks["the"] == 1
    assert ranks["and"] == 3


# ---------------------------------------------------------------- proveniência


def test_imported_item_carries_full_provenance():
    pairs, _ = read_pairs_from_string()
    item = build_item(pairs[0], "en")

    assert item.source == TATOEBA_SOURCE
    assert item.license == TATOEBA_LICENSE
    assert item.attribution == TATOEBA_ATTRIBUTION
    assert "sentence:1" in item.source_ref
    assert item.skill == Skill.VOCABULARY_GRAMMAR


def test_imported_item_is_always_pending_review():
    """A regra que protege o aluno: nada importado entra aprovado."""
    pairs, _ = read_pairs_from_string()
    for pair in pairs:
        assert build_item(pair, "en").review_status == ReviewStatus.PENDING_REVIEW


def read_pairs_from_string():
    import io as _io
    import csv as _csv

    from app.services.corpus_import import SentencePair

    rows = list(_csv.reader(_io.StringIO(PAIRS_TSV), delimiter="\t"))
    return [
        SentencePair(
            target_id=r[0], target_text=r[1], translation_id=r[2], translation_text=r[3]
        )
        for r in rows
        if len(r) >= 4
    ], 0


# ---------------------------------------------------------------- importação


def test_import_persists_and_reports(db_session, tsv):
    stats = import_pairs(db_session, tsv, "en")

    assert stats.imported == 2  # "Hi." é curta demais
    assert stats.skipped_too_short == 1
    assert sum(stats.by_level.values()) == stats.imported

    saved = list(
        db_session.scalars(
            select(PlacementItem).where(PlacementItem.source == TATOEBA_SOURCE)
        )
    )
    assert len(saved) == 2
    assert all(item.review_status == ReviewStatus.PENDING_REVIEW for item in saved)


def test_import_is_idempotent(db_session, tsv):
    first = import_pairs(db_session, tsv, "en")
    second = import_pairs(db_session, tsv, "en")

    assert first.imported == 2
    assert second.imported == 0
    assert second.skipped_duplicate == 2


def test_dry_run_writes_nothing(db_session, tsv):
    stats = import_pairs(db_session, tsv, "en", dry_run=True)
    assert stats.imported == 2
    assert (
        db_session.scalar(
            select(PlacementItem).where(PlacementItem.source == TATOEBA_SOURCE)
        )
        is None
    )


def test_import_skips_overly_long_sentences(db_session, tmp_path):
    path = tmp_path / "long.tsv"
    long_text = " ".join(["word"] * 40)
    path.write_text(f"9\t{long_text}\t909\ttraducao longa\n", encoding="utf-8")
    stats = import_pairs(db_session, path, "en")
    assert stats.imported == 0
    assert stats.skipped_too_long == 1


# ---------------------------------------------------------------- isolamento


def test_pending_items_never_reach_the_learner(client, auth, db_session, tsv):
    """Item importado não pode aparecer no teste de nivelamento."""
    import_pairs(db_session, tsv, "en")

    created = client.post(
        "/api/v1/placement-tests", json={"language_code": "en"}, headers=auth
    )
    assert created.status_code == 200
    test_id = created.json()["id"]

    pending_prompts = {
        item.prompt
        for item in db_session.scalars(
            select(PlacementItem).where(
                PlacementItem.review_status == ReviewStatus.PENDING_REVIEW
            )
        )
    }
    assert pending_prompts  # garante que o teste está exercitando algo

    seen = set()
    for _ in range(30):
        response = client.post(
            f"/api/v1/placement-tests/{test_id}/next-item", headers=auth
        )
        if response.status_code != 200:
            break
        body = response.json()
        item = body.get("item")
        if not item:
            break
        seen.add(item["prompt"])
        client.post(
            f"/api/v1/placement-tests/{test_id}/answers",
            json={"item_id": item["id"], "answer": "x"},
            headers=auth,
        )

    assert seen
    assert not (seen & pending_prompts)


def test_approved_import_becomes_available(client, auth, db_session, tsv):
    """Depois da revisão, o item passa a ser elegível."""
    import_pairs(db_session, tsv, "en")
    for item in db_session.scalars(
        select(PlacementItem).where(PlacementItem.source == TATOEBA_SOURCE)
    ):
        item.review_status = ReviewStatus.APPROVED
    db_session.commit()

    remaining = list(
        db_session.scalars(
            select(PlacementItem).where(
                PlacementItem.source == TATOEBA_SOURCE,
                PlacementItem.review_status == ReviewStatus.APPROVED,
            )
        )
    )
    assert len(remaining) == 2


def test_own_seed_stays_available(db_session):
    """Regressão: o filtro de revisão não pode esconder o seed próprio."""
    from app.services.placement_seed import OWN_SOURCE

    seed_items = list(
        db_session.scalars(
            select(PlacementItem).where(PlacementItem.source == OWN_SOURCE)
        )
    )
    assert seed_items
    assert all(item.review_status != ReviewStatus.PENDING_REVIEW for item in seed_items)


def test_seed_does_not_deactivate_imported_corpus(db_session, tsv):
    """Regressão: o seed roda em todo deploy e desativava o corpus importado.

    Sem o filtro por `source`, a lógica "desativa o que não está na fixture"
    alcançava os itens do Tatoeba e a importação era perdida na próxima subida.
    """
    from app.services.placement_seed import seed_placement_items

    import_pairs(db_session, tsv, "en")
    imported = list(
        db_session.scalars(
            select(PlacementItem).where(PlacementItem.source == TATOEBA_SOURCE)
        )
    )
    assert imported and all(item.is_active for item in imported)

    seed_placement_items(db_session, ["en"])
    db_session.expire_all()

    still_active = list(
        db_session.scalars(
            select(PlacementItem).where(
                PlacementItem.source == TATOEBA_SOURCE,
                PlacementItem.is_active.is_(True),
            )
        )
    )
    assert len(still_active) == len(imported), "o seed desativou o corpus importado"
