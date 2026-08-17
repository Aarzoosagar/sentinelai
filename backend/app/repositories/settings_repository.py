"""Data access for the settings table."""

from __future__ import annotations

from sqlalchemy import select

from app.models.settings import UserSettings
from app.repositories.base import BaseRepository


class SettingsRepository(BaseRepository[UserSettings]):
    model = UserSettings

    def get_for_user(self, user_id: str) -> UserSettings | None:
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        return self.db.scalar(stmt)

    def get_or_create_for_user(self, user_id: str) -> UserSettings:
        existing = self.get_for_user(user_id)
        if existing is not None:
            return existing
        created = UserSettings(user_id=user_id)
        return self.add(created)
