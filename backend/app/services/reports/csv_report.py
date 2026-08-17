"""CSV report generation via pandas."""

from __future__ import annotations

import pandas as pd

from app.models.audit_session import AuditSession
from app.models.finding import Finding


def generate_findings_csv(audit: AuditSession, findings: list[Finding]) -> str:
    """Returns CSV text (not written to disk here — callers decide the path)."""
    rows = []
    for f in findings:
        rows.append(
            {
                "Finding ID": f.id,
                "Service": f.service.value,
                "Title": f.title,
                "Severity": f.severity.value,
                "Status": f.status.value,
                "Resource ID": f.resource_id or "",
                "Resource ARN": f.resource_arn or "",
                "Region": f.region or "",
                "CIS Control": f.cis_control or "",
                "NIST Control": f.nist_control or "",
                "MITRE ATT&CK": f.mitre_attack or "",
                "Risk Score": f.risk_score.risk_score if f.risk_score else "",
                "Remediation": f.remediation,
                "Estimated Remediation Time": f.estimated_remediation_time or "",
                "Description": f.description,
                "Detected At": f.created_at.isoformat(),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(
            columns=[
                "Finding ID", "Service", "Title", "Severity", "Status", "Resource ID",
                "Resource ARN", "Region", "CIS Control", "NIST Control", "MITRE ATT&CK",
                "Risk Score", "Remediation", "Estimated Remediation Time", "Description", "Detected At",
            ]
        )
    return df.to_csv(index=False)
