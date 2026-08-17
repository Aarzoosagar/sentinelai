"""
Risk scoring.

Converts a collector's qualitative `Severity` hint into the quantitative
risk breakdown persisted on `RiskScore` (0-100 risk_score, 1-5 likelihood/
business_impact/exploitability), and computes the audit-wide 0-100
Security Score from the full set of persisted findings.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.models.enums import Severity

# (likelihood, business_impact, exploitability, base_risk_score) per severity band.
_SEVERITY_PARAMS: dict[Severity, tuple[int, int, int, int]] = {
    Severity.CRITICAL: (5, 5, 5, 95),
    Severity.HIGH: (4, 4, 4, 75),
    Severity.MEDIUM: (3, 3, 3, 50),
    Severity.LOW: (2, 2, 2, 25),
    Severity.INFORMATIONAL: (1, 1, 1, 5),
}

# Per-severity penalty applied to the overall 0-100 Security Score, with
# diminishing returns handled by the cap in compute_security_score.
_SEVERITY_PENALTY: dict[Severity, int] = {
    Severity.CRITICAL: 15,
    Severity.HIGH: 8,
    Severity.MEDIUM: 4,
    Severity.LOW: 1,
    Severity.INFORMATIONAL: 0,
}


@dataclass
class RiskBreakdown:
    risk_score: int
    likelihood: int
    business_impact: int
    exploitability: int


def _deterministic_jitter(title: str, spread: int = 4) -> int:
    """
    Small deterministic offset (-spread..+spread) derived from the finding
    title so that findings sharing a severity aren't all bit-for-bit
    identical scores, while remaining stable across re-runs of the same
    audit (no randomness, same input always produces the same score).
    """
    digest = hashlib.sha256(title.encode("utf-8")).hexdigest()
    value = int(digest[:4], 16) % (spread * 2 + 1)
    return value - spread


def score_finding(title: str, severity: Severity) -> RiskBreakdown:
    likelihood, business_impact, exploitability, base_score = _SEVERITY_PARAMS[severity]
    jitter = _deterministic_jitter(title)
    risk_score = max(0, min(100, base_score + jitter))
    return RiskBreakdown(
        risk_score=risk_score,
        likelihood=likelihood,
        business_impact=business_impact,
        exploitability=exploitability,
    )


def compute_security_score(severities: list[Severity]) -> int:
    """
    Overall 0-100 Security Score for an audit session. Starts at 100 and
    subtracts a per-finding penalty weighted by severity, capped so a very
    large finding count can't push the score below 0 in a way that hides
    relative improvement between audits.
    """
    if not severities:
        return 100

    penalty = sum(_SEVERITY_PENALTY[s] for s in severities)
    return max(0, 100 - min(100, penalty))
