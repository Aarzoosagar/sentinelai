"""
Audit-level AI summaries: Executive Summary, Technical Summary, Compliance
Summary, and the "top five risks" JSON feature used by the dashboard/chat.
"""

from __future__ import annotations

from app.models.audit_session import AuditSession
from app.models.compliance_result import ComplianceResult
from app.models.enums import ComplianceStatus
from app.models.finding import Finding
from app.prompts.templates import (
    compliance_summary_prompt,
    executive_summary_prompt,
    technical_summary_prompt,
    top_risks_json_prompt,
)
from app.services.ai import groq_client
from app.services.ai.serializers import audit_to_dict, finding_to_dict
from app.services.ai.guardrails.output import validate_top_risks
from app.services.risk.compliance_mapper import compute_framework_score


def generate_executive_summary(audit: AuditSession, findings: list[Finding]) -> str:
    messages = executive_summary_prompt(audit_to_dict(audit), [finding_to_dict(f) for f in findings])
    return groq_client.complete(messages, task="executive_summary")


def generate_technical_summary(audit: AuditSession, findings: list[Finding]) -> str:
    sorted_findings = sorted(
        findings,
        key=lambda f: {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}[f.severity.value],
    )
    messages = technical_summary_prompt(audit_to_dict(audit), [finding_to_dict(f) for f in sorted_findings])
    return groq_client.complete(messages)


def generate_compliance_summary(results_by_framework: dict[str, list[ComplianceResult]]) -> str:
    framework_scores = []
    for framework, results in results_by_framework.items():
        framework_scores.append(
            {
                "framework": framework,
                "score": compute_framework_score(results),
                "passed": sum(1 for r in results if r.status == ComplianceStatus.PASS),
                "warnings": sum(1 for r in results if r.status == ComplianceStatus.WARNING),
                "failed": sum(1 for r in results if r.status == ComplianceStatus.FAIL),
            }
        )
    messages = compliance_summary_prompt(framework_scores)
    return groq_client.complete(messages)


def generate_top_risks(findings: list[Finding], count: int = 5) -> list[dict]:
    if not findings:
        return []
    messages = top_risks_json_prompt([finding_to_dict(f) for f in findings], count=count)
    result = groq_client.complete_json(messages)
    return validate_top_risks(result, [finding.id for finding in findings])
