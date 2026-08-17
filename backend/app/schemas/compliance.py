"""Schemas for compliance framework mapping and scoring."""

from __future__ import annotations

from pydantic import BaseModel

from app.models.enums import ComplianceFramework, ComplianceStatus
from app.schemas.common import ORMBase


class ComplianceResultResponse(ORMBase):
    id: str
    framework: ComplianceFramework
    control_id: str
    control_title: str
    status: ComplianceStatus
    notes: str | None
    related_finding_id: str | None


class ComplianceFrameworkSummary(BaseModel):
    framework: ComplianceFramework
    score: int  # 0-100
    passed: int
    warnings: int
    failed: int
    total_controls: int
    results: list[ComplianceResultResponse]


class ComplianceOverviewResponse(BaseModel):
    audit_session_id: str
    frameworks: list[ComplianceFrameworkSummary]
