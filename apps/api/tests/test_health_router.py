"""Tests for health check endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.database import get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def client():
    mock_db = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.scalar.return_value = 1
    mock_db.execute = AsyncMock(return_value=result)

    async def _override():
        yield mock_db

    app.dependency_overrides[get_db] = _override
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


class TestHealthCheck:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ledgerdesk-api"
        assert "version" in data

    def test_db_health_healthy(self, client):
        resp = client.get("/health/db")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["component"] == "database"

    def test_db_health_unhealthy(self):
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute = AsyncMock(side_effect=Exception("Connection refused"))

        async def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.get("/health/db")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "unhealthy"
        app.dependency_overrides.clear()

    def test_readiness_mock_mode(self, client):
        with patch("app.routers.health.settings") as mock_settings:
            mock_settings.llm_provider = "mock"
            mock_settings.redis_url = "redis://fake:6379/0"
            mock_settings.openai_api_key = ""
            mock_settings.anthropic_api_key = ""
            # Redis will fail in test, but that's expected
            resp = client.get("/health/ready")
            assert resp.status_code == 200
            data = resp.json()
            assert "checks" in data
            assert data["checks"]["database"] == "healthy"
