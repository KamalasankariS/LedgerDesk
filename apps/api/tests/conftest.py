"""Shared test fixtures for API tests."""

import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure app is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.auth import create_access_token
from app.core.database import get_db
from app.main import app
from app.models.user import User


@pytest.fixture
def mock_db():
    """Provide a mocked AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def demo_user():
    """A demo analyst user for auth-dependent tests."""
    return User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        email="analyst@ledgerdesk.dev",
        full_name="Jane Analyst",
        role="analyst",
        is_active=True,
    )


@pytest.fixture
def admin_user():
    """An admin user."""
    return User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        email="admin@ledgerdesk.dev",
        full_name="System Admin",
        role="admin",
        is_active=True,
    )


@pytest.fixture
def auth_headers(demo_user):
    """JWT auth headers for an analyst user."""
    token = create_access_token(demo_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(admin_user):
    """JWT auth headers for an admin user."""
    token = create_access_token(admin_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(mock_db, demo_user):
    """TestClient with mocked DB and auth overridden to return demo_user."""
    from app.core.auth import get_current_user

    async def _override_get_db():
        yield mock_db

    async def _override_get_current_user():
        return demo_user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()
