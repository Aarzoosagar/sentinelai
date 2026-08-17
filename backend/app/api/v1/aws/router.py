"""AWS account connection and validation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database.session import get_db
from app.core.security import encrypt_secret
from app.middleware.auth import get_current_active_user
from app.models.aws_account import AwsAccount
from app.models.enums import AccountValidationStatus, AwsAuthMethod
from app.models.user import User
from app.repositories.aws_account_repository import AwsAccountRepository
from app.schemas.aws_account import (
    AwsAccountCreateRequest,
    AwsAccountResponse,
    AwsAccountValidationResponse,
)
from app.services.aws.client_factory import validate_account

router = APIRouter(prefix="/aws", tags=["AWS Accounts"])


@router.post("/accounts", response_model=AwsAccountResponse, status_code=status.HTTP_201_CREATED)
def connect_account(
    payload: AwsAccountCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AwsAccount:
    repo = AwsAccountRepository(db)

    account = AwsAccount(
        user_id=current_user.id,
        account_alias=payload.account_alias,
        aws_account_id=payload.aws_account_id,
        region=payload.region,
        auth_method=payload.auth_method,
        role_arn=payload.role_arn,
        external_id=payload.external_id,
    )
    if payload.auth_method == AwsAuthMethod.ACCESS_KEY:
        account.encrypted_access_key_id = encrypt_secret(payload.access_key_id)
        account.encrypted_secret_access_key = encrypt_secret(payload.secret_access_key)

    repo.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/accounts", response_model=list[AwsAccountResponse])
def list_accounts(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> list[AwsAccount]:
    return AwsAccountRepository(db).list_for_user(current_user.id)


@router.get("/accounts/{account_id}", response_model=AwsAccountResponse)
def get_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AwsAccount:
    account = AwsAccountRepository(db).get_for_user(account_id, current_user.id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AWS account not found")
    return account


@router.post("/accounts/{account_id}/validate", response_model=AwsAccountValidationResponse)
def validate_aws_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AwsAccountValidationResponse:
    repo = AwsAccountRepository(db)
    account = repo.get_for_user(account_id, current_user.id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AWS account not found")

    is_valid, caller_arn, error = validate_account(account)
    account.validation_status = AccountValidationStatus.VALID if is_valid else AccountValidationStatus.INVALID
    from app.core.database.base import utcnow

    account.validated_at = utcnow()
    db.commit()
    db.refresh(account)

    return AwsAccountValidationResponse(
        account_id=account.id,
        validation_status=account.validation_status,
        caller_identity_arn=caller_arn,
        error=error,
    )
