"""Authenticated HTTP entry point for the bounded investigation agent."""

from __future__ import annotations

from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database.session import get_db
from app.middleware.auth import get_current_active_user
from app.models.user import User
from app.repositories.audit_repository import AuditSessionRepository
from app.schemas.investigation import InvestigationRequest
from app.services.ai.agent.controller import SecurityInvestigationAgent
from app.services.ai.agent.schemas import InvestigationReport
from app.services.ai.guardrails.input import InputGuardrailViolation
from app.services.ai.observability import current_request_id, record, reset_correlation, set_correlation

router = APIRouter(prefix="/audit", tags=["Security Investigation"])


@router.post("/{audit_session_id}/investigate", response_model=InvestigationReport)
def investigate_audit(
    audit_session_id: str,
    payload: InvestigationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> InvestigationReport:
    """Investigate one owned audit; the request never supplies effective scope."""
    audit = AuditSessionRepository(db).get_for_user(audit_session_id, current_user.id)
    if audit is None:
        # Existing audit routes deliberately conceal whether an inaccessible ID exists.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit session not found")

    tokens = set_correlation(current_request_id(), audit.id)
    started = perf_counter()
    try:
        report = SecurityInvestigationAgent().investigate(db, audit.id, current_user.id, payload.question)
        record(
            "agent_investigation",
            agent_steps=report.steps_used,
            tool_calls=sum(1 for evidence in report.evidence if evidence.source_type == "tool"),
            latency_ms=round((perf_counter() - started) * 1000, 2),
            termination_reason=report.termination_reason,
            success=report.status == "completed",
        )
        return report
    except InputGuardrailViolation as exc:
        record("agent_investigation", latency_ms=round((perf_counter() - started) * 1000, 2), success=False, termination_reason="input_rejected")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question rejected by AI security controls") from exc
    except Exception as exc:  # noqa: BLE001 - do not expose AI/provider internals through HTTP
        record("agent_investigation", latency_ms=round((perf_counter() - started) * 1000, 2), success=False, termination_reason="agent_failure", error_type=type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Security investigation is temporarily unavailable") from exc
    finally:
        reset_correlation(tokens)
