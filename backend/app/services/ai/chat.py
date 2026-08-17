"""
AI Security Chat.

Every response is grounded in the findings of one specific completed audit
— the findings are injected as a system message on every call, and the
model is instructed (see prompts/templates.py) to only use that data. This
is what "Base responses only on collected audit data" means in practice
for the chat feature specifically.
"""

from __future__ import annotations

from collections.abc import Iterator
import json

from sqlalchemy.orm import Session

from app.models.ai_message import AiMessage
from app.models.audit_session import AuditSession
from app.models.enums import ChatRole
from app.prompts.templates import chat_findings_context_message, chat_system_prompt
from app.services.ai import groq_client
from app.services.ai.serializers import audit_to_dict, finding_to_dict
from app.services.rag.retrieval import RetrievedContext, retrieve
from app.services.ai.tools.audit_tools import ToolAuthorizationError, ToolExecutionContext
from app.services.ai.tools.registry import ToolValidationError, execute_tool, groq_tool_definitions
from app.services.ai.guardrails.input import validate_chat_input
from app.services.ai.guardrails.output import protect_chat_output
from app.services.ai.guardrails.policies import MAX_TOOL_ROUNDS
from app.services.ai.observability import current_request_id, reset_correlation, set_correlation



def _build_messages(
    audit: AuditSession, context: RetrievedContext, history: list[AiMessage], new_message: str
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [
        {"role": "system", "content": chat_system_prompt(audit_to_dict(audit))},
        chat_findings_context_message([finding_to_dict(f) for f in context.findings]),
    ]
    for msg in history:
        role = "user" if msg.role == ChatRole.USER else "assistant"
        messages.append({"role": role, "content": msg.content})
    messages.append({"role": "user", "content": new_message})
    return messages


def get_chat_reply(
    db: Session, audit: AuditSession, user_id: str, history: list[AiMessage], new_message: str
) -> tuple[str, RetrievedContext]:
    tokens = set_correlation(current_request_id(), audit.id)
    try:
        safe_message = validate_chat_input(new_message)
        context = retrieve(db, audit.id, user_id, safe_message)
        messages = _build_messages(audit, context, history, safe_message)
        allowed_finding_ids = {finding.id for finding in context.findings}
        answer = _complete_with_tools(db, audit.id, user_id, messages, allowed_finding_ids)
        return protect_chat_output(answer, allowed_finding_ids), context
    finally:
        reset_correlation(tokens)


def _complete_with_tools(
    db: Session, audit_session_id: str, user_id: str, messages: list[dict[str, object]], allowed_finding_ids: set[str] | None = None,
) -> str:
    """Run at most three model-directed, validated, audit-local tool rounds."""
    tool_context = ToolExecutionContext(db=db, audit_session_id=audit_session_id, user_id=user_id)
    tools = groq_tool_definitions()
    for _ in range(MAX_TOOL_ROUNDS):
        completion = groq_client.complete_with_tools(messages, tools, task="chat")
        if not completion.tool_calls:
            return completion.content
        messages.append({
            "role": "assistant", "content": completion.content or None,
            "tool_calls": [
                {"id": call.id, "type": "function", "function": {"name": call.name, "arguments": json.dumps(call.arguments)}}
                for call in completion.tool_calls
            ],
        })
        for call in completion.tool_calls:
            try:
                application_data = execute_tool(call.name, call.arguments, tool_context)
                _collect_finding_ids(application_data, allowed_finding_ids)
                result = {"application_data": application_data}
            except (ToolValidationError, ToolAuthorizationError):
                # Never reveal implementation detail or authorization state to the model.
                result = {"error": "The requested tool call is not available for this audit."}
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
    return "I could not complete the requested data lookup within the allowed tool-call limit."


def _collect_finding_ids(value: object, finding_ids: set[str] | None) -> None:
    if finding_ids is None:
        return
    if isinstance(value, dict):
        if isinstance(value.get("finding_id"), str):
            finding_ids.add(value["finding_id"])
        for item in value.values():
            _collect_finding_ids(item, finding_ids)
    elif isinstance(value, list):
        for item in value:
            _collect_finding_ids(item, finding_ids)


def stream_chat_reply(
    db: Session, audit: AuditSession, user_id: str, history: list[AiMessage], new_message: str
) -> Iterator[str]:
    safe_message = validate_chat_input(new_message)
    context = retrieve(db, audit.id, user_id, safe_message)
    messages = _build_messages(audit, context, history, safe_message)
    yield from groq_client.stream_completion(messages, task="chat")
