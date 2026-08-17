"""Converts ORM objects into plain dicts before they're ever put in a prompt.

This is a deliberate boundary: prompt templates only ever see dicts built
here, never live ORM objects, which keeps "base responses only on
collected audit data" easy to audit — there's no path for a prompt to
accidentally pull in an unrelated relationship.
"""

from __future__ import annotations

from app.models.audit_session import AuditSession
from app.models.finding import Finding


def finding_to_dict(finding: Finding) -> dict:
    return {
        "id": finding.id,
        "service": finding.service.value,
        "title": finding.title,
        "description": finding.description,
        "severity": finding.severity.value,
        "resource_id": finding.resource_id,
        "cis_control": finding.cis_control,
        "nist_control": finding.nist_control,
        "mitre_attack": finding.mitre_attack,
        "remediation": finding.remediation,
    }


def audit_to_dict(audit: AuditSession) -> dict:
    return {
        "id": audit.id,
        "security_score": audit.security_score,
        "resources_scanned": audit.resources_scanned,
        "status": audit.status.value,
    }
