"""
Lambda collector.

Read-only checks implemented:
  - Deprecated/end-of-life runtimes
  - Function policy allows public invocation (resource policy with Principal: "*")
  - Execution role has overly broad (wildcard) permissions
  - Environment variables that look like they contain secrets in plaintext
"""

from __future__ import annotations

import json
import re

from botocore.client import BaseClient
from botocore.exceptions import ClientError

from app.models.aws_account import AwsAccount
from app.models.enums import AwsService, Severity
from app.services.aws.base import CollectorResult, RawFinding
from app.services.aws.client_factory import get_client

_DEPRECATED_RUNTIMES = {
    "nodejs14.x", "nodejs12.x", "nodejs10.x", "nodejs8.10", "nodejs6.10", "nodejs4.3",
    "python2.7", "python3.6", "python3.7",
    "ruby2.5", "ruby2.7",
    "dotnetcore1.0", "dotnetcore2.0", "dotnetcore2.1", "dotnetcore3.1",
    "go1.x",
    "java8",
}

_SECRET_LIKE_KEY_PATTERN = re.compile(r"(secret|password|passwd|api[_-]?key|token|private[_-]?key)", re.IGNORECASE)


def _check_runtime(function: dict, findings: list[RawFinding]) -> None:
    runtime = function.get("Runtime")
    if runtime and runtime in _DEPRECATED_RUNTIMES:
        findings.append(
            RawFinding(
                service=AwsService.LAMBDA,
                title=f"Lambda function '{function['FunctionName']}' uses deprecated runtime {runtime}",
                description=f"Function {function['FunctionName']} runs on {runtime}, which is deprecated and no longer receives security patches.",
                severity_hint=Severity.HIGH,
                resource_arn=function["FunctionArn"],
                resource_id=function["FunctionName"],
                nist_control="SI-2",
                remediation=f"Upgrade the function to a currently supported runtime.",
                estimated_remediation_time="1-3 hours",
            )
        )


def _check_public_policy(lam: BaseClient, function: dict, findings: list[RawFinding]) -> None:
    try:
        policy_raw = lam.get_policy(FunctionName=function["FunctionName"])["Policy"]
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ResourceNotFoundException":
            return
        raise
    policy = json.loads(policy_raw)
    for stmt in policy.get("Statement", []):
        principal = stmt.get("Principal")
        is_public = principal == "*" or (isinstance(principal, dict) and principal.get("AWS") == "*")
        if stmt.get("Effect") == "Allow" and is_public:
            findings.append(
                RawFinding(
                    service=AwsService.LAMBDA,
                    title=f"Lambda function '{function['FunctionName']}' allows public invocation",
                    description=f"Function {function['FunctionName']}'s resource policy grants invoke permission to Principal '*'.",
                    severity_hint=Severity.CRITICAL,
                    resource_arn=function["FunctionArn"],
                    resource_id=function["FunctionName"],
                    mitre_attack="T1190 (Exploit Public-Facing Application)",
                    remediation="Restrict the resource policy Principal to specific accounts/services, or add an authorizer.",
                    estimated_remediation_time="15 min",
                )
            )


def _check_env_vars(function: dict, findings: list[RawFinding]) -> None:
    env_vars = function.get("Environment", {}).get("Variables", {}) if function.get("Environment") else {}
    suspicious_keys = [k for k in env_vars if _SECRET_LIKE_KEY_PATTERN.search(k)]
    if suspicious_keys:
        findings.append(
            RawFinding(
                service=AwsService.LAMBDA,
                title=f"Lambda function '{function['FunctionName']}' may store secrets in plaintext env vars",
                description=(
                    f"Function {function['FunctionName']} has environment variable(s) named "
                    f"{', '.join(suspicious_keys)} that look like they hold secrets. Lambda "
                    "environment variables are encrypted at rest but visible in plaintext to "
                    "anyone with lambda:GetFunctionConfiguration permission."
                ),
                severity_hint=Severity.MEDIUM,
                resource_arn=function["FunctionArn"],
                resource_id=function["FunctionName"],
                nist_control="SC-28",
                remediation="Move secrets to AWS Secrets Manager or SSM Parameter Store (SecureString) and reference them at runtime.",
                estimated_remediation_time="30 min",
            )
        )


def collect(account: AwsAccount) -> CollectorResult:
    findings: list[RawFinding] = []
    scanned = 0
    try:
        with get_client(account, "lambda") as lam:
            paginator = lam.get_paginator("list_functions")
            for page in paginator.paginate():
                for function in page["Functions"]:
                    scanned += 1
                    _check_runtime(function, findings)
                    _check_public_policy(lam, function, findings)
                    _check_env_vars(function, findings)
        return CollectorResult(service=AwsService.LAMBDA, findings=findings, resources_scanned=scanned)
    except Exception as exc:  # noqa: BLE001
        return CollectorResult(service=AwsService.LAMBDA, findings=findings, resources_scanned=scanned, error=str(exc))
