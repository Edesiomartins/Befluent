"""Política pedagógica central: nenhum idioma nativo é inferido."""
from collections.abc import Mapping
from app.core.errors import APIError
from app.services.language_codes import TARGET_LANGUAGE_CODES, validate_native_language

THIRD_LANGUAGE_RULE = "Do not use any third language in learner-facing content unless the activity explicitly requires it."

def language_policy(target_language, native_language, level):
    if target_language not in TARGET_LANGUAGE_CODES:
        raise ValueError("Idioma-alvo inválido.")
    validate_native_language(native_language)
    support = {
        "PRE_A1": "Frequent native scaffolding; short target examples.",
        "A1": "Frequent native scaffolding; short target examples.",
        "A2": "Brief native explanations supporting target practice.",
        "B1": "Mostly target language; occasional native clarification.",
        "B2": "Almost entirely target language; native only when needed.",
        "C1": "Target language; native only when explicitly requested or necessary.",
        "C2": "Target language; native only when explicitly requested or necessary.",
    }
    if level not in support:
        raise ValueError("CEFR inválido.")
    visibility = {
        "PRE_A1": "prominent", "A1": "prominent", "A2": "discreet",
        "B1": "spot", "B2": "expandable", "C1": "off", "C2": "off",
    }
    allowed = [target_language] + ([native_language] if native_language else [])
    return {
        "version": "native-v1",
        "target_language": target_language,
        "native_language": native_language,
        "native_language_required": native_language is None,
        "cefr_level": level,
        "support_visibility": visibility[level] if native_language else "off",
        "allowed_languages": list(dict.fromkeys(allowed)),
        "explanation_language": native_language if native_language and level in {"PRE_A1", "A1", "A2"} else target_language,
        "native_support": support[level] if native_language else "Target language only; native language has not been selected.",
        "third_language_rule": THIRD_LANGUAGE_RULE,
    }


def require_static_native_support(native_language):
    if native_language is None:
        raise APIError(409, "native_language_required", "Escolha sua língua nativa no perfil antes de usar este conteúdo.")
    if native_language != "pt-BR":
        raise APIError(409, "native_support_unavailable", "Este conteúdo estático ainda não oferece apoio na língua nativa escolhida.")


def ensure_stored_content_language(payload, native_language, *, target_language=None, stored_title=None, lesson_status=None):
    """Conteúdo antigo não é relabelado como tradução de outra língua."""
    payload = payload if isinstance(payload, Mapping) else {}
    declared_target = payload.get("target_language") or payload.get("language_code")
    target = target_language or declared_target
    if any(value is not None and not isinstance(value, str) for value in (
        payload.get("target_language"), payload.get("language_code"), target
    )):
        raise APIError(409, "lesson_target_language_mismatch", "Esta lição não registra um idioma válido; gere uma nova lição.")
    if any(value and target and value != target for value in (
        payload.get("target_language"), payload.get("language_code")
    )):
        raise APIError(409, "lesson_target_language_mismatch", "Esta lição foi criada para outro idioma; gere uma nova lição.")
    from app.services.editorial_validation import has_known_incompatible_english
    if lesson_status == "language_invalid" or has_known_incompatible_english(payload, target, native_language) or (
        stored_title is not None and has_known_incompatible_english({"title": stored_title}, target, native_language)
    ):
        raise APIError(409, "lesson_language_invalid", "Esta lição contém conteúdo incompatível com os idiomas atuais e precisa ser regenerada.")
    stored_native = payload.get("native_language")
    if "native_language" in payload:
        if stored_native != native_language:
            raise APIError(409, "lesson_native_language_mismatch", "Esta lição foi criada para outra língua nativa; gere uma nova lição.")
    else:
        require_static_native_support(native_language)
        static_origins = {"mock", "curated_library"}
        origins = {payload.get(key) for key in ("provider", "content_origin") if isinstance(payload.get(key), str) and payload[key]}
        static_legacy = bool(origins) and origins <= static_origins
        # Internal review queue is a known PT-scaffolded source too. Do not
        # accept an arbitrary lesson merely because it claims provider=srs.
        static_legacy = static_legacy or (
            origins == {"srs"} and payload.get("mode") == "review" and payload.get("source") == "srs_queue"
        )
        # Old static PT scaffolding is a bounded compatibility path, never a
        # native-language backfill. Unversioned EN/PT and empty legacy wrappers
        # keep their previous path, after the known-content checks above.
        if not static_legacy and (
            origins or payload.get("target_language") or (target and target != "en")
        ):
            raise APIError(409, "lesson_language_provenance_missing", "Esta lição antiga não registra um apoio nativo compatível; gere uma nova lição.")
