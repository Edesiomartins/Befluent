"""Motor do teste de nivelamento — seleção adaptativa e cálculo do resultado.

Lógica deliberadamente simples e substituível. NÃO é um modelo psicométrico
(IRT/Rasch): é uma heurística de faixas com regras explícitas e auditáveis.
Qualquer uso pedagógico sério exige validação com itens calibrados.

Regras de seleção (seção "teste adaptativo"):
- inicia em A2, salvo quando o usuário se declara iniciante absoluto;
- 3 acertos consecutivos na faixa atual -> testa a faixa superior;
- 2 erros consecutivos -> testa a faixa inferior;
- exige ao menos MIN_ITEMS_PER_BAND itens para considerar uma faixa;
- mínimo de MIN_OBJECTIVE_ITEMS itens objetivos, máximo de MAX_OBJECTIVE_ITEMS.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.levels import (
    ESSENTIAL_SKILLS,
    LEVEL_INDEX,
    SKILL_WEIGHTS,
    TESTABLE_LEVELS,
    CEFRLevel,
    Skill,
    level_at,
)

MIN_OBJECTIVE_ITEMS = 12
RECOMMENDED_OBJECTIVE_ITEMS = 20
MAX_OBJECTIVE_ITEMS = 30

MIN_ITEMS_PER_BAND = 4
PROMOTE_AFTER_CORRECT = 3
DEMOTE_AFTER_WRONG = 2

#: Acerto médio necessário para considerar uma faixa dominada.
BAND_MASTERY_THRESHOLD = 0.65
#: Itens objetivos abaixo disto numa competência não sustentam uma estimativa
#: própria — uma única questão de múltipla escolha não classifica ninguém.
MIN_ITEMS_PER_SKILL = 2

#: Produção (escrita/fala) é avaliada por rubrica sobre uma amostra extensa:
#: uma única tarefa já constitui evidência, ao contrário de um item objetivo.
PRODUCTION_SKILLS = {Skill.WRITING, Skill.SPEAKING}
#: Respostas mais rápidas que isto sugerem chute e reduzem a confiança.
FAST_RESPONSE_MS = 1500

OBJECTIVE_SKILLS = [Skill.VOCABULARY_GRAMMAR, Skill.READING, Skill.LISTENING]

#: Pesos explícitos por configuração de competências avaliadas.
WEIGHT_PROFILES: dict[frozenset[str], dict[str, float]] = {
    frozenset(
        {Skill.VOCABULARY_GRAMMAR, Skill.READING, Skill.LISTENING, Skill.WRITING, Skill.SPEAKING}
    ): {
        Skill.VOCABULARY_GRAMMAR: 0.20,
        Skill.READING: 0.20,
        Skill.LISTENING: 0.20,
        Skill.WRITING: 0.20,
        Skill.SPEAKING: 0.20,
    },
    frozenset({Skill.VOCABULARY_GRAMMAR, Skill.READING, Skill.LISTENING, Skill.WRITING}): {
        Skill.VOCABULARY_GRAMMAR: 0.30,
        Skill.READING: 0.25,
        Skill.LISTENING: 0.25,
        Skill.WRITING: 0.20,
    },
    frozenset({Skill.VOCABULARY_GRAMMAR, Skill.READING, Skill.WRITING}): {
        Skill.VOCABULARY_GRAMMAR: 0.45,
        Skill.READING: 0.35,
        Skill.WRITING: 0.20,
    },
}


@dataclass
class AnswerRecord:
    """Resposta já avaliada, na ordem em que foi dada."""

    skill: str
    cefr_level: str
    normalized_score: float
    response_time_ms: int | None = None


@dataclass
class TestState:
    current_band: str = CEFRLevel.A2
    answers: list[AnswerRecord] = field(default_factory=list)
    consecutive_correct: int = 0
    consecutive_wrong: int = 0


def initial_band(declared_beginner: bool = False) -> str:
    return CEFRLevel.PRE_A1 if declared_beginner else CEFRLevel.A2


def _band_neighbour(band: str, delta: int) -> str:
    """Move dentro das faixas testáveis (não escala para C1/C2 sem itens)."""
    testable = list(TESTABLE_LEVELS)
    try:
        position = testable.index(band)
    except ValueError:
        return CEFRLevel.A2
    return testable[max(0, min(position + delta, len(testable) - 1))]


def register_answer(state: TestState, record: AnswerRecord) -> TestState:
    """Atualiza streaks e faixa atual após uma resposta objetiva."""
    state.answers.append(record)
    correct = record.normalized_score >= 0.5

    if correct:
        state.consecutive_correct += 1
        state.consecutive_wrong = 0
    else:
        state.consecutive_wrong += 1
        state.consecutive_correct = 0

    if state.consecutive_correct >= PROMOTE_AFTER_CORRECT:
        state.current_band = _band_neighbour(state.current_band, 1)
        state.consecutive_correct = 0
    elif state.consecutive_wrong >= DEMOTE_AFTER_WRONG:
        state.current_band = _band_neighbour(state.current_band, -1)
        state.consecutive_wrong = 0

    return state


def next_skill(state: TestState) -> str:
    """Rotaciona competências objetivas para evitar sequência previsível."""
    counts = {skill: 0 for skill in OBJECTIVE_SKILLS}
    for answer in state.answers:
        if answer.skill in counts:
            counts[answer.skill] += 1
    return min(OBJECTIVE_SKILLS, key=lambda skill: (counts[skill], OBJECTIVE_SKILLS.index(skill)))


def should_stop(state: TestState) -> bool:
    answered = len(state.answers)
    if answered >= MAX_OBJECTIVE_ITEMS:
        return True
    if answered < MIN_OBJECTIVE_ITEMS:
        return False

    # Evidência suficiente: a faixa atual já tem itens bastantes e o
    # desempenho nela é consistente (nem promove nem rebaixa).
    band_answers = [a for a in state.answers if a.cefr_level == state.current_band]
    if len(band_answers) >= MIN_ITEMS_PER_BAND and answered >= RECOMMENDED_OBJECTIVE_ITEMS:
        return True
    return False


# --------------------------------------------------------------------- scoring


def _band_accuracy(answers: list[AnswerRecord]) -> dict[str, tuple[float, int]]:
    """{nível: (acerto médio, quantidade)}"""
    buckets: dict[str, list[float]] = {}
    for answer in answers:
        buckets.setdefault(answer.cefr_level, []).append(answer.normalized_score)
    return {
        level: (sum(scores) / len(scores), len(scores)) for level, scores in buckets.items()
    }


def estimate_skill_level(answers: list[AnswerRecord]) -> str | None:
    """Maior faixa dominada; None quando não há evidência suficiente."""
    if not answers:
        return None
    is_production = answers[0].skill in PRODUCTION_SKILLS
    if not is_production and len(answers) < MIN_ITEMS_PER_SKILL:
        return None

    accuracy = _band_accuracy(answers)
    mastered = [
        level
        for level, (mean, count) in accuracy.items()
        if mean >= BAND_MASTERY_THRESHOLD and count >= 1 and level in LEVEL_INDEX
    ]
    if mastered:
        return max(mastered, key=lambda level: LEVEL_INDEX[level])

    # Nenhuma faixa dominada: fica uma abaixo da menor faixa testada.
    tested = [level for level in accuracy if level in LEVEL_INDEX]
    if not tested:
        return None
    lowest = min(tested, key=lambda level: LEVEL_INDEX[level])
    return level_at(LEVEL_INDEX[lowest] - 1)


def skill_results(answers: list[AnswerRecord]) -> dict[str, dict]:
    """Resultado por competência, apenas para as efetivamente avaliadas."""
    grouped: dict[str, list[AnswerRecord]] = {}
    for answer in answers:
        grouped.setdefault(answer.skill, []).append(answer)

    results: dict[str, dict] = {}
    for skill, skill_answers in grouped.items():
        level = estimate_skill_level(skill_answers)
        if level is None:
            continue
        score = sum(a.normalized_score for a in skill_answers)
        results[skill] = {
            "skill": skill,
            "estimated_level": level,
            "score": round(score, 3),
            "max_score": float(len(skill_answers)),
            "items_count": len(skill_answers),
            "accuracy": round(score / len(skill_answers), 3),
        }
    return results


def effective_weights(assessed_skills: list[str]) -> dict[str, float]:
    """Pesos das competências realmente avaliadas.

    Nunca usa média simples. As três configurações previstas têm pesos
    definidos explicitamente (compreensão não pode dominar o resultado quando
    a produção sai do cálculo); qualquer outra combinação cai na
    renormalização proporcional a partir de `SKILL_WEIGHTS`.
    """
    if not assessed_skills:
        return {}

    assessed = frozenset(assessed_skills)
    profile = WEIGHT_PROFILES.get(assessed)
    if profile:
        return dict(profile)

    total = sum(SKILL_WEIGHTS[skill] for skill in assessed_skills)
    if total <= 0:
        return {}
    return {skill: SKILL_WEIGHTS[skill] / total for skill in assessed_skills}


def overall_level(results: dict[str, dict]) -> tuple[str | None, dict[str, float]]:
    """Nível geral ponderado, limitado pela menor competência essencial.

    O teto existe para não declarar fluência com base em compreensão apenas:
    o geral fica no máximo um nível acima da menor competência essencial
    avaliada (listening/speaking). Sem nenhuma essencial avaliada, o teto usa
    a menor competência avaliada.
    """
    if not results:
        return None, {}

    assessed = sorted(results.keys())
    weights = effective_weights(assessed)
    if not weights:
        return None, {}

    weighted_index = sum(
        LEVEL_INDEX[results[skill]["estimated_level"]] * weight
        for skill, weight in weights.items()
    )
    level_index = round(weighted_index)

    essential = [skill for skill in assessed if skill in ESSENTIAL_SKILLS]
    cap_pool = essential or assessed
    floor_index = min(LEVEL_INDEX[results[skill]["estimated_level"]] for skill in cap_pool)
    level_index = min(level_index, floor_index + 1)

    # Sem itens validados de C1/C2 o teste não classifica nessas faixas.
    max_testable = max(LEVEL_INDEX[level] for level in TESTABLE_LEVELS)
    level_index = min(level_index, max_testable)

    return level_at(level_index), weights


def confidence(results: dict[str, dict], answers: list[AnswerRecord]) -> float:
    """Confiança 0-100. Heurística explícita, sem pretensão psicométrica."""
    if not answers or not results:
        return 0.0

    score = 40.0

    # Volume de evidência.
    answered = len(answers)
    if answered >= RECOMMENDED_OBJECTIVE_ITEMS:
        score += 25
    elif answered >= MIN_OBJECTIVE_ITEMS:
        score += 15
    else:
        score += 5

    # Abrangência de competências.
    score += min(len(results), 5) * 4

    # Consistência: dispersão entre os níveis estimados.
    indexes = [LEVEL_INDEX[r["estimated_level"]] for r in results.values()]
    spread = max(indexes) - min(indexes)
    score -= spread * 5

    # Respostas suspeitas de chute.
    fast = [a for a in answers if a.response_time_ms is not None and a.response_time_ms < FAST_RESPONSE_MS]
    if fast:
        score -= min(len(fast) / len(answers), 0.5) * 20

    # Competências essenciais ausentes deixam a estimativa mais frágil.
    missing_essential = [skill for skill in ESSENTIAL_SKILLS if skill not in results]
    score -= len(missing_essential) * 7

    return round(max(0.0, min(100.0, score)), 1)


def confidence_label(value: float) -> str:
    if value >= 70:
        return "alta"
    if value >= 45:
        return "moderada"
    return "baixa"


def recommendations(results: dict[str, dict], overall: str | None) -> list[dict]:
    """Recomendações simples derivadas das lacunas por competência."""
    if not overall:
        return []

    overall_index = LEVEL_INDEX[overall]
    items: list[dict] = []

    for skill, result in sorted(results.items()):
        if LEVEL_INDEX[result["estimated_level"]] < overall_index:
            items.append({"skill": skill, "reason": "below_overall", "priority": 1})

    for skill in sorted(ESSENTIAL_SKILLS | {Skill.WRITING}):
        if skill not in results:
            items.append({"skill": skill, "reason": "not_assessed", "priority": 2})

    return sorted(items, key=lambda item: (item["priority"], item["skill"]))


def build_result(
    answers: list[AnswerRecord],
    duration_seconds: int | None = None,
) -> dict:
    """Resultado completo do teste. Fonte única do cálculo (backend)."""
    results = skill_results(answers)
    overall, weights = overall_level(results)
    confidence_value = confidence(results, answers)
    assessed = sorted(results.keys())
    not_assessed = sorted(set(SKILL_WEIGHTS) - set(assessed))

    total_score = sum(a.normalized_score for a in answers)

    return {
        "overall_level": overall,
        "confidence_score": confidence_value,
        "confidence_label": confidence_label(confidence_value),
        "total_score": round(total_score, 3),
        "max_score": float(len(answers)),
        "items_answered": len(answers),
        "duration_seconds": duration_seconds,
        "skills": results,
        "assessed_skills": assessed,
        "not_assessed_skills": not_assessed,
        "weights_used": {skill: round(weight, 4) for skill, weight in weights.items()},
        "recommendations": recommendations(results, overall),
    }
