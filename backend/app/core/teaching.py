"""Constantes de domínio do Teaching Engine — núcleo pedagógico entre currículo
e atividades.

Distingue formalmente **atividade concluída** (`CurriculumBlock.status`, já
existente) de **aprendizagem demonstrada** (`MasteryState`, aqui). Erro não
termina a atividade: gera diagnóstico → remediação → nova tentativa →
reavaliação, nunca um "reprovado" sem caminho de volta.

`FlowPhase` é a máquina de estados da sessão pedagógica (Teaching Flow V2);
`MasteryState` continua sendo o estado de domínio do objetivo — são eixos
ortogonais: um bloco pode estar COMPLETED enquanto o objetivo ainda PRACTICING.

Como em `core/levels.py` e `core/curriculum.py`: enums e tabelas de política
são constantes imutáveis de código, não linhas de banco.
"""

from __future__ import annotations

from enum import StrEnum


class FlowPhase(StrEnum):
    """Fases da sessão Teaching Flow. Backend é a fonte da verdade."""

    NOT_STARTED = "not_started"
    ACTIVATING = "activating"
    INPUT = "input"
    NOTICING = "noticing"
    PRACTICING = "practicing"
    PRODUCING = "producing"
    EVALUATING = "evaluating"
    NEEDS_REMEDIATION = "needs_remediation"
    RETRYING = "retrying"
    TRANSFER_CHECK = "transfer_check"
    MASTERED = "mastered"
    NEEDS_REVIEW = "needs_review"


#: Transições válidas da Teaching Flow. Chave = fase atual; valor = fases
#: permitidas. O frontend não pode inventar estado — só pede transição.
VALID_FLOW_TRANSITIONS: dict[str, frozenset[str]] = {
    FlowPhase.NOT_STARTED: frozenset({FlowPhase.ACTIVATING}),
    FlowPhase.ACTIVATING: frozenset({FlowPhase.INPUT}),
    FlowPhase.INPUT: frozenset({FlowPhase.NOTICING}),
    FlowPhase.NOTICING: frozenset({FlowPhase.PRACTICING}),
    FlowPhase.PRACTICING: frozenset(
        {FlowPhase.PRODUCING, FlowPhase.EVALUATING, FlowPhase.NEEDS_REMEDIATION}
    ),
    FlowPhase.PRODUCING: frozenset({FlowPhase.EVALUATING, FlowPhase.NEEDS_REMEDIATION}),
    FlowPhase.EVALUATING: frozenset(
        {
            FlowPhase.PRACTICING,
            FlowPhase.PRODUCING,
            FlowPhase.NEEDS_REMEDIATION,
            FlowPhase.TRANSFER_CHECK,
            FlowPhase.MASTERED,
            FlowPhase.NEEDS_REVIEW,
        }
    ),
    FlowPhase.NEEDS_REMEDIATION: frozenset({FlowPhase.RETRYING, FlowPhase.NEEDS_REVIEW}),
    FlowPhase.RETRYING: frozenset(
        {FlowPhase.EVALUATING, FlowPhase.NEEDS_REMEDIATION, FlowPhase.PRACTICING}
    ),
    FlowPhase.TRANSFER_CHECK: frozenset(
        {
            FlowPhase.EVALUATING,
            FlowPhase.MASTERED,
            FlowPhase.NEEDS_REMEDIATION,
            FlowPhase.NEEDS_REVIEW,
        }
    ),
    FlowPhase.MASTERED: frozenset({FlowPhase.NEEDS_REVIEW}),
    FlowPhase.NEEDS_REVIEW: frozenset({FlowPhase.PRACTICING, FlowPhase.ACTIVATING}),
}


class ActivityType(StrEnum):
    """Formas de prática geráveis a partir de um LearningObjective."""

    RECOGNITION = "recognition"
    MULTIPLE_CHOICE = "multiple_choice"
    MATCHING = "matching"
    CONTROLLED_RECALL = "controlled_recall"
    FILL_GAP = "fill_gap"
    WORD_ORDER = "word_order"
    LISTENING_RECOGNITION = "listening_recognition"
    GUIDED_PRODUCTION = "guided_production"
    FREE_PRODUCTION = "free_production"
    CONVERSATION_PROMPT = "conversation_prompt"
    TRANSFER_QUESTION = "transfer_question"
    REVIEW = "review"
    LISTEN = "listen"
    REPEAT = "repeat"
    SHADOW = "shadow"
    RECALL = "recall"
    RETELL = "retell"


class MemorySubjectType(StrEnum):
    VOCABULARY = "vocabulary"
    EXPRESSION = "expression"
    GRAMMAR_PATTERN = "grammar_pattern"
    LEARNER_ERROR = "learner_error"
    LEARNING_OBJECTIVE = "learning_objective"


class MasteryState(StrEnum):
    """Estado de domínio do aluno sobre um `LearningObjective`.

    `RETRYING` é o único estado que não sai de `evaluate_mastery` — é setado
    diretamente por `record_retry` enquanto a nova tentativa ainda não foi
    avaliada. Todos os demais são recomputados a partir de evidência/erro.
    """

    NOT_STARTED = "not_started"
    LEARNING = "learning"
    PRACTICING = "practicing"
    NEEDS_REMEDIATION = "needs_remediation"
    RETRYING = "retrying"
    MASTERED = "mastered"
    #: Atividade/bloco foi concluído, mas a evidência registrada não sustenta
    #: domínio — o princípio central do Teaching Engine: concluir ≠ dominar.
    NEEDS_REVIEW = "needs_review"


class AttemptResult(StrEnum):
    PENDING = "pending"
    CORRECT = "correct"
    PARTIAL = "partial"
    INCORRECT = "incorrect"


class EvidenceType(StrEnum):
    CORRECT_RESPONSE = "correct_response"
    SUCCESSFUL_RECALL = "successful_recall"
    COMPREHENSION = "comprehension"
    REQUIRED_PATTERN_USED = "required_pattern_used"
    WRITTEN_PRODUCTION = "written_production"
    ORAL_PRODUCTION_TRANSCRIBED = "oral_production_transcribed"
    SPOKEN_INTELLIGIBILITY = "spoken_intelligibility"
    STRUCTURE_APPLICATION = "structure_application"
    #: Aplicação do conhecimento numa pergunta nova — o sinal mais forte de
    #: domínio real, não de memorização do exemplo treinado.
    TRANSFER = "transfer"
    ERROR_REPAIRED = "error_repaired"


class ErrorCategory(StrEnum):
    GRAMMAR = "grammar"
    VOCABULARY = "vocabulary"
    WORD_ORDER = "word_order"
    COMPREHENSION = "comprehension"
    SPELLING = "spelling"
    REGISTER = "register"
    PRONUNCIATION_INTELLIGIBILITY = "pronunciation_intelligibility"
    OTHER = "other"


class ErrorSeverity(StrEnum):
    MINOR = "minor"
    MODERATE = "moderate"
    CRITICAL = "critical"


#: Ordem para comparação de limiar — não é um score, é só "quão grave" para
#: decidir se um erro pendente bloqueia domínio pela política configurada.
SEVERITY_RANK: dict[str, int] = {
    ErrorSeverity.MINOR: 0,
    ErrorSeverity.MODERATE: 1,
    ErrorSeverity.CRITICAL: 2,
}


class RemediationAction(StrEnum):
    EXPLAIN = "explain"
    HINT = "hint"
    SHOW_CONTRAST = "show_contrast"
    SHOW_EXAMPLE = "show_example"
    SIMPLIFY = "simplify"
    CONTROLLED_RETRY = "controlled_retry"
    REPHRASE = "rephrase"
    REPEAT_INPUT = "repeat_input"
    NEW_CONTEXT = "new_context"
    GUIDED_RETRY = "guided_retry"
    #: Aliases legados V1 — mantidos para não quebrar remediações já gravadas.
    GIVE_HINT = "give_hint"
    NEW_EXAMPLE = "new_example"


#: Escalonamento de remediação por ocorrências do mesmo erro (heurística).
#: 1ª → hint; 2ª → explain; recorrente → contraste + prática controlada.
REMEDIATION_ESCALATION: list[str] = [
    RemediationAction.HINT,
    RemediationAction.EXPLAIN,
    RemediationAction.SHOW_CONTRAST,
    RemediationAction.CONTROLLED_RETRY,
]

#: Limite de ciclos remediação→retry antes de marcar NEEDS_REVIEW no flow.
MAX_REMEDIATION_CYCLES = 3


#: Política padrão quando `LearningObjective.mastery_policy_json` está vazia.
#: Heurística declarada, sem validade científica: existe para dar um
#: comportamento previsível e transparente à primeira versão, não para modelar
#: aquisição de linguagem com precisão.
DEFAULT_MASTERY_POLICY: dict = {
    "min_evidence_count": 1,
    "required_evidence_types": [],
    "require_transfer_success": False,
    #: Só erro não resolvido nesta gravidade (ou acima) impede domínio.
    "block_on_unresolved_severity": ErrorSeverity.CRITICAL,
}

#: Remediação padrão por categoria, usada quando `choose_remediation` não
#: recebe uma ação explícita. Tabela fixa e auditável — não é a IA decidindo.
DEFAULT_REMEDIATION_BY_CATEGORY: dict[str, str] = {
    ErrorCategory.GRAMMAR: RemediationAction.SHOW_CONTRAST,
    ErrorCategory.VOCABULARY: RemediationAction.SHOW_EXAMPLE,
    ErrorCategory.WORD_ORDER: RemediationAction.SHOW_CONTRAST,
    ErrorCategory.COMPREHENSION: RemediationAction.SIMPLIFY,
    ErrorCategory.SPELLING: RemediationAction.HINT,
    ErrorCategory.REGISTER: RemediationAction.EXPLAIN,
    ErrorCategory.PRONUNCIATION_INTELLIGIBILITY: RemediationAction.REPEAT_INPUT,
    ErrorCategory.OTHER: RemediationAction.EXPLAIN,
}


class AiCapability(StrEnum):
    """Capabilities que podem usar IA — não "qual é a IA do BeFluent"."""

    LESSON_GENERATION = "lesson_generation"
    CONVERSATION = "conversation"
    CORRECTION = "correction"
    WRITING_EVALUATION = "writing_evaluation"
    ERROR_DIAGNOSIS = "error_diagnosis"
    REMEDIATION = "remediation"
    EXAMPLE_GENERATION = "example_generation"
    TRANSLATION = "translation"
    STT = "stt"
    TTS = "tts"


def mastery_policy(raw: dict | None) -> dict:
    """Política efetiva de um objetivo: padrão com overrides do objetivo."""
    return {**DEFAULT_MASTERY_POLICY, **(raw or {})}


def default_remediation_action(category: str) -> str:
    return DEFAULT_REMEDIATION_BY_CATEGORY.get(category, RemediationAction.EXPLAIN)


def escalated_remediation_action(occurrences: int, category: str | None = None) -> str:
    """Primeiro erro → hint; segundo → explain; recorrente → contraste/controlado."""
    index = max(0, min(occurrences - 1, len(REMEDIATION_ESCALATION) - 1))
    if occurrences <= 0:
        return default_remediation_action(category or ErrorCategory.OTHER)
    return REMEDIATION_ESCALATION[index]


def is_valid_flow_transition(current: str, target: str) -> bool:
    return target in VALID_FLOW_TRANSITIONS.get(current, frozenset())
