"""Orçamento da sessão: 36 exercícios, teto 40, variedade e evidência espalhada."""

from app.core.teaching import ActivityType, EvidenceType
from app.services.session_budget import (
    MAXIMUM_SESSION_EXERCISES,
    SESSION_ACTIVITY_BUDGET,
    TARGET_SESSION_EXERCISES,
)
from app.services.session_engine import modalities_for_item, plan_session
from app.services.session_progress import session_progress_from_activities


def _candidate(area: str, modality: str, phase: str, *, item_key: str, priority: int = 1, overflow: bool = False):
    return {
        "area": area,
        "modality": modality,
        "phase_hint": phase,
        "priority": priority,
        "item_key": item_key,
        "overflow": overflow,
        "activity": {"type": modality, "phase_hint": phase, "vocabulary_item_id": item_key},
    }


def _full_pool() -> list[dict]:
    pool = []
    phases = {
        "vocabulary": "input",
        "listening": "practicing",
        "grammar": "noticing",
        "production": "producing",
        "conversation": "producing",
    }
    modalities = {
        "vocabulary": "recognition",
        "listening": "listening_recognition",
        "grammar": "multiple_choice",
        "production": "lexical_production",
        "conversation": "conversation_prompt",
    }
    for area, budget in SESSION_ACTIVITY_BUDGET.items():
        for index in range(budget + 5):
            pool.append(
                _candidate(
                    area,
                    modalities[area],
                    phases[area],
                    item_key=f"{area}-{index}",
                )
            )
    return pool


def test_sessao_alvo_respeita_orcamento_36():
    plan = plan_session(_full_pool())
    assert plan["total"] == TARGET_SESSION_EXERCISES == 36
    assert plan["total"] <= MAXIMUM_SESSION_EXERCISES
    assert plan["counts"] == {
        "vocabulary": 8,
        "listening": 8,
        "grammar": 8,
        "production": 6,
        "conversation": 6,
    }


def test_sessao_normal_nao_ultrapassa_40_mesmo_com_folga_pedagogica():
    pool = _full_pool()
    pool.extend(
        _candidate(
            "vocabulary",
            "review",
            "practicing",
            item_key=f"extra-{index}",
            overflow=True,
        )
        for index in range(6)
    )
    plan = plan_session(pool)
    assert plan["total"] == MAXIMUM_SESSION_EXERCISES
    assert plan["counts"]["vocabulary"] == 8 + 4


def test_vocabulario_para_no_budget_e_revisao_nao_estoura():
    reviews = [
        _candidate("vocabulary", "recognition", "practicing", item_key=f"due-{index}", priority=0)
        for index in range(100)
    ]
    plan = plan_session(reviews)
    assert plan["counts"]["vocabulary"] == 8
    assert plan["total"] == 8


def test_item_nao_completa_todas_as_modalidades_na_mesma_sessao():
    opening = modalities_for_item(set(), available_types={
        ActivityType.PRESENTATION,
        ActivityType.RECOGNITION,
        ActivityType.REVERSE_RECOGNITION,
        ActivityType.LISTENING_RECOGNITION,
        ActivityType.LEXICAL_PRODUCTION,
    })
    assert opening == [ActivityType.PRESENTATION, ActivityType.RECOGNITION]
    later = modalities_for_item(
        {EvidenceType.EXPOSURE, EvidenceType.RECOGNITION},
        available_types={
            ActivityType.LISTENING_RECOGNITION,
            ActivityType.LEXICAL_PRODUCTION,
            ActivityType.REVERSE_RECOGNITION,
        },
    )
    assert later == [ActivityType.REVERSE_RECOGNITION]

    mixed = []
    for step in (
        ActivityType.PRESENTATION,
        ActivityType.RECOGNITION,
        ActivityType.LISTENING_RECOGNITION,
        ActivityType.LEXICAL_PRODUCTION,
    ):
        mixed.append(
            _candidate(
                "vocabulary" if step != ActivityType.LISTENING_RECOGNITION else "listening",
                step,
                "input" if step == ActivityType.PRESENTATION else "practicing",
                item_key="haus",
            )
        )
    # A área de production precisa do tipo certo para entrar no orçamento.
    mixed[3]["area"] = "production"
    mixed[3]["phase_hint"] = "producing"
    plan = plan_session(mixed)
    types = [activity["type"] for activity in plan["activities"]]
    assert ActivityType.PRESENTATION in types
    assert ActivityType.RECOGNITION in types
    assert ActivityType.LISTENING_RECOGNITION not in types
    assert ActivityType.LEXICAL_PRODUCTION not in types


def test_nao_repete_mais_de_tres_da_mesma_modalidade_se_houver_alternativa():
    pool = []
    for index in range(6):
        pool.append(_candidate("vocabulary", "recognition", "practicing", item_key=f"r-{index}"))
    for index in range(6):
        pool.append(
            _candidate("vocabulary", "reverse_recognition", "practicing", item_key=f"v-{index}")
        )
    plan = plan_session(pool)
    types = [activity["type"] for activity in plan["activities"]]
    run = 1
    for previous, current in zip(types, types[1:]):
        run = run + 1 if previous == current else 1
        assert run <= 3


def test_cursor_consome_a_area_certa_e_encerra_no_total():
    plan = plan_session(_full_pool())
    progress = session_progress_from_activities(plan["activities"], 8)
    vocabulary = next(area for area in progress["areas"] if area["key"] == "vocabulary")
    listening = next(area for area in progress["areas"] if area["key"] == "listening")
    assert progress["completed"] == 8
    assert progress["total"] == 36
    assert vocabulary["completed"] == vocabulary["total"] == 8
    assert listening["completed"] == 0


def test_a_fase_nao_anda_para_tras():
    plan = plan_session(_full_pool())
    ranks = []
    from app.services.session_budget import PHASE_RANK

    for activity in plan["activities"]:
        ranks.append(PHASE_RANK[activity["phase_hint"]])
    assert ranks == sorted(ranks)
