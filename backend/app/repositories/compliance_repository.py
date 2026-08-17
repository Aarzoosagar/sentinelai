"""Data access for the compliance_results table."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models.compliance_result import ComplianceResult
from app.models.enums import ComplianceFramework, ComplianceStatus
from app.repositories.base import BaseRepository


class ComplianceResultRepository(BaseRepository[ComplianceResult]):
    model = ComplianceResult

    def list_for_audit(
        self, audit_session_id: str, framework: ComplianceFramework | None = None
    ) -> list[ComplianceResult]:
        stmt = select(ComplianceResult).where(
            ComplianceResult.audit_session_id == audit_session_id
        )
        if framework:
            stmt = stmt.where(ComplianceResult.framework == framework)
        return list(self.db.scalars(stmt))

    def frameworks_present(self, audit_session_id: str) -> list[ComplianceFramework]:
        stmt = (
            select(ComplianceResult.framework)
            .where(ComplianceResult.audit_session_id == audit_session_id)
            .distinct()
        )
        return list(self.db.scalars(stmt))

    def status_counts(
        self, audit_session_id: str, framework: ComplianceFramework
    ) -> dict[ComplianceStatus, int]:
        stmt = (
            select(ComplianceResult.status, func.count(ComplianceResult.id))
            .where(
                ComplianceResult.audit_session_id == audit_session_id,
                ComplianceResult.framework == framework,
            )
            .group_by(ComplianceResult.status)
        )
        rows = self.db.execute(stmt).all()
        counts = {ComplianceStatus.PASS: 0, ComplianceStatus.WARNING: 0, ComplianceStatus.FAIL: 0}
        counts.update(dict(rows))
        return counts

    def bulk_add(self, results: list[ComplianceResult]) -> None:
        self.db.add_all(results)
        self.db.flush()
