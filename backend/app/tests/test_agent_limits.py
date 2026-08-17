from __future__ import annotations

from app.services.ai.agent.controller import SecurityInvestigationAgent
from app.services.ai.agent.policies import MAX_AGENT_STEPS


def test_agent_stops_at_hard_step_limit(monkeypatch):
    monkeypatch.setattr("app.services.ai.agent.controller.execute_tool", lambda *args: {"findings": [{"finding_id": "f-1", "title": "finding", "description": "detail"}]})
    monkeypatch.setattr("app.services.ai.agent.controller.groq_client.complete_json", lambda *args, **kwargs: {})
    agent = SecurityInvestigationAgent(lambda _: {"action": "get_critical_findings", "arguments": {"limit": 1}, "reason": "loop"})
    report = agent.investigate(None, "audit-1", "user-1", "Investigate highest risk")
    assert report.termination_reason == "step_limit_reached"
    assert report.steps_used == MAX_AGENT_STEPS


def test_invalid_and_dangerous_actions_terminate_safely():
    agent = SecurityInvestigationAgent(lambda _: {"action": "run_shell", "arguments": {"command": "whoami"}, "reason": "bad"})
    report = agent.investigate(None, "audit-1", "user-1", "Investigate highest risk")
    assert report.status == "failed"
    assert report.termination_reason == "invalid_action"
