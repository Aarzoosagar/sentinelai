"""Compliance overview endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database.session import get_db
from app.middleware.auth import get_current_active_user
from app.models.enums import ComplianceFramework, ComplianceStatus
from app.models.user import User
from app.repositories.audit_repository import AuditSessionRepository
from app.repositories.compliance_repository import ComplianceResultRepository
from app.schemas.compliance import (
    ComplianceFrameworkSummary,
    ComplianceOverviewResponse,
    ComplianceResultResponse,
)
from app.services.risk.compliance_mapper import compute_framework_score

router = APIRouter(prefix="/compliance", tags=["Compliance"])


@router.get("/{audit_id}", response_model=ComplianceOverviewResponse)
def get_compliance_overview(
    audit_id: str,
    framework: ComplianceFramework | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ComplianceOverviewResponse:
    audit = AuditSessionRepository(db).get_for_user(audit_id, current_user.id)
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit session not found")

    repo = ComplianceResultRepository(db)
    frameworks_to_show = [framework] if framework else repo.frameworks_present(audit_id)

    summaries = []
    for fw in frameworks_to_show:
        results = repo.list_for_audit(audit_id, fw)
        if not results:
            continue
        summaries.append(
            ComplianceFrameworkSummary(
                framework=fw,
                score=compute_framework_score(results),
                passed=sum(1 for r in results if r.status == ComplianceStatus.PASS),
                warnings=sum(1 for r in results if r.status == ComplianceStatus.WARNING),
                failed=sum(1 for r in results if r.status == ComplianceStatus.FAIL),
                total_controls=len(results),
                results=[ComplianceResultResponse.model_validate(r) for r in results],
            )
        )

    return ComplianceOverviewResponse(audit_session_id=audit_id, frameworks=summaries)
