"""Chat must receive only retrieval-selected findings; Groq stays mocked."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import AuditStatus, AwsService, Severity
from app.models.finding import Finding
from app.services.ai import chat
from app.services.ai import groq_client
from app.services.rag.retrieval import RetrievedContext
from app.tests.test_findings_flow import _seed_completed_audit


class _Audit:
    id = "audit-1"
    security_score = 80
    resources_scanned = 2
    status = AuditStatus.COMPLETED


def test_chat_uses_only_retrieved_context_and_mocks_groq(monkeypatch):
    selected = Finding(id="fnd-selected", audit_session_id="audit-1", service=AwsService.S3, title="Public bucket", description="public", severity=Severity.CRITICAL, remediation="block")
    context = RetrievedContext(findings=[selected])
    monkeypatch.setattr(chat, "retrieve", lambda *args, **kwargs: context)
    captured: dict[str, object] = {}

    def fake_complete(messages, tools, **kwargs):
        captured["messages"] = messages
        return groq_client.ToolCompletion("grounded reply", [])

    monkeypatch.setattr(chat.groq_client, "complete_with_tools", fake_complete)
    reply, sources = chat.get_chat_reply(None, _Audit(), "user-1", [], "How do I fix this?")
    assert reply == "grounded reply"
    assert sources.findings == [selected]
    assert "Public bucket" in captured["messages"][1]["content"]
    assert "fnd-selected" in captured["messages"][1]["content"]


def test_chat_history_endpoint_loads_an_authorized_audit(
    client: TestClient, db_session: Session, registered_user: dict
):
    audit_id = _seed_completed_audit(db_session, registered_user["email"])
    response = client.get(f"/api/v1/chat/{audit_id}/history", headers=registered_user["headers"])
    assert response.status_code == 200, response.text
    assert response.json() == {"audit_session_id": audit_id, "messages": []}
