"""Tests for user management endpoints."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from app.models.user import User


def _make_user_obj(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        email="test@ledgerdesk.dev",
        full_name="Test User",
        role="analyst",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    user = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _mock_scalar_result(items):
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = items
    result.scalars.return_value = scalars
    return result


def _mock_scalar_one(item):
    result = MagicMock()
    result.scalar_one_or_none.return_value = item
    return result


class TestListUsers:
    def test_list_users(self, client, mock_db):
        user = _make_user_obj()
        mock_db.execute = AsyncMock(return_value=_mock_scalar_result([user]))
        resp = client.get("/api/v1/users")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["email"] == "test@ledgerdesk.dev"


class TestCreateUser:
    def test_create_user(self, client, mock_db):
        # First call: check email uniqueness (no match)
        # Second call: not needed for create
        mock_db.execute = AsyncMock(return_value=_mock_scalar_one(None))
        resp = client.post(
            "/api/v1/users",
            json={
                "email": "new@ledgerdesk.dev",
                "full_name": "New User",
                "role": "analyst",
                "password": "testpass123",
            },
        )
        assert resp.status_code == 201
        assert mock_db.add.called

    def test_create_duplicate_email(self, client, mock_db):
        existing = _make_user_obj(email="dup@test.com")
        mock_db.execute = AsyncMock(return_value=_mock_scalar_one(existing))
        resp = client.post(
            "/api/v1/users",
            json={
                "email": "dup@test.com",
                "full_name": "Dup",
                "role": "analyst",
                "password": "pass",
            },
        )
        assert resp.status_code == 409

    def test_create_invalid_role(self, client, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_scalar_one(None))
        resp = client.post(
            "/api/v1/users",
            json={
                "email": "bad@test.com",
                "full_name": "Bad Role",
                "role": "superuser",
                "password": "pass",
            },
        )
        assert resp.status_code == 422


class TestUpdateUser:
    def test_update_user(self, client, mock_db):
        user = _make_user_obj()
        mock_db.execute = AsyncMock(return_value=_mock_scalar_one(user))
        resp = client.patch(
            f"/api/v1/users/{user.id}",
            json={"full_name": "Updated Name"},
        )
        assert resp.status_code == 200

    def test_update_nonexistent(self, client, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_scalar_one(None))
        resp = client.patch(
            f"/api/v1/users/{uuid.uuid4()}",
            json={"full_name": "Ghost"},
        )
        assert resp.status_code == 404


class TestDeactivateUser:
    def test_deactivate_user(self, client, mock_db):
        user = _make_user_obj()
        mock_db.execute = AsyncMock(return_value=_mock_scalar_one(user))
        resp = client.delete(f"/api/v1/users/{user.id}")
        assert resp.status_code == 204

    def test_deactivate_nonexistent(self, client, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_scalar_one(None))
        resp = client.delete(f"/api/v1/users/{uuid.uuid4()}")
        assert resp.status_code == 404
