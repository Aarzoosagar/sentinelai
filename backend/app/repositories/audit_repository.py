"""Data access for the audit_sessions table."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models.audit_session import AuditSession
from app.models.aws_account import AwsAccount
from app.models.enums import AuditStatus
from app.repositories.base import BaseRepository


class AuditSessionRepository(BaseRepository[AuditSession]):
    model = AuditSession

    def list_for_user(self, user_id: str, limit: int = 50) -> list[AuditSession]:
        stmt = (
            select(AuditSession)
            .join(AwsAccount, AuditSession.aws_account_id == AwsAccount.id)
            .where(AwsAccount.user_id == user_id)
            .options(joinedload(AuditSession.aws_account))
            .order_by(AuditSession.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).unique())

    def get_for_user(self, audit_id: str, user_id: str) -> AuditSession | None:
        stmt = (
            select(AuditSession)
            .join(AwsAccount, AuditSession.aws_account_id == AwsAccount.id)
            .where(AuditSession.id == audit_id, AwsAccount.user_id == user_id)
        )
        return self.db.scalar(stmt)

    def latest_completed_for_account(self, aws_account_id: str) -> AuditSession | None:
        stmt = (
            select(AuditSession)
            .where(
                AuditSession.aws_account_id == aws_account_id,
                AuditSession.status == AuditStatus.COMPLETED,
            )
            .order_by(AuditSession.completed_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)
