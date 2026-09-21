"""Tests for authentication endpoints."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.auth import create_access_token, hash_password
from app.core.database import get_db
from app.main import app
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def auth_client():
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    async def _override():
        yield mock_db

    app.dependency_overrides[get_db] = _override
    yield TestClient(app, raise_server_exceptions=False), mock_db
    app.dependency_overrides.clear()


def _make_user(password_hash=None, is_active=True):
    user = MagicMock(spec=User)
    user.id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    user.email = "analyst@ledgerdesk.dev"
    user.full_name = "Jane Analyst"
    user.role = "analyst"
    user.is_active = is_active
    user.password_hash = password_hash
    return user


class TestLogin:
    def test_login_with_hashed_password(self, auth_client):
        client, mock_db = auth_client
        pw_hash = hash_password("secret123")
        user = _make_user(password_hash=pw_hash)
        result = MagicMock()
        result.scalar_one_or_none.return_value = user
        mock_db.execute = AsyncMock(return_value=result)

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "analyst@ledgerdesk.dev", "password": "secret123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["role"] == "analyst"
        assert data["email"] == "analyst@ledgerdesk.dev"

    def test_login_demo_password(self, auth_client):
        client, mock_db = auth_client
        user = _make_user(password_hash=None)
        result = MagicMock()
        result.scalar_one_or_none.return_value = user
        mock_db.execute = AsyncMock(return_value=result)

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "analyst@ledgerdesk.dev", "password": "demo123"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, auth_client):
        client, mock_db = auth_client
        pw_hash = hash_password("correct")
        user = _make_user(password_hash=pw_hash)
        result = MagicMock()
        result.scalar_one_or_none.return_value = user
        mock_db.execute = AsyncMock(return_value=result)

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "analyst@ledgerdesk.dev", "password": "wrong"},
        )
        assert resp.status_code == 401

    def test_login_user_not_found(self, auth_client):
        client, mock_db = auth_client
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@test.com", "password": "pass"},
        )
        assert resp.status_code == 401

    def test_login_inactive_user(self, auth_client):
        client, mock_db = auth_client
        user = _make_user(is_active=False)
        result = MagicMock()
        result.scalar_one_or_none.return_value = user
        mock_db.execute = AsyncMock(return_value=result)

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "analyst@ledgerdesk.dev", "password": "demo123"},
        )
        assert resp.status_code == 401


class TestMe:
    def test_me_authenticated(self, auth_client):
        client, mock_db = auth_client
        user = _make_user(password_hash=hash_password("test"))
        token = create_access_token(user)

        # Mock the DB lookup for get_current_user
        result = MagicMock()
        result.scalar_one_or_none.return_value = user
        mock_db.execute = AsyncMock(return_value=result)

        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "analyst@ledgerdesk.dev"
        assert data["role"] == "analyst"

    def test_me_no_token(self, auth_client):
        client, _ = auth_client
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401
