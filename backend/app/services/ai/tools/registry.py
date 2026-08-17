"""The complete allowlist of callable Security Chat tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Type

from pydantic import BaseModel, ValidationError

from app.core.config.settings import get_settings
from app.services.ai.observability import timed
from app.services.ai.tools import audit_tools
from app.services.ai.tools.audit_tools import ToolExecutionContext
from app.services.ai.tools.schemas import (
    GetAffectedResourcesInput, GetAuditSummaryInput, GetCriticalFindingsInput,
    GetFindingByIdInput, GetFindingsByFrameworkInput, GetFindingsByServiceInput, GetFindingsInput,
)


class ToolValidationError(ValueError):
    pass


@dataclass(frozen=True)
class RegisteredTool:
    description: str
    input_model: Type[BaseModel]
    handler: Callable[[ToolExecutionContext, BaseModel], BaseModel]


TOOL_REGISTRY: dict[str, RegisteredTool] = {
    "get_audit_summary": RegisteredTool("Get summary metrics for the current authorized audit.", GetAuditSummaryInput, audit_tools.get_audit_summary),
    "get_findings": RegisteredTool("List findings from the current authorized audit with safe filters.", GetFindingsInput, audit_tools.get_findings),
    "get_finding_by_id": RegisteredTool("Get one finding only when it belongs to the current authorized audit.", GetFindingByIdInput, audit_tools.get_finding_by_id),
    "get_critical_findings": RegisteredTool("List critical findings from the current authorized audit.", GetCriticalFindingsInput, audit_tools.get_critical_findings),
    "get_findings_by_service": RegisteredTool("List findings for an AWS service in the current authorized audit.", GetFindingsByServiceInput, audit_tools.get_findings_by_service),
    "get_findings_by_framework": RegisteredTool("List CIS or NIST mapped findings from the current authorized audit.", GetFindingsByFrameworkInput, audit_tools.get_findings_by_framework),
    "get_affected_resources": RegisteredTool("List affected resources from the current authorized audit.", GetAffectedResourcesInput, audit_tools.get_affected_resources),
}


def execute_tool(name: str, arguments: dict[str, Any], context: ToolExecutionContext) -> dict[str, Any]:
    tool = TOOL_REGISTRY.get(name)
    if tool is None:
        raise ToolValidationError("Unknown tool")
    try:
        params = tool.input_model.model_validate(arguments)
    except ValidationError as exc:
        raise ToolValidationError("Invalid tool arguments") from exc
    with timed("ai_tool", counter="tool_calls", tool_name=name):
        result = tool.handler(context, params).model_dump(mode="json")
    # Tool schemas may allow up to 50 for the API, but the model receives a
    # separately configurable bounded result to protect prompt size.
    limit = get_settings().ai_tool_result_limit
    for collection_key in ("findings", "resources"):
        if collection_key in result:
            result[collection_key] = result[collection_key][:limit]
    return result


def groq_tool_definitions() -> list[dict[str, Any]]:
    return [
        {"type": "function", "function": {"name": name, "description": tool.description, "parameters": tool.input_model.model_json_schema()}}
        for name, tool in TOOL_REGISTRY.items()
    ]
