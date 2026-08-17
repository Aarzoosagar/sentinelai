"""Local, privacy-safe structured telemetry for SentinelAI's AI pipeline."""

from __future__ import annotations

import contextvars
import json
import logging
import time
import uuid
from collections import Counter, defaultdict
from contextlib import contextmanager
from typing import Iterator

from app.core.config.settings import get_settings
from app.services.ai.guardrails.policies import SENSITIVE_FIELD_NAMES
from app.services.ai.guardrails.sanitizer import redact_sensitive_data

logger = logging.getLogger("sentinelai.ai")
_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("ai_request_id", default=None)
_audit_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("ai_audit_id", default=None)
_operation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("ai_operation_id", default=None)
_counters: Counter[str] = Counter()
_latencies: dict[str, list[float]] = defaultdict(list)


def set_correlation(request_id: str | None = None, audit_session_id: str | None = None) -> tuple[contextvars.Token, contextvars.Token, contextvars.Token]:
    return (
        _request_id.set(request_id or str(uuid.uuid4())),
        _audit_id.set(audit_session_id),
        _operation_id.set(str(uuid.uuid4())),
    )


def reset_correlation(tokens: tuple[contextvars.Token, contextvars.Token, contextvars.Token]) -> None:
    _request_id.reset(tokens[0]); _audit_id.reset(tokens[1]); _operation_id.reset(tokens[2])


def current_request_id() -> str | None:
    return _request_id.get()


def classify_error(exc: Exception) -> str:
    name = type(exc).__name__.lower()
    if "timeout" in name: return "groq_timeout"
    if "ratelimit" in name: return "groq_rate_limit"
    if "connection" in name: return "groq_connection_error"
    if "server" in name: return "groq_server_error"
    if "authorization" in name or "permission" in name: return "authorization_error"
    if "validation" in name: return "validation_error"
    if "rerank" in name: return "reranking_error"
    return "tool_error" if "tool" in name else "retrieval_error"


def record(event: str, **fields: object) -> None:
    """Log only caller-supplied safe metadata; never serialize payloads by default."""
    settings = get_settings()
    if not settings.ai_observability_enabled:
        return
    safe_fields = {
        key: "[REDACTED]" if any(marker in key.lower() for marker in SENSITIVE_FIELD_NAMES) else redact_sensitive_data(value) if isinstance(value, str) else value
        for key, value in fields.items()
    }
    payload = {"event": event, "request_id": _request_id.get(), "audit_session_id": _audit_id.get(), "operation_id": _operation_id.get(), **safe_fields}
    logger.info(json.dumps(payload, default=str, sort_keys=True))


def increment(name: str, value: int = 1) -> None:
    if get_settings().ai_metrics_enabled:
        _counters[name] += value


def observe_latency(name: str, latency_ms: float) -> None:
    if get_settings().ai_metrics_enabled:
        _latencies[name].append(latency_ms)


@contextmanager
def timed(event: str, *, counter: str, **fields: object) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        increment(f"{counter}_errors_total")
        if counter == "llm_requests": increment("llm_errors_total")
        if counter == "tool_calls": increment("tool_errors_total")
        observe_latency(f"{counter}_latency_ms", latency_ms)
        record(event, status="failure", error_type=classify_error(exc), latency_ms=latency_ms, **fields)
        raise
    else:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        increment(f"{counter}_total")
        observe_latency(f"{counter}_latency_ms", latency_ms)
        record(event, status="success", latency_ms=latency_ms, **fields)


def metrics_snapshot() -> dict[str, object]:
    return {"counters": dict(_counters), "latencies": {name: list(values) for name, values in _latencies.items()}}


def reset_metrics() -> None:
    _counters.clear(); _latencies.clear()
