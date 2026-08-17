"""Schemas for the audit lifecycle: start, poll status, history."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import AuditStatus
from app.schemas.common import ORMBase


class AuditStartRequest(BaseModel):
    aws_account_id: str


class AuditSessionResponse(ORMBase):
    id: str
    aws_account_id: str
    status: AuditStatus
    started_at: datetime | None
    completed_at: datetime | None
    resources_scanned: int
    security_score: int | None
    error_message: str | None
    created_at: datetime


class AuditProgressResponse(BaseModel):
    id: str
    status: AuditStatus
    current_step: str | None = None
    services_completed: list[str] = []
    services_total: int = 9
    resources_scanned: int = 0
