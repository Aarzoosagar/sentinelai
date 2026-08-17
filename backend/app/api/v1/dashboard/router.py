"""Dashboard summary endpoint aggregating widgets and chart data."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database.session import get_db
from app.middleware.auth import get_current_active_user
from app.models.audit_session import AuditSession
from app.models.aws_account import AwsAccount
from app.models.compliance_result import ComplianceResult
from app.models.enums import AuditStatus, ComplianceStatus
from app.models.finding import Finding
from app.models.user import User
from app.repositories.audit_repository import AuditSessionRepository
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    RecentAuditSummary,
    ScoreTrendPoint,
    ServiceRiskPoint,
    SeverityBreakdown,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> DashboardSummaryResponse:
    audit_repo = AuditSessionRepository(db)
    recent_audits = audit_repo.list_for_user(current_user.id, limit=10)
    completed_audits = [a for a in recent_audits if a.status == AuditStatus.COMPLETED]
    latest = completed_audits[0] if completed_audits else None

    severity_breakdown = SeverityBreakdown(critical=0, high=0, medium=0, low=0, informational=0)
    risk_by_service: list[ServiceRiskPoint] = []
    compliance_score: int | None = None

    if latest is not None:
        severity_rows = db.execute(
            select(Finding.severity, func.count(Finding.id))
            .where(Finding.audit_session_id == latest.id)
            .group_by(Finding.severity)
        ).all()
        counts = {sev.value: count for sev, count in severity_rows}
        severity_breakdown = SeverityBreakdown(
            critical=counts.get("critical", 0),
            high=counts.get("high", 0),
            medium=counts.get("medium", 0),
            low=counts.get("low", 0),
            informational=counts.get("informational", 0),
        )

        service_rows = db.execute(
            select(Finding.service, func.count(Finding.id))
            .where(Finding.audit_session_id == latest.id)
            .group_by(Finding.service)
            .order_by(func.count(Finding.id).desc())
        ).all()
        for svc, count in service_rows:
            risk_by_service.append(ServiceRiskPoint(service=svc.value, finding_count=count, average_risk_score=0))

        compliance_rows = db.execute(
            select(ComplianceResult.status, func.count(ComplianceResult.id)).where(
                ComplianceResult.audit_session_id == latest.id
            ).group_by(ComplianceResult.status)
        ).all()
        if compliance_rows:
            weight = {ComplianceStatus.PASS: 1.0, ComplianceStatus.WARNING: 0.5, ComplianceStatus.FAIL: 0.0}
            total_controls = sum(count for _, count in compliance_rows)
            weighted = sum(weight[status] * count for status, count in compliance_rows)
            compliance_score = round((weighted / total_controls) * 100) if total_controls else None

    score_trend = [
        ScoreTrendPoint(audit_session_id=a.id, date=a.completed_at or a.created_at, security_score=a.security_score or 0)
        for a in reversed(completed_audits)
    ]

    recent_summaries = [
        RecentAuditSummary(
            id=a.id,
            aws_account_alias=a.aws_account.account_alias,
            status=a.status.value,
            security_score=a.security_score,
            completed_at=a.completed_at,
        )
        for a in recent_audits
    ]

    return DashboardSummaryResponse(
        security_score=latest.security_score if latest else None,
        resources_scanned=latest.resources_scanned if latest else 0,
        compliance_score=compliance_score,
        findings_by_severity=severity_breakdown,
        risk_by_service=risk_by_service,
        security_score_trend=score_trend,
        recent_audits=recent_summaries,
        top_vulnerable_services=risk_by_service[:5],
    )
