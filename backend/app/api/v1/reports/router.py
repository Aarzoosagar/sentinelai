"""Report generation and download endpoints."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database.session import get_db
from app.middleware.auth import get_current_active_user
from app.models.user import User
from app.repositories.audit_repository import AuditSessionRepository
from app.repositories.compliance_repository import ComplianceResultRepository
from app.repositories.finding_repository import FindingRepository
from app.repositories.report_repository import ReportRepository
from app.schemas.report import ReportGenerateRequest, ReportResponse
from app.services.ai.summary import generate_executive_summary
from app.services.reports.report_service import generate_report

router = APIRouter(prefix="/reports", tags=["Reports"])

_MEDIA_TYPES = {"pdf": "application/pdf", "csv": "text/csv", "json": "application/json"}


@router.post("/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def generate_report_endpoint(
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ReportResponse:
    audit = AuditSessionRepository(db).get_for_user(payload.audit_session_id, current_user.id)
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit session not found")

    findings = FindingRepository(db).list_for_audit(audit.id)
    compliance_results = ComplianceResultRepository(db).list_for_audit(audit.id)

    ai_summary = None
    try:
        ai_summary = generate_executive_summary(audit, findings)
    except Exception:  # noqa: BLE001 - report generation should succeed even if AI is unavailable
        ai_summary = None

    report = generate_report(
        db, audit, findings, compliance_results, payload.type, payload.category, ai_summary=ai_summary
    )
    db.commit()
    db.refresh(report)
    return report


@router.get("/audit/{audit_id}", response_model=list[ReportResponse])
def list_reports_for_audit(
    audit_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> list[ReportResponse]:
    audit = AuditSessionRepository(db).get_for_user(audit_id, current_user.id)
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit session not found")
    return ReportRepository(db).list_for_audit(audit_id)


@router.get("/{report_id}/download")
def download_report(
    report_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> FileResponse:
    report_repo = ReportRepository(db)
    report = report_repo.get(report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    audit = AuditSessionRepository(db).get_for_user(report.audit_session_id, current_user.id)
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if not os.path.exists(report.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file is no longer available")

    filename = os.path.basename(report.file_path)
    return FileResponse(
        path=report.file_path,
        media_type=_MEDIA_TYPES[report.type.value],
        filename=filename,
    )
