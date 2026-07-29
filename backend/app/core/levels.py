"""Níveis linguísticos oficiais do BeFluent (CEFR/QECR) e competências avaliadas.

Decisão de arquitetura: os sete níveis são constantes de domínio, não uma tabela.
São imutáveis, não têm relação por FK com dados do usuário (as colunas guardam o
código como texto) e uma tabela exigiria migration + seed para sete linhas
estáticas. `GET /api/v1/levels` serve estas constantes.
"""

from __future__ import annotations

from enum import StrEnum


class CEFRLevel(StrEnum):
    PRE_A1 = "PRE_A1"
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class Skill(StrEnum):
    VOCABULARY_GRAMMAR = "vocabulary_grammar"
    READING = "reading"
    LISTENING = "listening"
    WRITING = "writing"
    SPEAKING = "speaking"


class TestStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class LevelSource(StrEnum):
    PLACEMENT_TEST = "placement_test"
    SELF_DECLARED = "self_declared"
    SELF_DECLARED_BEGINNER = "self_declared_beginner"
    ADMIN = "admin"
    IMPORTED = "imported"
    PENDING = "pending"


class ItemType(StrEnum):
    MULTIPLE_CHOICE = "multiple_choice"
    FILL_BLANK = "fill_blank"
    MATCHING = "matching"
    READING_COMPREHENSION = "reading_comprehension"
    LISTENING_COMPREHENSION = "listening_comprehension"
    SHORT_WRITING = "short_writing"
    SPEAKING_PROMPT = "speaking_prompt"


LEVEL_ORDER: list[str] = [
    CEFRLevel.PRE_A1,
    CEFRLevel.A1,
    CEFRLevel.A2,
    CEFRLevel.B1,
    CEFRLevel.B2,
    CEFRLevel.C1,
    CEFRLevel.C2,
]

LEVEL_INDEX: dict[str, int] = {code: index for index, code in enumerate(LEVEL_ORDER)}

#: Faixas que o teste inicial consegue classificar. C1/C2 existem na arquitetura,
#: mas exigem um banco de itens avançado que ainda não foi validado.
TESTABLE_LEVELS: list[str] = [
    CEFRLevel.PRE_A1,
    CEFRLevel.A1,
    CEFRLevel.A2,
    CEFRLevel.B1,
    CEFRLevel.B2,
]

LEVEL_DETAILS: dict[str, dict[str, str]] = {
    CEFRLevel.PRE_A1: {
        "name_pt": "Pré-A1 — Primeiros passos",
        "short_description": "Reconhece palavras, cumprimentos e expressões muito básicas.",
    },
    CEFRLevel.A1: {
        "name_pt": "A1 — Iniciante",
        "short_description": "Consegue se apresentar, fornecer informações pessoais e compreender frases simples.",
    },
    CEFRLevel.A2: {
        "name_pt": "A2 — Básico",
        "short_description": "Comunica-se em situações rotineiras e compreende mensagens frequentes.",
    },
    CEFRLevel.B1: {
        "name_pt": "B1 — Intermediário",
        "short_description": "Mantém conversas sobre temas familiares e relata experiências.",
    },
    CEFRLevel.B2: {
        "name_pt": "B2 — Intermediário avançado",
        "short_description": "Interage com boa espontaneidade e compreende conteúdos mais complexos.",
    },
    CEFRLevel.C1: {
        "name_pt": "C1 — Avançado",
        "short_description": "Usa o idioma com flexibilidade em contextos acadêmicos, sociais e profissionais.",
    },
    CEFRLevel.C2: {
        "name_pt": "C2 — Domínio",
        "short_description": "Compreende praticamente tudo e se expressa com grande precisão e naturalidade.",
    },
}

SKILL_LABELS: dict[str, str] = {
    Skill.VOCABULARY_GRAMMAR: "Vocabulário e gramática",
    Skill.READING: "Leitura",
    Skill.LISTENING: "Compreensão auditiva",
    Skill.WRITING: "Escrita",
    Skill.SPEAKING: "Fala",
}

#: Pesos completos. Quando uma competência não é avaliada, os pesos são
#: renormalizados apenas entre as avaliadas (nunca média simples).
SKILL_WEIGHTS: dict[str, float] = {
    Skill.VOCABULARY_GRAMMAR: 0.20,
    Skill.READING: 0.20,
    Skill.LISTENING: 0.20,
    Skill.WRITING: 0.20,
    Skill.SPEAKING: 0.20,
}

#: Competências essenciais para fluência: limitam o nível geral (ver
#: `placement_engine.overall_level`). Suporte = reading / vocabulary_grammar.
ESSENTIAL_SKILLS: set[str] = {Skill.LISTENING, Skill.SPEAKING}

#: Mapeamento dos rótulos genéricos legados (pré-CEFR) para códigos oficiais.
#: Usado pelo backfill da migration 0003 e pelo onboarding de clientes antigos.
LEGACY_LEVEL_MAP: dict[str, str | None] = {
    "iniciante": CEFRLevel.A1,
    "basico": CEFRLevel.A2,
    "básico": CEFRLevel.A2,
    "intermediario": CEFRLevel.B1,
    "intermediário": CEFRLevel.B1,
    "avancado": CEFRLevel.C1,
    "avançado": CEFRLevel.C1,
    "nao-sei": None,
    "não-sei": None,
}


def is_valid_level(code: str | None) -> bool:
    return code in LEVEL_INDEX


def normalize_level(code: str | None) -> str | None:
    """Converte rótulo legado ou código CEFR em código oficial (ou None)."""
    if not code:
        return None
    raw = code.strip()
    if raw in LEVEL_INDEX:
        return raw
    upper = raw.upper().replace("-", "_")
    if upper in LEVEL_INDEX:
        return upper
    return LEGACY_LEVEL_MAP.get(raw.lower())


def level_at(index: int) -> str:
    """Índice saturado nos limites da escala."""
    return LEVEL_ORDER[max(0, min(index, len(LEVEL_ORDER) - 1))]


def level_payload(code: str) -> dict:
    details = LEVEL_DETAILS[code]
    return {
        "code": code,
        "name_pt": details["name_pt"],
        "short_description": details["short_description"],
        "order_index": LEVEL_INDEX[code],
        "testable": code in TESTABLE_LEVELS,
    }


def all_levels() -> list[dict]:
    return [level_payload(code) for code in LEVEL_ORDER]


class ReviewStatus(StrEnum):
    """Estado de revisão de um item do banco (migration 0004).

    Item importado de corpus externo entra como `PENDING_REVIEW` e não é servido
    ao aluno: a calibragem automática de nível é heurística e precisa de
    conferência humana antes de valer como avaliação.
    """

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
