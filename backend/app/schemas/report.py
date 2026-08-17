"""Schemas for generating and listing exportable reports."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ReportCategory, ReportType
from app.schemas.common import ORMBase


class ReportGenerateRequest(BaseModel):
    audit_session_id: str
    type: ReportType
    category: ReportCategory


class ReportResponse(ORMBase):
    id: str
    audit_session_id: str
    type: ReportType
    category: ReportCategory
    generated_at: datetime


class ReportDownloadResponse(BaseModel):
    id: str
    download_url: str
    filename: str
