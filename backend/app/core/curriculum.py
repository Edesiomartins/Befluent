"""Constantes de domínio do cronograma estruturado de estudo.

Separado de `levels.py` de propósito: `Skill` lá é a competência **avaliada**
pelo teste de nivelamento (cinco competências CEFR). Aqui `BlockSkill` é o tipo
de **bloco de estudo** do dia (oito áreas), que é uma granularidade diferente —
`grammar` e `vocabulary` são blocos distintos mas caem na mesma competência
avaliada, e `review` não é competência nenhuma: é a fila do SRS.

Como em `levels.py`, são constantes imutáveis, não tabela.
"""

from __future__ import annotations

from enum import StrEnum

from app.core.levels import Skill


class BlockSkill(StrEnum):
    VOCABULARY = "vocabulary"
    GRAMMAR = "grammar"
    PRONUNCIATION = "pronunciation"
    LISTENING = "listening"
    READING = "reading"
    CONVERSATION = "conversation"
    WRITING = "writing"
    REVIEW = "review"


class CurriculumStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    REGENERATED = "regenerated"


class DayStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class BlockStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"


class GeneratedFrom(StrEnum):
    PLACEMENT = "placement"
    MANUAL = "manual"
    ONBOARDING = "onboarding"


#: Durações permitidas, em dias. Fora disso o gerador recusa.
DURATION_90 = 90
DURATION_180 = 180
ALLOWED_DURATIONS: tuple[int, ...] = (DURATION_90, DURATION_180)

BLOCK_SKILL_LABELS: dict[str, str] = {
    BlockSkill.VOCABULARY: "Vocabulário",
    BlockSkill.GRAMMAR: "Gramática",
    BlockSkill.PRONUNCIATION: "Pronúncia",
    BlockSkill.LISTENING: "Compreensão auditiva",
    BlockSkill.READING: "Leitura",
    BlockSkill.CONVERSATION: "Conversação",
    BlockSkill.WRITING: "Escrita",
    BlockSkill.REVIEW: "Revisão",
}

#: Bloco de estudo → competência CEFR avaliada. Define de qual coluna de
#: `UserLanguage` sai o nível daquele bloco.
BLOCK_ASSESSED_SKILL: dict[str, str] = {
    BlockSkill.VOCABULARY: Skill.VOCABULARY_GRAMMAR,
    BlockSkill.GRAMMAR: Skill.VOCABULARY_GRAMMAR,
    BlockSkill.PRONUNCIATION: Skill.SPEAKING,
    BlockSkill.LISTENING: Skill.LISTENING,
    BlockSkill.READING: Skill.READING,
    BlockSkill.CONVERSATION: Skill.SPEAKING,
    BlockSkill.WRITING: Skill.WRITING,
    BlockSkill.REVIEW: Skill.VOCABULARY_GRAMMAR,
}

#: Bloco de estudo → modo de lição existente (`app/prompts/library.py`).
#: O currículo não inventa um segundo catálogo de conteúdo: ele reaproveita
#: os modos que já geram lição, mock ou por IA.
BLOCK_LESSON_MODE: dict[str, str] = {
    BlockSkill.VOCABULARY: "vocabulary",
    BlockSkill.GRAMMAR: "grammar",
    BlockSkill.PRONUNCIATION: "pronunciation",
    BlockSkill.LISTENING: "listening",
    BlockSkill.READING: "reading",
    BlockSkill.CONVERSATION: "conversation",
    BlockSkill.WRITING: "writing",
    BlockSkill.REVIEW: "review",
}

#: Blocos de entrada (compreensão) e de saída (produção). O dia alterna dentro
#: de cada par para não repetir a mesma habilidade dois dias seguidos.
INPUT_BLOCKS: tuple[str, ...] = (BlockSkill.LISTENING, BlockSkill.READING)
OUTPUT_BLOCKS: tuple[str, ...] = (BlockSkill.CONVERSATION, BlockSkill.WRITING)

#: Blocos que nunca saem do dia, mesmo em compressão de atraso.
ESSENTIAL_BLOCKS: frozenset[str] = frozenset(
    {BlockSkill.VOCABULARY, BlockSkill.GRAMMAR, BlockSkill.REVIEW}
)


class LessonPhase(StrEnum):
    """Fases pedagógicas do dia — ordem estilo path (ativar → produzir → fixar)."""

    ACTIVATE = "activate"
    STRUCTURE = "structure"
    INPUT = "input"
    OUTPUT = "output"
    CONSOLIDATE = "consolidate"


PHASE_LABELS: dict[str, str] = {
    LessonPhase.ACTIVATE: "Ativar",
    LessonPhase.STRUCTURE: "Estruturar",
    LessonPhase.INPUT: "Compreender",
    LessonPhase.OUTPUT: "Produzir",
    LessonPhase.CONSOLIDATE: "Consolidar",
}

PHASE_WHY: dict[str, str] = {
    LessonPhase.ACTIVATE: "Primeiro ativa o léxico do tema — sem palavras, o resto trava.",
    LessonPhase.STRUCTURE: "Depois organiza a forma: padrões e sons que você vai usar.",
    LessonPhase.INPUT: "Escuta ou lê o tema em contexto antes de falar ou escrever.",
    LessonPhase.OUTPUT: "Só então produz: conversa ou escrita com o que acabou de ver.",
    LessonPhase.CONSOLIDATE: "Fecha com revisão espaçada para não esquecer amanhã.",
}

BLOCK_PHASE: dict[str, str] = {
    BlockSkill.VOCABULARY: LessonPhase.ACTIVATE,
    BlockSkill.GRAMMAR: LessonPhase.STRUCTURE,
    BlockSkill.PRONUNCIATION: LessonPhase.STRUCTURE,
    BlockSkill.LISTENING: LessonPhase.INPUT,
    BlockSkill.READING: LessonPhase.INPUT,
    BlockSkill.CONVERSATION: LessonPhase.OUTPUT,
    BlockSkill.WRITING: LessonPhase.OUTPUT,
    BlockSkill.REVIEW: LessonPhase.CONSOLIDATE,
}


def block_skill_label(skill: str) -> str:
    return BLOCK_SKILL_LABELS.get(skill, skill)


def block_phase(skill: str) -> str:
    return BLOCK_PHASE.get(skill, LessonPhase.ACTIVATE)


def block_phase_label(skill: str) -> str:
    return PHASE_LABELS.get(block_phase(skill), "")


def block_phase_why(skill: str) -> str:
    return PHASE_WHY.get(block_phase(skill), "")
