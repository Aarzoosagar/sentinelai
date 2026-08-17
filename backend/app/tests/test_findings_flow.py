"""
Full-stack tests: seed an audit's findings straight through the risk engine
(the same code path the real background audit task uses), then verify the
findings, compliance, and dashboard endpoints all reflect that data
correctly.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database.base import utcnow
from app.models.audit_session import AuditSession
from app.models.aws_account import AwsAccount
from app.models.enums import AuditStatus, AwsAuthMethod, AwsService, Severity
from app.models.user import User
from app.repositories.audit_repository import AuditSessionRepository
from app.repositories.aws_account_repository import AwsAccountRepository
from app.repositories.user_repository import UserRepository
from app.services.aws.base import RawFinding
from app.services.risk.engine import process_audit


def _seed_completed_audit(db_session: Session, user_email: str) -> str:
    user = UserRepository(db_session).get_by_email(user_email)
    assert user is not None, "call this after registering the user via the API"

    account = AwsAccount(
        user_id=user.id,
        account_alias="test-account",
        aws_account_id="123456789012",
        region="us-east-1",
        auth_method=AwsAuthMethod.ASSUME_ROLE,
        role_arn="arn:aws:iam::123456789012:role/ReadOnly",
    )
    AwsAccountRepository(db_session).add(account)
    db_session.commit()

    audit = AuditSession(aws_account_id=account.id, status=AuditStatus.RUNNING, started_at=utcnow())
    AuditSessionRepository(db_session).add(audit)
    db_session.commit()
    db_session.refresh(audit)

    raw_findings = [
        RawFinding(
            service=AwsService.S3,
            title="Public S3 bucket",
            description="Bucket allows public read access",
            severity_hint=Severity.CRITICAL,
            remediation="Enable Block Public Access",
            cis_control="2.1.5",
        ),
        RawFinding(
            service=AwsService.EC2,
            title="Security group open to the world",
            description="Port 22 open to 0.0.0.0/0",
            severity_hint=Severity.HIGH,
            remediation="Restrict the CIDR range",
            cis_control="5.2 / 5.3",
        ),
        RawFinding(
            service=AwsService.KMS,
            title="Key rotation disabled",
            description="Customer-managed key has no rotation",
            severity_hint=Severity.LOW,
            remediation="Enable key rotation",
            cis_control="2.8",
        ),
    ]

    security_score = process_audit(db_session, audit.id, raw_findings)
    audit.status = AuditStatus.COMPLETED
    audit.completed_at = utcnow()
    audit.resources_scanned = 17
    audit.security_score = security_score
    db_session.commit()

    return audit.id


def test_findings_list_reflects_seeded_audit(client: TestClient, db_session: Session, registered_user: dict):
    audit_id = _seed_completed_audit(db_session, registered_user["email"])

    resp = client.get(
        "/api/v1/findings", params={"audit_session_id": audit_id}, headers=registered_user["headers"]
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    titles = {item["title"] for item in body["items"]}
    assert "Public S3 bucket" in titles


def test_findings_severity_filter_works(client: TestClient, db_session: Session, registered_user: dict):
    audit_id = _seed_completed_audit(db_session, registered_user["email"])

    resp = client.get(
        "/api/v1/findings",
        params={"audit_session_id": audit_id, "severity": "critical"},
        headers=registered_user["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_finding_detail_includes_risk_score(client: TestClient, db_session: Session, registered_user: dict):
    audit_id = _seed_completed_audit(db_session, registered_user["email"])
    list_resp = client.get(
        "/api/v1/findings", params={"audit_session_id": audit_id}, headers=registered_user["headers"]
    )
    finding_id = list_resp.json()["items"][0]["id"]

    resp = client.get(f"/api/v1/findings/{finding_id}", headers=registered_user["headers"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["risk_score"] is not None
    assert 0 <= body["risk_score"]["risk_score"] <= 100


def test_finding_status_can_be_updated(client: TestClient, db_session: Session, registered_user: dict):
    audit_id = _seed_completed_audit(db_session, registered_user["email"])
    list_resp = client.get(
        "/api/v1/findings", params={"audit_session_id": audit_id}, headers=registered_user["headers"]
    )
    finding_id = list_resp.json()["items"][0]["id"]

    resp = client.patch(
        f"/api/v1/findings/{finding_id}/status", json={"status": "resolved"}, headers=registered_user["headers"]
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


def test_findings_are_scoped_to_owning_user(client: TestClient, db_session: Session, registered_user: dict):
    """A finding belonging to another user's audit must not be visible."""
    audit_id = _seed_completed_audit(db_session, registered_user["email"])

    other = client.post(
        "/api/v1/auth/register",
        json={"email": "other.user@sentinelai.io", "password": "SuperSecret123", "full_name": "Other User"},
    )
    assert other.status_code == 201
    other_login = client.post(
        "/api/v1/auth/login", json={"email": "other.user@sentinelai.io", "password": "SuperSecret123"}
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    resp = client.get(
        "/api/v1/findings", params={"audit_session_id": audit_id}, headers=other_headers
    )
    assert resp.status_code == 404


def test_compliance_overview_reflects_seeded_findings(client: TestClient, db_session: Session, registered_user: dict):
    audit_id = _seed_completed_audit(db_session, registered_user["email"])

    resp = client.get(f"/api/v1/compliance/{audit_id}", headers=registered_user["headers"])
    assert resp.status_code == 200
    body = resp.json()
    frameworks = {f["framework"] for f in body["frameworks"]}
    assert "cis_aws_foundations" in frameworks
    assert "iso_27001" in frameworks

    cis = next(f for f in body["frameworks"] if f["framework"] == "cis_aws_foundations")
    assert cis["failed"] >= 1  # the critical S3 finding should fail its control


def test_dashboard_summary_reflects_seeded_findings(client: TestClient, db_session: Session, registered_user: dict):
    _seed_completed_audit(db_session, registered_user["email"])

    resp = client.get("/api/v1/dashboard/summary", headers=registered_user["headers"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["security_score"] is not None
    assert body["findings_by_severity"]["critical"] == 1
    assert body["findings_by_severity"]["high"] == 1
    assert body["findings_by_severity"]["low"] == 1
    assert body["resources_scanned"] == 17
    assert len(body["recent_audits"]) == 1
