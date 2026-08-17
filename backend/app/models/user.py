"""ORM model for application users (people who log into SentinelAI)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.aws_account import AwsAccount
    from app.models.ai_message import AiMessage
    from app.models.settings import UserSettings


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    aws_accounts: Mapped[list["AwsAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    ai_messages: Mapped[list["AiMessage"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    settings: Mapped["UserSettings | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
