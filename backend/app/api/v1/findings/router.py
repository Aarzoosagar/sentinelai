"""Findings endpoints: browse, filter, update status, and AI-assisted detail."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database.session import get_db
from app.middleware.auth import get_current_active_user
from app.models.enums import AwsService, FindingStatus, Severity
from app.models.user import User
from app.repositories.audit_repository import AuditSessionRepository
from app.repositories.finding_repository import FindingRepository
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.finding import (
    AiExplanationResponse,
    FindingDetailResponse,
    FindingListItemResponse,
    FindingStatusUpdateRequest,
)
from app.services.ai.explain import generate_iac_example, get_or_generate_explanation
from app.services.rag.retrieval import index_audit_findings

router = APIRouter(prefix="/findings", tags=["Findings"])


def _assert_audit_belongs_to_user(db: Session, audit_session_id: str | None, user_id: str) -> None:
    if audit_session_id is None:
        return
    audit = AuditSessionRepository(db).get_for_user(audit_session_id, user_id)
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit session not found")


@router.get("", response_model=PaginatedResponse[FindingListItemResponse])
def list_findings(
    audit_session_id: str | None = None,
    severity: Severity | None = None,
    service: AwsService | None = None,
    finding_status: FindingStatus | None = Query(default=None, alias="status"),
    region: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[FindingListItemResponse]:
    _assert_audit_belongs_to_user(db, audit_session_id, current_user.id)

    params = PaginationParams(page=page, page_size=page_size)
    repo = FindingRepository(db)
    items, total = repo.list_filtered(
        audit_session_id=audit_session_id,
        severity=severity,
        service=service,
        status=finding_status,
        region=region,
        search=search,
        offset=params.offset,
        limit=params.page_size,
    )
    dto_items = [FindingListItemResponse.model_validate(f) for f in items]
    return PaginatedResponse.build(dto_items, total, params)


@router.get("/{finding_id}", response_model=FindingDetailResponse)
def get_finding(
    finding_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> FindingDetailResponse:
    finding = FindingRepository(db).get_with_risk_score(finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    _assert_audit_belongs_to_user(db, finding.audit_session_id, current_user.id)
    return FindingDetailResponse.model_validate(finding)


@router.patch("/{finding_id}/status", response_model=FindingDetailResponse)
def update_finding_status(
    finding_id: str,
    payload: FindingStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FindingDetailResponse:
    repo = FindingRepository(db)
    finding = repo.get_with_risk_score(finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    _assert_audit_belongs_to_user(db, finding.audit_session_id, current_user.id)

    finding.status = payload.status
    db.commit()
    # Status is indexed content; refresh the derived index after DB commit.
    try:
        index_audit_findings(db, finding.audit_session_id)
    except Exception:  # noqa: BLE001 - canonical DB data remains correct
        import logging
        logging.getLogger("sentinelai.rag").exception("RAG reindex failed for audit %s", finding.audit_session_id)
    db.refresh(finding)
    return FindingDetailResponse.model_validate(finding)


@router.post("/{finding_id}/ai-explain", response_model=AiExplanationResponse)
def explain_finding(
    finding_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> AiExplanationResponse:
    finding = FindingRepository(db).get(finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    _assert_audit_belongs_to_user(db, finding.audit_session_id, current_user.id)

    explanation, generated_fresh = get_or_generate_explanation(db, finding)
    db.commit()
    return AiExplanationResponse(finding_id=finding.id, ai_explanation=explanation, generated_fresh=generated_fresh)


@router.get("/{finding_id}/iac-example")
def get_iac_example(
    finding_id: str,
    format: Literal["cli", "terraform", "cloudformation"] = "terraform",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, str]:
    finding = FindingRepository(db).get(finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    _assert_audit_belongs_to_user(db, finding.audit_session_id, current_user.id)

    snippet = generate_iac_example(finding, format)
    return {"finding_id": finding.id, "format": format, "snippet": snippet}
