"""ORM model holding the computed risk score breakdown for a finding."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.finding import Finding


class RiskScore(Base, TimestampMixin):
    __tablename__ = "risk_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    finding_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100
    likelihood: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    business_impact: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    exploitability: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # 1-5

    finding: Mapped["Finding"] = relationship(back_populates="risk_score")

    def __repr__(self) -> str:
        return f"<RiskScore finding_id={self.finding_id} score={self.risk_score}>"
