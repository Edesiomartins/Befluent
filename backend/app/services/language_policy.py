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


def ensure_stored_content_language(payload, native_language):
    """Conteúdo antigo não é relabelado como tradução de outra língua."""
    payload = payload if isinstance(payload, Mapping) else {}
    stored_native = payload.get("native_language")
    if "native_language" in payload:
        if stored_native != native_language:
            raise APIError(409, "lesson_native_language_mismatch", "Esta lição foi criada para outra língua nativa; gere uma nova lição.")
    else:
        require_static_native_support(native_language)
    if "en" not in {payload.get("language_code"), native_language}:
        def contaminated(value):
            if isinstance(value, list):
                return any(contaminated(v) for v in value)
            if not isinstance(value, dict):
                return False
            for key, item in value.items():
                if key in {"explanation", "explanation_native", "logic", "hint", "feedback"} and isinstance(item, str) and item.casefold().startswith(("we use the ", "use the present ", "the present simple ", "the past simple ")):
                    return True
                if contaminated(item):
                    return True
            return False
        if contaminated(payload):
            raise APIError(409, "lesson_language_invalid", "Esta lição contém apoio em um terceiro idioma e precisa ser regenerada.")
