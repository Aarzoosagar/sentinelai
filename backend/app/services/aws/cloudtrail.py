"""
CloudTrail collector.

Read-only checks implemented:
  - No trails configured at all
  - Trail not multi-region
  - Trail not encrypted with KMS
  - Log file validation disabled
  - Trail not actively logging (status check)
  - CloudWatch Logs integration missing (limits real-time visibility/retention)
"""

from __future__ import annotations

from botocore.client import BaseClient

from app.models.aws_account import AwsAccount
from app.models.enums import AwsService, Severity
from app.services.aws.base import CollectorResult, RawFinding
from app.services.aws.client_factory import get_client


def collect(account: AwsAccount) -> CollectorResult:
    findings: list[RawFinding] = []
    scanned = 0
    try:
        with get_client(account, "cloudtrail") as ct:
            trails = ct.describe_trails(includeShadowTrails=True)["trailList"]
            scanned = len(trails)

            if not trails:
                findings.append(
                    RawFinding(
                        service=AwsService.CLOUDTRAIL,
                        title="No CloudTrail trails configured",
                        description="This account has no CloudTrail trails, meaning API activity is not being recorded.",
                        severity_hint=Severity.CRITICAL,
                        cis_control="3.1",
                        nist_control="AU-2",
                        mitre_attack="T1562.008 (Disable Cloud Logs)",
                        remediation="Create a multi-region CloudTrail trail with log file validation and KMS encryption enabled.",
                        estimated_remediation_time="15 min",
                    )
                )
                return CollectorResult(service=AwsService.CLOUDTRAIL, findings=findings, resources_scanned=scanned)

            has_multi_region = any(t.get("IsMultiRegionTrail") for t in trails)
            if not has_multi_region:
                findings.append(
                    RawFinding(
                        service=AwsService.CLOUDTRAIL,
                        title="No multi-region CloudTrail trail",
                        description="None of the configured trails cover all regions, so activity in other regions may go unrecorded.",
                        severity_hint=Severity.HIGH,
                        cis_control="3.1",
                        nist_control="AU-2",
                        remediation="Enable 'IsMultiRegionTrail' on at least one trail.",
                        estimated_remediation_time="10 min",
                    )
                )

            for trail in trails:
                name = trail["Name"]
                arn = trail.get("TrailARN", name)

                status = ct.get_trail_status(Name=name)
                if not status.get("IsLogging"):
                    findings.append(
                        RawFinding(
                            service=AwsService.CLOUDTRAIL,
                            title=f"Trail '{name}' is not actively logging",
                            description=f"Trail {name} exists but logging is currently stopped.",
                            severity_hint=Severity.CRITICAL,
                            resource_arn=arn,
                            resource_id=name,
                            cis_control="3.1",
                            mitre_attack="T1562.008 (Disable Cloud Logs)",
                            remediation="Re-enable logging on this trail (StartLogging).",
                            estimated_remediation_time="5 min",
                        )
                    )

                if not trail.get("LogFileValidationEnabled"):
                    findings.append(
                        RawFinding(
                            service=AwsService.CLOUDTRAIL,
                            title=f"Log file validation disabled on trail '{name}'",
                            description=f"Trail {name} does not have log file integrity validation enabled, making tampering harder to detect.",
                            severity_hint=Severity.MEDIUM,
                            resource_arn=arn,
                            resource_id=name,
                            cis_control="3.2",
                            nist_control="AU-9",
                            remediation="Enable log file validation on the trail.",
                            estimated_remediation_time="5 min",
                        )
                    )

                if not trail.get("KmsKeyId"):
                    findings.append(
                        RawFinding(
                            service=AwsService.CLOUDTRAIL,
                            title=f"Trail '{name}' logs are not KMS-encrypted",
                            description=f"Trail {name} stores logs in S3 without SSE-KMS encryption configured.",
                            severity_hint=Severity.MEDIUM,
                            resource_arn=arn,
                            resource_id=name,
                            cis_control="3.7",
                            nist_control="SC-28",
                            remediation="Configure a customer-managed KMS key for this trail's log encryption.",
                            estimated_remediation_time="15 min",
                        )
                    )

                if not trail.get("CloudWatchLogsLogGroupArn"):
                    findings.append(
                        RawFinding(
                            service=AwsService.CLOUDTRAIL,
                            title=f"Trail '{name}' is not integrated with CloudWatch Logs",
                            description=f"Trail {name} does not deliver logs to CloudWatch Logs, limiting real-time alerting.",
                            severity_hint=Severity.LOW,
                            resource_arn=arn,
                            resource_id=name,
                            cis_control="3.4",
                            nist_control="AU-6",
                            remediation="Configure the trail to deliver logs to a CloudWatch Logs log group.",
                            estimated_remediation_time="10 min",
                        )
                    )

        return CollectorResult(service=AwsService.CLOUDTRAIL, findings=findings, resources_scanned=scanned)
    except Exception as exc:  # noqa: BLE001
        return CollectorResult(service=AwsService.CLOUDTRAIL, findings=findings, resources_scanned=scanned, error=str(exc))
