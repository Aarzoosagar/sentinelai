"""Tests for services/risk/scoring.py and compliance_mapper.py."""

from __future__ import annotations

from app.models.enums import Severity
from app.services.risk.scoring import compute_security_score, score_finding


def test_critical_finding_scores_higher_than_low():
    critical = score_finding("Public S3 bucket", Severity.CRITICAL)
    low = score_finding("Unused security group", Severity.LOW)
    assert critical.risk_score > low.risk_score
    assert critical.likelihood == 5
    assert low.likelihood == 2


def test_score_finding_is_deterministic():
    """Same title + severity must always produce the same score (no
    randomness) so re-running an audit doesn't silently reshuffle scores."""
    first = score_finding("Admin access on user X", Severity.HIGH)
    second = score_finding("Admin access on user X", Severity.HIGH)
    assert first.risk_score == second.risk_score


def test_score_finding_differs_for_different_titles_at_same_severity():
    """Two different findings at the same severity shouldn't be bit-for-bit
    identical — the deterministic jitter should differentiate them."""
    a = score_finding("Public S3 bucket alpha", Severity.CRITICAL)
    b = score_finding("Public S3 bucket beta", Severity.CRITICAL)
    assert a.risk_score != b.risk_score


def test_score_finding_stays_within_bounds():
    for severity in Severity:
        breakdown = score_finding("Some finding title", severity)
        assert 0 <= breakdown.risk_score <= 100
        assert 1 <= breakdown.likelihood <= 5
        assert 1 <= breakdown.business_impact <= 5
        assert 1 <= breakdown.exploitability <= 5


def test_compute_security_score_no_findings_is_perfect():
    assert compute_security_score([]) == 100


def test_compute_security_score_decreases_with_severity():
    only_low = compute_security_score([Severity.LOW])
    only_critical = compute_security_score([Severity.CRITICAL])
    assert only_critical < only_low


def test_compute_security_score_never_goes_negative():
    many_criticals = [Severity.CRITICAL] * 50
    score = compute_security_score(many_criticals)
    assert score == 0
