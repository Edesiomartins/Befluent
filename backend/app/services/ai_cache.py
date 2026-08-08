"""Cache pedagógico global + deduplicação in-process.

Nunca cacheia correção personalizada do aluno. Chave = capability + contexto
pedagógico + hash do input não-pessoal.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AiResponseCache

logger = logging.getLogger(__name__)


@dataclass
class _Inflight:
    event: threading.Event = field(default_factory=threading.Event)
    result: dict | None = None
    error: BaseException | None = None


_inflight_lock = threading.Lock()
_inflight: dict[str, _Inflight] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def build_cache_key(
    *,
    capability: str,
    language_code: str | None = None,
    level: str | None = None,
    objective_code: str | None = None,
    objective_version: int | None = None,
    task_type: str | None = None,
    prompt_version: str = "v1",
    input_payload: dict | str | None = None,
) -> str:
    material = {
        "capability": capability,
        "language_code": language_code,
        "level": level,
        "objective_code": objective_code,
        "objective_version": objective_version,
        "task_type": task_type,
        "prompt_version": prompt_version,
        "input": input_payload or {},
    }
    raw = json.dumps(material, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_personal_content(payload: dict | None) -> bool:
    """Heurística: se há resposta do aluno / histórico pessoal, não cachear."""
    if not payload:
        return False
    personal_keys = {
        "student_response",
        "user_id",
        "user_language_id",
        "history",
        "transcript",
        "corrections_for_user",
        "personal",
        "name",
        "writing",
        "conversation",
    }
    return any(key in payload for key in personal_keys)


def get_cached(db: Session, cache_key: str) -> dict | None:
    row = db.scalar(select(AiResponseCache).where(AiResponseCache.cache_key == cache_key))
    if row is None:
        return None
    row.hit_count += 1
    row.last_hit_at = _now()
    db.flush()
    logger.info("ai_cache_hit capability=%s key=%s", row.capability, cache_key[:12])
    return dict(row.response_json or {})


def store_cached(
    db: Session,
    *,
    cache_key: str,
    capability: str,
    response: dict,
    language_code: str | None = None,
    level: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    prompt_version: str = "v1",
) -> AiResponseCache:
    existing = db.scalar(select(AiResponseCache).where(AiResponseCache.cache_key == cache_key))
    if existing is not None:
        existing.response_json = response
        existing.hit_count += 1
        existing.last_hit_at = _now()
        db.flush()
        return existing
    row = AiResponseCache(
        cache_key=cache_key,
        capability=capability,
        language_code=language_code,
        level=level,
        provider=provider,
        model=model,
        prompt_version=prompt_version,
        response_json=response,
    )
    db.add(row)
    db.flush()
    logger.info("ai_cache_store capability=%s key=%s", capability, cache_key[:12])
    return row


def cached_or_compute(
    db: Session,
    *,
    cache_key: str,
    capability: str,
    compute: Callable[[], dict],
    language_code: str | None = None,
    level: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    prompt_version: str = "v1",
    allow_cache: bool = True,
    input_for_privacy: dict | None = None,
) -> tuple[dict, bool]:
    """Retorna (payload, cache_hit). Dedup in-process para requests idênticos.

    Conteúdo pessoal (`input_for_privacy`) nunca é persistido no cache global.
    O holder `_Inflight` evita memory leak: é removido do dict no `finally` do
    líder; waiters leem o resultado pela referência local ao holder.
    """
    if input_for_privacy is not None and is_personal_content(input_for_privacy):
        allow_cache = False
        logger.info("ai_cache_skip_personal capability=%s key=%s", capability, cache_key[:12])

    if allow_cache:
        hit = get_cached(db, cache_key)
        if hit is not None:
            return hit, True

    with _inflight_lock:
        holder = _inflight.get(cache_key)
        if holder is None:
            holder = _Inflight()
            _inflight[cache_key] = holder
            leader = True
        else:
            leader = False

    if not leader:
        holder.event.wait(timeout=60)
        if holder.error is not None:
            raise holder.error
        if holder.result is not None:
            logger.info("ai_dedup_join capability=%s key=%s", capability, cache_key[:12])
            return holder.result, True
        if allow_cache:
            hit = get_cached(db, cache_key)
            if hit is not None:
                return hit, True
        return compute(), False

    try:
        payload = compute()
        if allow_cache:
            store_cached(
                db,
                cache_key=cache_key,
                capability=capability,
                response=payload,
                language_code=language_code,
                level=level,
                provider=provider or payload.get("provider"),
                model=model or payload.get("model"),
                prompt_version=prompt_version,
            )
        holder.result = payload
        return payload, False
    except BaseException as exc:
        holder.error = exc
        raise
    finally:
        holder.event.set()
        with _inflight_lock:
            current = _inflight.get(cache_key)
            if current is holder:
                _inflight.pop(cache_key, None)
