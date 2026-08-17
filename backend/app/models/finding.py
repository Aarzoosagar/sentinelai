"""ORM model for individual security findings discovered during an audit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TimestampMixin, generate_uuid
from app.models.enums import AwsService, FindingStatus, Severity

if TYPE_CHECKING:
    from app.models.audit_session import AuditSession
    from app.models.risk_score import RiskScore
    from app.models.compliance_result import ComplianceResult


class Finding(Base, TimestampMixin):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    audit_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("audit_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    service: Mapped[AwsService] = mapped_column(Enum(AwsService), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), nullable=False, index=True)
    status: Mapped[FindingStatus] = mapped_column(
        Enum(FindingStatus), nullable=False, default=FindingStatus.OPEN, index=True
    )

    resource_arn: Mapped[str | None] = mapped_column(String(512), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Framework/control mappings
    cis_control: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nist_control: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mitre_attack: Mapped[str | None] = mapped_column(String(128), nullable=True)

    remediation: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_remediation_time: Mapped[str | None] = mapped_column(String(64), nullable=True)
    references: Mapped[str | None] = mapped_column(Text, nullable=True)  # newline-separated URLs

    # AI-generated narrative, cached after first request (see services/ai)
    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    audit_session: Mapped["AuditSession"] = relationship(back_populates="findings")
    risk_score: Mapped["RiskScore | None"] = relationship(
        back_populates="finding", cascade="all, delete-orphan", uselist=False
    )
    compliance_results: Mapped[list["ComplianceResult"]] = relationship(
        back_populates="related_finding"
    )

    def __repr__(self) -> str:
        return f"<Finding id={self.id} title={self.title!r} severity={self.severity}>"
