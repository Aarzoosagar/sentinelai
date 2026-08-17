"""ORM model mapping audit findings to compliance-framework control outcomes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TimestampMixin, generate_uuid
from app.models.enums import ComplianceFramework, ComplianceStatus

if TYPE_CHECKING:
    from app.models.audit_session import AuditSession
    from app.models.finding import Finding


class ComplianceResult(Base, TimestampMixin):
    __tablename__ = "compliance_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    audit_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("audit_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    framework: Mapped[ComplianceFramework] = mapped_column(
        Enum(ComplianceFramework), nullable=False, index=True
    )
    control_id: Mapped[str] = mapped_column(String(64), nullable=False)
    control_title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ComplianceStatus] = mapped_column(Enum(ComplianceStatus), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    related_finding_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("findings.id", ondelete="SET NULL"), nullable=True
    )

    audit_session: Mapped["AuditSession"] = relationship(back_populates="compliance_results")
    related_finding: Mapped["Finding | None"] = relationship(back_populates="compliance_results")

    def __repr__(self) -> str:
        return f"<ComplianceResult framework={self.framework} control={self.control_id} status={self.status}>"
