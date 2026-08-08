"""Retry low-cost + circuit breaker leve in-process.

Política (free-tier friendly):

- 401/403/404 → zero retry no mesmo modelo
- 429 → no máximo 1 wait+retry (Retry-After limitado) OU fallback do chamador
- timeout / network / 5xx → **sem** retry automático do mesmo modelo por padrão
  (preferir fallback rápido). `max_retries` só aumenta tentativas do mesmo
  modelo quando o chamador justificar.

Máximo típico por user action com OpenRouter (primary + fallback, max_retries=0):

- caminho feliz: **1** request
- primary falha (5xx/timeout) + fallback: **2** requests
- primary 429 (1 retry) + fallback: no máximo **3** requests
- nunca o padrão caro primary×2 + fallback×2 para todo 5xx

Circuit breaker: threshold pequeno, cooldown, half-open. Lock in-process
(sem Redis / filas / locks distribuídos).
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")

#: Teto absoluto de espera em 429 (segundos).
_MAX_RETRY_AFTER = 5.0


@dataclass
class CircuitState:
    status: str = "closed"  # closed | open | half_open
    failures: int = 0
    opened_at: float = 0.0
    cooldown_seconds: float = 30.0
    failure_threshold: int = 3


_circuits: dict[str, CircuitState] = {}
_lock = threading.Lock()


def get_circuit(name: str) -> CircuitState:
    with _lock:
        if name not in _circuits:
            _circuits[name] = CircuitState()
        return _circuits[name]


def reset_circuits() -> None:
    with _lock:
        _circuits.clear()


def _classify_http_status(status: int) -> str:
    if status in (401, 403):
        return "auth"
    if status == 404:
        return "not_found"
    if status == 429:
        return "rate_limit"
    if 500 <= status <= 599:
        return "server"
    return "other"


@dataclass
class ProviderCallResult:
    ok: bool
    value: object | None = None
    error: Exception | None = None
    attempts: int = 0
    rate_limited: bool = False
    circuit_state: str = "closed"
    fallback_used: bool = False


def call_with_policy(
    *,
    provider_name: str,
    operation: Callable[[], T],
    max_retries: int = 0,
    base_backoff: float = 0.5,
    on_fallback: Callable[[], T] | None = None,
    allow_rate_limit_retry: bool = True,
) -> ProviderCallResult:
    """Executa `operation` com política low-cost.

    `max_retries` = retries **adicionais** do mesmo modelo para 5xx/timeout
    (default 0 → uma tentativa, depois fallback do chamador).
    """
    circuit = get_circuit(provider_name)
    now = time.monotonic()

    if circuit.status == "open":
        if now - circuit.opened_at < circuit.cooldown_seconds:
            logger.warning(
                "provider_circuit_open provider=%s cooldown_left=%.1f",
                provider_name,
                circuit.cooldown_seconds - (now - circuit.opened_at),
            )
            if on_fallback is not None:
                return ProviderCallResult(
                    ok=True,
                    value=on_fallback(),
                    attempts=0,
                    circuit_state="open",
                    fallback_used=True,
                )
            return ProviderCallResult(
                ok=False,
                error=RuntimeError("circuit_open"),
                attempts=0,
                circuit_state="open",
            )
        circuit.status = "half_open"

    attempts = 0
    last_error: Exception | None = None
    rate_limited = False
    rate_limit_retry_used = False
    server_retries_used = 0

    while True:
        attempts += 1
        try:
            value = operation()
            circuit.failures = 0
            circuit.status = "closed"
            return ProviderCallResult(
                ok=True,
                value=value,
                attempts=attempts,
                circuit_state=circuit.status,
            )
        except httpx.HTTPStatusError as exc:
            last_error = exc
            kind = _classify_http_status(exc.response.status_code)
            logger.warning(
                "provider_http_error provider=%s status=%s kind=%s attempt=%s",
                provider_name,
                exc.response.status_code,
                kind,
                attempts,
            )
            if kind in {"auth", "not_found"}:
                break
            if kind == "rate_limit":
                rate_limited = True
                if allow_rate_limit_retry and not rate_limit_retry_used:
                    rate_limit_retry_used = True
                    retry_after = exc.response.headers.get("Retry-After")
                    sleep_for = (
                        float(retry_after)
                        if retry_after and retry_after.replace(".", "", 1).isdigit()
                        else base_backoff
                    )
                    sleep_for = min(max(sleep_for, 0.0), _MAX_RETRY_AFTER)
                    time.sleep(sleep_for)
                    continue
                break
            if kind == "server" and server_retries_used < max_retries:
                server_retries_used += 1
                time.sleep(base_backoff * (server_retries_used))
                continue
            break
        except (httpx.TimeoutException, httpx.NetworkError, httpx.TransportError) as exc:
            last_error = exc
            logger.warning(
                "provider_network_error provider=%s attempt=%s err=%s",
                provider_name,
                attempts,
                type(exc).__name__,
            )
            if server_retries_used < max_retries:
                server_retries_used += 1
                time.sleep(base_backoff * server_retries_used)
                continue
            break
        except Exception as exc:  # noqa: BLE001 — política genérica do provider
            last_error = exc
            break

    circuit.failures += 1
    if circuit.failures >= circuit.failure_threshold:
        circuit.status = "open"
        circuit.opened_at = time.monotonic()
        logger.warning(
            "provider_circuit_opened provider=%s failures=%s",
            provider_name,
            circuit.failures,
        )

    if on_fallback is not None:
        return ProviderCallResult(
            ok=True,
            value=on_fallback(),
            error=last_error,
            attempts=attempts,
            rate_limited=rate_limited,
            circuit_state=circuit.status,
            fallback_used=True,
        )
    return ProviderCallResult(
        ok=False,
        error=last_error,
        attempts=attempts,
        rate_limited=rate_limited,
        circuit_state=circuit.status,
    )
