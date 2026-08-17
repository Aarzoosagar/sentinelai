"""
Central exception handling.

Registers handlers so every error path in the API returns a consistent
`{"detail": "..."}` JSON body with the right HTTP status code, instead of
each router having to catch its own exceptions.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.services.ai.groq_client import AiServiceError, AiServiceNotConfigured
from app.services.aws.client_factory import WriteOperationBlocked

try:
    from groq import GroqError
except ImportError:  # pragma: no cover - groq is a required dependency, but keep this defensive
    GroqError = None  # type: ignore[assignment,misc]

logger = logging.getLogger("sentinelai")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Validation error", "errors": exc.errors()},
        )

    @app.exception_handler(LookupError)
    async def not_found_handler(request: Request, exc: LookupError):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    @app.exception_handler(PermissionError)
    async def forbidden_handler(request: Request, exc: PermissionError):
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": str(exc)})

    @app.exception_handler(AiServiceNotConfigured)
    async def ai_not_configured_handler(request: Request, exc: AiServiceNotConfigured):
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": str(exc)})

    @app.exception_handler(AiServiceError)
    async def ai_service_error_handler(request: Request, exc: AiServiceError):
        logger.warning("AI service error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": "The AI service is temporarily unavailable. Please try again."},
        )

    if GroqError is not None:

        @app.exception_handler(GroqError)
        async def groq_sdk_error_handler(request: Request, exc: Exception):
            # Any Groq SDK error that wasn't already converted to AiServiceError
            # upstream (e.g. an auth/permission error that we deliberately don't
            # retry) — surface a clean, non-leaky message instead of a 500.
            logger.warning("Unhandled Groq SDK error: %s", exc)
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"detail": "The AI service is temporarily unavailable. Please try again."},
            )

    @app.exception_handler(WriteOperationBlocked)
    async def write_blocked_handler(request: Request, exc: WriteOperationBlocked):
        # This should never trigger in normal operation — it means a collector
        # attempted a mutating AWS call and was stopped by the safety guard.
        logger.error("BLOCKED WRITE OPERATION ATTEMPTED: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "A read-only safety check blocked this operation. This has been logged."},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred."},
        )
