from __future__ import annotations

from app.services.ai.agent.controller import SecurityInvestigationAgent
from app.services.ai.agent.schemas import AgentDecision
from app.services.ai.tools.audit_tools import ToolAuthorizationError


def test_model_cannot_change_effective_audit_scope(monkeypatch):
    observed = []

    def fake_tool(name, arguments, context):
        observed.append((arguments, context.audit_session_id))
        return {"findings": []}

    agent = SecurityInvestigationAgent(lambda _: {"action": "get_critical_findings", "arguments": {"audit_session_id": "another-audit"}, "reason": "attack"})
    monkeypatch.setattr("app.services.ai.agent.controller.execute_tool", fake_tool)
    report = agent.investigate(None, "authorized-audit", "user-1", "Investigate highest risk")
    # Strict tool schemas reject model-injected scope before any database operation.
    assert observed == []
    assert report.status == "partial"


def test_authorization_failure_terminates_immediately(monkeypatch):
    monkeypatch.setattr("app.services.ai.agent.controller.execute_tool", lambda *args: (_ for _ in ()).throw(ToolAuthorizationError()))
    report = SecurityInvestigationAgent().investigate(None, "audit-1", "user-1", "Investigate highest risk")
    assert report.status == "unauthorized"
    assert report.termination_reason == "authorization_failed"
