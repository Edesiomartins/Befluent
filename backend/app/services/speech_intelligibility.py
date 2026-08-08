"""Camada local de inteligibilidade / correspondência da fala.

Audio → STT (externo) → transcript → normalize → tokenize → align.

NUNCA chama o resultado de "pronúncia X% correta". `coverage` é evidência
auxiliar de correspondência lexical, não score fonético.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def normalize_speech_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    text = text.lower().replace("’", "'").replace("`", "'")
    text = re.sub(r"[^\w\s']+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(value: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", normalize_speech_text(value))


def _lcs_table(a: list[str], b: list[str]) -> list[list[int]]:
    m, n = len(a), len(b)
    table = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                table[i][j] = table[i - 1][j - 1] + 1
            else:
                table[i][j] = max(table[i - 1][j], table[i][j - 1])
    return table


def align_tokens(target_tokens: list[str], recognized_tokens: list[str]) -> dict[str, Any]:
    """Alinhamento por LCS implementado do zero — identifica ausentes/extras."""
    table = _lcs_table(target_tokens, recognized_tokens)
    i, j = len(target_tokens), len(recognized_tokens)
    matched: list[str] = []
    missed: list[str] = []
    extra: list[str] = []
    while i > 0 and j > 0:
        if target_tokens[i - 1] == recognized_tokens[j - 1]:
            matched.append(target_tokens[i - 1])
            i -= 1
            j -= 1
        elif table[i - 1][j] >= table[i][j - 1]:
            missed.append(target_tokens[i - 1])
            i -= 1
        else:
            extra.append(recognized_tokens[j - 1])
            j -= 1
    while i > 0:
        missed.append(target_tokens[i - 1])
        i -= 1
    while j > 0:
        extra.append(recognized_tokens[j - 1])
        j -= 1
    matched.reverse()
    missed.reverse()
    extra.reverse()
    coverage = (len(matched) / len(target_tokens)) if target_tokens else 0.0
    return {
        "target_tokens": target_tokens,
        "recognized_tokens": recognized_tokens,
        "matched_tokens": matched,
        "missed_tokens": missed,
        "extra_tokens": extra,
        "coverage": round(coverage, 4),
        #: Nome explícito — NÃO é score fonético.
        "metric_name": "speech_correspondence",
        "metric_label_pt": "Correspondência da fala (tokens reconhecidos)",
    }


def assess_intelligibility(
    *,
    target_text: str,
    transcript: str,
    provider: str | None = None,
) -> dict[str, Any]:
    target_tokens = tokenize(target_text)
    recognized_tokens = tokenize(transcript)
    alignment = align_tokens(target_tokens, recognized_tokens)
    return {
        "transcript": transcript,
        "normalized_transcript": normalize_speech_text(transcript),
        "provider": provider,
        "intelligibility": alignment,
        #: Campo propositalmente ausente: pronunciation_score.
        "is_phonetic_score": False,
    }
