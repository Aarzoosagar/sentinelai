"""Data access for the aws_accounts table."""

from __future__ import annotations

from sqlalchemy import select

from app.models.aws_account import AwsAccount
from app.repositories.base import BaseRepository


class AwsAccountRepository(BaseRepository[AwsAccount]):
    model = AwsAccount

    def list_for_user(self, user_id: str) -> list[AwsAccount]:
        stmt = select(AwsAccount).where(AwsAccount.user_id == user_id).order_by(
            AwsAccount.created_at.desc()
        )
        return list(self.db.scalars(stmt))

    def get_for_user(self, account_id: str, user_id: str) -> AwsAccount | None:
        stmt = select(AwsAccount).where(
            AwsAccount.id == account_id, AwsAccount.user_id == user_id
        )
        return self.db.scalar(stmt)
