"""
Orchestrates all nine read-only AWS collectors for a single audit run.

This module is intentionally thin: it knows nothing about the database or
risk scoring. It just runs every collector against one AwsAccount and
returns the combined raw findings + a per-service error map so the caller
(services/risk or the audit API) can decide how to persist/report partial
failures.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.aws_account import AwsAccount
from app.models.enums import AwsService
from app.services.aws import cloudtrail, cloudwatch, ec2, iam, kms, lambda_svc, rds, s3, secrets_manager
from app.services.aws.base import CollectorResult, RawFinding

_COLLECTORS = {
    AwsService.IAM: iam.collect,
    AwsService.S3: s3.collect,
    AwsService.EC2: ec2.collect,
    AwsService.CLOUDTRAIL: cloudtrail.collect,
    AwsService.CLOUDWATCH: cloudwatch.collect,
    AwsService.LAMBDA: lambda_svc.collect,
    AwsService.RDS: rds.collect,
    AwsService.KMS: kms.collect,
    AwsService.SECRETS_MANAGER: secrets_manager.collect,
}


@dataclass
class AuditCollectionResult:
    findings: list[RawFinding]
    resources_scanned: int
    service_errors: dict[str, str]
    services_completed: list[str]


def run_full_audit(account: AwsAccount) -> AuditCollectionResult:
    """
    Runs every collector sequentially against the given AWS account.
    A failure in one service (e.g. missing permission for RDS) is captured
    per-service and does not prevent the other eight from running.
    """
    all_findings: list[RawFinding] = []
    total_scanned = 0
    service_errors: dict[str, str] = {}
    services_completed: list[str] = []

    for service, collector_fn in _COLLECTORS.items():
        result: CollectorResult = collector_fn(account)
        all_findings.extend(result.findings)
        total_scanned += result.resources_scanned
        services_completed.append(service.value)
        if result.error:
            service_errors[service.value] = result.error

    return AuditCollectionResult(
        findings=all_findings,
        resources_scanned=total_scanned,
        service_errors=service_errors,
        services_completed=services_completed,
    )


def run_single_service(account: AwsAccount, service: AwsService) -> CollectorResult:
    """Used by the Audit Wizard's scoped-audit option (single-service re-scan)."""
    collector_fn = _COLLECTORS[service]
    return collector_fn(account)
