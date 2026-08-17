"""Structured-output and lightweight grounding checks for model responses."""

from __future__ import annotations

import re
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config.settings import get_settings
from app.services.ai.guardrails.sanitizer import redact_sensitive_data


class OutputValidationError(ValueError):
    pass


class TopRisk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finding_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=1, max_length=255)
    reason: str = Field(min_length=1, max_length=1000)


class TopRisksResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    top_risks: list[TopRisk]


_FINDING_REFERENCE = re.compile(r"(?i)\bfinding\s+(?:id\s*)?[:#]?\s*([a-z0-9_-]{3,})")


def validate_top_risks(payload: object, allowed_finding_ids: Iterable[str]) -> list[dict[str, str]]:
    try:
        parsed = TopRisksResponse.model_validate(payload)
    except ValidationError as exc:
        raise OutputValidationError("Groq returned an invalid top-risks response") from exc
    allowed = set(allowed_finding_ids)
    if any(risk.finding_id not in allowed for risk in parsed.top_risks):
        raise OutputValidationError("Groq referenced a finding outside the authorized input")
    return [risk.model_dump() for risk in parsed.top_risks]


def protect_chat_output(answer: str, allowed_finding_ids: Iterable[str]) -> str:
    """Redact secrets and remove explicit finding citations unsupported by this turn's data."""
    settings = get_settings()
    protected = redact_sensitive_data(answer, (settings.groq_api_key, settings.jwt_secret_key, settings.credentials_encryption_key))
    allowed = set(allowed_finding_ids)

    def remove_unsupported(match: re.Match[str]) -> str:
        return match.group(0) if match.group(1) in allowed else "[unsupported finding reference removed]"

    return _FINDING_REFERENCE.sub(remove_unsupported, protected)
