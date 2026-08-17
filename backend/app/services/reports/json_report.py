"""JSON report generation — a complete machine-readable export of one audit."""

from __future__ import annotations

import json
from datetime import datetime

from app.models.audit_session import AuditSession
from app.models.compliance_result import ComplianceResult
from app.models.finding import Finding


def _default_serializer(value):
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value)} is not JSON serializable")


def generate_json_report(
    audit: AuditSession, findings: list[Finding], compliance_results: list[ComplianceResult]
) -> str:
    payload = {
        "audit": {
            "id": audit.id,
            "status": audit.status.value,
            "security_score": audit.security_score,
            "resources_scanned": audit.resources_scanned,
            "started_at": audit.started_at,
            "completed_at": audit.completed_at,
        },
        "findings": [
            {
                "id": f.id,
                "service": f.service.value,
                "title": f.title,
                "description": f.description,
                "severity": f.severity.value,
                "status": f.status.value,
                "resource_id": f.resource_id,
                "resource_arn": f.resource_arn,
                "region": f.region,
                "cis_control": f.cis_control,
                "nist_control": f.nist_control,
                "mitre_attack": f.mitre_attack,
                "remediation": f.remediation,
                "estimated_remediation_time": f.estimated_remediation_time,
                "risk_score": f.risk_score.risk_score if f.risk_score else None,
                "created_at": f.created_at,
            }
            for f in findings
        ],
        "compliance_results": [
            {
                "framework": c.framework.value,
                "control_id": c.control_id,
                "control_title": c.control_title,
                "status": c.status.value,
                "notes": c.notes,
            }
            for c in compliance_results
        ],
    }
    return json.dumps(payload, indent=2, default=_default_serializer)
