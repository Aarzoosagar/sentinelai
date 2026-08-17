"""AI Security Chat endpoints, grounded strictly in one audit's findings."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database.session import get_db
from app.middleware.auth import get_current_active_user
from app.models.ai_message import AiMessage
from app.models.enums import ChatRole
from app.models.user import User
from app.repositories.audit_repository import AuditSessionRepository
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import (
    SUGGESTED_QUESTIONS,
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatReplyResponse,
    ChatSource,
    SuggestedQuestion,
)
from app.services.ai.chat import get_chat_reply
from app.services.ai.guardrails.input import InputGuardrailViolation, validate_chat_input

router = APIRouter(prefix="/chat", tags=["AI Security Chat"])


@router.get("/suggested-questions", response_model=list[SuggestedQuestion])
def suggested_questions() -> list[SuggestedQuestion]:
    return SUGGESTED_QUESTIONS


@router.get("/{audit_id}/history", response_model=ChatHistoryResponse)
def get_chat_history(
    audit_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> ChatHistoryResponse:
    audit = AuditSessionRepository(db).get_for_user(audit_id, current_user.id)
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit session not found")

    messages = ChatRepository(db).list_for_session(audit_id, current_user.id)
    return ChatHistoryResponse(
        audit_session_id=audit_id,
        messages=[ChatMessageResponse.model_validate(m) for m in messages],
    )


@router.post("/message", response_model=ChatReplyResponse, status_code=status.HTTP_201_CREATED)
def send_chat_message(
    payload: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ChatReplyResponse:
    audit = AuditSessionRepository(db).get_for_user(payload.audit_session_id, current_user.id)
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit session not found")

    chat_repo = ChatRepository(db)
    history = chat_repo.list_for_session(payload.audit_session_id, current_user.id)
    try:
        safe_message = validate_chat_input(payload.message)
    except InputGuardrailViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    user_message = AiMessage(
        user_id=current_user.id,
        audit_session_id=payload.audit_session_id,
        role=ChatRole.USER,
        content=safe_message,
    )
    chat_repo.add(user_message)

    reply_text, retrieved = get_chat_reply(db, audit, current_user.id, history, safe_message)

    assistant_message = AiMessage(
        user_id=current_user.id,
        audit_session_id=payload.audit_session_id,
        role=ChatRole.ASSISTANT,
        content=reply_text,
    )
    chat_repo.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    return ChatReplyResponse(
        **ChatMessageResponse.model_validate(assistant_message).model_dump(),
        sources=[
            ChatSource(
                finding_id=finding.id,
                title=finding.title,
                service=finding.service.value,
                severity=finding.severity.value,
            )
            for finding in retrieved.findings
        ],
    )
