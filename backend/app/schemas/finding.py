"""Schemas for security findings, their risk scores, and AI explanations."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import AwsService, FindingStatus, Severity
from app.schemas.common import ORMBase


class RiskScoreResponse(ORMBase):
    risk_score: int
    likelihood: int
    business_impact: int
    exploitability: int


class FindingListItemResponse(ORMBase):
    id: str
    service: AwsService
    title: str
    severity: Severity
    status: FindingStatus
    resource_id: str | None
    region: str | None
    created_at: datetime


class FindingDetailResponse(ORMBase):
    id: str
    audit_session_id: str
    service: AwsService
    title: str
    description: str
    severity: Severity
    status: FindingStatus
    resource_arn: str | None
    resource_id: str | None
    region: str | None
    cis_control: str | None
    nist_control: str | None
    mitre_attack: str | None
    remediation: str
    estimated_remediation_time: str | None
    references: str | None
    ai_explanation: str | None
    risk_score: RiskScoreResponse | None
    created_at: datetime


class FindingFilterParams(BaseModel):
    audit_session_id: str | None = None
    severity: Severity | None = None
    service: AwsService | None = None
    status: FindingStatus | None = None
    region: str | None = None
    search: str | None = None


class FindingStatusUpdateRequest(BaseModel):
    status: FindingStatus


class AiExplanationResponse(BaseModel):
    finding_id: str
    ai_explanation: str
    generated_fresh: bool
