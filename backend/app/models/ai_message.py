"""ORM model for AI Security Chat message history."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TimestampMixin, generate_uuid
from app.models.enums import ChatRole

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.audit_session import AuditSession


class AiMessage(Base, TimestampMixin):
    __tablename__ = "ai_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    audit_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("audit_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    role: Mapped[ChatRole] = mapped_column(Enum(ChatRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped["User"] = relationship(back_populates="ai_messages")
    audit_session: Mapped["AuditSession"] = relationship(back_populates="ai_messages")

    def __repr__(self) -> str:
        return f"<AiMessage id={self.id} role={self.role}>"
