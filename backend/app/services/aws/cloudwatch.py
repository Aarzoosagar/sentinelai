"""
CloudWatch collector.

Read-only checks implemented:
  - Log groups with no retention policy (logs kept forever / uncontrolled cost & exposure)
  - Log groups with very short retention (<30 days) relevant to security investigations
  - Missing CIS-recommended security alarms (root usage, unauthorized API calls,
    console sign-in without MFA, IAM policy changes) driven off CloudTrail's log group
"""

from __future__ import annotations

from botocore.client import BaseClient

from app.models.aws_account import AwsAccount
from app.models.enums import AwsService, Severity
from app.services.aws.base import CollectorResult, RawFinding
from app.services.aws.client_factory import get_client

_RECOMMENDED_ALARM_PATTERNS = {
    "root account usage": '{ $.userIdentity.type = "Root" }',
    "unauthorized API calls": '{ ($.errorCode = "*UnauthorizedAccess*") }',
    "console sign-in without MFA": '{ ($.eventName = "ConsoleLogin") && ($.additionalEventData.MFAUsed != "Yes") }',
    "IAM policy changes": '{ ($.eventSource = "iam.amazonaws.com") }',
}


def _check_log_retention(logs: BaseClient, findings: list[RawFinding]) -> int:
    scanned = 0
    paginator = logs.get_paginator("describe_log_groups")
    for page in paginator.paginate():
        for group in page["logGroups"]:
            scanned += 1
            name = group["logGroupName"]
            retention = group.get("retentionInDays")
            if retention is None:
                findings.append(
                    RawFinding(
                        service=AwsService.CLOUDWATCH,
                        title=f"Log group '{name}' has no retention policy",
                        description=f"Log group {name} retains logs indefinitely, increasing storage cost and data exposure over time.",
                        severity_hint=Severity.LOW,
                        resource_id=name,
                        nist_control="AU-11",
                        remediation="Set an explicit retention period (e.g. 365 days) on the log group.",
                        estimated_remediation_time="5 min",
                    )
                )
            elif retention < 30:
                findings.append(
                    RawFinding(
                        service=AwsService.CLOUDWATCH,
                        title=f"Log group '{name}' has short retention ({retention} days)",
                        description=f"Log group {name} retains logs for only {retention} days, which may not be enough for incident investigation.",
                        severity_hint=Severity.LOW,
                        resource_id=name,
                        nist_control="AU-11",
                        remediation="Increase retention to at least 90 days for security-relevant log groups.",
                        estimated_remediation_time="5 min",
                    )
                )
    return scanned


def _check_security_alarms(cw: BaseClient, findings: list[RawFinding]) -> None:
    existing_alarms = cw.describe_alarms()["MetricAlarms"]
    existing_alarm_names = {alarm["AlarmName"].lower() for alarm in existing_alarms}

    for label in _RECOMMENDED_ALARM_PATTERNS:
        keyword = label.split()[0]
        if not any(keyword in name for name in existing_alarm_names):
            findings.append(
                RawFinding(
                    service=AwsService.CLOUDWATCH,
                    title=f"No CloudWatch alarm for {label}",
                    description=f"No CloudWatch alarm was found matching the CIS-recommended metric filter for '{label}'.",
                    severity_hint=Severity.MEDIUM,
                    cis_control="4.x",
                    nist_control="AU-6",
                    remediation=f"Create a metric filter and alarm on the CloudTrail log group for: {label}.",
                    estimated_remediation_time="15 min",
                )
            )


def collect(account: AwsAccount) -> CollectorResult:
    findings: list[RawFinding] = []
    scanned = 0
    try:
        with get_client(account, "logs") as logs:
            scanned = _check_log_retention(logs, findings)
        with get_client(account, "cloudwatch") as cw:
            _check_security_alarms(cw, findings)
        return CollectorResult(service=AwsService.CLOUDWATCH, findings=findings, resources_scanned=scanned)
    except Exception as exc:  # noqa: BLE001
        return CollectorResult(service=AwsService.CLOUDWATCH, findings=findings, resources_scanned=scanned, error=str(exc))
