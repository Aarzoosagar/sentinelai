"""Input normalization and narrow detection of clear manipulation attempts."""

from __future__ import annotations

import re
import unicodedata


class InputGuardrailViolation(ValueError):
    pass


_BLOCKED_PATTERNS = (
    re.compile(r"\bignore\s+(?:all\s+)?(?:previous|system)\s+instructions?\b", re.I),
    re.compile(r"\b(?:reveal|print|show)\s+(?:the\s+)?(?:system\s+prompt|api\s*key|jwt\s*(?:secret|token)?|environment\s+variables?)\b", re.I),
    re.compile(r"\b(?:call|use)\s+get_[a-z_]+\b.*\baudit(?:_session)?_?id\b", re.I),
    re.compile(r"\b(?:call|use)\s+get_[a-z_]+\b.*\banother\s+audit\b", re.I),
    re.compile(r"\b(?:select|insert|update|delete|drop|alter)\b.{0,80}\b(?:from|table|findings|users)\b", re.I),
    re.compile(r"\b(?:read|open|cat)\s+(?:[a-z]:\\|/)[^\s]+", re.I),
)


def validate_chat_input(message: str, *, max_length: int = 4000) -> str:
    """Return normalized safe input, rejecting only unambiguous control/exfiltration attempts."""
    normalized = unicodedata.normalize("NFKC", message).replace("\x00", "").strip()
    if not normalized or len(normalized) > max_length:
        raise InputGuardrailViolation("Message is empty or exceeds the allowed length")
    if any(pattern.search(normalized) for pattern in _BLOCKED_PATTERNS):
        raise InputGuardrailViolation("This request attempts to override security boundaries")
    return normalized
