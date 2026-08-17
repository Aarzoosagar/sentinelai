"""
Builds boto3 clients for a connected AwsAccount and hard-enforces the
read-only invariant at the SDK level — not just by convention.

Two auth paths:
  - AssumeRole (preferred): sts.assume_role(role_arn, external_id) with a
    short-lived session, no secrets ever stored.
  - Static access keys (fallback): decrypted only in-memory for the
    duration of the boto3 session construction, never logged.

READ-ONLY ENFORCEMENT
----------------------
Every client produced here has a botocore `before-parameter-build` event
handler attached that inspects the operation name and raises before any
mutating call can leave the process. This is a defense-in-depth backstop
in addition to the fact that collector code only ever calls Describe/Get/
List/Head operations, and in addition to the IAM policy itself being
scoped to `ReadOnlyAccess` (see README).
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from typing import Iterator

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from app.core.security import decrypt_secret
from app.models.aws_account import AwsAccount
from app.models.enums import AwsAuthMethod

# Operation name prefixes considered safe (read-only). Anything else is
# blocked. This intentionally denies-by-default rather than trying to
# enumerate every mutating verb.
_READ_ONLY_PREFIXES = ("Describe", "Get", "List", "Head", "Lookup", "Search", "GenerateCredentialReport")

_ASSUME_ROLE_SESSION_NAME = "SentinelAI-ReadOnlyAudit"


class WriteOperationBlocked(Exception):
    """Raised if collector code (or a bug) attempts a mutating AWS call."""


def _block_non_read_operations(params, model, **kwargs):  # noqa: ANN001 - botocore event signature
    operation_name = model.name
    if not operation_name.startswith(_READ_ONLY_PREFIXES):
        raise WriteOperationBlocked(
            f"SentinelAI is read-only: blocked attempted call to '{operation_name}'"
        )
    return params


def _attach_read_only_guard(client: BaseClient) -> BaseClient:
    service_name = client.meta.service_model.service_name
    client.meta.events.register(f"before-parameter-build.{service_name}.*", _block_non_read_operations)
    return client


def _build_boto3_session(account: AwsAccount) -> boto3.Session:
    if account.auth_method == AwsAuthMethod.ASSUME_ROLE:
        if not account.role_arn:
            raise ValueError("AWS account is configured for AssumeRole but has no role_arn")
        sts = boto3.client("sts", region_name=account.region)
        assume_kwargs = {
            "RoleArn": account.role_arn,
            "RoleSessionName": _ASSUME_ROLE_SESSION_NAME,
            "DurationSeconds": 3600,
        }
        if account.external_id:
            assume_kwargs["ExternalId"] = account.external_id
        response = sts.assume_role(**assume_kwargs)
        creds = response["Credentials"]
        return boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=account.region,
        )

    # Static access-key fallback
    if not account.encrypted_access_key_id or not account.encrypted_secret_access_key:
        raise ValueError("AWS account is configured for access keys but none are stored")
    access_key_id = decrypt_secret(account.encrypted_access_key_id)
    secret_access_key = decrypt_secret(account.encrypted_secret_access_key)
    return boto3.Session(
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=account.region,
    )


@contextmanager
def get_client(account: AwsAccount, service_name: str, region: str | None = None) -> Iterator[BaseClient]:
    """Yield a read-only-guarded boto3 client for the given service."""
    session = _build_boto3_session(account)
    client = session.client(service_name, region_name=region or account.region)
    yield _attach_read_only_guard(client)


def validate_account(account: AwsAccount) -> tuple[bool, str | None, str | None]:
    """
    Calls sts:GetCallerIdentity to confirm the stored credentials actually
    work. Returns (is_valid, caller_arn, error_message).
    """
    try:
        with get_client(account, "sts") as sts:
            identity = sts.get_caller_identity()
            return True, identity.get("Arn"), None
    except WriteOperationBlocked as exc:
        return False, None, str(exc)
    except ClientError as exc:
        return False, None, exc.response.get("Error", {}).get("Message", str(exc))
    except Exception as exc:  # noqa: BLE001 - surface any auth/config error to the user
        return False, None, str(exc)


def list_enabled_regions(account: AwsAccount) -> list[str]:
    """Used by CloudTrail's multi-region check."""
    with get_client(account, "ec2") as ec2:
        response = ec2.describe_regions(AllRegions=False)
        return [r["RegionName"] for r in response.get("Regions", [])]


_ARN_ACCOUNT_ID_RE = re.compile(r"^\d{12}$")


def is_valid_account_id(account_id: str) -> bool:
    return bool(_ARN_ACCOUNT_ID_RE.match(account_id))
