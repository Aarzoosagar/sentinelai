"""
ORM model for connected AWS accounts.

Supports two auth methods:
  - AssumeRole (preferred): role_arn + external_id, no secrets stored.
  - Static access keys (fallback): stored encrypted via app.core.security.
Only ReadOnly-scoped credentials are ever expected; the API layer never
exposes decrypted secret values in responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TimestampMixin, generate_uuid
from app.models.enums import AccountValidationStatus, AwsAuthMethod

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.audit_session import AuditSession


class AwsAccount(Base, TimestampMixin):
    __tablename__ = "aws_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    account_alias: Mapped[str] = mapped_column(String(255), nullable=False)
    aws_account_id: Mapped[str] = mapped_column(String(12), nullable=False)
    region: Mapped[str] = mapped_column(String(32), nullable=False, default="us-east-1")

    auth_method: Mapped[AwsAuthMethod] = mapped_column(
        Enum(AwsAuthMethod), nullable=False, default=AwsAuthMethod.ASSUME_ROLE
    )

    # AssumeRole fields (no secrets)
    role_arn: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Static access-key fields — always Fernet-encrypted at rest.
    encrypted_access_key_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    encrypted_secret_access_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    validation_status: Mapped[AccountValidationStatus] = mapped_column(
        Enum(AccountValidationStatus), nullable=False, default=AccountValidationStatus.PENDING
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="aws_accounts")
    audit_sessions: Mapped[list["AuditSession"]] = relationship(
        back_populates="aws_account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AwsAccount id={self.id} alias={self.account_alias}>"
