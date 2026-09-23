"""Política lexical única.

Recognition e production não têm a mesma força de memória. Os rótulos de
força são declarados aqui para não espalhar a regra pelo código. Não é FSRS:
o agendamento continua em MemorySchedule.

O default preserva o domínio atual: as quatro evidências avaliadas são
obrigatórias. Exposure é registrada, mas não conta para domínio.
"""

from __future__ import annotations

from app.core.teaching import EvidenceType

#: Ordem pedagógica da revisão. A próxima modalidade segue esta ordem.
REQUIRED_EVIDENCE_ORDER: tuple[str, ...] = (
    EvidenceType.RECOGNITION,
    EvidenceType.REVERSE_RECOGNITION,
    EvidenceType.LISTENING_RECOGNITION,
    EvidenceType.LEXICAL_PRODUCTION,
)

EVIDENCE_STRENGTH: dict[str, str] = {
    EvidenceType.EXPOSURE: "weak",
    EvidenceType.RECOGNITION: "moderate",
    EvidenceType.REVERSE_RECOGNITION: "moderate",
    EvidenceType.LISTENING_RECOGNITION: "moderate",
    EvidenceType.LEXICAL_PRODUCTION: "strong",
}


def lexical_mastery_policy() -> dict:
    """Política efetiva do léxico. Outros conteúdos podem ter outra no futuro."""
    return {
        "required_evidence_types": list(REQUIRED_EVIDENCE_ORDER),
        "evidence_strength": dict(EVIDENCE_STRENGTH),
        "review_policy": {
            "avoid_immediate_same_modality": True,
            "max_mastered_when_weak": 1,
        },
    }


def required_evidence_types() -> frozenset[str]:
    return frozenset(lexical_mastery_policy()["required_evidence_types"])


def next_review_modality(
    evaluated_types: set[str] | frozenset[str],
    last_activity_type: str | None,
) -> str:
    """Próxima modalidade: o que falta, sem repetir a forma do erro imediato."""
    required = list(lexical_mastery_policy()["required_evidence_types"])
    missing = [item for item in required if item not in evaluated_types]
    candidates = missing or required
    rotated = [item for item in candidates if item != last_activity_type]
    return rotated[0] if rotated else candidates[0]
