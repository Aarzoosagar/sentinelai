"""
Compliance mapper.

Turns a list of already-persisted `Finding` rows for one audit session into
`ComplianceResult` rows for every supported framework:
  - CIS AWS Foundations and NIST CSF are derived directly from the
    cis_control / nist_control fields collectors already attach to findings.
  - ISO 27001, SOC 2, and AWS Well-Architected are derived from CIS controls
    via the static crosswalk in control_mapping.py.

A control with no matching finding is reported PASS — the collector ran the
underlying check and found nothing wrong. A control with only medium/low
findings is WARNING; a control with any critical/high finding is FAIL.
"""

from __future__ import annotations

from app.models.compliance_result import ComplianceResult
from app.models.enums import ComplianceFramework, ComplianceStatus, Severity
from app.models.finding import Finding
from app.services.risk.control_mapping import CIS_CONTROL_TITLES, CIS_CROSSWALK, NIST_CONTROL_TITLES

_SEVERITY_RANK: dict[Severity, int] = {
    Severity.CRITICAL: 4,
    Severity.HIGH: 3,
    Severity.MEDIUM: 2,
    Severity.LOW: 1,
    Severity.INFORMATIONAL: 0,
}


def _status_for_matches(matches: list[Finding]) -> tuple[ComplianceStatus, str | None, str | None]:
    if not matches:
        return ComplianceStatus.PASS, None, None

    worst = max(matches, key=lambda f: _SEVERITY_RANK[f.severity])
    if worst.severity in (Severity.CRITICAL, Severity.HIGH):
        status = ComplianceStatus.FAIL
    else:
        status = ComplianceStatus.WARNING

    note = f"{len(matches)} related finding(s); worst severity: {worst.severity.value}."
    return status, worst.id, note


def _build_cis_results(audit_session_id: str, findings: list[Finding]) -> list[ComplianceResult]:
    by_control: dict[str, list[Finding]] = {}
    for f in findings:
        if f.cis_control:
            by_control.setdefault(f.cis_control, []).append(f)

    results = []
    for control_id, title in CIS_CONTROL_TITLES.items():
        status, related_id, note = _status_for_matches(by_control.get(control_id, []))
        results.append(
            ComplianceResult(
                audit_session_id=audit_session_id,
                framework=ComplianceFramework.CIS_AWS_FOUNDATIONS,
                control_id=control_id,
                control_title=title,
                status=status,
                related_finding_id=related_id,
                notes=note,
            )
        )
    return results


def _build_nist_results(audit_session_id: str, findings: list[Finding]) -> list[ComplianceResult]:
    by_control: dict[str, list[Finding]] = {}
    for f in findings:
        if f.nist_control:
            by_control.setdefault(f.nist_control, []).append(f)

    results = []
    for control_id, title in NIST_CONTROL_TITLES.items():
        status, related_id, note = _status_for_matches(by_control.get(control_id, []))
        results.append(
            ComplianceResult(
                audit_session_id=audit_session_id,
                framework=ComplianceFramework.NIST_CSF,
                control_id=control_id,
                control_title=title,
                status=status,
                related_finding_id=related_id,
                notes=note,
            )
        )
    return results


def _build_crosswalk_results(audit_session_id: str, findings: list[Finding]) -> list[ComplianceResult]:
    by_cis_control: dict[str, list[Finding]] = {}
    for f in findings:
        if f.cis_control:
            by_cis_control.setdefault(f.cis_control, []).append(f)

    results: list[ComplianceResult] = []
    seen: set[tuple[ComplianceFramework, str]] = set()
    for cis_control_id, derived_controls in CIS_CROSSWALK.items():
        matches = by_cis_control.get(cis_control_id, [])
        status, related_id, note = _status_for_matches(matches)
        for framework, control_id, title in derived_controls:
            key = (framework, control_id)
            if key in seen:
                continue  # avoid duplicate rows if two CIS controls map to the same derived control
            seen.add(key)
            results.append(
                ComplianceResult(
                    audit_session_id=audit_session_id,
                    framework=framework,
                    control_id=control_id,
                    control_title=title,
                    status=status,
                    related_finding_id=related_id,
                    notes=note,
                )
            )
    return results


def build_compliance_results(audit_session_id: str, findings: list[Finding]) -> list[ComplianceResult]:
    """Builds ComplianceResult rows (not yet persisted) for every framework."""
    results: list[ComplianceResult] = []
    results.extend(_build_cis_results(audit_session_id, findings))
    results.extend(_build_nist_results(audit_session_id, findings))
    results.extend(_build_crosswalk_results(audit_session_id, findings))
    # AWS Well-Architected control set is a subset of the crosswalk output above
    # (only entries tagged AWS_WELL_ARCHITECTED in control_mapping.py appear).
    return results


def compute_framework_score(results: list[ComplianceResult]) -> int:
    """0-100 score for one framework's set of ComplianceResult rows."""
    if not results:
        return 100
    weight = {ComplianceStatus.PASS: 1.0, ComplianceStatus.WARNING: 0.5, ComplianceStatus.FAIL: 0.0}
    total = sum(weight[r.status] for r in results)
    return round((total / len(results)) * 100)
