"""Orçamento único da sessão.

Os números do alvo, do teto, das áreas e da variedade ficam aqui.
O Teaching Engine continua dono da fase; esta tabela só limita
quantos exercícios entram no plano.
"""

from __future__ import annotations

TARGET_SESSION_EXERCISES = 36
MAXIMUM_SESSION_EXERCISES = 40
MAX_CONSECUTIVE_SAME_MODALITY = 3

#: Áreas reais do bloco de estudo. Produção e conversação usam os nomes
#: já existentes no currículo (`conversation`), não um rótulo novo.
SESSION_ACTIVITY_BUDGET: dict[str, int] = {
    "vocabulary": 8,
    "listening": 8,
    "grammar": 8,
    "production": 6,
    "conversation": 6,
}

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
