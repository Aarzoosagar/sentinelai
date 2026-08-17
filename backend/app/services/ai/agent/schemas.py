"""Typed, bounded state and contracts for security investigations."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentAction(str, Enum):
    GET_CRITICAL_FINDINGS = "get_critical_findings"
    GET_FINDING = "get_finding_by_id"
    GET_AFFECTED_RESOURCES = "get_affected_resources"
    RETRIEVE_SECURITY_CONTEXT = "retrieve_security_context"
    FINISH = "finish"


class AgentDecision(BaseModel):
    """The only model-shaped instruction the controller will consider."""
    model_config = ConfigDict(extra="forbid")
    action: AgentAction
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(min_length=1, max_length=500)


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_type: Literal["finding", "tool", "rag"]
    source_id: str
    title: str
    context: str = Field(max_length=2000)


class InvestigationState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    audit_session_id: str
    user_request: str
    current_finding_id: str | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    tool_calls: list[str] = Field(default_factory=list)
    retrieved_sources: list[str] = Field(default_factory=list)
    steps_completed: list[str] = Field(default_factory=list)
    status: Literal["running", "completed", "partial", "failed", "unauthorized"] = "running"
    termination_reason: str | None = None
    consecutive_failures: int = 0


class InvestigationFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finding_id: str
    title: str
    service: str
    severity: str
    description: str
    remediation: str


class InvestigationReport(BaseModel):
    """Report fields deliberately label facts, retrieved guidance, and recommendations."""
    model_config = ConfigDict(extra="forbid")
    finding: InvestigationFinding | None = None
    observed_finding: str
    risk_analysis: str
    affected_resources: list[dict[str, Any]] = Field(default_factory=list)
    security_guidance: list[str] = Field(default_factory=list)
    ai_generated_analysis: str
    recommended_remediation: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    steps_used: int = Field(ge=0)
    status: Literal["completed", "partial", "failed", "unauthorized"]
    termination_reason: str
