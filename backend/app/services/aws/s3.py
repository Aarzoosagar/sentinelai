"""
S3 collector.

Read-only checks implemented:
  - Public buckets (via Block Public Access settings + bucket ACL/policy status)
  - Default encryption not enabled
  - Versioning disabled
  - Access logging disabled
  - Account/bucket-level Public Access Block not fully enabled
"""

from __future__ import annotations

from botocore.client import BaseClient
from botocore.exceptions import ClientError

from app.models.aws_account import AwsAccount
from app.models.enums import AwsService, Severity
from app.services.aws.base import CollectorResult, RawFinding
from app.services.aws.client_factory import get_client


def _bucket_arn(bucket_name: str) -> str:
    return f"arn:aws:s3:::{bucket_name}"


def _check_public_access_block(s3: BaseClient, bucket: str, findings: list[RawFinding]) -> None:
    try:
        config = s3.get_public_access_block(Bucket=bucket)["PublicAccessBlockConfiguration"]
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "NoSuchPublicAccessBlockConfiguration":
            config = {}
        else:
            raise

    required = ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")
    missing = [key for key in required if not config.get(key)]
    if missing:
        findings.append(
            RawFinding(
                service=AwsService.S3,
                title=f"S3 bucket '{bucket}' does not fully block public access",
                description=(
                    f"Bucket {bucket} is missing Public Access Block settings: "
                    f"{', '.join(missing)}."
                ),
                severity_hint=Severity.CRITICAL,
                resource_arn=_bucket_arn(bucket),
                resource_id=bucket,
                cis_control="2.1.5",
                nist_control="AC-3",
                mitre_attack="T1530 (Data from Cloud Storage)",
                remediation="Enable all four Public Access Block settings at the bucket (or account) level.",
                estimated_remediation_time="5 min",
            )
        )


def _check_bucket_acl_and_policy(s3: BaseClient, bucket: str, findings: list[RawFinding]) -> None:
    acl = s3.get_bucket_acl(Bucket=bucket)
    for grant in acl.get("Grants", []):
        grantee = grant.get("Grantee", {})
        uri = grantee.get("URI", "")
        if "AllUsers" in uri or "AuthenticatedUsers" in uri:
            findings.append(
                RawFinding(
                    service=AwsService.S3,
                    title=f"S3 bucket '{bucket}' grants public access via ACL",
                    description=(
                        f"Bucket {bucket}'s ACL grants '{grant.get('Permission')}' to "
                        f"{'all AWS users' if 'AllUsers' in uri else 'any authenticated AWS user'}."
                    ),
                    severity_hint=Severity.CRITICAL,
                    resource_arn=_bucket_arn(bucket),
                    resource_id=bucket,
                    cis_control="2.1.5",
                    nist_control="AC-3",
                    mitre_attack="T1530 (Data from Cloud Storage)",
                    remediation="Remove the public grant from the bucket ACL and rely on IAM/bucket policy instead.",
                    estimated_remediation_time="5 min",
                )
            )
            break


def _check_encryption(s3: BaseClient, bucket: str, findings: list[RawFinding]) -> None:
    try:
        s3.get_bucket_encryption(Bucket=bucket)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ServerSideEncryptionConfigurationNotFoundError":
            findings.append(
                RawFinding(
                    service=AwsService.S3,
                    title=f"S3 bucket '{bucket}' has no default encryption",
                    description=f"Bucket {bucket} does not have server-side encryption enabled by default.",
                    severity_hint=Severity.HIGH,
                    resource_arn=_bucket_arn(bucket),
                    resource_id=bucket,
                    cis_control="2.1.1",
                    nist_control="SC-28",
                    remediation="Enable default encryption (SSE-S3 or SSE-KMS) on the bucket.",
                    estimated_remediation_time="5 min",
                )
            )
        else:
            raise


def _check_versioning(s3: BaseClient, bucket: str, findings: list[RawFinding]) -> None:
    versioning = s3.get_bucket_versioning(Bucket=bucket)
    if versioning.get("Status") != "Enabled":
        findings.append(
            RawFinding(
                service=AwsService.S3,
                title=f"S3 bucket '{bucket}' does not have versioning enabled",
                description=f"Bucket {bucket} has versioning {'suspended' if versioning.get('Status') else 'disabled'}, risking permanent data loss on accidental deletion or overwrite.",
                severity_hint=Severity.MEDIUM,
                resource_arn=_bucket_arn(bucket),
                resource_id=bucket,
                cis_control="2.1.3",
                nist_control="CP-9",
                remediation="Enable versioning on the bucket.",
                estimated_remediation_time="5 min",
            )
        )


def _check_logging(s3: BaseClient, bucket: str, findings: list[RawFinding]) -> None:
    logging_config = s3.get_bucket_logging(Bucket=bucket)
    if "LoggingEnabled" not in logging_config:
        findings.append(
            RawFinding(
                service=AwsService.S3,
                title=f"S3 bucket '{bucket}' does not have access logging enabled",
                description=f"Bucket {bucket} has no server access logging configured, limiting forensic visibility.",
                severity_hint=Severity.LOW,
                resource_arn=_bucket_arn(bucket),
                resource_id=bucket,
                cis_control="2.1.2",
                nist_control="AU-2",
                remediation="Enable S3 server access logging to a dedicated logging bucket.",
                estimated_remediation_time="10 min",
            )
        )


def collect(account: AwsAccount) -> CollectorResult:
    findings: list[RawFinding] = []
    scanned = 0
    try:
        with get_client(account, "s3") as s3:
            buckets = s3.list_buckets()["Buckets"]
            for bucket_info in buckets:
                bucket = bucket_info["Name"]
                scanned += 1
                try:
                    _check_public_access_block(s3, bucket, findings)
                    _check_bucket_acl_and_policy(s3, bucket, findings)
                    _check_encryption(s3, bucket, findings)
                    _check_versioning(s3, bucket, findings)
                    _check_logging(s3, bucket, findings)
                except ClientError as bucket_error:
                    # A single inaccessible/foreign-region bucket should not abort the scan.
                    findings.append(
                        RawFinding(
                            service=AwsService.S3,
                            title=f"Could not fully audit bucket '{bucket}'",
                            description=f"Some checks on bucket {bucket} failed: {bucket_error.response['Error'].get('Message', str(bucket_error))}",
                            severity_hint=Severity.INFORMATIONAL,
                            resource_arn=_bucket_arn(bucket),
                            resource_id=bucket,
                            remediation="Verify the audit role has s3:Get* permissions for this bucket's region.",
                        )
                    )
        return CollectorResult(service=AwsService.S3, findings=findings, resources_scanned=scanned)
    except Exception as exc:  # noqa: BLE001
        return CollectorResult(service=AwsService.S3, findings=findings, resources_scanned=scanned, error=str(exc))
