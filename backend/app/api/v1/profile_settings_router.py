"""Profile and per-user settings endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database.session import get_db
from app.core.security import hash_password, verify_password
from app.middleware.auth import get_current_active_user
from app.models.user import User
from app.repositories.settings_repository import SettingsRepository
from app.schemas.auth import UserResponse
from app.schemas.settings import ProfileUpdateRequest, UserSettingsResponse, UserSettingsUpdateRequest

router = APIRouter(tags=["Profile & Settings"])


@router.patch("/profile", response_model=UserResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> User:
    if payload.new_password is not None:
        if not payload.current_password or not verify_password(
            payload.current_password, current_user.hashed_password
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
        current_user.hashed_password = hash_password(payload.new_password)

    if payload.full_name is not None:
        current_user.full_name = payload.full_name

    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/settings", response_model=UserSettingsResponse)
def get_settings_endpoint(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> UserSettingsResponse:
    settings = SettingsRepository(db).get_or_create_for_user(current_user.id)
    db.commit()
    return UserSettingsResponse.model_validate(settings)


@router.patch("/settings", response_model=UserSettingsResponse)
def update_settings_endpoint(
    payload: UserSettingsUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserSettingsResponse:
    repo = SettingsRepository(db)
    settings = repo.get_or_create_for_user(current_user.id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    db.commit()
    db.refresh(settings)
    return UserSettingsResponse.model_validate(settings)
