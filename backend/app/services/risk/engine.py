"""
Risk engine orchestration.

Bridges services/aws (RawFinding, no DB access) and the persistence layer:
takes the raw findings collected for an audit, persists them as Finding +
RiskScore rows, computes the audit-wide Security Score, and generates
ComplianceResult rows across every framework.

This is called by the audit API/background task after
services.aws.orchestrator.run_full_audit() returns.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.finding import Finding
from app.models.risk_score import RiskScore
from app.repositories.compliance_repository import ComplianceResultRepository
from app.repositories.finding_repository import FindingRepository
from app.repositories.risk_score_repository import RiskScoreRepository
from app.services.aws.base import RawFinding
from app.services.risk import scoring
from app.services.risk.compliance_mapper import build_compliance_results


def persist_findings(db: Session, audit_session_id: str, raw_findings: list[RawFinding]) -> list[Finding]:
    finding_repo = FindingRepository(db)
    risk_repo = RiskScoreRepository(db)

    persisted: list[Finding] = []
    for raw in raw_findings:
        finding = Finding(
            audit_session_id=audit_session_id,
            service=raw.service,
            title=raw.title,
            description=raw.description,
            severity=raw.severity_hint,
            resource_arn=raw.resource_arn,
            resource_id=raw.resource_id,
            region=raw.region,
            cis_control=raw.cis_control,
            nist_control=raw.nist_control,
            mitre_attack=raw.mitre_attack,
            remediation=raw.remediation,
            estimated_remediation_time=raw.estimated_remediation_time,
            references="\n".join(raw.references) if raw.references else None,
        )
        finding_repo.add(finding)
        persisted.append(finding)

        breakdown = scoring.score_finding(raw.title, raw.severity_hint)
        risk_repo.add(
            RiskScore(
                finding_id=finding.id,
                risk_score=breakdown.risk_score,
                likelihood=breakdown.likelihood,
                business_impact=breakdown.business_impact,
                exploitability=breakdown.exploitability,
            )
        )

    db.flush()
    return persisted


def build_and_persist_compliance(db: Session, audit_session_id: str, findings: list[Finding]) -> None:
    compliance_repo = ComplianceResultRepository(db)
    results = build_compliance_results(audit_session_id, findings)
    compliance_repo.bulk_add(results)


def compute_overall_security_score(findings: list[Finding]) -> int:
    return scoring.compute_security_score([f.severity for f in findings])


def process_audit(db: Session, audit_session_id: str, raw_findings: list[RawFinding]) -> int:
    """
    Full risk-engine pipeline for one completed collection run:
    persist findings + risk scores, build compliance results, return the
    overall 0-100 security score. Caller is responsible for committing and
    updating the AuditSession row's status/security_score.
    """
    findings = persist_findings(db, audit_session_id, raw_findings)
    build_and_persist_compliance(db, audit_session_id, findings)
    return compute_overall_security_score(findings)
