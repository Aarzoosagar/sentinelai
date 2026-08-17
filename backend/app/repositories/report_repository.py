"""Data access for the reports table."""

from __future__ import annotations

from sqlalchemy import select

from app.models.report import Report
from app.repositories.base import BaseRepository


class ReportRepository(BaseRepository[Report]):
    model = Report

    def list_for_audit(self, audit_session_id: str) -> list[Report]:
        stmt = (
            select(Report)
            .where(Report.audit_session_id == audit_session_id)
            .order_by(Report.generated_at.desc())
        )
        return list(self.db.scalars(stmt))

    def list_for_user(self, user_id: str) -> list[Report]:
        from app.models.audit_session import AuditSession
        from app.models.aws_account import AwsAccount

        stmt = (
            select(Report)
            .join(AuditSession, Report.audit_session_id == AuditSession.id)
            .join(AwsAccount, AuditSession.aws_account_id == AwsAccount.id)
            .where(AwsAccount.user_id == user_id)
            .order_by(Report.generated_at.desc())
        )
        return list(self.db.scalars(stmt))
