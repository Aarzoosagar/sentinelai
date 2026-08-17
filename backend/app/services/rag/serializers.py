"""Canonical finding documents for retrieval, separate from presentation prompts."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.finding import Finding


@dataclass(frozen=True)
class RagDocument:
    id: str
    text: str
    metadata: dict[str, str]


def finding_to_rag_document(finding: Finding) -> RagDocument:
    text = "\n".join(
        (
            f"Finding ID: {finding.id}", f"AWS service: {finding.service.value}", f"Title: {finding.title}",
            f"Description: {finding.description}", f"Severity: {finding.severity.value}",
            f"Status: {finding.status.value}", f"Resource ARN: {finding.resource_arn or 'N/A'}",
            f"Resource ID: {finding.resource_id or 'N/A'}", f"Region: {finding.region or 'N/A'}",
            f"CIS control: {finding.cis_control or 'N/A'}", f"NIST control: {finding.nist_control or 'N/A'}",
            f"MITRE ATT&CK: {finding.mitre_attack or 'N/A'}", f"Remediation: {finding.remediation}",
            f"References: {finding.references or 'N/A'}",
        )
    )
    return RagDocument(
        id=finding.id,
        text=text,
        metadata={"finding_id": finding.id, "audit_session_id": finding.audit_session_id},
    )
