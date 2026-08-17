"""
IAM collector.

Read-only IAM checks implemented here:
  - Users/roles with AdministratorAccess attached
  - Wildcard ("*":"*") permissions in managed or inline policies
  - Inline policies present on users (harder to audit than managed policies)
  - IAM users without MFA enabled
  - Access keys older than 90 days
  - Root account usage in the last 90 days
  - Account password policy weaker than CIS baseline
  - Users with no console/API activity in 90+ days (unused users)

All calls are Describe/Get/List/Generate-prefixed and therefore pass the
read-only guard in client_factory.py.
"""

from __future__ import annotations

import csv
import io
import time
from datetime import datetime, timedelta, timezone

from botocore.client import BaseClient

from app.models.aws_account import AwsAccount
from app.models.enums import AwsService, Severity
from app.services.aws.base import CollectorResult, RawFinding
from app.services.aws.client_factory import get_client

_UNUSED_THRESHOLD_DAYS = 90
_OLD_KEY_THRESHOLD_DAYS = 90


def _has_wildcard_statement(policy_document: dict) -> bool:
    statements = policy_document.get("Statement", [])
    if isinstance(statements, dict):
        statements = [statements]
    for stmt in statements:
        if stmt.get("Effect") != "Allow":
            continue
        actions = stmt.get("Action", [])
        resources = stmt.get("Resource", [])
        actions = [actions] if isinstance(actions, str) else actions
        resources = [resources] if isinstance(resources, str) else resources
        if "*" in actions and "*" in resources:
            return True
    return False


def _check_admin_and_wildcard_policies(iam: BaseClient, findings: list[RawFinding]) -> int:
    scanned = 0
    paginator = iam.get_paginator("list_users")
    for page in paginator.paginate():
        for user in page["Users"]:
            scanned += 1
            username = user["UserName"]
            arn = user["Arn"]

            attached = iam.list_attached_user_policies(UserName=username)["AttachedPolicies"]
            for policy in attached:
                if policy["PolicyName"] == "AdministratorAccess":
                    findings.append(
                        RawFinding(
                            service=AwsService.IAM,
                            title=f"IAM user '{username}' has AdministratorAccess",
                            description=(
                                f"The IAM user {username} has the AWS-managed "
                                "AdministratorAccess policy attached, granting "
                                "unrestricted access to every AWS service and resource "
                                "in this account."
                            ),
                            severity_hint=Severity.CRITICAL,
                            resource_arn=arn,
                            resource_id=username,
                            cis_control="1.16",
                            nist_control="AC-6",
                            mitre_attack="T1078 (Valid Accounts)",
                            remediation=(
                                "Remove AdministratorAccess and grant the minimum set of "
                                "permissions required, ideally through a role rather than "
                                "a long-lived user."
                            ),
                            estimated_remediation_time="15 min",
                            references=[
                                "https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html"
                            ],
                        )
                    )

                policy_doc = iam.get_policy_version(
                    PolicyArn=policy["PolicyArn"],
                    VersionId=iam.get_policy(PolicyArn=policy["PolicyArn"])["Policy"][
                        "DefaultVersionId"
                    ],
                )["PolicyVersion"]["Document"]
                if _has_wildcard_statement(policy_doc):
                    findings.append(
                        RawFinding(
                            service=AwsService.IAM,
                            title=f"Wildcard permissions on policy '{policy['PolicyName']}'",
                            description=(
                                f"Managed policy {policy['PolicyName']} attached to user "
                                f"{username} allows Action:'*' on Resource:'*'."
                            ),
                            severity_hint=Severity.HIGH,
                            resource_arn=policy["PolicyArn"],
                            resource_id=username,
                            cis_control="1.16",
                            nist_control="AC-6",
                            mitre_attack="T1078 (Valid Accounts)",
                            remediation="Scope the policy to specific actions and resources following least privilege.",
                            estimated_remediation_time="30 min",
                        )
                    )

            inline_names = iam.list_user_policies(UserName=username)["PolicyNames"]
            for inline_name in inline_names:
                findings.append(
                    RawFinding(
                        service=AwsService.IAM,
                        title=f"Inline policy on user '{username}'",
                        description=(
                            f"User {username} has inline policy '{inline_name}'. Inline "
                            "policies are harder to audit and reuse than managed policies."
                        ),
                        severity_hint=Severity.LOW,
                        resource_arn=arn,
                        resource_id=username,
                        cis_control="1.16",
                        remediation="Convert inline policies to customer-managed policies for centralized review.",
                        estimated_remediation_time="20 min",
                    )
                )
                doc = iam.get_user_policy(UserName=username, PolicyName=inline_name)["PolicyDocument"]
                if _has_wildcard_statement(doc):
                    findings.append(
                        RawFinding(
                            service=AwsService.IAM,
                            title=f"Wildcard permissions in inline policy '{inline_name}'",
                            description=(
                                f"Inline policy '{inline_name}' on user {username} allows "
                                "Action:'*' on Resource:'*'."
                            ),
                            severity_hint=Severity.HIGH,
                            resource_arn=arn,
                            resource_id=username,
                            cis_control="1.16",
                            nist_control="AC-6",
                            remediation="Scope the inline policy to specific actions and resources.",
                            estimated_remediation_time="30 min",
                        )
                    )

            mfa_devices = iam.list_mfa_devices(UserName=username)["MFADevices"]
            login_profile_exists = True
            try:
                iam.get_login_profile(UserName=username)
            except iam.exceptions.NoSuchEntityException:
                login_profile_exists = False
            if login_profile_exists and not mfa_devices:
                findings.append(
                    RawFinding(
                        service=AwsService.IAM,
                        title=f"MFA not enabled for user '{username}'",
                        description=(
                            f"IAM user {username} has console access but no MFA device "
                            "registered, leaving the account vulnerable to password compromise."
                        ),
                        severity_hint=Severity.HIGH,
                        resource_arn=arn,
                        resource_id=username,
                        cis_control="1.10",
                        nist_control="IA-2",
                        mitre_attack="T1078 (Valid Accounts)",
                        remediation="Enable a virtual or hardware MFA device for this user.",
                        estimated_remediation_time="10 min",
                    )
                )

            keys = iam.list_access_keys(UserName=username)["AccessKeyMetadata"]
            for key in keys:
                if key["Status"] != "Active":
                    continue
                age_days = (datetime.now(timezone.utc) - key["CreateDate"]).days
                if age_days > _OLD_KEY_THRESHOLD_DAYS:
                    findings.append(
                        RawFinding(
                            service=AwsService.IAM,
                            title=f"Access key for '{username}' is {age_days} days old",
                            description=(
                                f"Active access key {key['AccessKeyId']} for user {username} "
                                f"was created {age_days} days ago and has not been rotated."
                            ),
                            severity_hint=Severity.MEDIUM,
                            resource_arn=arn,
                            resource_id=key["AccessKeyId"],
                            cis_control="1.14",
                            nist_control="IA-5",
                            remediation="Rotate the access key and update any applications using it.",
                            estimated_remediation_time="20 min",
                        )
                    )
    return scanned


def _check_password_policy(iam: BaseClient, findings: list[RawFinding]) -> None:
    try:
        policy = iam.get_account_password_policy()["PasswordPolicy"]
    except iam.exceptions.NoSuchEntityException:
        findings.append(
            RawFinding(
                service=AwsService.IAM,
                title="No account password policy configured",
                description="This account has no IAM password policy, so default (weak) rules apply.",
                severity_hint=Severity.MEDIUM,
                cis_control="1.5-1.11",
                nist_control="IA-5",
                remediation="Configure a password policy requiring length >=14, complexity, rotation, and reuse prevention.",
                estimated_remediation_time="10 min",
            )
        )
        return

    issues = []
    if policy.get("MinimumPasswordLength", 0) < 14:
        issues.append("minimum length is below 14 characters")
    if not policy.get("RequireSymbols"):
        issues.append("symbols are not required")
    if not policy.get("RequireNumbers"):
        issues.append("numbers are not required")
    if policy.get("PasswordReusePrevention", 0) < 24:
        issues.append("password reuse prevention is below 24")
    if not policy.get("ExpirePasswords") or policy.get("MaxPasswordAge", 999) > 90:
        issues.append("passwords do not expire within 90 days")

    if issues:
        findings.append(
            RawFinding(
                service=AwsService.IAM,
                title="Account password policy does not meet CIS baseline",
                description="Password policy gaps: " + "; ".join(issues) + ".",
                severity_hint=Severity.MEDIUM,
                cis_control="1.5-1.11",
                nist_control="IA-5",
                remediation="Update the account password policy to meet CIS AWS Foundations length, complexity, and rotation requirements.",
                estimated_remediation_time="10 min",
            )
        )


def _check_root_usage_and_unused_users(iam: BaseClient, findings: list[RawFinding]) -> None:
    # Credential report gives root last-used + per-user last-activity data in one call.
    for _ in range(10):
        state = iam.generate_credential_report()["State"]
        if state == "COMPLETE":
            break
        time.sleep(1)
    else:
        return  # report generation timed out; skip rather than block the whole audit

    report_csv = iam.get_credential_report()["Content"]
    rows = list(csv.DictReader(io.StringIO(report_csv.decode("utf-8") if isinstance(report_csv, (bytes, bytearray)) else report_csv)))

    now = datetime.now(timezone.utc)
    for row in rows:
        user = row["user"]
        if user == "<root_account>":
            last_used_fields = [
                row.get("password_last_used", "N/A"),
                row.get("access_key_1_last_used_date", "N/A"),
                row.get("access_key_2_last_used_date", "N/A"),
            ]
            for value in last_used_fields:
                if value and value not in ("N/A", "no_information", "not_supported"):
                    try:
                        last_used = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                    if (now - last_used).days <= _UNUSED_THRESHOLD_DAYS:
                        findings.append(
                            RawFinding(
                                service=AwsService.IAM,
                                title="Root account has been used recently",
                                description=(
                                    f"The AWS root account shows activity within the last "
                                    f"{_UNUSED_THRESHOLD_DAYS} days ({value}). The root "
                                    "account should never be used for daily operations."
                                ),
                                severity_hint=Severity.CRITICAL,
                                resource_id="root",
                                cis_control="1.7",
                                nist_control="AC-6",
                                mitre_attack="T1078.004 (Cloud Accounts)",
                                remediation="Stop using the root account; create IAM users/roles for all activity and enable MFA on root.",
                                estimated_remediation_time="N/A — process change",
                            )
                        )
                    break
            continue

        password_last_used = row.get("password_last_used", "N/A")
        key1_last_used = row.get("access_key_1_last_used_date", "N/A")
        key2_last_used = row.get("access_key_2_last_used_date", "N/A")
        all_unused_or_na = all(
            v in ("N/A", "no_information", "not_supported") or v == ""
            for v in (password_last_used, key1_last_used, key2_last_used)
        )
        if all_unused_or_na:
            continue  # never had credentials used at all — not flagged as "unused", just new

        most_recent = None
        for v in (password_last_used, key1_last_used, key2_last_used):
            if v and v not in ("N/A", "no_information", "not_supported"):
                try:
                    dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                    if most_recent is None or dt > most_recent:
                        most_recent = dt
                except ValueError:
                    continue
        if most_recent and (now - most_recent).days > _UNUSED_THRESHOLD_DAYS:
            findings.append(
                RawFinding(
                    service=AwsService.IAM,
                    title=f"IAM user '{user}' unused for over {_UNUSED_THRESHOLD_DAYS} days",
                    description=(
                        f"User {user} has had no console login or API activity since "
                        f"{most_recent.date().isoformat()}."
                    ),
                    severity_hint=Severity.LOW,
                    resource_id=user,
                    cis_control="1.12",
                    nist_control="AC-2",
                    remediation="Deactivate or remove this IAM user if it is no longer needed.",
                    estimated_remediation_time="10 min",
                )
            )


def collect(account: AwsAccount) -> CollectorResult:
    findings: list[RawFinding] = []
    try:
        with get_client(account, "iam") as iam:
            scanned = _check_admin_and_wildcard_policies(iam, findings)
            _check_password_policy(iam, findings)
            _check_root_usage_and_unused_users(iam, findings)
        return CollectorResult(service=AwsService.IAM, findings=findings, resources_scanned=scanned)
    except Exception as exc:  # noqa: BLE001 - one service failing must not abort the whole audit
        return CollectorResult(service=AwsService.IAM, findings=findings, resources_scanned=0, error=str(exc))
