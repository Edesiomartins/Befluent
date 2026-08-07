"""Sequência pedagógica do dia: fases travadas e conteúdo encadeado.

Duas garantias distintas são verificadas aqui. A **ordem** (um bloco só abre
depois do anterior) e o **fio** (o bloco seguinte reaproveita o material do
anterior). Só a primeira já existia: sem a segunda, a sequência era de rótulos.
"""

from datetime import date

from sqlalchemy import select

from app.core.curriculum import BlockSkill, LessonPhase, block_phase
from app.core.levels import CEFRLevel, LevelSource
from app.models import (
    CurriculumBlock,
    CurriculumDay,
    CurriculumWeek,
    Language,
    ReviewItem,
    User,
    UserLanguage,
)
from app.services.curriculum_generator import generate_curriculum

START = date(2026, 8, 3)


def _profile(db, language_code="en", entry=CEFRLevel.A2):
    user = db.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db.scalar(select(Language).where(Language.code == language_code))
    profile = UserLanguage(
        user_id=user.id,
        language_id=language.id,
        is_active=True,
        onboarding_completed=True,
        diagnostic_completed=True,
        current_level=entry,
        level_source=LevelSource.PLACEMENT_TEST,
        vocabulary_grammar_level=entry,
        reading_level=entry,
        listening_level=entry,
        writing_level=entry,
        speaking_level=entry,
    )
    db.add(profile)
    db.commit()
    return profile, user


def _full_day(db, curriculum):
    days = list(
        db.scalars(
            select(CurriculumDay)
            .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
            .where(CurriculumWeek.curriculum_id == curriculum.id)
            .order_by(CurriculumDay.day_number)
        )
    )
    for day in days:
        blocks = list(
            db.scalars(
                select(CurriculumBlock)
                .where(CurriculumBlock.day_id == day.id)
                .order_by(CurriculumBlock.position)
            )
        )
        if len(blocks) >= 5:
            return day, blocks
    day = days[0]
    blocks = list(
        db.scalars(
            select(CurriculumBlock)
            .where(CurriculumBlock.day_id == day.id)
            .order_by(CurriculumBlock.position)
        )
    )
    return day, blocks


def test_day_follows_activate_to_consolidate_phases(db_session):
    profile, _ = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    _, blocks = _full_day(db_session, curriculum)
    phases = [block_phase(block.skill) for block in blocks]
    assert phases[0] == LessonPhase.ACTIVATE
    assert LessonPhase.STRUCTURE in phases
    assert LessonPhase.INPUT in phases or LessonPhase.OUTPUT in phases
    assert phases[-1] == LessonPhase.CONSOLIDATE


def test_start_block_rejects_skipping_ahead(client, auth, db_session):
    profile, _ = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    _, blocks = _full_day(db_session, curriculum)
    assert len(blocks) >= 2
    locked = client.post(
        f"/api/v1/curriculum/block/{blocks[1].id}/start", headers=auth, json={}
    )
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "curriculum_block_locked"

    opened = client.post(
        f"/api/v1/curriculum/block/{blocks[0].id}/start", headers=auth, json={}
    )
    assert opened.status_code == 200
    assert opened.json()["block"]["locked"] is False
    assert opened.json()["block"]["is_current"] is True


def test_day_payload_marks_locked_blocks(client, auth, db_session):
    profile, _ = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    day, _ = _full_day(db_session, curriculum)
    detail = client.get(f"/api/v1/curriculum/day/{day.id}", headers=auth)
    assert detail.status_code == 200
    body = detail.json()["day"]
    assert "Ativar" in body["sequence_label"]
    blocks = body["blocks"]
    assert blocks[0]["locked"] is False
    assert blocks[0]["is_current"] is True
    assert blocks[1]["locked"] is True

    first_id = blocks[0]["id"]
    assert (
        client.post(f"/api/v1/curriculum/block/{first_id}/start", headers=auth, json={}).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/curriculum/block/{first_id}/complete", headers=auth, json={}
        ).status_code
        == 200
    )
    again = client.get(f"/api/v1/curriculum/day/{day.id}", headers=auth).json()["day"]["blocks"]
    assert again[1]["locked"] is False
    assert again[1]["is_current"] is True


def _run_until(client, auth, blocks, target_skill):
    """Executa a sequência até o bloco pedido e devolve (lições, bloco-alvo).

    Devolve o payload de cada bloco aberto no caminho, que é o que permite
    comparar o que um bloco entregou com o que o seguinte reaproveitou.
    """
    lessons = {}
    for block in blocks:
        payload = client.post(
            f"/api/v1/curriculum/block/{block.id}/start", headers=auth, json={}
        ).json()["lesson"]
        lessons[block.skill] = payload
        if block.skill == target_skill:
            return lessons, block
        client.post(f"/api/v1/curriculum/block/{block.id}/complete", headers=auth, json={})
    return lessons, None


def test_conversation_reuses_the_vocabulary_of_the_day(client, auth, db_session):
    """Produção usa o léxico ativado no início do dia, não uma lista paralela."""
    profile, _ = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    _, blocks = _full_day(db_session, curriculum)

    lessons, conversation = _run_until(client, auth, blocks, BlockSkill.CONVERSATION)
    assert conversation is not None

    studied = {item["term"] for item in lessons[BlockSkill.VOCABULARY]["items"]}
    targets = set(lessons[BlockSkill.CONVERSATION]["target_expressions"])
    assert targets
    assert targets <= studied
    assert lessons[BlockSkill.CONVERSATION]["thread"]["carried_terms"]


def test_grammar_applies_to_the_words_just_introduced(client, auth, db_session):
    profile, _ = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    _, blocks = _full_day(db_session, curriculum)

    lessons, grammar = _run_until(client, auth, blocks, BlockSkill.GRAMMAR)
    assert grammar is not None
    studied = {item["term"] for item in lessons[BlockSkill.VOCABULARY]["items"]}
    assert set(lessons[BlockSkill.GRAMMAR]["apply_to_terms"]) <= studied


def test_completing_a_block_feeds_the_spaced_repetition_queue(client, auth, db_session):
    """O ciclo fecha: o que foi estudado hoje passa a existir na fila do SRS."""
    profile, _ = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    _, blocks = _full_day(db_session, curriculum)
    vocabulary = next(block for block in blocks if block.skill == BlockSkill.VOCABULARY)

    started = client.post(
        f"/api/v1/curriculum/block/{vocabulary.id}/start", headers=auth, json={}
    ).json()
    studied = {item["term"] for item in started["lesson"]["items"]}

    before = db_session.scalar(
        select(ReviewItem).where(ReviewItem.user_language_id == profile.id)
    )
    assert before is None

    done = client.post(
        f"/api/v1/curriculum/block/{vocabulary.id}/complete", headers=auth, json={}
    ).json()
    assert done["review_items_added"] > 0

    db_session.expire_all()
    enrolled = {
        (item.payload_json or {}).get("term")
        for item in db_session.scalars(
            select(ReviewItem).where(ReviewItem.user_language_id == profile.id)
        )
    }
    assert enrolled <= studied
    assert enrolled


def test_two_days_do_not_open_with_the_same_lexicon(client, auth, db_session):
    """O banco é pequeno, mas o dia 2 não pode abrir idêntico ao dia 1."""
    profile, _ = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    days = list(
        db_session.scalars(
            select(CurriculumDay)
            .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
            .where(CurriculumWeek.curriculum_id == curriculum.id)
            .order_by(CurriculumDay.day_number)
            .limit(2)
        )
    )
    opened = []
    for day in days:
        first = db_session.scalar(
            select(CurriculumBlock)
            .where(CurriculumBlock.day_id == day.id)
            .order_by(CurriculumBlock.position)
        )
        payload = client.post(
            f"/api/v1/curriculum/block/{first.id}/start", headers=auth, json={}
        ).json()["lesson"]
        opened.append([item["term"] for item in payload["items"]])

    assert opened[0] != opened[1]


def test_day_payload_exposes_the_thread(client, auth, db_session):
    profile, _ = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    day, blocks = _full_day(db_session, curriculum)

    empty = client.get(f"/api/v1/curriculum/day/{day.id}", headers=auth).json()["day"]
    assert empty["thread"]["terms"] == []

    client.post(f"/api/v1/curriculum/block/{blocks[0].id}/start", headers=auth, json={})
    filled = client.get(f"/api/v1/curriculum/day/{day.id}", headers=auth).json()["day"]
    assert filled["thread"]["terms"]
    assert filled["thread"]["sources"] == ["Vocabulário"]


def test_dashboard_prefers_curriculum_path(client, auth, db_session):
    profile, _ = _profile(db_session)
    generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    dash = client.get("/api/v1/dashboard", headers=auth)
    assert dash.status_code == 200
    body = dash.json()
    assert body["next_activity"]["kind"] == "curriculum"
    assert "/cronograma/dia/" in body["next_activity"]["href"]
    assert body["day_plan"]["source"] == "curriculum"
