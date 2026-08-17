"""HTTP coverage for the existing bounded security investigation controller."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database.base import utcnow
from app.models.audit_session import AuditSession
from app.models.aws_account import AwsAccount
from app.models.enums import AuditStatus, AwsAuthMethod
from app.repositories.audit_repository import AuditSessionRepository
from app.repositories.aws_account_repository import AwsAccountRepository
from app.repositories.user_repository import UserRepository
from app.services.ai.agent.schemas import EvidenceItem, InvestigationReport


def _seed_audit(db: Session, email: str) -> str:
    user = UserRepository(db).get_by_email(email)
    assert user is not None
    account = AwsAccount(
        user_id=user.id, account_alias="investigation-test", aws_account_id="123456789012",
        region="us-east-1", auth_method=AwsAuthMethod.ASSUME_ROLE,
        role_arn="arn:aws:iam::123456789012:role/ReadOnly",
    )
    AwsAccountRepository(db).add(account)
    db.commit()
    audit = AuditSession(
        aws_account_id=account.id, status=AuditStatus.COMPLETED,
        started_at=utcnow(), completed_at=utcnow(), resources_scanned=1,
    )
    AuditSessionRepository(db).add(audit)
    db.commit()
    return audit.id


def _report() -> InvestigationReport:
    return InvestigationReport(
        observed_finding="A public bucket was observed.", risk_analysis="It may expose data.",
        affected_resources=[], security_guidance=["Public bucket"],
        ai_generated_analysis="Review bucket access.", recommended_remediation="Enable Block Public Access.",
        evidence=[EvidenceItem(source_type="finding", source_id="finding-1", title="Public bucket", context="Canonical finding.")],
        steps_used=4, status="completed", termination_reason="sufficient_evidence",
    )


def test_investigate_endpoint_invokes_existing_agent_and_returns_typed_report(monkeypatch, client: TestClient, db_session: Session, registered_user: dict):
    audit_id = _seed_audit(db_session, registered_user["email"])
    calls = []

    class FakeAgent:
        def investigate(self, db, audit_session_id, user_id, question):
            calls.append((db, audit_session_id, user_id, question))
            return _report()

    monkeypatch.setattr("app.api.v1.investigations.router.SecurityInvestigationAgent", FakeAgent)
    response = client.post(f"/api/v1/audit/{audit_id}/investigate", json={"question": "Investigate my highest-risk security issue."}, headers=registered_user["headers"])
    assert response.status_code == 200, response.text
    assert response.json()["risk_analysis"] == "It may expose data."
    assert response.json()["steps_used"] == 4
    assert calls and calls[0][1] == audit_id and calls[0][3].startswith("Investigate")


def test_investigate_endpoint_denies_another_users_audit(monkeypatch, client: TestClient, db_session: Session, registered_user: dict):
    audit_id = _seed_audit(db_session, registered_user["email"])
    other = client.post("/api/v1/auth/register", json={"email": "investigator.other@sentinelai.io", "password": "SuperSecret123", "full_name": "Other User"})
    assert other.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": "investigator.other@sentinelai.io", "password": "SuperSecret123"})
    response = client.post(f"/api/v1/audit/{audit_id}/investigate", json={"question": "Investigate highest risk"}, headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert response.status_code == 404


def test_investigate_endpoint_validates_question(client: TestClient, db_session: Session, registered_user: dict):
    audit_id = _seed_audit(db_session, registered_user["email"])
    for question in ("", "x" * 4001):
        response = client.post(f"/api/v1/audit/{audit_id}/investigate", json={"question": question}, headers=registered_user["headers"])
        assert response.status_code == 422


def test_investigate_endpoint_hides_agent_failure(monkeypatch, client: TestClient, db_session: Session, registered_user: dict):
    audit_id = _seed_audit(db_session, registered_user["email"])

    class FailingAgent:
        def investigate(self, *args):
            raise RuntimeError("provider internals must not leak")

    monkeypatch.setattr("app.api.v1.investigations.router.SecurityInvestigationAgent", FailingAgent)
    response = client.post(f"/api/v1/audit/{audit_id}/investigate", json={"question": "Investigate highest risk"}, headers=registered_user["headers"])
    assert response.status_code == 503
    assert "internals" not in response.json()["detail"]
