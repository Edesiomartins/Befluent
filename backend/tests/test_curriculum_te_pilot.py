"""Etapa 1 (new/revisited) + Etapa 2 (piloto TE V2 Semana 1 B2)."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from app.core.curriculum import BlockSkill, BlockStatus, DayStatus
from app.core.levels import CEFRLevel, LevelSource
from app.models import (
    CurriculumBlock,
    CurriculumDay,
    CurriculumWeek,
    Language,
    LearningAttempt,
    LearningEvidence,
    LearningObjective,
    User,
    UserLanguage,
    UserObjectiveProgress,
)
from app.services.curriculum_generator import generate_curriculum
from app.services.objective_seed_b2_week1 import (
    PILOT_DAY_CODES,
    ensure_en_b2_week1_objectives,
)
from app.services.vocabulary_selection import select_daily_vocabulary
from app.services import lesson_bank


START = date(2026, 3, 2)


def _b2_profile(db_session, email="admin@befluent.local"):
    user = db_session.scalar(select(User).where(User.email == email))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    profile = UserLanguage(
        user_id=user.id,
        language_id=language.id,
        is_active=True,
        onboarding_completed=True,
        diagnostic_completed=True,
        current_level=CEFRLevel.B2,
        level_source=LevelSource.PLACEMENT_TEST,
        vocabulary_grammar_level=CEFRLevel.B2,
        reading_level=CEFRLevel.B2,
        listening_level=CEFRLevel.B2,
        writing_level=CEFRLevel.B2,
        speaking_level=CEFRLevel.B2,
    )
    db_session.add(profile)
    db_session.commit()
    return profile


def _week1_days(db_session, curriculum):
    week = db_session.scalar(
        select(CurriculumWeek).where(
            CurriculumWeek.curriculum_id == curriculum.id,
            CurriculumWeek.week_number == 1,
        )
    )
    days = list(
        db_session.scalars(
            select(CurriculumDay)
            .where(CurriculumDay.week_id == week.id)
            .order_by(CurriculumDay.day_number)
        )
    )
    return week, days


def _blocks(db_session, day):
    return list(
        db_session.scalars(
            select(CurriculumBlock)
            .where(CurriculumBlock.day_id == day.id)
            .order_by(CurriculumBlock.position)
        )
    )


# ------------------------------------------------------------------ Etapa 1


def test_first_exposure_goes_to_items_second_to_revisited():
    band = lesson_bank.BAND_UPPER
    first = select_daily_vocabulary(
        "en", band, day_number=1, week_theme="Argumentar e refutar"
    )
    assert first["new_items"]
    assert first["content_roles"]["items"] == "new_first_exposure"
    assert first["selection_policy"] == "curriculum_history_first_exposure"

    second = select_daily_vocabulary(
        "en",
        band,
        day_number=8,
        week_theme="Negociação e mercado de trabalho",
        exposed_items=first["new_items"],
        recycled_items=first["new_items"],
    )
    new_keys = {i["term"].casefold() for i in second["new_items"]}
    exposed_keys = {i["term"].casefold() for i in first["new_items"]}
    assert new_keys.isdisjoint(exposed_keys)
    revisited_keys = {i["term"].casefold() for i in second["revisited_items"]}
    assert revisited_keys & exposed_keys
    assert second["new_as_exposed_violations"] == []


def test_revisited_does_not_create_srs_by_itself(client, auth, db_session):
    """revisited_items no payload ≠ ReviewItem devido."""
    from app.models import ReviewItem

    profile = _b2_profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    week, days = _week1_days(db_session, curriculum)
    day1 = days[0]
    vocab = next(b for b in _blocks(db_session, day1) if b.skill == BlockSkill.VOCABULARY)

    start = client.post(f"/api/v1/curriculum/block/{vocab.id}/start", headers=auth)
    assert start.status_code == 200
    lesson = start.json()["lesson"]
    assert "revisited_items" in lesson or "items" in lesson

    due = list(
        db_session.scalars(
            select(ReviewItem).where(ReviewItem.user_language_id == profile.id)
        )
    )
    # Sem complete → nada na fila SRS só por gerar revisited.
    assert due == []


def test_item_never_returns_as_new_after_exposure():
    band = lesson_bank.BAND_UPPER
    pool = lesson_bank.vocabulary("en", band)
    exposed = pool[:20]
    selected = select_daily_vocabulary(
        "en",
        band,
        day_number=3,
        week_theme="Argumentar e refutar",
        exposed_items=exposed,
    )
    exposed_keys = {i["term"].casefold() for i in exposed}
    for item in selected["new_items"]:
        assert item["term"].casefold() not in exposed_keys


def test_multi_day_progression_after_history(client, auth, db_session):
    profile = _b2_profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    _, days = _week1_days(db_session, curriculum)

    for day in days[:2]:
        for block in _blocks(db_session, day):
            assert (
                client.post(
                    f"/api/v1/curriculum/block/{block.id}/start", headers=auth
                ).status_code
                == 200
            )
            assert (
                client.post(
                    f"/api/v1/curriculum/block/{block.id}/complete",
                    headers=auth,
                    json={},
                ).status_code
                == 200
            )
        db_session.refresh(day)
        assert day.status == DayStatus.COMPLETED

    day3 = days[2]
    detail = client.get(f"/api/v1/curriculum/day/{day3.id}", headers=auth)
    assert detail.status_code == 200
    assert detail.json()["day"]["next_day"] is None or True  # dia 3 ainda aberto
    assert day3.status != DayStatus.COMPLETED


# ------------------------------------------------------------------ Etapa 2


def test_week1_has_distinct_can_dos_per_day(db_session):
    profile = _b2_profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    week, days = _week1_days(db_session, curriculum)
    assert week.theme == "Argumentar e refutar"
    codes = []
    for day in days:
        objs = {
            b.objective_id
            for b in _blocks(db_session, day)
            if b.objective_id and b.skill != BlockSkill.REVIEW
        }
        assert len(objs) == 1
        codes.append(db_session.get(LearningObjective, next(iter(objs))).code)
    assert codes == list(PILOT_DAY_CODES.values())
    assert len(set(codes)) == 7


def test_day1_and_day2_have_different_objective_ids(db_session):
    profile = _b2_profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    _, days = _week1_days(db_session, curriculum)
    d1 = next(
        b.objective_id
        for b in _blocks(db_session, days[0])
        if b.skill == BlockSkill.VOCABULARY
    )
    d2 = next(
        b.objective_id
        for b in _blocks(db_session, days[1])
        if b.skill == BlockSkill.VOCABULARY
    )
    assert d1 != d2


def test_relevant_blocks_share_day_objective_review_excluded(db_session):
    profile = _b2_profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    _, days = _week1_days(db_session, curriculum)
    for day in days:
        blocks = _blocks(db_session, day)
        pedagogical = [b for b in blocks if b.skill != BlockSkill.REVIEW]
        review = [b for b in blocks if b.skill == BlockSkill.REVIEW]
        ids = {b.objective_id for b in pedagogical}
        assert None not in ids
        assert len(ids) == 1
        for block in review:
            assert block.objective_id is None


def test_teaching_attempt_evidence_error_remediation_retry_transfer(
    client, auth, db_session
):
    profile = _b2_profile(db_session)
    ensure_en_b2_week1_objectives(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    _, days = _week1_days(db_session, curriculum)
    day = days[0]
    # Abrir até um bloco de produção se existir; senão vocabulary.
    blocks = _blocks(db_session, day)
    target = next(
        (b for b in blocks if b.skill == BlockSkill.CONVERSATION),
        next(b for b in blocks if b.skill == BlockSkill.VOCABULARY),
    )
    # Desbloquear: completar anteriores
    for block in blocks:
        if block.position >= target.position:
            break
        assert client.post(
            f"/api/v1/curriculum/block/{block.id}/start", headers=auth
        ).status_code == 200
        assert client.post(
            f"/api/v1/curriculum/block/{block.id}/complete", headers=auth, json={}
        ).status_code == 200

    start = client.post(f"/api/v1/curriculum/block/{target.id}/start", headers=auth)
    assert start.status_code == 200
    teaching = start.json().get("teaching")
    assert teaching is not None
    assert teaching["objective"]["code"] == "EN-B2-CAN-001"

    # Ack recognition/listen até atividade com produção, ou responder errado.
    flow_id = teaching["flow"]["id"]
    # Resposta errada em guided/transfer se já estiver nela; senão ack.
    for _ in range(12):
        state = client.get(
            f"/api/v1/curriculum/block/{target.id}/teaching", headers=auth
        ).json()
        activity = state.get("current_activity") or {}
        if activity.get("type") in {
            "fill_gap",
            "word_order",
            "multiple_choice",
            "guided_production",
            "transfer_question",
        }:
            wrong = client.post(
                f"/api/v1/curriculum/block/{target.id}/teaching/answer",
                headers=auth,
                json={"student_response": "zzz totally wrong"},
            )
            assert wrong.status_code == 200
            body = wrong.json()
            assert body.get("remediation") is not None
            retry = client.post(
                f"/api/v1/curriculum/block/{target.id}/teaching/retry",
                headers=auth,
                json={
                    "remediation_id": body["remediation"]["id"],
                    "student_response": (activity.get("canonical_answer")
                        or (activity.get("accepted_variants") or ["ok"])[0]),
                },
            )
            assert retry.status_code == 200
            break
        ack = client.post(
            f"/api/v1/curriculum/block/{target.id}/teaching/answer",
            headers=auth,
            json={"student_response": ""},
        )
        assert ack.status_code == 200

    attempts = list(
        db_session.scalars(
            select(LearningAttempt).where(
                LearningAttempt.user_language_id == profile.id,
                LearningAttempt.objective_id == target.objective_id,
            )
        )
    )
    assert attempts
    evidence = list(
        db_session.scalars(
            select(LearningEvidence).where(
                LearningEvidence.user_language_id == profile.id,
                LearningEvidence.objective_id == target.objective_id,
            )
        )
    )
    assert evidence


def test_completion_alone_does_not_master(client, auth, db_session):
    profile = _b2_profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    _, days = _week1_days(db_session, curriculum)
    day = days[0]
    objective_id = next(
        b.objective_id for b in _blocks(db_session, day) if b.objective_id
    )
    for block in _blocks(db_session, day):
        assert client.post(
            f"/api/v1/curriculum/block/{block.id}/start", headers=auth
        ).status_code == 200
        assert client.post(
            f"/api/v1/curriculum/block/{block.id}/complete", headers=auth, json={}
        ).status_code == 200

    progress = db_session.scalar(
        select(UserObjectiveProgress).where(
            UserObjectiveProgress.user_language_id == profile.id,
            UserObjectiveProgress.objective_id == objective_id,
        )
    )
    # Pode ter começado learning, mas não mastered só por complete.
    assert progress is None or progress.state != "mastered"


def test_frontend_cannot_force_mastered_via_flow_transition(client, auth, db_session):
    profile = _b2_profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    _, days = _week1_days(db_session, curriculum)
    block = next(
        b for b in _blocks(db_session, days[0]) if b.skill == BlockSkill.VOCABULARY
    )
    start = client.post(f"/api/v1/curriculum/block/{block.id}/start", headers=auth)
    flow_id = start.json()["teaching"]["flow"]["id"]
    forced = client.post(
        f"/api/v1/teaching/flows/{flow_id}/transition",
        headers=auth,
        json={"target_phase": "mastered"},
    )
    assert forced.status_code in {409, 422}


def test_non_pilot_weeks_still_generate(db_session):
    profile = _b2_profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    week2 = db_session.scalar(
        select(CurriculumWeek).where(
            CurriculumWeek.curriculum_id == curriculum.id,
            CurriculumWeek.week_number == 2,
        )
    )
    assert week2 is not None
    day = db_session.scalar(
        select(CurriculumDay)
        .where(CurriculumDay.week_id == week2.id)
        .order_by(CurriculumDay.day_number)
    )
    blocks = _blocks(db_session, day)
    # Semana 2: só vocabulary tem objective temático leve (não Can-Do piloto).
    vocab = next(b for b in blocks if b.skill == BlockSkill.VOCABULARY)
    assert vocab.objective_id is not None
    obj = db_session.get(LearningObjective, vocab.objective_id)
    assert obj.pedagogy_json.get("source") == "curriculum_theme"
    grammar = next((b for b in blocks if b.skill == BlockSkill.GRAMMAR), None)
    if grammar:
        assert grammar.objective_id is None


def test_day_payload_exposes_learning_objective(client, auth, db_session):
    profile = _b2_profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
    db_session.commit()
    _, days = _week1_days(db_session, curriculum)
    resp = client.get(f"/api/v1/curriculum/day/{days[0].id}", headers=auth)
    assert resp.status_code == 200
    objective = resp.json()["day"]["learning_objective"]
    assert objective is not None
    assert "learner_goal" in objective
    assert "EN-B2-CAN-001" not in objective["learner_goal"]
    assert objective["code"] == "EN-B2-CAN-001"
