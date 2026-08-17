"""
Shared pytest fixtures.

Every test gets a fresh in-memory SQLite database (via StaticPool so the
same in-memory DB is shared across connections within one test) and a
FastAPI TestClient with `get_db` overridden to use it — so tests never
touch the real `sentinelai.db` file.
"""

from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production-use-only-in-pytest")
os.environ.setdefault("CREDENTIALS_ENCRYPTION_KEY", "3rF9wZ2mQvT8xN1pL6yB4cJ0hK7sD5aE2gU9iO3nM8Y=")
os.environ.setdefault("GROQ_API_KEY", "test-key-not-real")
os.environ.setdefault("DATABASE_URL", "sqlite://")
# Some development shells use DEBUG=release for other tooling.  Settings
# expects a boolean, so make the test process deterministic regardless of
# the inherited host environment.
os.environ["DEBUG"] = "true"
# Unit tests mock the reranker where ordering is under test; avoid downloading
# its ONNX model for unrelated API and persistence tests.
os.environ.setdefault("RAG_RERANK_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database.base import Base
from app.core.database.session import get_db
import app.models  # noqa: F401 - registers all ORM models on Base.metadata
from app.main import app


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db_session(db_engine):
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_engine):
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def _override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def registered_user(client: TestClient) -> dict:
    """Registers a user and returns {email, password, headers}."""
    email = "pytest.user@sentinelai.io"
    password = "TestPassword123"
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Pytest User"},
    )
    assert resp.status_code == 201, resp.text

    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]

    return {"email": email, "password": password, "headers": {"Authorization": f"Bearer {token}"}}
