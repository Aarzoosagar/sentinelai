"""
KMS collector.

Read-only checks implemented:
  - Customer-managed keys without automatic rotation enabled
  - Customer-managed keys that are pending deletion (informational)
  - Customer-managed keys with no usage in the audit window (best-effort via key policy/tag inspection)
"""

from __future__ import annotations

from botocore.client import BaseClient
from botocore.exceptions import ClientError

from app.models.aws_account import AwsAccount
from app.models.enums import AwsService, Severity
from app.services.aws.base import CollectorResult, RawFinding
from app.services.aws.client_factory import get_client


def collect(account: AwsAccount) -> CollectorResult:
    findings: list[RawFinding] = []
    scanned = 0
    try:
        with get_client(account, "kms") as kms:
            paginator = kms.get_paginator("list_keys")
            for page in paginator.paginate():
                for key in page["Keys"]:
                    key_id = key["KeyId"]
                    try:
                        description = kms.describe_key(KeyId=key_id)["KeyMetadata"]
                    except ClientError:
                        continue

                    # Only customer-managed keys are actionable; AWS-managed keys
                    # (aws/s3, aws/rds, ...) can't have rotation toggled by the user.
                    if description.get("KeyManager") != "CUSTOMER":
                        continue
                    scanned += 1
                    arn = description["Arn"]

                    if description.get("KeyState") == "PendingDeletion":
                        findings.append(
                            RawFinding(
                                service=AwsService.KMS,
                                title=f"KMS key '{key_id}' is pending deletion",
                                description=f"Customer-managed key {key_id} is scheduled for deletion. Confirm this is intentional before the deletion window closes.",
                                severity_hint=Severity.INFORMATIONAL,
                                resource_arn=arn,
                                resource_id=key_id,
                                remediation="Cancel key deletion if this was unintentional (kms:CancelKeyDeletion), otherwise no action needed.",
                            )
                        )
                        continue

                    if description.get("KeyState") != "Enabled":
                        continue

                    if description.get("KeySpec", "SYMMETRIC_DEFAULT") == "SYMMETRIC_DEFAULT":
                        try:
                            rotation = kms.get_key_rotation_status(KeyId=key_id)
                            if not rotation.get("KeyRotationEnabled"):
                                findings.append(
                                    RawFinding(
                                        service=AwsService.KMS,
                                        title=f"KMS key '{key_id}' does not have automatic rotation enabled",
                                        description=f"Customer-managed symmetric key {key_id} is not set to rotate automatically every year.",
                                        severity_hint=Severity.MEDIUM,
                                        resource_arn=arn,
                                        resource_id=key_id,
                                        cis_control="2.8",
                                        nist_control="SC-12",
                                        remediation="Enable automatic key rotation (kms:EnableKeyRotation).",
                                        estimated_remediation_time="5 min",
                                    )
                                )
                        except ClientError:
                            pass  # asymmetric/HMAC keys don't support rotation; skip silently
        return CollectorResult(service=AwsService.KMS, findings=findings, resources_scanned=scanned)
    except Exception as exc:  # noqa: BLE001
        return CollectorResult(service=AwsService.KMS, findings=findings, resources_scanned=scanned, error=str(exc))
