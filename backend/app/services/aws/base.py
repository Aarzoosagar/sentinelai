"""
Shared types for AWS collector modules.

Every collector (iam.py, s3.py, ec2.py, ...) returns a list of `RawFinding`
objects — normalized, framework-agnostic security observations. The Risk
Engine (services/risk/) later turns these into persisted `Finding` +
`RiskScore` rows with numeric scoring. Keeping this boundary means a
collector never touches the database and the risk engine never touches
boto3.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import AwsService, Severity


@dataclass
class RawFinding:
    service: AwsService
    title: str
    description: str
    severity_hint: Severity
    remediation: str
    resource_arn: str | None = None
    resource_id: str | None = None
    region: str | None = None
    cis_control: str | None = None
    nist_control: str | None = None
    mitre_attack: str | None = None
    estimated_remediation_time: str | None = None
    references: list[str] = field(default_factory=list)


@dataclass
class CollectorResult:
    service: AwsService
    findings: list[RawFinding]
    resources_scanned: int
    error: str | None = None
