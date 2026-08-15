import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request

from app.core.errors import APIError

# Em memória: o backend roda um único processo uvicorn (sem --workers, sem
# Redis). Se algum dia isto escalar para múltiplas réplicas, o estado precisa
# migrar para um store compartilhado — um bucket por processo deixaria de
# limitar de verdade.
_buckets: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(request: Request, scope: str, limit: int, window_seconds: int) -> None:
    """Limita tentativas por IP numa janela deslizante; levanta 429 se excedido.

    Protege /login e /register, que antes não tinham nenhuma fricção contra
    força bruta além do custo do bcrypt.
    """
    key = f"{scope}:{_client_ip(request)}"
    now = time.monotonic()
    cutoff = now - window_seconds
    with _lock:
        bucket = _buckets[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            raise APIError(
                429,
                "rate_limited",
                "Muitas tentativas. Aguarde alguns minutos e tente novamente.",
                retryable=True,
            )
        bucket.append(now)


def reset() -> None:
    """Limpa todo o estado. Uso exclusivo de testes (isolamento entre casos)."""
    with _lock:
        _buckets.clear()
