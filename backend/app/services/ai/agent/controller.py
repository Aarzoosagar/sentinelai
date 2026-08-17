"""Deterministic, finite controller for a single security investigation."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.services.ai import groq_client
from app.services.ai.agent.policies import ALLOWED_AGENT_ACTIONS, MAX_AGENT_STEPS, MAX_CONSECUTIVE_TOOL_FAILURES
from app.services.ai.agent.prompts import investigation_report_messages
from app.services.ai.agent.schemas import AgentAction, AgentDecision, EvidenceItem, InvestigationFinding, InvestigationReport, InvestigationState
from app.services.ai.guardrails.input import validate_chat_input
from app.services.ai.observability import current_request_id, record, reset_correlation, set_correlation
from app.services.ai.tools.audit_tools import ToolAuthorizationError, ToolExecutionContext
from app.services.ai.tools.registry import ToolValidationError, execute_tool
from app.services.rag.retrieval import retrieve


DecisionProvider = Callable[[InvestigationState], AgentDecision | dict[str, Any]]


class SecurityInvestigationAgent:
    """Uses a fixed safe plan; optional providers are validated before execution."""

    def __init__(self, decision_provider: DecisionProvider | None = None) -> None:
        self.decision_provider = decision_provider

    def investigate(self, db: Session, audit_session_id: str, user_id: str, user_request: str) -> InvestigationReport:
        safe_request = validate_chat_input(user_request)
        tokens = set_correlation(current_request_id(), audit_session_id)
        state = InvestigationState(audit_session_id=audit_session_id, user_request=safe_request)
        try:
            context = ToolExecutionContext(db=db, audit_session_id=audit_session_id, user_id=user_id)
            for step in range(MAX_AGENT_STEPS):
                decision = self._decision(state)
                if decision is None:
                    state.status, state.termination_reason = "failed", "invalid_action"
                    break
                if decision.action.value not in ALLOWED_AGENT_ACTIONS:
                    state.status, state.termination_reason = "failed", "invalid_action"
                    break
                if decision.action is AgentAction.FINISH:
                    state.status, state.termination_reason = "completed", "sufficient_evidence"
                    break
                started = perf_counter()
                try:
                    self._execute(decision, state, context)
                    state.consecutive_failures = 0
                    success = True
                except ToolAuthorizationError:
                    state.status, state.termination_reason, success = "unauthorized", "authorization_failed", False
                    self._record_step(step + 1, decision.action.value, success, started, state.termination_reason)
                    break
                except Exception:
                    state.consecutive_failures += 1
                    success = False
                    if decision.action is AgentAction.RETRIEVE_SECURITY_CONTEXT:
                        state.status, state.termination_reason = "partial", "retrieval_failed"
                    elif state.consecutive_failures >= MAX_CONSECUTIVE_TOOL_FAILURES:
                        state.status, state.termination_reason = "partial", "repeated_tool_failure"
                    else:
                        state.steps_completed.append(f"{decision.action.value}:failed")
                self._record_step(step + 1, decision.action.value, success, started, state.termination_reason)
                if state.status != "running":
                    break
            else:
                state.status, state.termination_reason = "partial", "step_limit_reached"
            if state.status == "running":
                state.status, state.termination_reason = "partial", "no_useful_tool"
            return self._report(state)
        finally:
            reset_correlation(tokens)

    def _decision(self, state: InvestigationState) -> AgentDecision | None:
        if self.decision_provider:
            try:
                raw = self.decision_provider(state)
                return raw if isinstance(raw, AgentDecision) else AgentDecision.model_validate(raw)
            except (ValidationError, TypeError, ValueError):
                return None
        if not state.current_finding_id:
            if "get_critical_findings" in state.tool_calls:
                return AgentDecision(action=AgentAction.FINISH, reason="No critical finding is available in this audit.")
            return AgentDecision(action=AgentAction.GET_CRITICAL_FINDINGS, arguments={"limit": 1}, reason="Select the highest-risk critical finding.")
        if "get_finding_by_id" not in state.tool_calls:
            return AgentDecision(action=AgentAction.GET_FINDING, arguments={"finding_id": state.current_finding_id}, reason="Collect canonical finding details.")
        if "get_affected_resources" not in state.tool_calls:
            return AgentDecision(action=AgentAction.GET_AFFECTED_RESOURCES, arguments={"limit": 25}, reason="Collect affected resources.")
        if "retrieve_security_context" not in state.steps_completed:
            return AgentDecision(action=AgentAction.RETRIEVE_SECURITY_CONTEXT, reason="Retrieve audit-scoped security context.")
        return AgentDecision(action=AgentAction.FINISH, reason="Evidence collection is complete.")

    def _execute(self, decision: AgentDecision, state: InvestigationState, context: ToolExecutionContext) -> None:
        if decision.action is AgentAction.RETRIEVE_SECURITY_CONTEXT:
            results = retrieve(context.db, context.audit_session_id, context.user_id, state.user_request)
            for finding in results.findings:
                state.retrieved_sources.append(finding.id)
                state.evidence.append(EvidenceItem(source_type="rag", source_id=finding.id, title=finding.title, context="Retrieved through the authorized hybrid RAG pipeline."))
            state.steps_completed.append("retrieve_security_context")
            return
        # Only action-owned arguments are passed; audit scope always comes from context.
        if "audit_session_id" in decision.arguments:
            raise ToolValidationError("Model-provided audit scope is forbidden")
        output = execute_tool(decision.action.value, decision.arguments, context)
        state.tool_calls.append(decision.action.value)
        state.steps_completed.append(decision.action.value)
        for finding in output.get("findings", []):
            finding_id = finding.get("finding_id")
            if finding_id and not state.current_finding_id:
                state.current_finding_id = finding_id
            state.evidence.append(EvidenceItem(source_type="finding", source_id=finding_id or "unknown", title=finding.get("title", "Finding"), context=finding.get("description", "Canonical audit finding.")))
        for resource in output.get("resources", []):
            state.evidence.append(EvidenceItem(source_type="tool", source_id=resource.get("resource_arn") or resource.get("resource_id") or "unknown", title=resource.get("title", "Affected resource"), context="Reported by the authorized affected-resources tool."))

    def _report(self, state: InvestigationState) -> InvestigationReport:
        finding_evidence = next((item for item in state.evidence if item.source_type == "finding"), None)
        finding = InvestigationFinding(finding_id=state.current_finding_id, title=finding_evidence.title, service="Unknown", severity="Unknown", description=finding_evidence.context, remediation="See recommended remediation.") if state.current_finding_id and finding_evidence else None
        guidance = [item.title for item in state.evidence if item.source_type == "rag"]
        analysis = self._synthesis(state)
        return InvestigationReport(
            finding=finding,
            observed_finding=finding_evidence.context if finding_evidence else "No finding was available in the authorized audit.",
            risk_analysis=analysis["risk_analysis"],
            affected_resources=[{"source_id": item.source_id, "title": item.title} for item in state.evidence if item.source_type == "tool"],
            security_guidance=guidance,
            ai_generated_analysis=analysis["ai_generated_analysis"],
            recommended_remediation=analysis["recommended_remediation"],
            evidence=state.evidence,
            steps_used=len(state.steps_completed), status=state.status, termination_reason=state.termination_reason or "completed",
        )

    def _synthesis(self, state: InvestigationState) -> dict[str, str]:
        fallback = {"risk_analysis": "Assessment is limited to the collected evidence.", "ai_generated_analysis": "AI analysis was unavailable; observed evidence is listed separately.", "recommended_remediation": "Follow the canonical finding remediation and applicable retrieved guidance."}
        if not state.evidence:
            return fallback
        try:
            raw = groq_client.complete_json(investigation_report_messages(state.user_request, [item.model_dump() for item in state.evidence]), task="chat")
            return {key: str(raw[key]) for key in fallback if isinstance(raw.get(key), str) and raw[key].strip()} | {key: fallback[key] for key in fallback if not isinstance(raw.get(key), str) or not raw[key].strip()}
        except Exception:
            return fallback

    @staticmethod
    def _record_step(step: int, action: str, success: bool, started: float, termination_reason: str | None) -> None:
        record("agent_step", agent_step=step, action=action, tool_name=action, step_latency_ms=round((perf_counter() - started) * 1000, 2), step_success=success, termination_reason=termination_reason)
