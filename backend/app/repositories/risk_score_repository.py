"""Data access for the risk_scores table."""

from __future__ import annotations

from sqlalchemy import select

from app.models.risk_score import RiskScore
from app.repositories.base import BaseRepository


class RiskScoreRepository(BaseRepository[RiskScore]):
    model = RiskScore

    def get_for_finding(self, finding_id: str) -> RiskScore | None:
        stmt = select(RiskScore).where(RiskScore.finding_id == finding_id)
        return self.db.scalar(stmt)
