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
MIN_ITEMS_PER_SKILL = 4
MIN_ITEMS_AT_DECIDING_BAND = 2

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
    evidence_keys: tuple[str, ...] = ()
    eligible: bool = True


@dataclass
class SkillTestState:
    current_band: str = CEFRLevel.A2
    consecutive_correct: int = 0
    consecutive_wrong: int = 0


@dataclass
class TestState:
    initial_band: str = CEFRLevel.A2
    answers: list[AnswerRecord] = field(default_factory=list)
    skill_states: dict[str, SkillTestState] = field(default_factory=dict)
    # Compatibilidade temporária com o fluxo da API atual. Representa a faixa
    # da habilidade que acabou de responder ou que será apresentada a seguir.
    current_band: str = CEFRLevel.A2
    active_skill: str = Skill.VOCABULARY_GRAMMAR

    def __post_init__(self) -> None:
        if self.initial_band == CEFRLevel.A2 and self.current_band != CEFRLevel.A2:
            self.initial_band = self.current_band
        else:
            self.current_band = self.initial_band
        for skill in OBJECTIVE_SKILLS:
            self.skill_states.setdefault(skill, SkillTestState(self.initial_band))


def state_for(state: TestState, skill: str) -> SkillTestState:
    """Obtém o estado adaptativo isolado de uma habilidade."""
    return state.skill_states.setdefault(skill, SkillTestState(state.initial_band))


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
    skill_state = state_for(state, record.skill)
    if record.cefr_level != skill_state.current_band:
        skill_state.consecutive_correct = 0
        skill_state.consecutive_wrong = 0
        return state
    correct = record.normalized_score >= 0.5

    if correct:
        skill_state.consecutive_correct += 1
        skill_state.consecutive_wrong = 0
    else:
        skill_state.consecutive_wrong += 1
        skill_state.consecutive_correct = 0

    if skill_state.consecutive_correct >= PROMOTE_AFTER_CORRECT:
        skill_state.current_band = _band_neighbour(skill_state.current_band, 1)
        skill_state.consecutive_correct = 0
    elif skill_state.consecutive_wrong >= DEMOTE_AFTER_WRONG:
        skill_state.current_band = _band_neighbour(skill_state.current_band, -1)
        skill_state.consecutive_wrong = 0

    state.active_skill = record.skill
    state.current_band = skill_state.current_band
    return state


def next_skill(state: TestState) -> str:
    """Escolhe a habilidade com menos evidência, priorizando menos de quatro itens."""
    counts = {skill: 0 for skill in OBJECTIVE_SKILLS}
    for answer in state.answers:
        if answer.skill in counts:
            counts[answer.skill] += 1
    skill = min(
        OBJECTIVE_SKILLS,
        key=lambda item: (
            not (counts[item] >= MIN_ITEMS_PER_SKILL and confirmation_policy([a for a in state.answers if a.skill == item])["confirmation_required"]),
            estimate_skill_level([a for a in state.answers if a.skill == item]) is not None,
            counts[item] >= MIN_ITEMS_PER_SKILL,
            counts[item],
            OBJECTIVE_SKILLS.index(item),
        ),
    )
    state.active_skill = skill
    state.current_band = state_for(state, skill).current_band
    return skill


def should_stop(state: TestState) -> bool:
    answered = len(state.answers)
    if answered >= MAX_OBJECTIVE_ITEMS:
        return True
    if answered < MIN_OBJECTIVE_ITEMS:
        return False

    # Evidência suficiente: a faixa atual já tem itens bastantes e o
    # desempenho nela é consistente (nem promove nem rebaixa).
    return all((policy := confirmation_policy([a for a in state.answers if a.skill == skill]))["estimated_level"]
               is not None and not policy["confirmation_required"] for skill in OBJECTIVE_SKILLS)


# --------------------------------------------------------------------- scoring


def _band_accuracy(answers: list[AnswerRecord]) -> dict[str, tuple[float, int]]:
    """{nível: (acerto médio, quantidade)}"""
    buckets: dict[str, list[float]] = {}
    for answer in answers:
        buckets.setdefault(answer.cefr_level, []).append(answer.normalized_score)
    return {
        level: (sum(scores) / len(scores), len(scores)) for level, scores in buckets.items()
    }


def independent_answers(answers: list[AnswerRecord]) -> list[AnswerRecord]:
    """One eligible observation per connected stimulus group; first response wins.

    Union all keys before counting so a passage/family bridge cannot turn two
    related items into independent observations. API supplies snapshot keys.
    Empty keys are reserved for synthetic engine callers.
    """
    import math
    valid = [a for a in answers if a.eligible and a.cefr_level in TESTABLE_LEVELS
             and not isinstance(a.normalized_score, bool)
             and math.isfinite(a.normalized_score) and 0 <= a.normalized_score <= 1]
    groups = []
    for answer in valid:
        keys = set(answer.evidence_keys)
        matches = [i for i, (_, existing) in enumerate(groups) if keys & existing]
        if not matches:
            groups.append((answer, keys))
        else:
            first = matches[0]
            groups[first][1].update(keys)
            for i in reversed(matches[1:]):
                groups[first][1].update(groups[i][1])
                groups.pop(i)
    return [a for a, _ in groups]


def confirmation_policy(answers: list[AnswerRecord]) -> dict:
    """Candidate is the highest band with a positive independent signal.

    Means >=.65 and two observations support measurement; failed/lower-band
    conflict requires three candidate observations and the same mean. Four
    observations across the skill remain mandatory for any measured estimate.
    """
    answers = independent_answers(answers)
    buckets = _band_accuracy(answers)
    signals = [a.cefr_level for a in answers if a.normalized_score >= BAND_MASTERY_THRESHOLD]
    candidate = max(signals, key=LEVEL_INDEX.__getitem__) if signals else None
    count = buckets.get(candidate, (0, 0))[1]
    conflict = bool(candidate and (
        any(a.cefr_level == candidate and a.normalized_score < BAND_MASTERY_THRESHOLD for a in answers)
        or any(LEVEL_INDEX[b] < LEVEL_INDEX[candidate] and n >= 2 and mean < BAND_MASTERY_THRESHOLD
               for b, (mean, n) in buckets.items())))
    needed = 3 if conflict else MIN_ITEMS_AT_DECIDING_BAND
    mastered = []
    if len(answers) >= MIN_ITEMS_PER_SKILL:
        for band, (mean, n) in buckets.items():
            band_conflict = any(a.cefr_level == band and a.normalized_score < BAND_MASTERY_THRESHOLD for a in answers) or any(
                LEVEL_INDEX[b] < LEVEL_INDEX[band] and qty >= 2 and avg < BAND_MASTERY_THRESHOLD
                for b, (avg, qty) in buckets.items())
            if mean >= BAND_MASTERY_THRESHOLD and n >= (3 if band_conflict else MIN_ITEMS_AT_DECIDING_BAND):
                mastered.append(band)
    measured = max(mastered, key=LEVEL_INDEX.__getitem__) if mastered else None
    required = candidate is not None and measured != candidate
    return {"candidate_level": candidate, "highest_supported_signal": candidate,
            "estimated_level": measured, "confirmation_required": required,
            "confirmation_count": count, "confirmation_needed": needed if candidate else 0,
            "confirmation_required_total": needed if candidate else 0,
            "confirmation_remaining": max(needed - count, 0) if candidate else 0,
            "candidate_reason": ("conflicting_band_evidence" if conflict else
                "confirmation_required" if required else "confirmed" if candidate else "no_positive_signal"),
            "selection_phase": "confirmed" if measured == candidate and measured else
                "confirmation" if required and len(answers) >= MIN_ITEMS_PER_SKILL else
                "candidate" if candidate else "exploration"}


def estimate_skill_level(answers: list[AnswerRecord]) -> str | None:
    return confirmation_policy(answers)["estimated_level"]


def skill_results(answers: list[AnswerRecord]) -> dict[str, dict]:
    """Resultado por competência, apenas para as efetivamente avaliadas."""
    grouped: dict[str, list[AnswerRecord]] = {}
    for answer in answers:
        grouped.setdefault(answer.skill, []).append(answer)

    results: dict[str, dict] = {}
    for skill, skill_answers in grouped.items():
        if skill in PRODUCTION_SKILLS:
            continue
        policy = confirmation_policy(skill_answers)
        independent = independent_answers(skill_answers)
        level = policy["estimated_level"]
        score = sum(a.normalized_score for a in skill_answers)
        results[skill] = {
            "skill": skill,
            **policy,
            "estimated_level": level,
            "score": round(score, 3),
            "max_score": float(len(skill_answers)),
            "items_count": len(skill_answers),
            "accuracy": round(score / len(skill_answers), 3),
            "independent_accuracy": round(sum(a.normalized_score for a in independent) / len(independent), 3) if independent else None,
            "status": "estimated" if level else "insufficient_evidence",
            "eligible_for_overall": level is not None,
            "evidence_counts": {
                "answered": len(skill_answers), "valid": len(independent), "independent": len(independent), "excluded": len(skill_answers) - len(independent),
                "by_cefr": {band: count for band, (_, count) in _band_accuracy(skill_answers).items()},
                "deciding_band": level,
                "at_deciding_band": sum(a.cefr_level == level for a in skill_answers) if level else 0,
            },
            "independent_evidence_counts": {"by_cefr": {band: n for band, (_, n) in _band_accuracy(independent).items()}, "total": len(independent)},
            "skill_confidence": {
                "basis": "rule_based_evidence", "label": "supported" if level else "insufficient",
                "reasons": [] if level else ["insufficient_or_conflicting_band_evidence"],
            },
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
    """Global conservative summary requires every skill to be eligible."""
    if set(results) != set(SKILL_WEIGHTS) or any(
        result.get("estimated_level") not in TESTABLE_LEVELS or not result.get("eligible_for_overall", False)
        for result in results.values()
    ):
        return None, {}
    return min((r["estimated_level"] for r in results.values()), key=LEVEL_INDEX.__getitem__), {}



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
    production_results: dict[str, dict] | None = None,
) -> dict:
    """Resultado completo do teste. Fonte única do cálculo (backend)."""
    answers = [a for a in answers if a.skill in OBJECTIVE_SKILLS]
    results = skill_results(answers)
    results.update(production_results or {})
    for skill in SKILL_WEIGHTS:
        results.setdefault(skill, {
            "skill": skill, "estimated_level": None,
            **(confirmation_policy([]) if skill in OBJECTIVE_SKILLS else {}),
            **({"independent_evidence_counts": {"by_cefr": {}, "total": 0}} if skill in OBJECTIVE_SKILLS else {}),
            "status": "not_collected", "eligible_for_overall": False,
            "score": None, "max_score": None,
            "evidence_counts": {"answered": 0, "valid": 0, "excluded": 0, "by_cefr": {}},
            "skill_confidence": {"basis": "rule_based_evidence", "label": "insufficient", "reasons": ["not_collected"]},
        })
    overall, weights = overall_level(results)
    confidence_value = None
    assessed = sorted(skill for skill, data in results.items() if data["estimated_level"])
    not_assessed = sorted(set(SKILL_WEIGHTS) - set(assessed))

    total_score = sum(a.normalized_score for a in answers)

    return {
        "overall_level": overall,
        "confidence_score": confidence_value,
        "confidence_label": None,
        "result_schema_version": 2,
        "policy_version": "placement-coverage-v2",
        "profile_status": "complete" if overall else "partial",
        "overall_estimate_status": "sufficient" if overall else "partial",
        "assessment_coverage": {
            "required_for_overall": list(SKILL_WEIGHTS),
            "sufficient_skills": [skill for skill, data in results.items() if data["eligible_for_overall"]],
            "missing_skills": [skill for skill, data in results.items() if not data["eligible_for_overall"]],
            "objective_answered": len(answers),
        },
        "total_score": round(total_score, 3),
        "max_score": float(len(answers)),
        "items_answered": len(answers),
        "duration_seconds": duration_seconds,
        "skills": results,
        "assessed_skills": assessed,
        "not_assessed_skills": not_assessed,
        "weights_used": {skill: round(weight, 4) for skill, weight in weights.items()},
        "recommendations": recommendations({s: r for s, r in results.items() if r["estimated_level"]}, overall) if overall else [
            {"skill": skill, "reason": "insufficient_evidence" if data["evidence_counts"]["answered"] else "not_assessed", "priority": 1}
            for skill, data in results.items() if not data["eligible_for_overall"] and data["status"] != "unavailable"],
    }
