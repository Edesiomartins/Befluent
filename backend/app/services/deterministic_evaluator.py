"""Avaliador determinístico — sem chamada de IA.

Contrato por tipo de atividade:

- lexical: token/feature basta (fill-gap de uma palavra)
- structural: frase/ordem; variantes ou padrões
- guided: produção guiada — estrutura mínima + features/padrões
- transfer: mesma exigência estrutural; variantes preferidas

`required_features` usa âncora lexical com fronteira de palavra — nunca
substring solta que aceite "professor" como domínio de "I'm a professor.".
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

#: Tipos estruturais / de produção — resposta lexical isolada não basta.
_STRUCTURAL_KINDS = frozenset({"structural", "guided", "transfer"})
_KIND_BY_TYPE = {
    "fill_gap": "lexical",
    "matching": "lexical",
    "listen": "lexical",
    "recognition": "lexical",
    "word_order": "structural",
    "multiple_choice": "structural",
    "guided_production": "guided",
    "transfer_question": "transfer",
}


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    text = text.strip().lower()
    text = text.replace("’", "'").replace("`", "'")
    text = re.sub(r"[^\w\s']+", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _variant_set(canonical: str | None, accepted: list[str] | None) -> set[str]:
    values = []
    if canonical:
        values.append(canonical)
    values.extend(accepted or [])
    return {normalize_text(v) for v in values if v}


def _activity_kind(activity: dict[str, Any]) -> str:
    explicit = activity.get("evaluation_mode") or activity.get("activity_kind")
    if explicit in {"lexical", "structural", "guided", "transfer"}:
        return str(explicit)
    return _KIND_BY_TYPE.get(str(activity.get("type") or ""), "lexical")


def _token_present(feature: str, normalized: str) -> bool:
    """Âncora lexical com fronteira de palavra (não substring cega)."""
    token = normalize_text(feature)
    if not token:
        return True
    return bool(re.search(rf"(?<!\w){re.escape(token)}(?!\w)", normalized))


def _pattern_present(pattern: str, normalized: str) -> bool:
    """Padrão simples: regex leve OU substring normalizada."""
    raw = (pattern or "").strip()
    if not raw:
        return True
    try:
        if re.search(raw, normalized, flags=re.IGNORECASE):
            return True
    except re.error:
        pass
    return normalize_text(raw) in normalized


def _has_clause_structure(normalized: str) -> bool:
    """Heurística A1: sujeito + verbo/cópula (inclui contrações I'm/he's)."""
    tokens = normalized.split()
    if len(tokens) < 2:
        return False
    has_subject = bool(
        re.search(r"\b(i|he|she|they|we|you|my|his|her|our|their)\b", normalized)
    )
    has_verb = bool(
        re.search(
            r"\b(am|is|are|was|were|do|does|did|have|has|work|live|like|come|go|'m|'s|'re)\b",
            normalized,
        )
    ) or bool(re.search(r"\b\w+'(?:m|s|re|ve|ll|d)\b", normalized))
    return has_subject and has_verb


def _minimum_structure_ok(normalized: str, activity: dict[str, Any], kind: str) -> bool:
    policy = activity.get("minimum_structure")
    if policy is None:
        if kind in _STRUCTURAL_KINDS:
            policy = "clause"
        else:
            return True
    if policy in {"none", "token", "lexical"}:
        return True
    if policy in {"clause", "sentence", "structure"}:
        return _has_clause_structure(normalized)
    return True


def evaluate_response(
    *,
    student_response: str,
    activity: dict[str, Any] | None = None,
    canonical_answer: str | None = None,
    accepted_variants: list[str] | None = None,
    required_features: list[str] | None = None,
    forbidden_features: list[str] | None = None,
    required_patterns: list[str] | None = None,
) -> dict[str, Any]:
    """Avalia resposta. Método sempre `deterministic` — nunca chama IA."""
    activity = activity or {}
    kind = _activity_kind(activity)
    canonical = canonical_answer if canonical_answer is not None else activity.get("canonical_answer")
    accepted = (
        accepted_variants
        if accepted_variants is not None
        else list(activity.get("accepted_variants") or [])
    )
    required = (
        required_features
        if required_features is not None
        else list(activity.get("required_features") or [])
    )
    forbidden = (
        forbidden_features
        if forbidden_features is not None
        else list(activity.get("forbidden_features") or [])
    )
    patterns = (
        required_patterns
        if required_patterns is not None
        else list(activity.get("required_patterns") or [])
    )

    normalized = normalize_text(student_response)
    activity_type = activity.get("type")

    if activity_type == "word_order":
        tokens = activity.get("tokens") or []
        student_tokens = re.findall(r"[A-Za-z']+", student_response)
        expected = [normalize_text(t) for t in tokens]
        got = [normalize_text(t) for t in student_tokens]
        exact = got == expected
        variants = _variant_set(canonical, accepted)
        in_variants = normalized in variants if variants else exact
        correct = exact or in_variants
        return {
            "result": "correct" if correct else "incorrect",
            "evaluation_method": "deterministic",
            "normalized_response": normalized,
            "matched_variant": normalized if in_variants else None,
            "ai_called": False,
            "details": {"token_match": exact, "activity_kind": kind},
        }

    variants = _variant_set(canonical, accepted)
    if variants and normalized in variants:
        return {
            "result": "correct",
            "evaluation_method": "deterministic",
            "normalized_response": normalized,
            "matched_variant": normalized,
            "ai_called": False,
            "details": {"mode": "accepted_variants", "activity_kind": kind},
        }

    # Sem required/patterns: variantes (se houver) fecham a avaliação.
    if variants and not required and not patterns:
        return {
            "result": "incorrect",
            "evaluation_method": "deterministic",
            "normalized_response": normalized,
            "matched_variant": None,
            "ai_called": False,
            "details": {"mode": "accepted_variants", "activity_kind": kind},
        }

    missing_features = [f for f in required if not _token_present(f, normalized)]
    forbidden_hit = [f for f in forbidden if _token_present(f, normalized)]
    missing_patterns = [p for p in patterns if not _pattern_present(p, normalized)]
    structure_ok = _minimum_structure_ok(normalized, activity, kind)

    # Produção estrutural: lexical isolado (ex.: "professor") não passa.
    if kind in _STRUCTURAL_KINDS and not structure_ok:
        return {
            "result": "incorrect",
            "evaluation_method": "deterministic",
            "normalized_response": normalized,
            "matched_variant": None,
            "ai_called": False,
            "details": {
                "mode": "minimum_structure",
                "activity_kind": kind,
                "missing_features": missing_features,
                "missing_patterns": missing_patterns,
                "forbidden_hit": forbidden_hit,
                "structure_ok": False,
            },
        }

    if required or patterns:
        features_ok = not missing_features
        patterns_ok = not missing_patterns
        # Padrões: se declarados, todos devem casar. Features: todas.
        if features_ok and patterns_ok and not forbidden_hit and structure_ok:
            return {
                "result": "correct",
                "evaluation_method": "deterministic",
                "normalized_response": normalized,
                "matched_variant": None,
                "ai_called": False,
                "details": {
                    "mode": "required_criteria",
                    "activity_kind": kind,
                    "missing_features": [],
                    "missing_patterns": [],
                    "forbidden_hit": [],
                    "structure_ok": True,
                },
            }
        partial = (
            (required and len(missing_features) < len(required) and not forbidden_hit)
            or (patterns and len(missing_patterns) < len(patterns) and not forbidden_hit)
        )
        if partial and structure_ok:
            return {
                "result": "partial",
                "evaluation_method": "deterministic",
                "normalized_response": normalized,
                "matched_variant": None,
                "ai_called": False,
                "details": {
                    "mode": "required_criteria",
                    "activity_kind": kind,
                    "missing_features": missing_features,
                    "missing_patterns": missing_patterns,
                    "forbidden_hit": forbidden_hit,
                    "structure_ok": structure_ok,
                },
            }
        return {
            "result": "incorrect",
            "evaluation_method": "deterministic",
            "normalized_response": normalized,
            "matched_variant": None,
            "ai_called": False,
            "details": {
                "mode": "required_criteria",
                "activity_kind": kind,
                "missing_features": missing_features,
                "missing_patterns": missing_patterns,
                "forbidden_hit": forbidden_hit,
                "structure_ok": structure_ok,
            },
        }

    return {
        "result": "incorrect",
        "evaluation_method": "deterministic",
        "normalized_response": normalized,
        "matched_variant": None,
        "ai_called": False,
        "details": {"mode": "no_criteria", "activity_kind": kind},
    }
