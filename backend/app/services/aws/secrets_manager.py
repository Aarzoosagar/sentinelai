"""
Secrets Manager collector.

Read-only checks implemented:
  - Secrets without rotation enabled
  - Secrets that have not been accessed/rotated in a long time (likely unused)
  - Secrets scheduled for deletion (informational)
"""

from __future__ import annotations

from datetime import datetime, timezone

from botocore.client import BaseClient

from app.models.aws_account import AwsAccount
from app.models.enums import AwsService, Severity
from app.services.aws.base import CollectorResult, RawFinding
from app.services.aws.client_factory import get_client

_STALE_THRESHOLD_DAYS = 180


def collect(account: AwsAccount) -> CollectorResult:
    findings: list[RawFinding] = []
    scanned = 0
    try:
        with get_client(account, "secretsmanager") as sm:
            paginator = sm.get_paginator("list_secrets")
            now = datetime.now(timezone.utc)
            for page in paginator.paginate():
                for secret in page["SecretList"]:
                    scanned += 1
                    name = secret["Name"]
                    arn = secret["ARN"]

                    if secret.get("DeletedDate"):
                        findings.append(
                            RawFinding(
                                service=AwsService.SECRETS_MANAGER,
                                title=f"Secret '{name}' is scheduled for deletion",
                                description=f"Secret {name} is pending deletion. Confirm this is intentional before the recovery window closes.",
                                severity_hint=Severity.INFORMATIONAL,
                                resource_arn=arn,
                                resource_id=name,
                                remediation="Restore the secret if deletion was unintentional (secretsmanager:RestoreSecret).",
                            )
                        )
                        continue

                    if not secret.get("RotationEnabled"):
                        findings.append(
                            RawFinding(
                                service=AwsService.SECRETS_MANAGER,
                                title=f"Secret '{name}' does not have automatic rotation enabled",
                                description=f"Secret {name} is not configured for automatic rotation, increasing the blast radius if it is ever leaked.",
                                severity_hint=Severity.MEDIUM,
                                resource_arn=arn,
                                resource_id=name,
                                cis_control="2.9",
                                nist_control="IA-5",
                                remediation="Configure automatic rotation with a rotation Lambda function.",
                                estimated_remediation_time="30 min",
                            )
                        )

                    last_changed = secret.get("LastChangedDate")
                    last_accessed = secret.get("LastAccessedDate")
                    reference_date = last_accessed or last_changed
                    if reference_date and (now - reference_date).days > _STALE_THRESHOLD_DAYS:
                        findings.append(
                            RawFinding(
                                service=AwsService.SECRETS_MANAGER,
                                title=f"Secret '{name}' appears unused",
                                description=f"Secret {name} has not been accessed or changed in over {_STALE_THRESHOLD_DAYS} days.",
                                severity_hint=Severity.LOW,
                                resource_arn=arn,
                                resource_id=name,
                                remediation="Verify whether this secret is still needed; delete it if it is orphaned.",
                                estimated_remediation_time="10 min",
                            )
                        )
        return CollectorResult(service=AwsService.SECRETS_MANAGER, findings=findings, resources_scanned=scanned)
    except Exception as exc:  # noqa: BLE001
        return CollectorResult(service=AwsService.SECRETS_MANAGER, findings=findings, resources_scanned=scanned, error=str(exc))
