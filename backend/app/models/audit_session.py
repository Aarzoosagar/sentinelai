"""ORM model for a single audit run against one AWS account."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TimestampMixin, generate_uuid
from app.models.enums import AuditStatus

if TYPE_CHECKING:
    from app.models.aws_account import AwsAccount
    from app.models.finding import Finding
    from app.models.compliance_result import ComplianceResult
    from app.models.report import Report
    from app.models.ai_message import AiMessage


class AuditSession(Base, TimestampMixin):
    __tablename__ = "audit_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    aws_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("aws_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[AuditStatus] = mapped_column(
        Enum(AuditStatus), nullable=False, default=AuditStatus.QUEUED
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    resources_scanned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    security_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-100
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    aws_account: Mapped["AwsAccount"] = relationship(back_populates="audit_sessions")
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="audit_session", cascade="all, delete-orphan"
    )
    compliance_results: Mapped[list["ComplianceResult"]] = relationship(
        back_populates="audit_session", cascade="all, delete-orphan"
    )
    reports: Mapped[list["Report"]] = relationship(
        back_populates="audit_session", cascade="all, delete-orphan"
    )
    ai_messages: Mapped[list["AiMessage"]] = relationship(
        back_populates="audit_session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AuditSession id={self.id} status={self.status}>"
