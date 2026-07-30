"""Similaridade textual para revisão de conteúdo pedagógico."""

from __future__ import annotations

import re
from collections import Counter

from app.core.config import get_settings
from app.core.content_policy import SimilarityVerdict

_SHINGLE_LANGS = frozenset({"en", "es-ES", "fr"})
_CJK_LANGS = frozenset({"ja", "zh-CN"})


def _normalize_words(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


def _word_shingles(text: str, size: int = 3) -> set[str]:
    words = _normalize_words(text)
    if len(words) < size:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + size]) for i in range(len(words) - size + 1)}


def _char_ngrams(text: str, size: int = 3) -> set[str]:
    compact = re.sub(r"\s+", "", text.lower())
    if len(compact) < size:
        return {compact} if compact else set()
    return {compact[i : i + size] for i in range(len(compact) - size + 1)}


def fingerprint(text: str, language_code: str) -> set[str]:
    if language_code in _CJK_LANGS:
        return _char_ngrams(text)
    return _word_shingles(text)


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def max_similarity(candidate: str, references: list[str], language_code: str) -> float:
    if not candidate.strip() or not references:
        return 0.0
    fp = fingerprint(candidate, language_code)
    return max((jaccard(fp, fingerprint(ref, language_code)) for ref in references if ref), default=0.0)


def similarity_verdict(score: float) -> SimilarityVerdict:
    settings = get_settings()
    if score >= settings.content_similarity_block_threshold:
        return SimilarityVerdict.BLOCKED
    if score >= settings.content_similarity_review_threshold:
        return SimilarityVerdict.NEEDS_REVIEW
    return SimilarityVerdict.APPROVED


def token_overlap_stats(text: str) -> Counter[str]:
    return Counter(_normalize_words(text))
