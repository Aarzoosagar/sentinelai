"""Read-only, request-context-scoped audit tools. No model-provided audit ID is used."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import Severity
from app.models.finding import Finding
from app.repositories.audit_repository import AuditSessionRepository
from app.repositories.finding_repository import FindingRepository
from app.services.ai.tools.schemas import (
    AffectedResourceToolResult, AffectedResourcesToolOutput, AuditSummaryToolOutput,
    FindingListToolOutput, FindingToolResult, GetAffectedResourcesInput,
    GetAuditSummaryInput, GetCriticalFindingsInput, GetFindingByIdInput,
    GetFindingsByFrameworkInput, GetFindingsByServiceInput, GetFindingsInput,
)


class ToolAuthorizationError(PermissionError):
    """Raised when the request context does not own the audit being queried."""


@dataclass(frozen=True)
class ToolExecutionContext:
    db: Session
    audit_session_id: str
    user_id: str


def _audit(context: ToolExecutionContext):
    audit = AuditSessionRepository(context.db).get_for_user(context.audit_session_id, context.user_id)
    if audit is None:
        raise ToolAuthorizationError("Audit session not found or not accessible")
    return audit


def _finding_result(finding: Finding) -> FindingToolResult:
    return FindingToolResult(
        finding_id=finding.id, title=finding.title, service=finding.service.value,
        severity=finding.severity.value, status=finding.status.value,
        description=finding.description, remediation=finding.remediation,
        resource_id=finding.resource_id, resource_arn=finding.resource_arn,
        cis_control=finding.cis_control, nist_control=finding.nist_control,
    )


def get_audit_summary(context: ToolExecutionContext, _: GetAuditSummaryInput) -> AuditSummaryToolOutput:
    audit = _audit(context)
    return AuditSummaryToolOutput(
        audit_session_id=audit.id, status=audit.status.value, security_score=audit.security_score,
        resources_scanned=audit.resources_scanned,
        findings_by_severity=FindingRepository(context.db).count_by_severity(audit.id),
    )


def get_findings(context: ToolExecutionContext, params: GetFindingsInput) -> FindingListToolOutput:
    audit = _audit(context)
    findings, total = FindingRepository(context.db).list_filtered(
        audit_session_id=audit.id, severity=params.severity, service=params.service,
        status=params.status, limit=params.limit,
    )
    return FindingListToolOutput(findings=[_finding_result(item) for item in findings], total=total)


def get_finding_by_id(context: ToolExecutionContext, params: GetFindingByIdInput) -> FindingListToolOutput:
    audit = _audit(context)
    finding = context.db.scalar(select(Finding).where(Finding.id == params.finding_id, Finding.audit_session_id == audit.id))
    return FindingListToolOutput(findings=[_finding_result(finding)] if finding else [], total=1 if finding else 0)


def get_critical_findings(context: ToolExecutionContext, params: GetCriticalFindingsInput) -> FindingListToolOutput:
    return get_findings(context, GetFindingsInput(limit=params.limit, severity=Severity.CRITICAL))


def get_findings_by_service(context: ToolExecutionContext, params: GetFindingsByServiceInput) -> FindingListToolOutput:
    return get_findings(context, GetFindingsInput(limit=params.limit, service=params.service))


def get_findings_by_framework(context: ToolExecutionContext, params: GetFindingsByFrameworkInput) -> FindingListToolOutput:
    audit = _audit(context)
    control_column = Finding.cis_control if params.framework == "cis" else Finding.nist_control
    statement = select(Finding).where(Finding.audit_session_id == audit.id, control_column.is_not(None))
    if params.control:
        statement = statement.where(control_column.ilike(f"%{params.control}%"))
    findings = list(context.db.scalars(statement.order_by(Finding.created_at.desc()).limit(params.limit)))
    return FindingListToolOutput(findings=[_finding_result(item) for item in findings], total=len(findings))


def get_affected_resources(context: ToolExecutionContext, params: GetAffectedResourcesInput) -> AffectedResourcesToolOutput:
    audit = _audit(context)
    findings, total = FindingRepository(context.db).list_filtered(audit_session_id=audit.id, limit=params.limit)
    return AffectedResourcesToolOutput(
        resources=[AffectedResourceToolResult(finding_id=item.id, service=item.service.value, resource_id=item.resource_id, resource_arn=item.resource_arn, title=item.title) for item in findings],
        total=total,
    )
