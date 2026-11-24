"""Papéis de idioma de um turno: alvo, apoio e feedback.

Roda antes de gravar ou devolver o payload. Não apaga texto: o original
fica em `language_role_originals` e o trace recebe campo, papel e ação.

Ações:
- repaired: um trecho no idioma-alvo saiu de um campo de apoio.
- review_required: o campo inteiro está no idioma errado para o papel e
  não havia uma moldura para separar. O texto continua no campo.
- blocked: um campo de alvo está, com confiança alta, em outra língua.
  O texto continua no campo. Quem já filtra `language_invalid` segue igual.
"""

from __future__ import annotations

from typing import Any

from app.services.language_detection import HIGH_CONFIDENCE, top_language

_SPAN_CONFIDENCE = 0.50
_SPAN_MIN = 4
_SPAN_MAX = 8
_REMAINDER_MIN = 2

_PT_NATIVES = {"pt", "pt-BR", "pt-PT"}
# O detector não inclui português. Frases em pt-BR caem em espanhol ou italiano.
_ROMANCE_FALSE_FRIENDS = {"es-ES", "it"}
_DISTANT = {"en", "de", "ja", "zh-CN", "la"}

_NATIVE = {
    "objective",
    "hint_pt",
    "instruction_native",
    "opening_translation",
    "reply_translation",
    "thread_note",
    "translation",
    "usage_note",
}
_TARGET = {
    "audio_text",
    "example",
    "example_sentence",
    "focus_target",
    "opening",
    "prompt",
    "reply",
    "scenario_target",
    "situation",
    "term",
    "text",
    "transcript",
}
_FEEDBACK = {"explanation", "hint", "rationale", "remember", "why_correct", "why_selected"}
_SPAN_FIELDS = {
    "explanation_native",
    "hint_pt",
    "instruction_native",
    "objective",
    "prompt_native",
    "prompt_pt",
    "thread_note",
    "usage_note",
}
_SKIP = {
    "language_policy",
    "language_role_findings",
    "language_role_originals",
    "language_role_status",
    "selection_events",
    "selection_trace",
    "support_visibility",
    "thread",
}
_CLOSED = {
    "a",
    "ao",
    "aos",
    "as",
    "com",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "esta",
    "este",
    "isso",
    "isto",
    "na",
    "nas",
    "não",
    "nao",
    "no",
    "nos",
    "o",
    "os",
    "ou",
    "para",
    "por",
    "se",
    "sem",
    "seu",
    "sua",
    "suas",
    "seus",
    "que",
    "um",
    "uma",
    "umas",
    "uns",
    "você",
    "voce",
}


def apply_language_roles(
    payload: dict[str, Any],
    *,
    target_language: str | None,
    native_language: str | None,
) -> list[dict[str, Any]]:
    """Valida e, quando dá, separa os papéis. Devolve os achados, sem o texto."""
    if not isinstance(payload, dict):
        return []
    findings: list[dict[str, Any]] = []
    originals: dict[str, str] = {}
    _visit(
        payload,
        findings,
        originals,
        target_language=target_language,
        native_language=native_language,
        path="",
    )
    if not findings:
        return []
    payload["language_role_findings"] = findings
    if originals:
        payload["language_role_originals"] = originals
    payload["language_role_status"] = _status(findings)
    return findings


def _visit(
    node: dict[str, Any],
    findings: list[dict[str, Any]],
    originals: dict[str, str],
    *,
    target_language: str | None,
    native_language: str | None,
    path: str,
) -> None:
    for key, value in list(node.items()):
        if key in _SKIP:
            continue
        field = f"{path}.{key}" if path else str(key)
        if key == "option_rationales" and isinstance(value, dict):
            for opt, text in list(value.items()):
                if isinstance(text, str) and text.strip():
                    _judge(
                        node,
                        key=str(opt),
                        field=field,
                        text=text,
                        role="feedback",
                        findings=findings,
                        originals=originals,
                        target_language=target_language,
                        native_language=native_language,
                        allow_repair=False,
                    )
            continue
        role = _role(str(key), node)
        if role and isinstance(value, str) and value.strip():
            _judge(
                node,
                key=str(key),
                field=field,
                text=value,
                role=role,
                findings=findings,
                originals=originals,
                target_language=target_language,
                native_language=native_language,
                allow_repair=str(key) in _SPAN_FIELDS or str(key).endswith("_native") or str(key).endswith("_pt"),
            )
            continue
        if isinstance(value, dict):
            _visit(
                value,
                findings,
                originals,
                target_language=target_language,
                native_language=native_language,
                path=field,
            )
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    _visit(
                        item,
                        findings,
                        originals,
                        target_language=target_language,
                        native_language=native_language,
                        path=f"{field}[{index}]",
                    )


def _role(key: str, parent: dict[str, Any]) -> str | None:
    if key in {"answer", "canonical_answer", "email", "password", "student_response", "token"}:
        return None
    if key.endswith("_native") or key.endswith("_pt"):
        return "native"
    if key.endswith("_target"):
        return "target"
    if key in _FEEDBACK:
        return "feedback"
    if key in _NATIVE:
        return "native"
    if key == "prompt" and "prompt_target" in parent:
        return None
    if key in _TARGET:
        return "target"
    return None


def _judge(
    node: dict[str, Any],
    *,
    key: str,
    field: str,
    text: str,
    role: str,
    findings: list[dict[str, Any]],
    originals: dict[str, str],
    target_language: str | None,
    native_language: str | None,
    allow_repair: bool,
) -> None:
    if role == "target":
        blocked = _target_block(text, target_language)
        if blocked is None:
            return
        detected, confidence = blocked
        findings.append(_finding(field, "target", "blocked", "language_invalid", detected, confidence))
        return

    if allow_repair:
        repaired = _repair_span(
            node,
            key=key,
            text=text,
            target_language=target_language,
        )
        if repaired is not None:
            span, confidence = repaired
            originals.setdefault(field, text)
            findings.append(
                _finding(field, role, "repaired", "mixed_target_span", target_language, confidence)
            )
            return

    if role not in {"native", "feedback"}:
        return
    mismatch = _support_mismatch(text, target_language=target_language, native_language=native_language)
    if mismatch is None:
        return
    detected, confidence = mismatch
    findings.append(_finding(field, role, "review_required", "language_invalid", detected, confidence))


def _repair_span(
    node: dict[str, Any],
    *,
    key: str,
    text: str,
    target_language: str | None,
) -> tuple[str, float] | None:
    if not target_language:
        return None
    words = text.split()
    if len(words) < _SPAN_MIN + _REMAINDER_MIN:
        return None
    best: tuple[float, int, int] | None = None
    last = len(words)
    for start in range(last):
        for length in range(_SPAN_MIN, min(_SPAN_MAX, last - start) + 1):
            if last - length < _REMAINDER_MIN:
                continue
            span_words = words[start : start + length]
            if any(_closed(word) for word in span_words):
                continue
            span = " ".join(span_words)
            detected, confidence = top_language(span)
            if detected != target_language or confidence < _SPAN_CONFIDENCE:
                continue
            if best is None or confidence > best[0] or (confidence == best[0] and length < best[2]):
                best = (confidence, start, length)
    if best is None:
        return None
    confidence, start, length = best
    span = " ".join(words[start : start + length])
    remainder = " ".join(words[:start] + words[start + length :])
    if len(remainder.split()) < _REMAINDER_MIN:
        return None
    node[key] = remainder
    target_key = _target_key(key)
    current = node.get(target_key)
    if not isinstance(current, str) or not current.strip():
        node[target_key] = span
    return span, confidence


def _target_key(field: str) -> str:
    if field.endswith("_native"):
        return f"{field[: -len('_native')]}_target"
    if field.endswith("_pt"):
        return f"{field[: -len('_pt')]}_target"
    return f"{field}_target"


def _target_block(text: str, target_language: str | None) -> tuple[str, float] | None:
    if not target_language or len(text.split()) < _SPAN_MIN:
        return None
    detected, confidence = top_language(text)
    if detected and detected != target_language and confidence >= HIGH_CONFIDENCE:
        return detected, confidence
    return None


def _support_mismatch(
    text: str,
    *,
    target_language: str | None,
    native_language: str | None,
) -> tuple[str, float] | None:
    if len(text.split()) < _SPAN_MIN:
        return None
    detected, confidence = top_language(text)
    if not detected or confidence < HIGH_CONFIDENCE:
        return None
    if _same(detected, native_language):
        return None
    if detected == target_language:
        return detected, confidence
    if native_language in _PT_NATIVES and detected in _ROMANCE_FALSE_FRIENDS:
        return None
    if detected in _DISTANT:
        return detected, confidence
    return None


def _same(detected: str, native_language: str | None) -> bool:
    if not native_language:
        return False
    if detected == native_language:
        return True
    return native_language in _PT_NATIVES and detected == "pt"


def _closed(word: str) -> bool:
    return word.strip(".,;:!?\"“”()[]").casefold() in _CLOSED


def _finding(
    field: str,
    role: str,
    action: str,
    reason: str,
    detected: str | None,
    confidence: float,
) -> dict[str, Any]:
    return {
        "field": field,
        "role": role,
        "action": action,
        "reason": reason,
        "detected_language": detected,
        "confidence": round(confidence, 3),
    }


def _status(findings: list[dict[str, Any]]) -> str:
    actions = {row["action"] for row in findings}
    if "blocked" in actions:
        return "blocked"
    if "review_required" in actions:
        return "review_required"
    return "repaired"
