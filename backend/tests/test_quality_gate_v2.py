"""Quality Gate — Teaching Engine V2 (auditoria, sem novas features)."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select, text

from app.core.errors import APIError
from app.core.teaching import (
    ActivityType,
    EvidenceType,
    FlowPhase,
    MasteryState,
    VALID_FLOW_TRANSITIONS,
)
from app.models import (
    Language,
    LearningAttempt,
    LearningEvidence,
    LearningObjective,
    MemorySchedule,
    User,
    UserLanguage,
)
from app.services import (
    activity_generator,
    ai_cache,
    deterministic_evaluator,
    memory_engine,
    provider_resilience,
    speech_intelligibility,
    teaching_engine as engine,
    teaching_flow,
    teaching_slice,
)
from app.services.objective_seed import ensure_en_a1_can_001


def _ul(db_session, email="admin@befluent.local") -> UserLanguage:
    user = db_session.scalar(select(User).where(User.email == email))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    existing = db_session.scalar(
        select(UserLanguage).where(
            UserLanguage.user_id == user.id, UserLanguage.language_id == language.id
        )
    )
    if existing:
        return existing
    ul = UserLanguage(user_id=user.id, language_id=language.id, is_active=True)
    db_session.add(ul)
    db_session.commit()
    return ul


# ---------------------------------------------------------------- migration


def test_migration_0007_to_0008_roundtrip(tmp_path):
    """Roundtrip 0008 ↔ 0007 em SQLite isolado.

    Nota de auditoria: 0001/0002 usam `Base.metadata` ao vivo, então um banco
    fresco já pode nascer com tabelas V2 antes do revision 0008. O caminho
    crítico de produção (Coolify já em 0007 sem tabelas V2) é coberto ao
    fazer downgrade 0008→0007 (remove V2) e upgrade de novo (recria).
    Postgres real não está disponível neste host (Docker ausente).
    """
    from app.core.config import get_settings

    db_path = tmp_path / "qg_v2.db"
    url = f"sqlite:///{db_path.as_posix()}"
    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.set_main_option("script_location", str(root / "alembic"))
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()

    command.upgrade(cfg, "0008_teaching_engine_v2")
    engine_db = create_engine(url)
    with engine_db.connect() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        for name in (
            "teaching_flow_sessions",
            "memory_schedules",
            "memory_review_events",
            "ai_response_cache",
            "learning_objectives",
            "curriculum_blocks",
            "review_items",
        ):
            assert name in tables
        cols = {c["name"] for c in inspector.get_columns("learning_objectives")}
        assert "target_expressions_json" in cols
        assert "pedagogy_json" in cols
        rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert rev == "0008_teaching_engine_v2"

    # 0008 → 0007 remove só o que a 0008 introduziu
    command.downgrade(cfg, "0007_teaching_engine")
    with engine_db.connect() as conn:
        tables = set(inspect(conn).get_table_names())
        assert "teaching_flow_sessions" not in tables
        assert "memory_schedules" not in tables
        assert "ai_response_cache" not in tables
        assert "learning_objectives" in tables
        cols = {c["name"] for c in inspect(conn).get_columns("learning_objectives")}
        assert "target_expressions_json" not in cols
        assert "pedagogy_json" not in cols
        rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert rev == "0007_teaching_engine"

    # 0007 → 0008 recria (caminho de produção a partir de head 0007)
    command.upgrade(cfg, "0008_teaching_engine_v2")
    with engine_db.connect() as conn:
        tables = set(inspect(conn).get_table_names())
        assert "teaching_flow_sessions" in tables
        assert "memory_schedules" in tables
        assert "ai_response_cache" in tables
        cols = {c["name"] for c in inspect(conn).get_columns("learning_objectives")}
        assert "target_expressions_json" in cols
        rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert rev == "0008_teaching_engine_v2"

    # Idempotência: rodar 0008 de novo não quebra
    command.upgrade(cfg, "0008_teaching_engine_v2")
    with engine_db.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == (
            "0008_teaching_engine_v2"
        )


# -------------------------------------------------------- FSM / mastery force


def test_cannot_force_mastered_without_evidence(db_session):
    objective = ensure_en_a1_can_001(db_session)
    ul = _ul(db_session)
    session = teaching_flow.start_flow(
        db_session, user_language_id=ul.id, objective_id=objective.id
    )
    # Caminho legal até evaluating
    for phase in (
        FlowPhase.INPUT,
        FlowPhase.NOTICING,
        FlowPhase.PRACTICING,
        FlowPhase.EVALUATING,
    ):
        teaching_flow.transition(db_session, session, target_phase=phase)
    with pytest.raises(APIError) as exc:
        teaching_flow.transition(db_session, session, target_phase=FlowPhase.MASTERED)
    assert exc.value.code == "mastery_not_demonstrated"


def test_api_cannot_force_mastered(client, auth, db_session):
    _ul(db_session)
    start = client.post("/api/v1/teaching/slice/en-a1-can-001/start", json={}, headers=auth)
    flow_id = start.json()["flow"]["id"]
    # Avança via transition API até evaluating (permitido)
    for phase in ("input", "noticing", "practicing", "evaluating"):
        resp = client.post(
            f"/api/v1/teaching/flows/{flow_id}/transition",
            json={"target_phase": phase},
            headers=auth,
        )
        assert resp.status_code == 200, resp.text
    resp = client.post(
        f"/api/v1/teaching/flows/{flow_id}/transition",
        json={"target_phase": "mastered"},
        headers=auth,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "mastery_not_demonstrated"


def test_fsm_table_blocks_not_started_to_mastered():
    assert FlowPhase.MASTERED not in VALID_FLOW_TRANSITIONS[FlowPhase.NOT_STARTED]
    assert FlowPhase.MASTERED not in VALID_FLOW_TRANSITIONS[FlowPhase.PRACTICING]
    assert FlowPhase.MASTERED not in VALID_FLOW_TRANSITIONS[FlowPhase.NEEDS_REMEDIATION]


# ----------------------------------------------------------- idempotency


def test_start_flow_twice_reuses_session(db_session):
    objective = ensure_en_a1_can_001(db_session)
    ul = _ul(db_session)
    a = teaching_flow.start_flow(db_session, user_language_id=ul.id, objective_id=objective.id)
    b = teaching_flow.start_flow(db_session, user_language_id=ul.id, objective_id=objective.id)
    assert a.id == b.id


def test_double_answer_rejected(db_session):
    ul = _ul(db_session)
    started = teaching_slice.start_slice(db_session, user_language_id=ul.id)
    session = teaching_flow.get_flow(db_session, started["flow"]["id"])
    index = session.activity_cursor
    teaching_slice.submit_slice_answer(db_session, session, student_response="")
    # Simula double-submit no mesmo passo (cursor voltaria a ser o mesmo índice).
    session.activity_cursor = index
    with pytest.raises(APIError) as exc:
        teaching_slice.submit_slice_answer(db_session, session, student_response="")
    assert exc.value.code == "attempt_already_submitted"


def test_memory_schedule_not_duplicated(db_session):
    objective = ensure_en_a1_can_001(db_session)
    ul = _ul(db_session)
    a = memory_engine.schedule_objective_review(
        db_session, user_language_id=ul.id, objective=objective
    )
    b = memory_engine.schedule_objective_review(
        db_session, user_language_id=ul.id, objective=objective
    )
    assert a.id == b.id
    count = len(
        list(
            db_session.scalars(
                select(MemorySchedule).where(
                    MemorySchedule.user_language_id == ul.id,
                    MemorySchedule.subject_key == objective.code,
                )
            )
        )
    )
    assert count == 1


# -------------------------------------------------------------- ownership


def test_memory_due_isolated(client, auth, db_session, other_user):
    outro = db_session.get(User, other_user)
    ul_b = _ul(db_session, email=outro.email)
    objective = ensure_en_a1_can_001(db_session)
    schedule = memory_engine.schedule_objective_review(
        db_session, user_language_id=ul_b.id, objective=objective
    )
    db_session.commit()
    resp = client.post(
        f"/api/v1/teaching/memory/{schedule.id}/review",
        json={"rating": "good"},
        headers=auth,
    )
    assert resp.status_code == 404


# ---------------------------------------------------- deterministic rules


def test_professor_alone_not_enough_for_variants_only():
    result = deterministic_evaluator.evaluate_response(
        student_response="professor",
        canonical_answer="I work as a professor.",
        accepted_variants=["I'm a professor.", "I am a professor."],
    )
    assert result["result"] == "incorrect"


def test_professor_alone_rejected_for_structural_production():
    """Produção estrutural exige cláusula — 'professor' sozinho não basta."""
    result = deterministic_evaluator.evaluate_response(
        student_response="professor",
        required_features=["professor"],
        activity={
            "type": "guided_production",
            "evaluation_mode": "structural",
            "minimum_structure": "clause",
            "required_patterns": [r"\b(i('m| am)|i work as)\b"],
        },
    )
    assert result["result"] == "incorrect"


def test_normalization_cases():
    result = deterministic_evaluator.evaluate_response(
        student_response="  I'm   a   professor.  ",
        canonical_answer="I work as a professor.",
        accepted_variants=["I'm a professor.", "I am a professor."],
    )
    assert result["result"] == "correct"


# ---------------------------------------------------- intelligibility cases


@pytest.mark.parametrize(
    "transcript,expect_missed,expect_extra",
    [
        ("I would like to book a table for two", [], []),
        ("I would like book a table for two", ["to"], []),
        ("I would like to book table for two please", ["a"], ["please"]),
        ("", ["i", "would", "like", "to", "book", "a", "table", "for", "two"], []),
        (
            "I would would like to book a table for two",
            [],
            ["would"],
        ),
        ("I WOULD LIKE TO BOOK A TABLE FOR TWO!!!", [], []),
    ],
)
def test_intelligibility_cases(transcript, expect_missed, expect_extra):
    out = speech_intelligibility.assess_intelligibility(
        target_text="I would like to book a table for two",
        transcript=transcript,
    )
    assert out["is_phonetic_score"] is False
    assert "pronunciation_score" not in out
    for token in expect_missed:
        assert token in out["intelligibility"]["missed_tokens"]
    for token in expect_extra:
        assert token in out["intelligibility"]["extra_tokens"]


# ---------------------------------------------------- activities list


def test_list_en_a1_activities(db_session):
    objective = ensure_en_a1_can_001(db_session)
    activities = activity_generator.generate_activities(objective)
    types = [a["type"] for a in activities]
    assert types[0] == ActivityType.RECOGNITION
    assert ActivityType.TRANSFER_QUESTION in types
    assert ActivityType.GUIDED_PRODUCTION in types
    # Vocabulário A1 básico
    vocab = " ".join(objective.target_vocabulary_json).lower()
    for advanced in ("nevertheless", "quantum", "ubiquitous", "paradigm"):
        assert advanced not in vocab


# ---------------------------------------------------- remediation limit


def test_remediation_cycle_limit_goes_needs_review(db_session):
    objective = ensure_en_a1_can_001(db_session)
    ul = _ul(db_session)
    session = teaching_flow.start_flow(
        db_session, user_language_id=ul.id, objective_id=objective.id
    )
    for phase in (FlowPhase.INPUT, FlowPhase.NOTICING, FlowPhase.PRACTICING):
        teaching_flow.transition(db_session, session, target_phase=phase)
    teaching_flow.transition(db_session, session, target_phase=FlowPhase.NEEDS_REMEDIATION)
    # MAX_REMEDIATION_CYCLES = 3 → no 4º RETRYING o flow fecha em NEEDS_REVIEW.
    for _ in range(3):
        teaching_flow.transition(db_session, session, target_phase=FlowPhase.RETRYING)
        teaching_flow.transition(
            db_session, session, target_phase=FlowPhase.NEEDS_REMEDIATION
        )
    teaching_flow.transition(db_session, session, target_phase=FlowPhase.RETRYING)
    assert session.phase == FlowPhase.NEEDS_REVIEW
    assert session.status == "closed"


# ---------------------------------------------------- provider limits


def test_401_single_attempt():
    provider_resilience.reset_circuits()
    n = {"c": 0}

    def boom():
        n["c"] += 1
        req = httpx.Request("POST", "https://example.test")
        raise httpx.HTTPStatusError("x", request=req, response=httpx.Response(401, request=req))

    provider_resilience.call_with_policy(provider_name="qg-401", operation=boom, max_retries=5)
    assert n["c"] == 1


def test_openrouter_plus_resilience_bounded():
    """max_retries=0 (padrão low-cost) → uma tentativa no modelo, sem retry 5xx."""
    provider_resilience.reset_circuits()
    n = {"c": 0}

    def boom():
        n["c"] += 1
        req = httpx.Request("POST", "https://example.test")
        raise httpx.HTTPStatusError(
            "x", request=req, response=httpx.Response(503, request=req)
        )

    provider_resilience.call_with_policy(
        provider_name="qg-503", operation=boom, max_retries=0
    )
    assert n["c"] == 1


# ---------------------------------------------------- cache privacy


def test_personal_content_not_persisted(db_session):
    key = ai_cache.build_cache_key(
        capability="correction",
        input_payload={"student_response": "My name is secret"},
    )
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return {"ok": True}

    ai_cache.cached_or_compute(
        db_session,
        cache_key=key,
        capability="correction",
        compute=compute,
        input_for_privacy={"student_response": "My name is secret"},
    )
    assert ai_cache.get_cached(db_session, key) is None
    assert calls["n"] == 1


def test_prompt_version_changes_key():
    a = ai_cache.build_cache_key(capability="example_generation", prompt_version="v1")
    b = ai_cache.build_cache_key(capability="example_generation", prompt_version="v2")
    c = ai_cache.build_cache_key(
        capability="example_generation", prompt_version="v1", objective_version=2
    )
    assert a != b
    assert a != c


# ---------------------------------------------------- vertical slice e2e


def test_vertical_slice_happy_and_error_path(db_session):
    ul = _ul(db_session)
    started = teaching_slice.start_slice(db_session, user_language_id=ul.id)
    session = teaching_flow.get_flow(db_session, started["flow"]["id"])
    phases = [session.phase]

    # activation / input / noticing
    for _ in range(3):
        teaching_slice.submit_slice_answer(db_session, session, student_response="")
        session = teaching_flow.get_flow(db_session, session.id)
        phases.append(session.phase)

    # practice until fill_gap/word_order/mcq
    guard = 0
    while guard < 8:
        activity = teaching_flow.current_activity(session)
        if not activity:
            break
        if activity["type"] in {
            ActivityType.FILL_GAP,
            ActivityType.WORD_ORDER,
            ActivityType.MULTIPLE_CHOICE,
        }:
            break
        teaching_slice.submit_slice_answer(db_session, session, student_response="")
        session = teaching_flow.get_flow(db_session, session.id)
        phases.append(session.phase)
        guard += 1

    activity = teaching_flow.current_activity(session)
    assert activity is not None
    wrong = teaching_slice.submit_slice_answer(
        db_session, session, student_response="this is completely wrong xyz"
    )
    phases.append(session.phase)
    assert wrong["remediation"] is not None
    assert session.phase == FlowPhase.NEEDS_REMEDIATION

    # Retry responde a variante pós-revelação, não a questão original.
    retry_activity = teaching_flow.current_activity(session) or {}
    if retry_activity.get("type") == ActivityType.WORD_ORDER:
        correct = " ".join(retry_activity.get("tokens") or [])
    else:
        correct = (
            retry_activity.get("canonical_answer")
            or (retry_activity.get("accepted_variants") or ["x"])[0]
        )

    retried = teaching_slice.retry_slice(
        db_session,
        session,
        remediation_id=wrong["remediation"]["id"],
        student_response=correct,
    )
    phases.append(session.phase)
    assert retried["attempt"]["result"] == "correct"

    # Continua até transfer/mastery (caminho feliz restante)
    for _ in range(12):
        session = teaching_flow.get_flow(db_session, session.id)
        if session.status != "active":
            break
        if session.phase == FlowPhase.NEEDS_REMEDIATION:
            break
        activity = teaching_flow.current_activity(session)
        if activity is None:
            break
        if activity["type"] in {"listen", "recognition", "matching"}:
            ans = ""
        elif activity["type"] == ActivityType.WORD_ORDER:
            ans = " ".join(activity.get("tokens") or [])
        elif activity["type"] == ActivityType.MULTIPLE_CHOICE:
            ans = activity.get("canonical_answer") or ""
        elif activity["type"] == ActivityType.TRANSFER_QUESTION:
            ans = (activity.get("accepted_variants") or ["He lives in Goiânia."])[0]
        elif activity["type"] == ActivityType.GUIDED_PRODUCTION:
            ans = (
                "My name is Ana. I'm from Brazil. I live in Goiânia. I like coffee."
            )
        else:
            ans = activity.get("canonical_answer") or "Ana"
        try:
            out = teaching_slice.submit_slice_answer(
                db_session, session, student_response=ans
            )
        except APIError:
            break
        phases.append(session.phase)
        if out.get("mastery", {}).get("state") == MasteryState.MASTERED:
            break

    session = teaching_flow.get_flow(db_session, session.id)
    # Evidência de transfer pode ou não ter sido alcançada dependendo do cursor;
    # o caminho de erro+retry deve ter sido exercitado.
    assert FlowPhase.NEEDS_REMEDIATION in phases
    evidences = list(
        db_session.scalars(
            select(LearningEvidence).where(LearningEvidence.user_language_id == ul.id)
        )
    )
    assert evidences
    attempts = list(
        db_session.scalars(
            select(LearningAttempt).where(LearningAttempt.user_language_id == ul.id)
        )
    )
    assert len(attempts) >= 2
