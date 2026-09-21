"""Tests for workflow orchestration endpoints."""

import uuid
from unittest.mock import AsyncMock


class TestWorkflowStates:
    def test_get_workflow_states(self, client, mock_db):
        resp = client.get("/api/v1/workflow/states")
        assert resp.status_code == 200
        data = resp.json()
        assert "states" in data
        assert "transitions" in data
        assert "created" in data["transitions"]
        assert "completed" in data["transitions"]
        # Completed should have no outgoing transitions
        assert data["transitions"]["completed"] == []

    def test_all_states_have_transitions(self, client, mock_db):
        resp = client.get("/api/v1/workflow/states")
        data = resp.json()
        for state in data["states"]:
            assert state in data["transitions"], f"Missing transitions for {state}"


class TestRunWorkflow:
    def test_run_workflow_unauthorized(self):
        """Workflow run requires auth."""
        from app.core.database import get_db
        from app.main import app
        from fastapi.testclient import TestClient

        mock_db = AsyncMock()

        async def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.post(
            "/api/v1/workflow/run",
            json={"case_id": str(uuid.uuid4())},
        )
        assert resp.status_code in (401, 403)
        app.dependency_overrides.clear()

    def test_run_stream_unauthorized(self):
        """Workflow stream requires auth."""
        from app.core.database import get_db
        from app.main import app
        from fastapi.testclient import TestClient

        mock_db = AsyncMock()

        async def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.post(
            "/api/v1/workflow/run/stream",
            json={"case_id": str(uuid.uuid4())},
        )
        assert resp.status_code in (401, 403)
        app.dependency_overrides.clear()
