"""Aceite da fase 1: errar não repete a questão; reavalia o objetivo com outro estímulo.

Cenários A–H do pedido 2bbf6b59c0cb0b5b, nos dois caminhos reais de sessão:
Teaching Engine (TeachingFlowSession) e lição legada (LessonActivityAttempt).
SQLite local; nenhum provedor, produção ou migration.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from app.core.teaching import FlowPhase
from app.models import Language, LearningObjective, TeachingFlowSession, User, UserLanguage
from app.services import activity_pool, lesson_attempts, teaching_flow, teaching_slice
from app.services.objective_seed import ensure_en_a1_can_001

from test_activity_pool import item, unit_for
from test_lesson_activity_attempts import _lesson_with_grammar


@pytest.fixture
def admin(db_session):
    return db_session.scalar(select(User).where(User.email == "admin@befluent.local"))


def _flow(db, *, activities: list[dict], pool: list[dict]) -> tuple[TeachingFlowSession, LearningObjective]:
    objective = ensure_en_a1_can_001(db)
    user = db.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db.scalar(select(Language).where(Language.code == "en"))
    owner = UserLanguage(user_id=user.id, language_id=language.id, is_active=True)
    db.add(owner)
    db.flush()
    unit = unit_for(db, objective)
    bound = [
        {**candidate, "learning_objective_id": objective.id, "content_unit_id": unit.id, "skill": objective.skill_focus,
         "phase_hint": "practicing", "ai_required": False}
        for candidate in pool
    ]
    if bound:
        activity_pool.append_objective_batch(db, objective_id=objective.id, batch=bound)
    planned = [
        {**candidate, "learning_objective_id": objective.id, "skill": objective.skill_focus,
         "phase_hint": "practicing", "ai_required": False}
        for candidate in activities
    ]
    flow = TeachingFlowSession(user_language_id=owner.id, objective_id=objective.id, phase=FlowPhase.PRACTICING,
                               payload_json={"activities": planned}, status="active")
    db.add(flow)
    db.commit()
    return flow, objective


# A — atividade A errada → retry → próxima activity_id != A
def test_a_wrong_answer_retry_never_returns_same_activity(db_session):
    flow, _ = _flow(db_session, activities=[item("a")], pool=[item("b", "Who is the visitor?")])
    response = teaching_slice.submit_slice_answer(db_session, flow, student_response="Rome", activity_index=0)
    assert response["attempt"]["result"] == "incorrect"
    assert response["current_activity"]["activity_id"] == "b"
    assert response["current_activity"]["activity_id"] != "a"
    assert flow.payload_json["selection_trace"]["remediation_reason"] == "incorrect_same_objective"
    assert flow.payload_json["selection_trace"]["fallback_used"] is False


# B — A respondida corretamente não volta na mesma sessão
def test_b_correct_activity_is_consumed_for_the_session(db_session):
    flow, _ = _flow(db_session, activities=[item("a"), item("c", "Fresh context")], pool=[item("a")])
    response = teaching_slice.submit_slice_answer(db_session, flow, student_response="Ada", activity_index=0)
    assert response["attempt"]["result"] == "correct"
    assert "a" in flow.payload_json["seen_activity_ids"]
    assert flow.activity_cursor == 1
    assert teaching_flow.current_activity(flow)["activity_id"] == "c"
    # Mesmo que o orçamento ainda comporte, A não fica elegível de novo.
    assert activity_pool.select_activity([item("a")], objective_id="objective-x", session_payload=flow.payload_json) is None


# C — A e B vistas; selector recebe A, B, C → só C elegível
def test_c_selector_keeps_only_unseen_candidate():
    a, b, c = item("a"), item("b", "Second context"), item("c", "Third context")
    payload = {}
    activity_pool.record_exposure(payload, a)
    activity_pool.record_exposure(payload, b)
    trace = {}
    chosen = activity_pool.select_activity([a, b, c], objective_id="objective-x", session_payload=payload, trace=trace)
    assert chosen == c
    assert trace["exclusions"]["seen"] == 2
    assert trace["chosen_activity"] == "c"


# D — remediação do objetivo X: A errada, B inédita do mesmo X → B selecionável
def test_d_remediation_selects_unseen_sibling_of_same_objective():
    a = item("a")
    b = item("b", "Who is introducing herself?", type="fill_gap", options=[], context="office")
    other = item("z", "Unrelated", learning_objective_id="objective-y")
    payload = {}
    activity_pool.record_exposure(payload, a)
    chosen = activity_pool.select_activity([other, a, b], objective_id="objective-x", session_payload=payload, previous=a)
    assert chosen == b
    assert chosen["learning_objective_id"] == a["learning_objective_id"]
    assert chosen["activity_id"] != a["activity_id"]


# E — retomada: A e B respondidas, sai e volta → continuam inelegíveis
def test_e_session_resume_preserves_seen_activities(db_session):
    flow, objective = _flow(
        db_session,
        activities=[item("a"), item("b", "Second context"), item("c", "Third context")],
        pool=[item("a"), item("b", "Second context")],
    )
    teaching_slice.submit_slice_answer(db_session, flow, student_response="Ada", activity_index=0)
    teaching_slice.submit_slice_answer(db_session, flow, student_response="Ada", activity_index=1)
    db_session.commit()
    db_session.expire_all()

    resumed = db_session.get(TeachingFlowSession, flow.id)
    payload = json.loads(json.dumps(resumed.payload_json))
    assert {"a", "b"} <= set(payload["seen_activity_ids"])
    assert resumed.activity_cursor == 2
    restored = teaching_slice.restore_session_payload(db_session, resumed, objective=objective)
    assert restored["current_activity"]["activity_id"] == "c"
    assert activity_pool.select_activity([item("a"), item("b", "Second context")], objective_id="objective-x",
                                         session_payload=payload) is None
    assert sorted(payload["submitted_indices"]) == [0, 1]


# F — pool insuficiente: só existe A e A já foi vista → não devolver A como nova
def test_f_insufficient_pool_never_repeats_previous_activity(db_session):
    # Objetivo com padrões: o fallback determinístico ainda pode gerar outro
    # estímulo, mas nunca com a identidade/conteúdo de A.
    flow, _ = _flow(db_session, activities=[item("a")], pool=[])
    response = teaching_slice.submit_slice_answer(db_session, flow, student_response="Rome", activity_index=0)
    assert response["attempt"]["result"] == "incorrect"
    retry = flow.payload_json["retry_activity"]
    assert activity_pool.activity_id(retry) != "a"
    assert not activity_pool.same_stimulus(retry, item("a"))
    assert retry.get("prompt") != item("a")["prompt"]
    assert retry.get("retry_strategy") != "objective_pool"
    # Variante de padrão tem identidade derivada do conteúdo, nunca o ID de A.
    assert response["current_activity"].get("activity_id") != "a"
    assert activity_pool.activity_id(response["current_activity"]) != "a"


def test_f_insufficient_pool_without_patterns_falls_back_to_continue(db_session):
    from app.services.objective_seed import ensure_theme_objective
    objective = ensure_theme_objective(db_session, language_code="en", level="A1", theme="Aceite fase 1")
    assert not objective.target_patterns_json
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    owner = UserLanguage(user_id=user.id, language_id=language.id, is_active=True)
    db_session.add(owner)
    db_session.flush()
    a = {**item("a"), "learning_objective_id": objective.id, "skill": objective.skill_focus,
         "phase_hint": "practicing", "ai_required": False}
    flow = TeachingFlowSession(user_language_id=owner.id, objective_id=objective.id, phase=FlowPhase.PRACTICING,
                               payload_json={"activities": [a]}, status="active")
    db_session.add(flow)
    db_session.commit()
    response = teaching_slice.submit_slice_answer(db_session, flow, student_response="Rome", activity_index=0)
    assert response["attempt"]["result"] == "incorrect"
    retry = flow.payload_json["retry_activity"]
    assert retry["retry_safe"] is False
    assert retry["retry_strategy"] == "fallback_continue"
    assert flow.payload_json["selection_trace"]["fallback_used"] is True
    assert flow.payload_json["selection_trace"]["chosen_activity"] is None
    assert response["current_activity"].get("prompt") != a["prompt"]


def test_f_legacy_lesson_with_single_candidate_does_not_repeat(db_session, admin):
    lesson = _lesson_with_grammar(db_session, admin)
    owner = db_session.get(UserLanguage, lesson.user_language_id)
    content = dict(lesson.content_json)
    content["activity_pool"] = []
    lesson.content_json = content
    db_session.commit()
    first = lesson_attempts.submit_objective_answer(
        db_session, lesson=lesson, owner=owner, activity_key="grammar:exercise:0", selected_answer="Where",
    )
    db_session.commit()
    assert first["retry"]["available"] is False
    assert first["retry"]["strategy"] == "fallback_continue"
    with pytest.raises(Exception) as exc:
        lesson_attempts.submit_objective_answer(
            db_session, lesson=lesson, owner=owner, activity_key="grammar:exercise:0",
            selected_answer="What", request_retry=True,
        )
    assert getattr(exc.value, "code", None) == "retry_variant_unavailable"


# G — fallback não pode ignorar seen_ids
def test_g_fallback_variant_cannot_reuse_seen_identity():
    a = item("a")
    payload = {}
    activity_pool.record_exposure(payload, a)
    clone_with_new_id = item("fresh-id")  # mesmo estímulo, ID novo
    assert activity_pool.is_seen(clone_with_new_id, payload)
    assert activity_pool.select_activity([clone_with_new_id], objective_id="objective-x", session_payload=payload) is None


def test_g_legacy_fallback_never_borrows_planned_or_seen_questions():
    a = {"prompt": "____ is your name?", "options": ["What", "Where"], "answer": "What", "learning_objective_id": "qw"}
    b = {"prompt": "____ are you from?", "options": ["Where", "What"], "answer": "Where", "learning_objective_id": "qw"}
    content = {"exercises": [a, b], "level": "A1", "native_language": "pt-BR", "target_language": "en"}
    variant, strategy = lesson_attempts._build_legacy_retry_activity(
        content=content, activity_key="grammar:exercise:0", current=a, seen_activities=[a],
    )
    assert variant is None
    assert strategy == "fallback_continue"


# H — regras de target_language / native_language continuam valendo
@pytest.mark.parametrize("change", [{"target_language": "fr"}, {"native_language": "de"}, {"cefr_level": "B1"}])
def test_h_language_rules_still_filter_remediation(change):
    assert activity_pool.select_activity(
        [item("b", "Other context", **change)], objective_id="objective-x",
        target_language="en", native_language="pt-BR", level="A1",
    ) is None


def test_h_objective_candidates_respect_native_language(db_session):
    flow, objective = _flow(db_session, activities=[item("a")], pool=[item("b", "Who is the visitor?")])
    assert [c["activity_id"] for c in activity_pool.objective_candidates(db_session, objective, native_language="pt-BR")] == ["b"]
    assert activity_pool.objective_candidates(db_session, objective, native_language="es-ES") == []
