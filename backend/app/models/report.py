"""ORM model for generated report artifacts (PDF/CSV/JSON)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TimestampMixin, generate_uuid, utcnow
from app.models.enums import ReportCategory, ReportType

if TYPE_CHECKING:
    from app.models.audit_session import AuditSession


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    audit_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("audit_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    type: Mapped[ReportType] = mapped_column(Enum(ReportType), nullable=False)
    category: Mapped[ReportCategory] = mapped_column(Enum(ReportCategory), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    audit_session: Mapped["AuditSession"] = relationship(back_populates="reports")

    def __repr__(self) -> str:
        return f"<Report id={self.id} type={self.type} category={self.category}>"
