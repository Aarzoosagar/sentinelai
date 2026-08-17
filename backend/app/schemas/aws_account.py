"""Schemas for connecting and validating AWS accounts (read-only)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import AccountValidationStatus, AwsAuthMethod
from app.schemas.common import ORMBase


class AwsAccountCreateRequest(BaseModel):
    account_alias: str = Field(min_length=1, max_length=255)
    aws_account_id: str = Field(min_length=12, max_length=12, pattern=r"^\d{12}$")
    region: str = Field(default="us-east-1", max_length=32)
    auth_method: AwsAuthMethod = AwsAuthMethod.ASSUME_ROLE

    # AssumeRole path
    role_arn: str | None = Field(default=None, max_length=255)
    external_id: str | None = Field(default=None, max_length=255)

    # Static access-key path (not recommended; encrypted at rest if used)
    access_key_id: str | None = Field(default=None, max_length=128)
    secret_access_key: str | None = Field(default=None, max_length=256)

    @model_validator(mode="after")
    def validate_credentials_present(self) -> "AwsAccountCreateRequest":
        if self.auth_method == AwsAuthMethod.ASSUME_ROLE:
            if not self.role_arn:
                raise ValueError("role_arn is required when auth_method is assume_role")
        else:
            if not self.access_key_id or not self.secret_access_key:
                raise ValueError(
                    "access_key_id and secret_access_key are required when auth_method is access_key"
                )
        return self


class AwsAccountResponse(ORMBase):
    id: str
    account_alias: str
    aws_account_id: str
    region: str
    auth_method: AwsAuthMethod
    validation_status: AccountValidationStatus
    validated_at: datetime | None
    created_at: datetime
    # role_arn is safe to expose (not a secret); access keys are never returned
    role_arn: str | None


class AwsAccountValidationResponse(BaseModel):
    account_id: str
    validation_status: AccountValidationStatus
    caller_identity_arn: str | None = None
    error: str | None = None
