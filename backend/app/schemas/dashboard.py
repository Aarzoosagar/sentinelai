"""Schemas for the dashboard summary endpoint (widgets + chart data)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SeverityBreakdown(BaseModel):
    critical: int
    high: int
    medium: int
    low: int
    informational: int


class ServiceRiskPoint(BaseModel):
    service: str
    finding_count: int
    average_risk_score: float


class ScoreTrendPoint(BaseModel):
    audit_session_id: str
    date: datetime
    security_score: int


class RecentAuditSummary(BaseModel):
    id: str
    aws_account_alias: str
    status: str
    security_score: int | None
    completed_at: datetime | None


class DashboardSummaryResponse(BaseModel):
    security_score: int | None
    resources_scanned: int
    compliance_score: int | None
    findings_by_severity: SeverityBreakdown
    risk_by_service: list[ServiceRiskPoint]
    security_score_trend: list[ScoreTrendPoint]
    recent_audits: list[RecentAuditSummary]
    top_vulnerable_services: list[ServiceRiskPoint]
