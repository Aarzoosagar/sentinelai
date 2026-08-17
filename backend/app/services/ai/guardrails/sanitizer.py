"""Keep untrusted context as data and redact obvious sensitive values."""

from __future__ import annotations

import re
from typing import Iterable

_ASSIGNMENT_SECRET = re.compile(r"(?i)\b(api[_ -]?key|jwt(?:[_ -]?(?:secret|token|key))*|secret|password|authorization|database[_ -]?url|encryption[_ -]?key)\s*[:=]\s*[^\s,;]+")
_BEARER_SECRET = re.compile(r"(?i)\bbearer\s+[a-z0-9._-]+")
_GROQ_KEY = re.compile(r"\bgsk_[a-zA-Z0-9_-]+")


def wrap_untrusted_retrieved_data(content: str) -> str:
    return "<RETRIEVED_SECURITY_DATA>\n" + content + "\n</RETRIEVED_SECURITY_DATA>"


def redact_sensitive_data(text: str, sensitive_values: Iterable[str] = ()) -> str:
    redacted = _ASSIGNMENT_SECRET.sub("[REDACTED_SENSITIVE_DATA]", text)
    redacted = _BEARER_SECRET.sub("[REDACTED_SENSITIVE_DATA]", redacted)
    redacted = _GROQ_KEY.sub("[REDACTED_SENSITIVE_DATA]", redacted)
    for value in sensitive_values:
        if value and len(value) >= 6:
            redacted = redacted.replace(value, "[REDACTED_SENSITIVE_DATA]")
    return redacted
