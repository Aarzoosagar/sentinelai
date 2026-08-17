"""
Central AI service. Every AI feature in SentinelAI (finding explanations,
chat, summaries, IaC generation) goes through this module — nothing else
in the codebase imports the `groq` package directly. This is the "central
AI service" the project rules require.

Implements:
  - Retry with exponential backoff on transient errors (rate limit, timeout,
    connection, and 5xx server errors)
  - Per-request timeout (from GroqRuntimeConfig)
  - Streaming (`stream_completion`) and non-streaming (`complete`) paths
  - JSON structured output via Groq's `response_format={"type": "json_object"}`
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from typing import Any
from dataclasses import dataclass

from groq import (
    APIConnectionError,
    APITimeoutError,
    Groq,
    InternalServerError,
    RateLimitError,
)

from app.core.config.groq_config import GroqRuntimeConfig, get_groq_config
from app.services.ai.observability import increment, record, timed

_RETRYABLE_EXCEPTIONS = (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError)


class AiServiceError(Exception):
    """Raised when the Groq API call ultimately fails after all retries."""


class AiServiceNotConfigured(Exception):
    """Raised when GROQ_API_KEY is not set."""


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolCompletion:
    content: str
    tool_calls: list[ToolCall]


def _get_client(config: GroqRuntimeConfig) -> Groq:
    if not config.api_key:
        raise AiServiceNotConfigured(
            "GROQ_API_KEY is not set. Add it to your .env file to enable AI features."
        )
    return Groq(api_key=config.api_key, timeout=config.timeout_seconds)


def _with_retry(fn, max_retries: int, on_retry=None):
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except _RETRYABLE_EXCEPTIONS as exc:
            last_error = exc
            if on_retry:
                on_retry(type(exc).__name__)
            if attempt == max_retries:
                break
            backoff_seconds = min(2**attempt, 8)
            time.sleep(backoff_seconds)
    raise AiServiceError(f"Groq API call failed after {max_retries + 1} attempt(s): {last_error}") from last_error


def complete(
    messages: list[dict[str, str]],
    *,
    task: str | None = None,
    json_mode: bool = False,
) -> str:
    """
    Non-streaming completion. Returns the assistant's text content. If
    json_mode=True, the caller must instruct the model (in the prompt) to
    return JSON — Groq's json_object mode requires "JSON" to appear in the
    prompt itself.
    """
    config = get_groq_config(task)
    client = _get_client(config)
    retries = [0]

    def _call() -> str:
        create_kwargs: dict[str, Any] = dict(
            model=config.model,
            messages=messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            stream=False,
        )
        if json_mode:
            create_kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**create_kwargs)
        return response.choices[0].message.content or ""

    with timed("groq_inference", counter="llm_requests", model=config.model, task=task or "default"):
        response = _with_retry(_call, config.max_retries, lambda _: retries.__setitem__(0, retries[0] + 1))
        record("groq_response", model=config.model, response_size=len(response), retry_count=retries[0])
        return response


def complete_json(messages: list[dict[str, str]], *, task: str | None = None) -> dict[str, Any]:
    """Convenience wrapper: calls complete() in json_mode and parses the result."""
    raw = complete(messages, task=task, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AiServiceError(f"Groq did not return valid JSON: {exc}") from exc


def complete_with_tools(messages: list[dict[str, Any]], tools: list[dict[str, Any]], *, task: str | None = None) -> ToolCompletion:
    """Use Groq's function-call protocol without exposing its SDK to chat code."""
    config = get_groq_config(task)
    client = _get_client(config)
    retries = [0]

    def _call() -> ToolCompletion:
        response = client.chat.completions.create(
            model=config.model, messages=messages, tools=tools, tool_choice="auto",
            temperature=config.temperature, max_tokens=config.max_tokens, stream=False,
        )
        message = response.choices[0].message
        calls: list[ToolCall] = []
        for call in message.tool_calls or []:
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError as exc:
                raise AiServiceError("Groq returned invalid tool arguments") from exc
            if not isinstance(arguments, dict):
                raise AiServiceError("Groq tool arguments must be an object")
            calls.append(ToolCall(id=call.id, name=call.function.name, arguments=arguments))
        return ToolCompletion(content=message.content or "", tool_calls=calls)

    with timed("groq_inference", counter="llm_requests", model=config.model, task=task or "chat"):
        response = _with_retry(_call, config.max_retries, lambda _: retries.__setitem__(0, retries[0] + 1))
        record("groq_response", model=config.model, response_size=len(response.content), tool_call_count=len(response.tool_calls), retry_count=retries[0])
        return response


def stream_completion(
    messages: list[dict[str, str]],
    *,
    task: str | None = None,
) -> Iterator[str]:
    """Yields text chunks as they arrive, for the AI Security Chat streaming UI."""
    config = get_groq_config(task)
    client = _get_client(config)

    def _call():
        return client.chat.completions.create(
            model=config.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            stream=True,
        )

    with timed("groq_stream", counter="llm_requests", model=config.model, task=task or "chat"):
        stream = _with_retry(_call, config.max_retries)
        response_size = 0
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                response_size += len(delta)
                yield delta
        record("groq_stream_complete", model=config.model, response_size=response_size)
