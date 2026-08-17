"""Schemas for the AI Security Chat feature."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ChatRole
from app.schemas.common import ORMBase


class ChatMessageRequest(BaseModel):
    audit_session_id: str
    message: str = Field(min_length=1, max_length=4000)


class ChatMessageResponse(ORMBase):
    id: str
    role: ChatRole
    content: str
    created_at: datetime


class ChatSource(BaseModel):
    finding_id: str
    title: str
    service: str
    severity: str


class ChatReplyResponse(ChatMessageResponse):
    """New reply plus the canonical findings used to ground it."""

    sources: list[ChatSource] = []


class ChatHistoryResponse(BaseModel):
    audit_session_id: str
    messages: list[ChatMessageResponse]


class SuggestedQuestion(BaseModel):
    label: str
    prompt: str


SUGGESTED_QUESTIONS: list[SuggestedQuestion] = [
    SuggestedQuestion(label="Top 5 risks", prompt="What are my top five risks?"),
    SuggestedQuestion(label="Summarize audit", prompt="Summarize my audit."),
    SuggestedQuestion(label="CLI fix", prompt="Show AWS CLI commands to fix the top finding."),
    SuggestedQuestion(label="Terraform fix", prompt="Show a Terraform example to fix the top finding."),
]
