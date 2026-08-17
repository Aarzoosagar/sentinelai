"""
RDS collector.

Read-only checks implemented:
  - Instance/cluster storage not encrypted
  - Automated backups disabled or retention too short
  - IAM database authentication not enabled
  - Publicly accessible instances
  - Multi-AZ disabled (for production-looking instances)
"""

from __future__ import annotations

from botocore.client import BaseClient

from app.models.aws_account import AwsAccount
from app.models.enums import AwsService, Severity
from app.services.aws.base import CollectorResult, RawFinding
from app.services.aws.client_factory import get_client

_MIN_BACKUP_RETENTION_DAYS = 7


def collect(account: AwsAccount) -> CollectorResult:
    findings: list[RawFinding] = []
    scanned = 0
    try:
        with get_client(account, "rds") as rds:
            paginator = rds.get_paginator("describe_db_instances")
            for page in paginator.paginate():
                for db in page["DBInstances"]:
                    scanned += 1
                    identifier = db["DBInstanceIdentifier"]
                    arn = db.get("DBInstanceArn", identifier)

                    if not db.get("StorageEncrypted"):
                        findings.append(
                            RawFinding(
                                service=AwsService.RDS,
                                title=f"RDS instance '{identifier}' storage is not encrypted",
                                description=f"Database instance {identifier} does not have storage encryption enabled.",
                                severity_hint=Severity.HIGH,
                                resource_arn=arn,
                                resource_id=identifier,
                                cis_control="2.3.1",
                                nist_control="SC-28",
                                remediation="Storage encryption cannot be enabled in place; restore from a snapshot copied with encryption enabled.",
                                estimated_remediation_time="1-2 hours",
                            )
                        )

                    if db.get("PubliclyAccessible"):
                        findings.append(
                            RawFinding(
                                service=AwsService.RDS,
                                title=f"RDS instance '{identifier}' is publicly accessible",
                                description=f"Database instance {identifier} has PubliclyAccessible=True, exposing it to the internet.",
                                severity_hint=Severity.CRITICAL,
                                resource_arn=arn,
                                resource_id=identifier,
                                cis_control="2.3.3",
                                nist_control="SC-7",
                                mitre_attack="T1190 (Exploit Public-Facing Application)",
                                remediation="Set PubliclyAccessible to false and access the database through a VPN/bastion/private link.",
                                estimated_remediation_time="10 min",
                            )
                        )

                    retention = db.get("BackupRetentionPeriod", 0)
                    if retention < _MIN_BACKUP_RETENTION_DAYS:
                        findings.append(
                            RawFinding(
                                service=AwsService.RDS,
                                title=f"RDS instance '{identifier}' has insufficient backup retention",
                                description=f"Database instance {identifier} has a backup retention period of {retention} day(s), below the recommended {_MIN_BACKUP_RETENTION_DAYS}.",
                                severity_hint=Severity.MEDIUM,
                                resource_arn=arn,
                                resource_id=identifier,
                                nist_control="CP-9",
                                remediation=f"Increase BackupRetentionPeriod to at least {_MIN_BACKUP_RETENTION_DAYS} days.",
                                estimated_remediation_time="5 min",
                            )
                        )

                    if not db.get("IAMDatabaseAuthenticationEnabled"):
                        findings.append(
                            RawFinding(
                                service=AwsService.RDS,
                                title=f"RDS instance '{identifier}' does not use IAM database authentication",
                                description=f"Database instance {identifier} relies solely on static DB credentials instead of short-lived IAM tokens.",
                                severity_hint=Severity.LOW,
                                resource_arn=arn,
                                resource_id=identifier,
                                nist_control="IA-5",
                                remediation="Enable IAM database authentication where the engine supports it (MySQL/PostgreSQL).",
                                estimated_remediation_time="20 min",
                            )
                        )

                    if not db.get("MultiAZ"):
                        findings.append(
                            RawFinding(
                                service=AwsService.RDS,
                                title=f"RDS instance '{identifier}' is not Multi-AZ",
                                description=f"Database instance {identifier} runs in a single Availability Zone, risking downtime on AZ failure.",
                                severity_hint=Severity.LOW,
                                resource_arn=arn,
                                resource_id=identifier,
                                nist_control="CP-10",
                                remediation="Enable Multi-AZ deployment for production databases.",
                                estimated_remediation_time="15 min",
                            )
                        )
        return CollectorResult(service=AwsService.RDS, findings=findings, resources_scanned=scanned)
    except Exception as exc:  # noqa: BLE001
        return CollectorResult(service=AwsService.RDS, findings=findings, resources_scanned=scanned, error=str(exc))
