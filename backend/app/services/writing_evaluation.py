"""Avaliação da produção escrita do teste de nivelamento.

Duas estratégias, nesta ordem:

1. IA (OpenRouter), quando configurada, exigindo resposta JSON estruturada.
   O score do modelo é validado e saturado — nunca aceito cegamente.
2. Heurística de baseline, quando a IA está indisponível ou em modo mock.

A heurística NÃO mede qualidade linguística real: ela verifica volume,
segmentação em frases e diversidade lexical. Por isso o resultado é marcado
com `evaluated_by="heuristic"` e a UI o apresenta como preliminar. Se nem a
heurística puder ser aplicada (texto vazio), a competência fica
`not_evaluated` — o teste conclui mesmo assim.
"""

from __future__ import annotations

import re

from app.core.config import get_settings
from app.core.levels import LEVEL_INDEX, level_at
from app.services.ai import OpenRouterUnavailableError, openrouter_chat_with_fallback

MAX_WRITING_CHARS = 4000

RUBRIC_CRITERIA = [
    "adequacao_ao_tema",
    "coerencia",
    "vocabulario",
    "gramatica",
    "clareza",
    "organizacao",
]

RUBRIC_LABELS: dict[str, str] = {
    "adequacao_ao_tema": "Adequação ao tema",
    "coerencia": "Coerência",
    "vocabulario": "Vocabulário",
    "gramatica": "Gramática",
    "clareza": "Clareza",
    "organizacao": "Organização",
}

#: Estimativa de caracteres por palavra, para converter a faixa de palavras da
#: tarefa no `min_chars` que a heurística usa.
CHARS_PER_WORD = 5


def _tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[^\w']+", text.lower()) if token]


def _sentence_count(text: str) -> int:
    parts = [part for part in re.split(r"[.!?。！？\n]+", text) if part.strip()]
    return max(len(parts), 1)


def heuristic_evaluation(text: str, target_level: str, min_chars: int = 20) -> dict:
    """Baseline transparente: volume, segmentação e diversidade lexical.

    Devolve score 0..1 saturado no nível-alvo — não promove acima do nível do
    item, apenas indica se a produção sustenta aquela faixa.
    """
    cleaned = text.strip()
    if not cleaned:
        return {
            "status": "not_evaluated",
            "reason": "empty_text",
            "evaluated_by": "heuristic",
        }

    tokens = _tokenize(cleaned)
    sentences = _sentence_count(cleaned)
    unique_ratio = len(set(tokens)) / len(tokens) if tokens else 0.0

    length_ratio = min(len(cleaned) / max(min_chars, 1), 2.0) / 2.0
    sentence_ratio = min(sentences / 3.0, 1.0)
    diversity_ratio = min(unique_ratio / 0.6, 1.0)

    score = 0.5 * length_ratio + 0.2 * sentence_ratio + 0.3 * diversity_ratio
    score = round(max(0.0, min(1.0, score)), 3)

    return {
        "status": "assessed",
        "evaluated_by": "heuristic",
        "normalized_score": score,
        "target_level": target_level,
        "estimated_level": _score_to_level(score, target_level),
        "metrics": {
            "chars": len(cleaned),
            "tokens": len(tokens),
            "sentences": sentences,
            "lexical_diversity": round(unique_ratio, 3),
        },
        "notice": "Avaliação automática preliminar, sem análise linguística completa.",
    }


def _score_to_level(score: float, target_level: str) -> str:
    """Converte score em nível, limitado ao nível do item (nunca acima)."""
    target_index = LEVEL_INDEX.get(target_level, LEVEL_INDEX["A2"])
    if score >= 0.7:
        return target_level
    if score >= 0.45:
        return level_at(target_index - 1)
    return level_at(target_index - 2)


def _validate_ai_payload(payload: dict, target_level: str) -> dict | None:
    """Rejeita respostas fora do contrato em vez de confiar no modelo."""
    raw_score = payload.get("normalized_score")
    if not isinstance(raw_score, (int, float)):
        return None
    score = round(max(0.0, min(1.0, float(raw_score))), 3)

    estimated = payload.get("estimated_level")
    if estimated not in LEVEL_INDEX:
        estimated = _score_to_level(score, target_level)
    # O modelo não pode promover acima do nível do item avaliado.
    if LEVEL_INDEX[estimated] > LEVEL_INDEX.get(target_level, LEVEL_INDEX["B2"]):
        estimated = target_level

    criteria = payload.get("criteria")
    if not isinstance(criteria, dict):
        criteria = {}

    return {
        "status": "assessed",
        "evaluated_by": "ai",
        "normalized_score": score,
        "target_level": target_level,
        "estimated_level": estimated,
        "criteria": {key: criteria.get(key) for key in RUBRIC_CRITERIA if key in criteria},
        "feedback": str(payload.get("feedback", ""))[:1000],
    }


def _ai_evaluation(text: str, language_code: str, target_level: str) -> dict | None:
    """IA (primário → fallback do OpenRouter, mesma cadeia de `app.services.ai`).

    Retorna `None` quando a IA está em modo mock ou indisponível — o chamador
    cai para a heurística nesse caso. Indisponibilidade de IA não pode
    bloquear a conclusão do teste de nivelamento.
    """
    settings = get_settings()
    if settings.ai_mock_mode or not settings.openrouter_api_key:
        return None
    if not settings.openrouter_model and not settings.openrouter_fallback_model:
        return None

    instruction = (
        "Avalie a produção escrita de um estudante de idiomas segundo o CEFR. "
        "Responda APENAS em JSON com as chaves: normalized_score (0 a 1), "
        "estimated_level (PRE_A1, A1, A2, B1, B2, C1 ou C2), "
        "criteria (objeto com adequacao_ao_tema, coerencia, vocabulario, gramatica, "
        "clareza, organizacao, cada um de 0 a 1) e feedback (texto curto em português)."
    )
    messages = [
        {"role": "system", "content": instruction},
        {
            "role": "user",
            "content": (
                f"Idioma avaliado: {language_code}. Nível-alvo da tarefa: {target_level}.\n"
                f"Texto do estudante:\n{text[:MAX_WRITING_CHARS]}"
            ),
        },
    ]

    try:
        content, _model = openrouter_chat_with_fallback(
            settings,
            messages,
            lambda p: isinstance(p, dict) and isinstance(p.get("normalized_score"), (int, float)),
            timeout=30,
        )
    except OpenRouterUnavailableError:
        return None
    return _validate_ai_payload(content, target_level)


def evaluate_writing(
    text: str,
    language_code: str,
    target_level: str,
    min_chars: int = 20,
) -> dict:
    """Avalia a escrita, caindo para heurística quando a IA não responde."""
    result = _ai_evaluation(text, language_code, target_level)
    if result is not None:
        return result
    return heuristic_evaluation(text, target_level, min_chars)


def evaluate_lesson_writing(
    text: str,
    language_code: str,
    target_level: str,
    min_words: int,
    max_words: int,
) -> dict:
    """Correção da produção escrita de uma lição.

    Difere de `evaluate_writing` no propósito: o teste de nivelamento quer
    estimar um nível, a lição quer devolver correção acionável. Por isso aqui
    entram a aderência à faixa de palavras pedida e a rubrica rotulada para a
    interface.

    A heurística não analisa gramática — quando ela responde, o resultado sai
    marcado como preliminar em vez de fingir uma correção linguística.
    """
    cleaned = text.strip()
    words = len(_tokenize(cleaned))
    base = evaluate_writing(
        cleaned,
        language_code,
        target_level,
        min_chars=max(min_words * CHARS_PER_WORD, 20),
    )

    if base.get("status") != "assessed":
        return {
            **base,
            "word_count": words,
            "min_words": min_words,
            "max_words": max_words,
            "within_range": False,
            "criteria": [],
        }

    raw_criteria = base.get("criteria") or {}
    criteria = [
        {
            "key": key,
            "label": RUBRIC_LABELS[key],
            "score": round(float(value), 3),
        }
        for key, value in raw_criteria.items()
        if key in RUBRIC_LABELS and isinstance(value, (int, float))
    ]

    return {
        **base,
        "criteria": criteria,
        "word_count": words,
        "min_words": min_words,
        "max_words": max_words,
        "within_range": min_words <= words <= max_words,
    }
