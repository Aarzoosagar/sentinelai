"""Data access for the findings table, including filtered listing for the UI."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from app.models.enums import AwsService, FindingStatus, Severity
from app.models.finding import Finding
from app.repositories.base import BaseRepository


class FindingRepository(BaseRepository[Finding]):
    model = Finding

    def get_with_risk_score(self, finding_id: str) -> Finding | None:
        stmt = (
            select(Finding)
            .where(Finding.id == finding_id)
            .options(joinedload(Finding.risk_score))
        )
        return self.db.scalar(stmt)

    def list_filtered(
        self,
        *,
        audit_session_id: str | None = None,
        severity: Severity | None = None,
        service: AwsService | None = None,
        status: FindingStatus | None = None,
        region: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 25,
    ) -> tuple[list[Finding], int]:
        stmt = select(Finding)
        count_stmt = select(func.count(Finding.id))

        conditions = []
        if audit_session_id:
            conditions.append(Finding.audit_session_id == audit_session_id)
        if severity:
            conditions.append(Finding.severity == severity)
        if service:
            conditions.append(Finding.service == service)
        if status:
            conditions.append(Finding.status == status)
        if region:
            conditions.append(Finding.region == region)
        if search:
            like = f"%{search}%"
            conditions.append(or_(Finding.title.ilike(like), Finding.description.ilike(like)))

        for condition in conditions:
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        total = self.db.scalar(count_stmt) or 0
        stmt = stmt.order_by(Finding.created_at.desc()).offset(offset).limit(limit)
        items = list(self.db.scalars(stmt))
        return items, total

    def list_for_audit(self, audit_session_id: str) -> list[Finding]:
        stmt = select(Finding).where(Finding.audit_session_id == audit_session_id)
        return list(self.db.scalars(stmt))

    def count_by_severity(self, audit_session_id: str) -> dict[str, int]:
        stmt = (
            select(Finding.severity, func.count(Finding.id))
            .where(Finding.audit_session_id == audit_session_id)
            .group_by(Finding.severity)
        )
        rows = self.db.execute(stmt).all()
        return {severity.value: count for severity, count in rows}
