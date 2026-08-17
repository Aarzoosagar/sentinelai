"""Schemas for per-user application settings."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class UserSettingsResponse(ORMBase):
    groq_model_override: str | None
    email_notifications_enabled: bool
    critical_finding_alerts_enabled: bool
    theme: str


class UserSettingsUpdateRequest(BaseModel):
    groq_model_override: str | None = None
    email_notifications_enabled: bool | None = None
    critical_finding_alerts_enabled: bool | None = None
    theme: str | None = Field(default=None, pattern="^dark$")  # dark mode only, per spec


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    current_password: str | None = Field(default=None, min_length=1)
    new_password: str | None = Field(default=None, min_length=8, max_length=128)
