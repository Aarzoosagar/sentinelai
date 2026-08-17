from __future__ import annotations

from app.services.ai.agent.controller import SecurityInvestigationAgent
from app.services.ai import groq_client
from app.services.rag.retrieval import RetrievedContext


def test_investigates_highest_risk_finding_with_authorized_components(monkeypatch):
    calls = []

    def fake_tool(name, arguments, context):
        calls.append((name, arguments, context.audit_session_id))
        if name == "get_affected_resources":
            return {"resources": [{"resource_id": "bucket-a", "title": "Public bucket"}], "total": 1}
        return {"findings": [{"finding_id": "finding-1", "title": "Public bucket", "description": "Bucket permits public access"}], "total": 1}

    class Finding:
        id = "finding-1"
        title = "Public bucket"

    monkeypatch.setattr("app.services.ai.agent.controller.execute_tool", fake_tool)
    monkeypatch.setattr("app.services.ai.agent.controller.retrieve", lambda *args: RetrievedContext(findings=[Finding()]))
    monkeypatch.setattr(groq_client, "complete_json", lambda *args, **kwargs: {"risk_analysis": "Public data exposure is high impact.", "ai_generated_analysis": "The bucket should be reviewed.", "recommended_remediation": "Block public access."})

    report = SecurityInvestigationAgent().investigate(None, "audit-1", "user-1", "Investigate my highest-risk issue")
    assert [call[0] for call in calls] == ["get_critical_findings", "get_finding_by_id", "get_affected_resources"]
    assert report.status == "completed"
    assert report.finding and report.finding.finding_id == "finding-1"
    assert report.security_guidance == ["Public bucket"]
    assert report.steps_used == 4
