"""
Central configuration for SentinelAI.

Every environment-dependent value (secrets, DB URL, CORS origins, JWT
parameters, rate limits) is read from environment variables via
pydantic-settings. Nothing security-sensitive is hard-coded here.
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────
    app_name: str = Field(default="SentinelAI")
    app_env: str = Field(default="development")
    debug: bool = Field(default=True)
    api_v1_prefix: str = Field(default="/api/v1")

    # ── Security ─────────────────────────────────────────────
    jwt_secret_key: str = Field(...)
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=60)
    jwt_refresh_token_expire_days: int = Field(default=7)
    credentials_encryption_key: str = Field(...)

    # ── Database ─────────────────────────────────────────────
    database_url: str = Field(default="sqlite:///./sentinelai.db")

    # ── CORS ─────────────────────────────────────────────────
    cors_origins: str = Field(default="http://localhost:5173")

    # ── Rate limiting ────────────────────────────────────────
    rate_limit_per_minute: int = Field(default=60)

    # ── Groq AI ──────────────────────────────────────────────
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="llama-3.3-70b-versatile")
    groq_timeout_seconds: int = Field(default=30)
    groq_max_retries: int = Field(default=3)
    groq_temperature: float = Field(default=0.2)
    groq_max_tokens: int = Field(default=2048)
    ai_tool_result_limit: int = Field(default=25, ge=1, le=50)
    ai_observability_enabled: bool = Field(default=True)
    ai_log_sensitive_data: bool = Field(default=False)
    ai_metrics_enabled: bool = Field(default=True)

    # RAG indices are derived from persisted findings, never the source of truth.
    rag_embedding_model: str = Field(default="BAAI/bge-small-en-v1.5")
    rag_index_dir: str = Field(default="./data/rag")
    rag_top_k: int = Field(default=5, ge=1, le=20)
    rag_semantic_candidate_k: int = Field(default=10, ge=1, le=50)
    rag_keyword_candidate_k: int = Field(default=10, ge=1, le=50)
    rag_rerank_candidate_k: int = Field(default=15, ge=1, le=50)
    rag_final_top_k: int = Field(default=5, ge=1, le=20)
    rag_rerank_enabled: bool = Field(default=True)
    rag_reranker_model: str = Field(default="Xenova/ms-marco-MiniLM-L-6-v2")

    # Directory FastEmbed uses to cache downloaded ONNX model files.
    # Development default keeps everything local to the repo checkout;
    # production should point at a persistent, writable directory.
    fastembed_cache_dir: str = Field(default="./.fastembed_cache")

    # ── AWS ──────────────────────────────────────────────────
    aws_default_region: str = Field(default="us-east-1")

    # ── Reports ──────────────────────────────────────────────
    # Directory generated PDF/CSV/JSON audit reports are written to.
    sentinelai_reports_dir: str = Field(default="./generated_reports")

    @field_validator("jwt_secret_key", "credentials_encryption_key")
    @classmethod
    def _reject_placeholder_secrets(cls, value: str) -> str:
        if not value or value.startswith("change-me"):
            raise ValueError(
                "Refusing to start with a placeholder secret. Set a real "
                "JWT_SECRET_KEY / CREDENTIALS_ENCRYPTION_KEY in your .env file."
            )
        return value

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance; environment is only read once per process."""
    return Settings()
