"""
Tests for the read-only enforcement guard in services/aws/client_factory.py.

This is the single most safety-critical piece of code in the application:
it's the last line of defense ensuring SentinelAI can never mutate a
customer's AWS account, even if a bug slips into a collector.
"""

from __future__ import annotations

import boto3
import pytest
from botocore.stub import Stubber

from app.services.aws.client_factory import WriteOperationBlocked, _attach_read_only_guard


def _guarded_client(service: str):
    return _attach_read_only_guard(
        boto3.client(service, region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="y")
    )


@pytest.mark.parametrize(
    ("service", "method", "kwargs"),
    [
        ("s3", "delete_bucket", {"Bucket": "should-never-happen"}),
        ("s3", "put_bucket_policy", {"Bucket": "x", "Policy": "{}"}),
        ("iam", "create_user", {"UserName": "hacker"}),
        ("iam", "attach_user_policy", {"UserName": "x", "PolicyArn": "arn:aws:iam::aws:policy/AdministratorAccess"}),
        ("iam", "delete_user", {"UserName": "x"}),
        ("ec2", "terminate_instances", {"InstanceIds": ["i-123"]}),
        ("ec2", "authorize_security_group_ingress", {"GroupId": "sg-123"}),
        ("rds", "delete_db_instance", {"DBInstanceIdentifier": "x"}),
        ("rds", "modify_db_instance", {"DBInstanceIdentifier": "x"}),
        ("kms", "schedule_key_deletion", {"KeyId": "x"}),
        ("lambda", "delete_function", {"FunctionName": "x"}),
        ("secretsmanager", "delete_secret", {"SecretId": "x"}),
    ],
)
def test_mutating_calls_are_blocked_before_any_network_request(service, method, kwargs):
    client = _guarded_client(service)
    with pytest.raises(WriteOperationBlocked):
        getattr(client, method)(**kwargs)


@pytest.mark.parametrize(
    ("service", "method", "kwargs", "response"),
    [
        ("s3", "list_buckets", {}, {"Buckets": []}),
        ("iam", "list_users", {}, {"Users": []}),
        ("ec2", "describe_instances", {}, {"Reservations": []}),
    ],
)
def test_read_only_calls_pass_through_the_guard(service, method, kwargs, response):
    client = _guarded_client(service)
    stubber = Stubber(client)
    stubber.add_response(method, response)
    stubber.activate()

    result = getattr(client, method)(**kwargs)
    assert result is not None
