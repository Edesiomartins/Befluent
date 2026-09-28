"""Dois tamanhos de sessão: dose do dia (12 exercícios) e sessão longa (36).

A dose do dia existe porque uma sessão de 36 exercícios é uma tarefa que se
adia. O tamanho curto não muda a pedagogia — mesmas cinco áreas, mesma ordem
de fases —, só o quanto entra de uma vez.
"""

from app.services.session_budget import (
    FULL_SESSION_BUDGET,
    SHORT_SESSION_BUDGET,
    budget_for,
)
from app.services.session_engine import plan_session
from app.services.session_progress import session_progress_from_activities


def _candidate(area: str, modality: str, phase: str, *, item_key: str, overflow: bool = False):
    return {
        "area": area,
        "modality": modality,
        "phase_hint": phase,
        "priority": 1,
        "item_key": item_key,
        "overflow": overflow,
        "activity": {"type": modality, "phase_hint": phase, "vocabulary_item_id": item_key},
    }


_PHASES = {
    "vocabulary": "input",
    "listening": "practicing",
    "grammar": "noticing",
    "production": "producing",
    "conversation": "producing",
}
_MODALITIES = {
    "vocabulary": "recognition",
    "listening": "listening_recognition",
    "grammar": "multiple_choice",
    "production": "lexical_production",
    "conversation": "conversation_prompt",
}


def _pool() -> list[dict]:
    """Candidatos de sobra em todas as áreas: o corte vem do orçamento."""
    pool = []
    for area in _PHASES:
        for index in range(12):
            pool.append(
                _candidate(area, _MODALITIES[area], _PHASES[area], item_key=f"{area}-{index}")
            )
    return pool


def test_dose_do_dia_planeja_doze_exercicios():
    plan = plan_session(_pool(), budget=SHORT_SESSION_BUDGET)
    assert plan["total"] == 12
    assert plan["target_total"] == 12


def test_dose_do_dia_mantem_as_cinco_areas():
    plan = plan_session(_pool(), budget=SHORT_SESSION_BUDGET)
    assert plan["counts"] == {
        "vocabulary": 3,
        "listening": 3,
        "grammar": 2,
        "production": 2,
        "conversation": 2,
    }


def test_sem_tamanho_informado_continua_a_sessao_longa():
    plan = plan_session(_pool())
    assert plan["total"] == 36
    assert plan["size"] == "full"


def test_plano_declara_tamanho_e_tempo_estimado():
    plan = plan_session(_pool(), budget=SHORT_SESSION_BUDGET)
    assert plan["size"] == "short"
    assert plan["estimated_minutes"] == SHORT_SESSION_BUDGET.estimated_minutes
    assert plan["estimated_minutes"] < FULL_SESSION_BUDGET.estimated_minutes


def test_dose_do_dia_nao_estoura_o_teto_com_revisao_vencida():
    pool = _pool()
    pool.extend(
        _candidate("vocabulary", "review", "input", item_key=f"due-{index}", overflow=True)
        for index in range(10)
    )
    plan = plan_session(pool, budget=SHORT_SESSION_BUDGET)
    assert plan["total"] <= SHORT_SESSION_BUDGET.maximum_total == 14


def test_progresso_usa_o_alvo_do_plano_curto():
    plan = plan_session(_pool(), budget=SHORT_SESSION_BUDGET)
    progress = session_progress_from_activities(plan["activities"], 0, plan=plan)
    assert progress["target_total"] == 12
    assert progress["size"] == "short"
    assert progress["estimated_minutes"] == SHORT_SESSION_BUDGET.estimated_minutes


def test_progresso_sem_plano_declara_a_sessao_longa():
    progress = session_progress_from_activities([], 0)
    assert progress["target_total"] == 36
    assert progress["size"] == "full"


def test_tamanho_desconhecido_cai_na_sessao_longa():
    assert budget_for("short") is SHORT_SESSION_BUDGET
    assert budget_for("full") is FULL_SESSION_BUDGET
    assert budget_for(None) is FULL_SESSION_BUDGET
    assert budget_for("gigante") is FULL_SESSION_BUDGET
