"""Orçamento da sessão, em dois tamanhos.

Os números do alvo, do teto, das áreas e da variedade ficam aqui.
O Teaching Engine continua dono da fase; esta tabela só limita
quantos exercícios entram no plano.

Há dois tamanhos porque 36 exercícios são uma tarefa que se adia. A
**dose do dia** (12) existe para o dia comum; a **sessão longa** (36)
continua disponível para quem tem tempo. A pedagogia não muda entre as
duas: mesmas cinco áreas, mesma ordem de fases, mesmo limite de
modalidade repetida. Muda só quanto entra de uma vez.
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_CONSECUTIVE_SAME_MODALITY = 3


@dataclass(frozen=True)
class SessionBudget:
    """Quanto cabe numa sessão e quanto tempo ela deve custar.

    `areas` soma exatamente `target_total`: o planejador percorre as áreas
    em rodadas e para quando cada uma enche, então um total de área maior
    que o alvo faria a sessão passar do alvo.

    `estimated_minutes` é **estimativa declarada, não medida**. Ninguém
    cronometrou sessões reais deste app; o número serve para o aluno
    decidir se começa agora, e a interface deve apresentá-lo como
    aproximação.
    """

    key: str
    label: str
    target_total: int
    maximum_total: int
    areas: dict[str, int]
    estimated_minutes: int


#: Áreas reais do bloco de estudo. Produção e conversação usam os nomes
#: já existentes no currículo (`conversation`), não um rótulo novo.
FULL_SESSION_BUDGET = SessionBudget(
    key="full",
    label="Sessão longa",
    target_total=36,
    maximum_total=40,
    areas={
        "vocabulary": 8,
        "listening": 8,
        "grammar": 8,
        "production": 6,
        "conversation": 6,
    },
    estimated_minutes=35,
)

#: Proporção da sessão longa dividida por três. 2,67 não existe: vocabulário
#: e listening arredondam para cima e gramática para baixo, porque padrão
#: gramatical também aparece dentro dos itens de produção e conversação,
#: enquanto escuta só é treinada no próprio bloco de escuta.
SHORT_SESSION_BUDGET = SessionBudget(
    key="short",
    label="Dose do dia",
    target_total=12,
    maximum_total=14,
    areas={
        "vocabulary": 3,
        "listening": 3,
        "grammar": 2,
        "production": 2,
        "conversation": 2,
    },
    estimated_minutes=12,
)

SESSION_BUDGETS: dict[str, SessionBudget] = {
    FULL_SESSION_BUDGET.key: FULL_SESSION_BUDGET,
    SHORT_SESSION_BUDGET.key: SHORT_SESSION_BUDGET,
}


def budget_for(size: str | None) -> SessionBudget:
    """Tamanho pedido → orçamento. Desconhecido nunca inventa: cai na longa."""
    return SESSION_BUDGETS.get(size or "", FULL_SESSION_BUDGET)


#: Compatibilidade: o resto do código ainda lê a sessão longa por estes nomes.
TARGET_SESSION_EXERCISES = FULL_SESSION_BUDGET.target_total
MAXIMUM_SESSION_EXERCISES = FULL_SESSION_BUDGET.maximum_total
SESSION_ACTIVITY_BUDGET: dict[str, int] = FULL_SESSION_BUDGET.areas

AREA_LABELS: dict[str, str] = {
    "vocabulary": "Vocabulário",
    "listening": "Listening",
    "grammar": "Gramática",
    "production": "Produção",
    "conversation": "Conversação",
}

AREA_ORDER: tuple[str, ...] = tuple(SESSION_ACTIVITY_BUDGET)

#: Ordem das fases do Teaching Engine. O plano não volta para trás.
PHASE_RANK: dict[str, int] = {
    "activating": 0,
    "input": 1,
    "noticing": 2,
    "practicing": 3,
    "producing": 4,
    "transfer_check": 5,
}

#: Cortes do marco sobre o progresso efetivo (0–100), que já conta
#: objetivo não visto como zero. Não servem para promover CEFR.
MILESTONE_UPPER_BOUNDS: tuple[int, ...] = (20, 40, 60, 80)
