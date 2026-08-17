"""SentinelAI FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.core.config.settings import get_settings
from app.core.database.base import Base
from app.core.database.session import engine
from app.middleware.exceptions import register_exception_handlers
from app.middleware.rate_limit import limiter
from app.services.ai.observability import current_request_id, reset_correlation, set_correlation

# Importing app.models registers every ORM model on Base.metadata before
# create_all runs below.
import app.models  # noqa: F401,E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentinelai")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # SQLite convenience path for local/demo use only. Production schema
    # management is handled out-of-band via `alembic upgrade head` — the
    # app must never call create_all() when running in production, since
    # that would bypass the Alembic migration history.
    if settings.app_env != "production" and settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
    logger.info("SentinelAI backend started (env=%s)", settings.app_env)
    yield


app = FastAPI(
    title=settings.app_name,
    description="AI-Powered AWS Cloud Security Auditor — read-only by design.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def ai_correlation_middleware(request: Request, call_next):
    tokens = set_correlation(request.headers.get("X-Request-ID"))
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = current_request_id() or ""
        return response
    finally:
        reset_correlation(tokens)

register_exception_handlers(app)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/api/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
