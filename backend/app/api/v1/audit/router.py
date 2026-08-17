"""
Audit lifecycle endpoints.

POST /audit/start kicks off the full 9-service collection pipeline in a
FastAPI BackgroundTask (so the HTTP response returns immediately with a
QUEUED session) and the client polls GET /audit/{id}/status for progress.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database.base import utcnow
from app.core.database.session import SessionLocal, get_db
from app.middleware.auth import get_current_active_user
from app.models.audit_session import AuditSession
from app.models.enums import AuditStatus
from app.models.user import User
from app.repositories.audit_repository import AuditSessionRepository
from app.repositories.aws_account_repository import AwsAccountRepository
from app.schemas.audit_session import AuditProgressResponse, AuditSessionResponse, AuditStartRequest
from app.services.aws.orchestrator import run_full_audit
from app.services.risk.engine import process_audit
from app.services.rag.retrieval import index_audit_findings

logger = logging.getLogger("sentinelai.audit")

router = APIRouter(prefix="/audit", tags=["Audit"])


def _run_audit_background(audit_session_id: str) -> None:
    """Runs in a background task with its own DB session (request-scoped
    session is already closed by the time this executes)."""
    db = SessionLocal()
    try:
        audit_repo = AuditSessionRepository(db)
        audit = audit_repo.get(audit_session_id)
        if audit is None:
            return

        audit.status = AuditStatus.RUNNING
        audit.started_at = utcnow()
        db.commit()

        account = audit.aws_account
        try:
            collection = run_full_audit(account)
            security_score = process_audit(db, audit.id, collection.findings)

            # Findings have been normalized and persisted. RAG is derived, so a
            # failure is logged but must not make a successful audit fail.
            try:
                db.flush()
                index_audit_findings(db, audit.id)
            except Exception:  # noqa: BLE001 - index can be rebuilt from the DB
                logger.exception("RAG indexing failed for audit %s; completing without a derived index", audit.id)

            audit.resources_scanned = collection.resources_scanned
            audit.security_score = security_score
            audit.status = AuditStatus.COMPLETED
            audit.completed_at = utcnow()
            if collection.service_errors:
                audit.error_message = "; ".join(
                    f"{svc}: {err}" for svc, err in collection.service_errors.items()
                )
            db.commit()
        except Exception as exc:  # noqa: BLE001 - must not leave the session stuck in RUNNING
            logger.exception("Audit %s failed", audit_session_id)
            audit.status = AuditStatus.FAILED
            audit.error_message = str(exc)
            audit.completed_at = utcnow()
            db.commit()
    finally:
        db.close()


@router.post("/start", response_model=AuditSessionResponse, status_code=status.HTTP_202_ACCEPTED)
def start_audit(
    payload: AuditStartRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AuditSession:
    account = AwsAccountRepository(db).get_for_user(payload.aws_account_id, current_user.id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AWS account not found")

    audit = AuditSession(aws_account_id=account.id, status=AuditStatus.QUEUED)
    AuditSessionRepository(db).add(audit)
    db.commit()
    db.refresh(audit)

    background_tasks.add_task(_run_audit_background, audit.id)
    return audit


@router.get("/{audit_id}/status", response_model=AuditProgressResponse)
def get_audit_status(
    audit_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> AuditProgressResponse:
    audit = AuditSessionRepository(db).get_for_user(audit_id, current_user.id)
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit session not found")

    return AuditProgressResponse(
        id=audit.id,
        status=audit.status,
        resources_scanned=audit.resources_scanned,
    )


@router.get("/{audit_id}", response_model=AuditSessionResponse)
def get_audit(
    audit_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> AuditSession:
    audit = AuditSessionRepository(db).get_for_user(audit_id, current_user.id)
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit session not found")
    return audit


@router.get("/history/all", response_model=list[AuditSessionResponse])
def audit_history(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> list[AuditSession]:
    return AuditSessionRepository(db).list_for_user(current_user.id)
