"""Contrato explícito de idioma e de interação.

Não infere tradução porque um campo legado existe. `prompt` já é o estímulo
no idioma-alvo neste código; `prompt_pt` continua legado e não é copiado
para `prompt_native`.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.services.editorial_validation import has_known_incompatible_english
from app.services.language_codes import TARGET_LANGUAGE_CODES, validate_native_language

QUALITY_STATUSES = frozenset({
    "draft",
    "generated",
    "review_required",
    "approved",
    "language_invalid",
    "rejected",
})

INTERACTION_BY_TYPE = {
    "presentation": "presentation",
    "recognition": "choice",
    "reverse_recognition": "choice",
    "multiple_choice": "choice",
    "listening_recognition": "audio_choice",
    "listen": "audio_model",
    "fill_gap": "inline_gap",
    "word_order": "tap_order",
    "matching": "pair_match",
    "lexical_production": "recall",
    "controlled_recall": "recall",
    "recall": "recall",
    "guided_production": "guided_input",
    "free_production": "open_input",
    "repeat": "speech_repeat",
    "shadow": "speech_shadow",
    "retell": "speech_retell",
    "conversation_prompt": "dialogue",
    "transfer_question": "transfer",
    "review": "presentation",
    "dictation": "dictation",
}

_PORTUGUESE = frozenset({"pt", "pt-BR", "pt-PT"})


def interaction_family(activity_type: str | None) -> str:
    return INTERACTION_BY_TYPE.get(str(activity_type or ""), "unknown")


def portuguese_native(native_language: str | None) -> bool:
    return native_language in _PORTUGUESE


def require_language_pair(target_language: str, native_language: str | None) -> None:
    if target_language not in TARGET_LANGUAGE_CODES:
        raise ValueError("Idioma-alvo inválido.")
    if native_language is not None:
        validate_native_language(native_language)


def language_safety(payload: Mapping, target_language: str | None, native_language: str | None) -> str:
    """`language_invalid` quando o guarda editorial não pode deixar o item passar.

    Não tenta identificar qualquer língua do mundo. Clones conhecidos de inglês
    e o status já gravado são a camada determinística.
    """
    if payload.get("quality_status") == "language_invalid":
        return "language_invalid"
    target = target_language or payload.get("target_language") or payload.get("language_code")
    if isinstance(target, str) and has_known_incompatible_english(payload, target, native_language):
        return "language_invalid"
    status = payload.get("quality_status")
    if isinstance(status, str) and status in QUALITY_STATUSES:
        return status
    return "unspecified"


def deliverable(payload: Mapping, target_language: str | None = None, native_language: str | None = None) -> bool:
    return language_safety(payload, target_language, native_language) != "language_invalid"


def apply_language_contract(
    payload: Mapping,
    *,
    target_language: str | None = None,
    native_language: str | None = None,
) -> dict:
    """Copia papéis já inequívocos. Não promove `prompt_pt` a apoio nativo."""
    activity = dict(payload)
    target = activity.get("target_language") or target_language
    native = activity.get("native_language") if "native_language" in activity else native_language
    if target and "target_language" not in activity:
        activity["target_language"] = target
    if native is not None and "native_language" not in activity:
        activity["native_language"] = native
    if activity.get("prompt") and "prompt_target" not in activity:
        activity["prompt_target"] = activity["prompt"]
    if activity.get("title") and "title_target" not in activity:
        activity["title_target"] = activity["title"]
    activity["interaction_family"] = activity.get("interaction_family") or interaction_family(activity.get("type"))
    if activity.get("type") == "dictation":
        activity["show_text"] = False
        activity.setdefault("response_mode", "typing")
        activity.setdefault("compare", "normalized_text")
    safety = language_safety(activity, target if isinstance(target, str) else None, native if isinstance(native, str) else None)
    if safety == "language_invalid":
        activity["quality_status"] = "language_invalid"
    return activity


def dictation_contract(
    *,
    audio_text: str,
    canonical_answer: str,
    target_language: str,
    native_language: str,
    instruction_native: str,
) -> dict:
    """Áudio, digitação e comparação. O transcript não vai no enunciado."""
    return apply_language_contract({
        "type": "dictation",
        "audio_text": audio_text,
        "canonical_answer": canonical_answer,
        "accepted_variants": [canonical_answer],
        "prompt_target": "",
        "instruction_native": instruction_native,
        "prompt_native": instruction_native,
        "target_language": target_language,
        "native_language": native_language,
        "show_text": False,
        "ai_required": False,
    })
