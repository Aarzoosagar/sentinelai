"""Tests for services/risk/compliance_mapper.py."""

from __future__ import annotations

from app.models.enums import AwsService, ComplianceFramework, ComplianceStatus, Severity
from app.models.finding import Finding
from app.services.risk.compliance_mapper import build_compliance_results, compute_framework_score


def _make_finding(**overrides) -> Finding:
    defaults = dict(
        id="finding-1",
        audit_session_id="audit-1",
        service=AwsService.S3,
        title="Public S3 bucket",
        description="desc",
        severity=Severity.CRITICAL,
        remediation="fix it",
        cis_control="2.1.5",
    )
    defaults.update(overrides)
    return Finding(**defaults)


def test_control_with_no_matching_finding_passes():
    results = build_compliance_results("audit-1", findings=[])
    cis_results = [r for r in results if r.framework == ComplianceFramework.CIS_AWS_FOUNDATIONS]
    assert len(cis_results) > 0
    assert all(r.status == ComplianceStatus.PASS for r in cis_results)


def test_control_with_critical_finding_fails():
    finding = _make_finding(cis_control="2.1.5", severity=Severity.CRITICAL)
    results = build_compliance_results("audit-1", findings=[finding])
    control = next(
        r
        for r in results
        if r.framework == ComplianceFramework.CIS_AWS_FOUNDATIONS and r.control_id == "2.1.5"
    )
    assert control.status == ComplianceStatus.FAIL
    assert control.related_finding_id == "finding-1"


def test_control_with_medium_finding_warns_not_fails():
    finding = _make_finding(cis_control="2.8", severity=Severity.MEDIUM, id="finding-2")
    results = build_compliance_results("audit-1", findings=[finding])
    control = next(
        r for r in results if r.framework == ComplianceFramework.CIS_AWS_FOUNDATIONS and r.control_id == "2.8"
    )
    assert control.status == ComplianceStatus.WARNING


def test_crosswalk_derives_iso_and_soc2_from_cis_control():
    finding = _make_finding(cis_control="2.1.5", severity=Severity.CRITICAL)
    results = build_compliance_results("audit-1", findings=[finding])
    iso_results = [r for r in results if r.framework == ComplianceFramework.ISO_27001]
    soc2_results = [r for r in results if r.framework == ComplianceFramework.SOC_2]
    assert len(iso_results) > 0
    assert len(soc2_results) > 0
    # The derived ISO/SOC2 controls tied to this CIS control should also FAIL.
    assert any(r.status == ComplianceStatus.FAIL for r in iso_results)


def test_compute_framework_score_all_pass_is_100():
    finding = _make_finding()  # unrelated control, so everything else passes
    results = build_compliance_results("audit-1", findings=[])
    score = compute_framework_score([r for r in results if r.framework == ComplianceFramework.CIS_AWS_FOUNDATIONS])
    assert score == 100


def test_compute_framework_score_empty_list_is_100():
    assert compute_framework_score([]) == 100
