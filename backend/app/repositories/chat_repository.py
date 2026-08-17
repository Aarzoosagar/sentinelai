"""Data access for the ai_messages table (AI Security Chat)."""

from __future__ import annotations

from sqlalchemy import select

from app.models.ai_message import AiMessage
from app.repositories.base import BaseRepository


class ChatRepository(BaseRepository[AiMessage]):
    model = AiMessage

    def list_for_session(self, audit_session_id: str, user_id: str) -> list[AiMessage]:
        stmt = (
            select(AiMessage)
            .where(
                AiMessage.audit_session_id == audit_session_id,
                AiMessage.user_id == user_id,
            )
            .order_by(AiMessage.created_at.asc())
        )
        return list(self.db.scalars(stmt))
