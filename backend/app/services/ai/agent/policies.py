"""Non-negotiable deterministic limits for the investigation agent."""

from __future__ import annotations

from app.services.ai.guardrails.policies import AI_SECURITY_POLICY

MAX_AGENT_STEPS = 5
MAX_CONSECUTIVE_TOOL_FAILURES = 2
ALLOWED_AGENT_ACTIONS = {
    "get_critical_findings",
    "get_finding_by_id",
    "get_affected_resources",
    "retrieve_security_context",
    "finish",
}

AGENT_POLICY = AI_SECURITY_POLICY + "\nThe investigation controller owns audit scope, action allowlisting, and step limits."
