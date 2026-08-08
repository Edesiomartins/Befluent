"""Constantes de domínio do Teaching Engine — núcleo pedagógico entre currículo
e atividades.

Distingue formalmente **atividade concluída** (`CurriculumBlock.status`, já
existente) de **aprendizagem demonstrada** (`MasteryState`, aqui). Erro não
termina a atividade: gera diagnóstico → remediação → nova tentativa →
reavaliação, nunca um "reprovado" sem caminho de volta.

Como em `core/levels.py` e `core/curriculum.py`: enums e tabelas de política
são constantes imutáveis de código, não linhas de banco.
"""

from __future__ import annotations

from enum import StrEnum


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
    WRITTEN_PRODUCTION = "written_production"
    ORAL_PRODUCTION_TRANSCRIBED = "oral_production_transcribed"
    STRUCTURE_APPLICATION = "structure_application"
    COMPREHENSION = "comprehension"
    #: Aplicação do conhecimento numa pergunta nova — o sinal mais forte de
    #: domínio real, não de memorização do exemplo treinado.
    TRANSFER = "transfer"


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
    SHOW_CONTRAST = "show_contrast"
    CONTROLLED_RETRY = "controlled_retry"
    SIMPLIFY = "simplify"
    GIVE_HINT = "give_hint"
    NEW_EXAMPLE = "new_example"
    REPEAT_INPUT = "repeat_input"


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
    ErrorCategory.VOCABULARY: RemediationAction.NEW_EXAMPLE,
    ErrorCategory.WORD_ORDER: RemediationAction.SHOW_CONTRAST,
    ErrorCategory.COMPREHENSION: RemediationAction.SIMPLIFY,
    ErrorCategory.SPELLING: RemediationAction.GIVE_HINT,
    ErrorCategory.REGISTER: RemediationAction.EXPLAIN,
    ErrorCategory.PRONUNCIATION_INTELLIGIBILITY: RemediationAction.REPEAT_INPUT,
    ErrorCategory.OTHER: RemediationAction.EXPLAIN,
}


def mastery_policy(raw: dict | None) -> dict:
    """Política efetiva de um objetivo: padrão com overrides do objetivo."""
    return {**DEFAULT_MASTERY_POLICY, **(raw or {})}


def default_remediation_action(category: str) -> str:
    return DEFAULT_REMEDIATION_BY_CATEGORY.get(category, RemediationAction.EXPLAIN)
