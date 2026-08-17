from __future__ import annotations

import pytest

from app.models.audit_session import AuditSession
from app.models.aws_account import AwsAccount
from app.models.enums import AuditStatus, AwsAuthMethod, AwsService, Severity
from app.models.finding import Finding
from app.models.user import User
from app.services.ai.tools.audit_tools import ToolAuthorizationError, ToolExecutionContext
from app.services.ai.tools.registry import TOOL_REGISTRY, ToolValidationError, execute_tool


@pytest.fixture()
def audit_data(db_session):
    user = User(email="tools@test.io", hashed_password="x", full_name="Tools")
    other_user = User(email="other-tools@test.io", hashed_password="x", full_name="Other")
    db_session.add_all([user, other_user]); db_session.flush()
    account = AwsAccount(user_id=user.id, account_alias="tools", aws_account_id="11", region="us-east-1", auth_method=AwsAuthMethod.ASSUME_ROLE, role_arn="arn")
    other_account = AwsAccount(user_id=other_user.id, account_alias="other", aws_account_id="12", region="us-east-1", auth_method=AwsAuthMethod.ASSUME_ROLE, role_arn="arn")
    db_session.add_all([account, other_account]); db_session.flush()
    audit = AuditSession(aws_account_id=account.id, status=AuditStatus.COMPLETED, security_score=70, resources_scanned=4)
    other_audit = AuditSession(aws_account_id=other_account.id, status=AuditStatus.COMPLETED)
    db_session.add_all([audit, other_audit]); db_session.flush()
    critical = Finding(audit_session_id=audit.id, service=AwsService.S3, title="Public bucket", description="public access", severity=Severity.CRITICAL, remediation="block public access", cis_control="2.1.5", nist_control="AC-3", resource_id="bucket-a")
    iam = Finding(audit_session_id=audit.id, service=AwsService.IAM, title="Admin policy", description="wildcard permissions", severity=Severity.HIGH, remediation="least privilege", cis_control="1.16", nist_control="AC-6")
    foreign = Finding(audit_session_id=other_audit.id, service=AwsService.S3, title="Foreign", description="foreign", severity=Severity.CRITICAL, remediation="block")
    db_session.add_all([critical, iam, foreign]); db_session.flush()
    return user, audit, other_audit, critical, iam, foreign


def test_registry_is_explicit_and_tool_queries_are_audit_scoped(db_session, audit_data):
    user, audit, _, critical, iam, _ = audit_data
    context = ToolExecutionContext(db_session, audit.id, user.id)
    assert set(TOOL_REGISTRY) == {"get_audit_summary", "get_findings", "get_finding_by_id", "get_critical_findings", "get_findings_by_service", "get_findings_by_framework", "get_affected_resources"}
    critical_result = execute_tool("get_critical_findings", {"limit": 10}, context)
    assert [item["finding_id"] for item in critical_result["findings"]] == [critical.id]
    service_result = execute_tool("get_findings_by_service", {"service": "iam"}, context)
    assert [item["finding_id"] for item in service_result["findings"]] == [iam.id]
    framework_result = execute_tool("get_findings_by_framework", {"framework": "nist", "control": "AC-3"}, context)
    assert [item["finding_id"] for item in framework_result["findings"]] == [critical.id]
    assert execute_tool("get_finding_by_id", {"finding_id": "not-present"}, context)["findings"] == []


def test_tool_rejects_unknown_malformed_out_of_range_and_model_audit_id(db_session, audit_data):
    user, audit, other_audit, _, _, _ = audit_data
    context = ToolExecutionContext(db_session, audit.id, user.id)
    for name, args in [
        ("run_sql", {"sql": "select * from findings"}),
        ("get_findings", {"limit": 51}),
        ("get_findings", {"audit_session_id": other_audit.id}),
        ("get_findings_by_service", {"service": "filesystem"}),
    ]:
        with pytest.raises(ToolValidationError):
            execute_tool(name, args, context)


def test_tool_revalidates_ownership_and_prevents_cross_audit_finding_access(db_session, audit_data):
    user, audit, other_audit, _, _, foreign = audit_data
    unauthorized_context = ToolExecutionContext(db_session, other_audit.id, user.id)
    with pytest.raises(ToolAuthorizationError):
        execute_tool("get_audit_summary", {}, unauthorized_context)
    context = ToolExecutionContext(db_session, audit.id, user.id)
    result = execute_tool("get_finding_by_id", {"finding_id": foreign.id}, context)
    assert result == {"findings": [], "total": 0}
