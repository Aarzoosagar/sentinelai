"""
Security primitives: password hashing, JWT issuance/verification, and
symmetric encryption for any AWS static credentials stored at rest.

AssumeRole (role_arn + external_id) is the recommended AWS auth method and
requires no secret storage at all. Static access keys are supported as a
fallback and are always encrypted before hitting the database — see
services/aws/client_factory.py for how these are consumed.
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config.settings import get_settings

settings = get_settings()
_fernet = Fernet(settings.credentials_encryption_key.encode())


# ── Password hashing ─────────────────────────────────────────────────────


def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except ValueError:
        return False


# ── JWT ───────────────────────────────────────────────────────────────────


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    sub: str
    type: TokenType
    exp: datetime
    iat: datetime


def _create_token(subject: str, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str) -> str:
    return _create_token(
        subject,
        TokenType.ACCESS,
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject,
        TokenType.REFRESH,
        timedelta(days=settings.jwt_refresh_token_expire_days),
    )


class InvalidTokenError(Exception):
    """Raised when a JWT is malformed, expired, or of the wrong type."""


def decode_token(token: str, expected_type: TokenType = TokenType.ACCESS) -> TokenPayload:
    try:
        raw: dict[str, Any] = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise InvalidTokenError("Token is invalid or expired") from exc

    payload = TokenPayload.model_validate(raw)
    if payload.type != expected_type:
        raise InvalidTokenError(
            f"Expected a {expected_type.value} token, got {payload.type.value}"
        )
    return payload


# ── AWS credential encryption (Fernet, symmetric) ───────────────────────


def encrypt_secret(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Stored credential could not be decrypted") from exc
