"""Strict Pydantic contracts for data returned to the model by audit tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AwsService, FindingStatus, Severity


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GetAuditSummaryInput(ToolInput):
    pass


class GetFindingsInput(ToolInput):
    limit: int = Field(default=25, ge=1, le=50)
    severity: Severity | None = None
    service: AwsService | None = None
    status: FindingStatus | None = None


class GetFindingByIdInput(ToolInput):
    finding_id: str = Field(min_length=1, max_length=36)


class GetCriticalFindingsInput(ToolInput):
    limit: int = Field(default=10, ge=1, le=50)


class GetFindingsByServiceInput(ToolInput):
    service: AwsService
    limit: int = Field(default=25, ge=1, le=50)


class GetFindingsByFrameworkInput(ToolInput):
    framework: Literal["cis", "nist"]
    control: str | None = Field(default=None, min_length=1, max_length=64)
    limit: int = Field(default=25, ge=1, le=50)


class GetAffectedResourcesInput(ToolInput):
    limit: int = Field(default=25, ge=1, le=50)


class FindingToolResult(BaseModel):
    finding_id: str
    title: str
    service: str
    severity: str
    status: str
    description: str
    remediation: str
    resource_id: str | None
    resource_arn: str | None
    cis_control: str | None
    nist_control: str | None


class FindingListToolOutput(BaseModel):
    findings: list[FindingToolResult]
    total: int


class AuditSummaryToolOutput(BaseModel):
    audit_session_id: str
    status: str
    security_score: int | None
    resources_scanned: int
    findings_by_severity: dict[str, int]


class AffectedResourceToolResult(BaseModel):
    finding_id: str
    service: str
    resource_id: str | None
    resource_arn: str | None
    title: str


class AffectedResourcesToolOutput(BaseModel):
    resources: list[AffectedResourceToolResult]
    total: int
