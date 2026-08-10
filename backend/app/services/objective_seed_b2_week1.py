"""Piloto Teaching Engine V2 — Semana 1 B2 EN «Argumentar e refutar».

Can-Dos reais por jornada (EN-B2-CAN-001 … 007). Idempotente.
Não expandir automaticamente para outras semanas.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.teaching import EvidenceType
from app.models import Language, LearningObjective

PILOT_THEME = "Argumentar e refutar"
PILOT_LEVEL = "B2"
PILOT_LANGUAGE = "en"
PILOT_WEEK_NUMBER = 1

#: day_in_week (1..7) → código estável
PILOT_DAY_CODES: dict[int, str] = {
    1: "EN-B2-CAN-001",
    2: "EN-B2-CAN-002",
    3: "EN-B2-CAN-003",
    4: "EN-B2-CAN-004",
    5: "EN-B2-CAN-005",
    6: "EN-B2-CAN-006",
    7: "EN-B2-CAN-007",
}

_SHARED_MASTERY = {
    "min_evidence_count": 2,
    "required_evidence_types": [
        EvidenceType.CORRECT_RESPONSE,
        EvidenceType.TRANSFER,
    ],
    "require_transfer_success": True,
    "block_on_unresolved_severity": "critical",
}


def _obj(
    *,
    code: str,
    title: str,
    can_do: str,
    description: str,
    vocabulary: list[str],
    expressions: list[str],
    patterns: list[dict],
    pedagogy: dict,
) -> dict:
    return {
        "code": code,
        "level": PILOT_LEVEL,
        "title": title,
        "can_do": can_do,
        "description": description,
        "skill_focus": "conversation",
        "target_vocabulary": vocabulary,
        "target_expressions": expressions,
        "target_patterns": patterns,
        "pronunciation_focus": vocabulary[:3],
        "pedagogy": pedagogy,
        "mastery_policy": dict(_SHARED_MASTERY),
    }


EN_B2_WEEK1: list[dict] = [
    _obj(
        code="EN-B2-CAN-001",
        title="Expressar uma opinião com clareza",
        can_do=(
            "O aluno consegue expressar uma opinião clara sobre um tema "
            "argumentativo usando estruturas apropriadas a B2."
        ),
        description="Dia 1 · Semana 1 B2 · Argumentar e refutar",
        vocabulary=["opinion", "view", "to hold that", "clearly", "personally"],
        expressions=[
            "In my opinion, the policy needs revision.",
            "I hold that transparency matters here.",
            "Personally, I see a clearer alternative.",
        ],
        patterns=[
            {
                "canonical": "In my opinion, the policy needs revision.",
                "accepted": [
                    "In my opinion, the policy needs revision.",
                    "In my opinion the policy needs revision.",
                ],
                "required_features": ["opinion"],
            },
            {
                "canonical": "I hold that transparency matters here.",
                "accepted": [
                    "I hold that transparency matters here.",
                    "I hold that transparency matters.",
                ],
                "required_features": ["hold"],
            },
        ],
        pedagogy={
            "activation": {
                "title_pt": "Expressar uma opinião",
                "can_do": "Expressar uma opinião de forma clara.",
                "support_pt": "Hoje você vai aprender a declarar uma posição com clareza.",
            },
            "noticing": {
                "prompt_pt": "Note: In my opinion… / I hold that… / Personally…",
                "examples": [
                    "In my opinion, the policy needs revision.",
                    "I hold that transparency matters here.",
                ],
            },
            "guided_prompt": {
                "prompt": "What is your opinion on remote work?",
                "prompt_pt": "Qual é a sua opinião sobre trabalho remoto?",
                "scaffold_pt": "In my opinion… / I hold that…",
                "required_features": ["opinion"],
                "evaluation_mode": "guided",
                "minimum_structure": "clause",
            },
            "transfer_prompts": [
                {
                    "prompt": "Should cities ban cars from downtown?",
                    "prompt_pt": "As cidades deveriam banir carros do centro?",
                    "scaffold_pt": "In my opinion…",
                    "expected_features": ["opinion"],
                    "evaluation_mode": "transfer",
                    "minimum_structure": "clause",
                    "accepted_variants": [
                        "In my opinion, cities should ban cars from downtown.",
                        "In my opinion cities should not ban cars from downtown.",
                        "I hold that cities should ban cars downtown.",
                    ],
                }
            ],
            "pilot": {"week": 1, "day_in_week": 1, "theme": PILOT_THEME},
        },
    ),
    _obj(
        code="EN-B2-CAN-002",
        title="Sustentar uma opinião com razões e exemplos",
        can_do=(
            "O aluno consegue sustentar uma opinião apresentando razões e "
            "exemplos relevantes."
        ),
        description="Dia 2 · Semana 1 B2 · Argumentar e refutar",
        vocabulary=["because", "for instance", "to support", "evidence", "reason"],
        expressions=[
            "I support this view because the data is clear.",
            "For instance, smaller teams decide faster.",
            "One reason is the cost of delay.",
        ],
        patterns=[
            {
                "canonical": "I support this view because the data is clear.",
                "accepted": [
                    "I support this view because the data is clear.",
                    "I support this view because the data are clear.",
                ],
                "required_features": ["because"],
            },
            {
                "canonical": "For instance, smaller teams decide faster.",
                "accepted": [
                    "For instance, smaller teams decide faster.",
                    "For instance smaller teams decide faster.",
                ],
                "required_features": ["instance"],
            },
        ],
        pedagogy={
            "activation": {
                "title_pt": "Sustentar com razões",
                "can_do": "Sustentar uma opinião apresentando razões e exemplos.",
                "support_pt": "Hoje você vai apoiar sua opinião com razões e exemplos.",
            },
            "noticing": {
                "prompt_pt": "Note: because… / for instance… / one reason is…",
                "examples": [
                    "I support this view because the data is clear.",
                    "For instance, smaller teams decide faster.",
                ],
            },
            "guided_prompt": {
                "prompt": "Support your opinion on flexible hours with one reason.",
                "prompt_pt": "Sustente sua opinião sobre horário flexível com uma razão.",
                "scaffold_pt": "I support… because… / For instance…",
                "required_features": ["because"],
                "evaluation_mode": "guided",
                "minimum_structure": "clause",
            },
            "transfer_prompts": [
                {
                    "prompt": "Why should schools delay the start of the day?",
                    "prompt_pt": "Por que as escolas deveriam atrasar o início do dia?",
                    "scaffold_pt": "… because… / For instance…",
                    "expected_features": ["because"],
                    "evaluation_mode": "transfer",
                    "minimum_structure": "clause",
                    "accepted_variants": [
                        "Schools should delay the start because students sleep better.",
                        "I support a later start because the evidence is clear.",
                        "For instance, teens learn better after 9 a.m.",
                    ],
                }
            ],
            "pilot": {"week": 1, "day_in_week": 2, "theme": PILOT_THEME},
        },
    ),
    _obj(
        code="EN-B2-CAN-003",
        title="Concordar e discordar com adequação",
        can_do=(
            "O aluno consegue concordar e discordar de forma adequada e "
            "respeitosa em um debate."
        ),
        description="Dia 3 · Semana 1 B2 · Argumentar e refutar",
        vocabulary=["agree", "disagree", "on the contrary", "partly", "respectfully"],
        expressions=[
            "I partly agree with that point.",
            "On the contrary, the trend is falling.",
            "I respectfully disagree with that claim.",
        ],
        patterns=[
            {
                "canonical": "I partly agree with that point.",
                "accepted": [
                    "I partly agree with that point.",
                    "I partly agree with that.",
                ],
                "required_features": ["agree"],
            },
            {
                "canonical": "I respectfully disagree with that claim.",
                "accepted": [
                    "I respectfully disagree with that claim.",
                    "I respectfully disagree.",
                ],
                "required_features": ["disagree"],
            },
        ],
        pedagogy={
            "activation": {
                "title_pt": "Concordar e discordar",
                "can_do": "Concordar e discordar de forma adequada.",
                "support_pt": "Hoje você pratica concordância e discordância diplomáticas.",
            },
            "noticing": {
                "prompt_pt": "Note: I partly agree… / On the contrary… / I respectfully disagree…",
                "examples": [
                    "I partly agree with that point.",
                    "On the contrary, the trend is falling.",
                ],
            },
            "guided_prompt": {
                "prompt": "A colleague says meetings are always useful. Respond.",
                "prompt_pt": "Um colega diz que reuniões são sempre úteis. Responda.",
                "scaffold_pt": "I partly agree… / I respectfully disagree…",
                "required_features": ["agree"],
                "evaluation_mode": "guided",
                "minimum_structure": "clause",
            },
            "transfer_prompts": [
                {
                    "prompt": "Someone claims AI will replace all teachers. Respond politely.",
                    "prompt_pt": "Alguém afirma que a IA substituirá todos os professores. Responda com educação.",
                    "scaffold_pt": "I respectfully disagree… / I partly agree…",
                    "expected_features": ["disagree"],
                    "evaluation_mode": "transfer",
                    "minimum_structure": "clause",
                    "accepted_variants": [
                        "I respectfully disagree with that claim.",
                        "I partly agree, but teachers still matter.",
                        "On the contrary, teachers remain essential.",
                    ],
                }
            ],
            "pilot": {"week": 1, "day_in_week": 3, "theme": PILOT_THEME},
        },
    ),
    _obj(
        code="EN-B2-CAN-004",
        title="Introduzir um contraponto",
        can_do=(
            "O aluno consegue introduzir um contraponto a uma opinião de forma "
            "clara e coerente."
        ),
        description="Dia 4 · Semana 1 B2 · Argumentar e refutar",
        vocabulary=["however", "that said", "counterpoint", "although", "nonetheless"],
        expressions=[
            "That said, the costs are still high.",
            "However, the evidence is incomplete.",
            "Although the idea is popular, the risks remain.",
        ],
        patterns=[
            {
                "canonical": "That said, the costs are still high.",
                "accepted": [
                    "That said, the costs are still high.",
                    "That said the costs are still high.",
                ],
                "required_features": ["said"],
            },
            {
                "canonical": "However, the evidence is incomplete.",
                "accepted": [
                    "However, the evidence is incomplete.",
                    "However the evidence is incomplete.",
                ],
                "required_features": ["however"],
            },
        ],
        pedagogy={
            "activation": {
                "title_pt": "Introduzir um contraponto",
                "can_do": "Introduzir um contraponto a uma opinião.",
                "support_pt": "Hoje você aprende a abrir espaço para o outro lado do argumento.",
            },
            "noticing": {
                "prompt_pt": "Note: That said… / However… / Although…",
                "examples": [
                    "That said, the costs are still high.",
                    "However, the evidence is incomplete.",
                ],
            },
            "guided_prompt": {
                "prompt": "Add a counterpoint to: 'Online courses are enough.'",
                "prompt_pt": "Acrescente um contraponto a: 'Cursos online bastam.'",
                "scaffold_pt": "That said… / However…",
                "required_features": ["however"],
                "evaluation_mode": "guided",
                "minimum_structure": "clause",
            },
            "transfer_prompts": [
                {
                    "prompt": "Respond with a counterpoint to: 'Growth always justifies risk.'",
                    "prompt_pt": "Responda com um contraponto a: 'Crescimento sempre justifica risco.'",
                    "scaffold_pt": "That said… / However…",
                    "expected_features": ["however"],
                    "evaluation_mode": "transfer",
                    "minimum_structure": "clause",
                    "accepted_variants": [
                        "However, the evidence is incomplete.",
                        "That said, the costs are still high.",
                        "Although growth matters, the risks remain.",
                    ],
                }
            ],
            "pilot": {"week": 1, "day_in_week": 4, "theme": PILOT_THEME},
        },
    ),
    _obj(
        code="EN-B2-CAN-005",
        title="Refutar com clareza e respeito",
        can_do=(
            "O aluno consegue refutar um argumento de forma clara e respeitosa, "
            "usando evidência ou lógica."
        ),
        description="Dia 5 · Semana 1 B2 · Argumentar e refutar",
        vocabulary=["to rebut", "to call into question", "claim", "flaw", "respectfully"],
        expressions=[
            "I would rebut that claim with three facts.",
            "This calls into question the official figures.",
            "The main flaw is the missing sample.",
        ],
        patterns=[
            {
                "canonical": "I would rebut that claim with three facts.",
                "accepted": [
                    "I would rebut that claim with three facts.",
                    "I rebut that claim with three facts.",
                ],
                "required_features": ["rebut"],
            },
            {
                "canonical": "This calls into question the official figures.",
                "accepted": [
                    "This calls into question the official figures.",
                    "This calls the official figures into question.",
                ],
                "required_features": ["question"],
            },
        ],
        pedagogy={
            "activation": {
                "title_pt": "Refutar com respeito",
                "can_do": "Refutar um argumento de forma clara e respeitosa.",
                "support_pt": "Hoje você pratica refutação sem agressividade.",
            },
            "noticing": {
                "prompt_pt": "Note: rebut… / call into question… / the main flaw…",
                "examples": [
                    "I would rebut that claim with three facts.",
                    "This calls into question the official figures.",
                ],
            },
            "guided_prompt": {
                "prompt": "Refute: 'The report proves the policy worked.'",
                "prompt_pt": "Refute: 'O relatório prova que a política funcionou.'",
                "scaffold_pt": "I would rebut… / This calls into question…",
                "required_features": ["rebut"],
                "evaluation_mode": "guided",
                "minimum_structure": "clause",
            },
            "transfer_prompts": [
                {
                    "prompt": "Politely rebut: 'Nobody benefits from regulation.'",
                    "prompt_pt": "Refute com educação: 'Ninguém se beneficia da regulação.'",
                    "scaffold_pt": "I would rebut… / This calls into question…",
                    "expected_features": ["rebut"],
                    "evaluation_mode": "transfer",
                    "minimum_structure": "clause",
                    "accepted_variants": [
                        "I would rebut that claim with three facts.",
                        "This calls into question the official figures.",
                        "The main flaw is the missing sample.",
                    ],
                }
            ],
            "pilot": {"week": 1, "day_in_week": 5, "theme": PILOT_THEME},
        },
    ),
    _obj(
        code="EN-B2-CAN-006",
        title="Defender uma posição na interação",
        can_do=(
            "O aluno consegue defender uma posição em uma interação/conversação "
            "argumentativa, mantendo coerência."
        ),
        description="Dia 6 · Semana 1 B2 · Argumentar e refutar",
        vocabulary=["to stand by", "to put forward", "position", "defend", "consistent"],
        expressions=[
            "I stand by my earlier conclusion.",
            "Let me put forward a clearer framework.",
            "I can defend this position with two points.",
        ],
        patterns=[
            {
                "canonical": "I stand by my earlier conclusion.",
                "accepted": [
                    "I stand by my earlier conclusion.",
                    "I stand by that conclusion.",
                ],
                "required_features": ["stand"],
            },
            {
                "canonical": "Let me put forward a clearer framework.",
                "accepted": [
                    "Let me put forward a clearer framework.",
                    "I put forward a clearer framework.",
                ],
                "required_features": ["forward"],
            },
        ],
        pedagogy={
            "activation": {
                "title_pt": "Defender na conversa",
                "can_do": "Defender uma posição em uma interação/conversação.",
                "support_pt": "Hoje você defende sua posição em um diálogo.",
            },
            "noticing": {
                "prompt_pt": "Note: I stand by… / put forward… / defend this position…",
                "examples": [
                    "I stand by my earlier conclusion.",
                    "Let me put forward a clearer framework.",
                ],
            },
            "guided_prompt": {
                "prompt": "Defend your position on public transport investment.",
                "prompt_pt": "Defenda sua posição sobre investimento em transporte público.",
                "scaffold_pt": "I stand by… / Let me put forward…",
                "required_features": ["stand"],
                "evaluation_mode": "guided",
                "minimum_structure": "clause",
            },
            "transfer_prompts": [
                {
                    "prompt": "In a meeting, someone challenges your plan. Defend it briefly.",
                    "prompt_pt": "Em uma reunião, alguém questiona seu plano. Defenda-o brevemente.",
                    "scaffold_pt": "I stand by… / I can defend…",
                    "expected_features": ["stand"],
                    "evaluation_mode": "transfer",
                    "minimum_structure": "clause",
                    "accepted_variants": [
                        "I stand by my earlier conclusion.",
                        "Let me put forward a clearer framework.",
                        "I can defend this position with two points.",
                    ],
                }
            ],
            "pilot": {"week": 1, "day_in_week": 6, "theme": PILOT_THEME},
        },
    ),
    _obj(
        code="EN-B2-CAN-007",
        title="Transferência — argumentar em situação nova",
        can_do=(
            "O aluno consegue aplicar os recursos da semana (opinião, razões, "
            "contraponto e refutação) em uma situação nova de argumentação."
        ),
        description="Dia 7 · Checkpoint/transfer · Semana 1 B2",
        vocabulary=[
            "opinion",
            "because",
            "however",
            "to rebut",
            "to stand by",
            "compromise",
        ],
        expressions=[
            "In my opinion, we should delay the launch.",
            "I support this because the risks outweigh the gains.",
            "That said, a smaller pilot could work.",
            "I would rebut the urgency claim with the latest metrics.",
        ],
        patterns=[
            {
                "canonical": "In my opinion, we should delay the launch.",
                "accepted": [
                    "In my opinion, we should delay the launch.",
                    "In my opinion we should delay the launch.",
                ],
                "required_features": ["opinion"],
            },
            {
                "canonical": "I support this because the risks outweigh the gains.",
                "accepted": [
                    "I support this because the risks outweigh the gains.",
                    "I support this because the risks outweigh the benefits.",
                ],
                "required_features": ["because"],
            },
        ],
        pedagogy={
            "activation": {
                "title_pt": "Checkpoint — situação nova",
                "can_do": "Aplicar os recursos da semana em uma situação nova.",
                "support_pt": (
                    "Situação nova: uma equipe quer lançar um produto cedo. "
                    "Apresente posição, justifique, responda a um contraponto e refute ou negocie."
                ),
            },
            "noticing": {
                "prompt_pt": "Combine: opinião → razão → contraponto → resposta.",
                "examples": [
                    "In my opinion, we should delay the launch.",
                    "I support this because the risks outweigh the gains.",
                    "That said, a smaller pilot could work.",
                ],
            },
            "guided_prompt": {
                "prompt": (
                    "Your team wants to launch next week despite weak tests. "
                    "State your position and one reason."
                ),
                "prompt_pt": (
                    "Sua equipe quer lançar na próxima semana apesar de testes fracos. "
                    "Declare sua posição e uma razão."
                ),
                "scaffold_pt": "In my opinion… because…",
                "required_features": ["opinion", "because"],
                "evaluation_mode": "guided",
                "minimum_structure": "clause",
            },
            "transfer_prompts": [
                {
                    "prompt": (
                        "A manager says delay is unacceptable. Present a position, "
                        "one reason, a counterpoint response, and a brief rebuttal or compromise."
                    ),
                    "prompt_pt": (
                        "Um gestor diz que atrasar é inaceitável. Apresente posição, "
                        "uma razão, resposta a um contraponto e uma refutação ou compromisso breve."
                    ),
                    "scaffold_pt": "In my opinion… because… That said… I would rebut…",
                    "expected_features": ["opinion", "because"],
                    "evaluation_mode": "transfer",
                    "minimum_structure": "clause",
                    "accepted_variants": [
                        "In my opinion, we should delay the launch because the risks outweigh the gains.",
                        "I support a delay because the tests are weak. That said, a smaller pilot could work.",
                        "In my opinion we should delay. I would rebut the urgency claim with the latest metrics.",
                    ],
                }
            ],
            "pilot": {"week": 1, "day_in_week": 7, "theme": PILOT_THEME, "transfer_day": True},
        },
    ),
]


def _upsert(db: Session, language_id: str, data: dict) -> LearningObjective:
    existing = db.scalar(
        select(LearningObjective).where(
            LearningObjective.language_id == language_id,
            LearningObjective.code == data["code"],
        )
    )
    fields = dict(
        level=data["level"],
        title=data["title"],
        can_do=data["can_do"],
        description=data["description"],
        skill_focus=data["skill_focus"],
        prerequisites_json=[],
        target_vocabulary_json=data["target_vocabulary"],
        target_expressions_json=data["target_expressions"],
        target_patterns_json=data["target_patterns"],
        pronunciation_focus_json=data["pronunciation_focus"],
        pedagogy_json=data["pedagogy"],
        mastery_policy_json=data["mastery_policy"],
        is_active=True,
        version=1,
    )
    if existing is None:
        objective = LearningObjective(
            language_id=language_id,
            code=data["code"],
            **fields,
        )
        db.add(objective)
        db.flush()
        return objective
    for key, value in fields.items():
        setattr(existing, key, value)
    db.flush()
    return existing


def ensure_en_b2_week1_objectives(db: Session) -> list[LearningObjective]:
    language = db.scalar(select(Language).where(Language.code == PILOT_LANGUAGE))
    if language is None:
        raise RuntimeError("Idioma 'en' não encontrado — rode seed_languages antes.")
    return [_upsert(db, language.id, data) for data in EN_B2_WEEK1]


def resolve_pilot_objective(
    db: Session,
    *,
    language_code: str,
    cefr_level: str,
    theme: str,
    week_number: int,
    day_in_week: int,
) -> LearningObjective | None:
    """Resolve Can-Do do piloto Semana 1 B2; None fora do escopo."""
    if (
        language_code != PILOT_LANGUAGE
        or cefr_level != PILOT_LEVEL
        or week_number != PILOT_WEEK_NUMBER
        or theme != PILOT_THEME
    ):
        return None
    code = PILOT_DAY_CODES.get(day_in_week)
    if not code:
        return None
    ensure_en_b2_week1_objectives(db)
    language = db.scalar(select(Language).where(Language.code == PILOT_LANGUAGE))
    if language is None:
        return None
    return db.scalar(
        select(LearningObjective).where(
            LearningObjective.language_id == language.id,
            LearningObjective.code == code,
        )
    )


def is_pilot_day(*, language_code: str, cefr_level: str, theme: str, week_number: int) -> bool:
    return (
        language_code == PILOT_LANGUAGE
        and cefr_level == PILOT_LEVEL
        and week_number == PILOT_WEEK_NUMBER
        and theme == PILOT_THEME
    )
