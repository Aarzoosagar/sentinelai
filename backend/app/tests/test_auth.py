"""Tests for registration, login, refresh, and the auth guard."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_register_creates_user(client: TestClient):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "new.user@sentinelai.io", "password": "SuperSecret123", "full_name": "New User"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new.user@sentinelai.io"
    assert body["full_name"] == "New User"
    assert "hashed_password" not in body  # never leak the hash


def test_register_duplicate_email_rejected(client: TestClient):
    payload = {"email": "dup@sentinelai.io", "password": "SuperSecret123", "full_name": "Dup"}
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


def test_login_with_correct_credentials_succeeds(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={"email": "login.test@sentinelai.io", "password": "SuperSecret123", "full_name": "Login Test"},
    )
    resp = client.post(
        "/api/v1/auth/login", json={"email": "login.test@sentinelai.io", "password": "SuperSecret123"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_login_with_wrong_password_rejected(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpw@sentinelai.io", "password": "SuperSecret123", "full_name": "Wrong PW"},
    )
    resp = client.post("/api/v1/auth/login", json={"email": "wrongpw@sentinelai.io", "password": "nope"})
    assert resp.status_code == 401


def test_me_requires_authentication(client: TestClient):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)


def test_me_returns_current_user(client: TestClient, registered_user: dict):
    resp = client.get("/api/v1/auth/me", headers=registered_user["headers"])
    assert resp.status_code == 200
    assert resp.json()["email"] == registered_user["email"]


def test_refresh_token_issues_new_access_token(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={"email": "refresh.test@sentinelai.io", "password": "SuperSecret123", "full_name": "Refresh Test"},
    )
    login = client.post(
        "/api/v1/auth/login", json={"email": "refresh.test@sentinelai.io", "password": "SuperSecret123"}
    )
    refresh_token = login.json()["refresh_token"]

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_refresh_with_access_token_rejected(client: TestClient, registered_user: dict):
    # An access token used where a refresh token is expected must fail —
    # this is the boundary that stops a leaked access token from being
    # used to mint fresh tokens indefinitely.
    access_token = registered_user["headers"]["Authorization"].split(" ")[1]
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401
