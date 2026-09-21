"""Tests for prompt version management endpoints."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from app.models.audit import PromptVersion


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


def _make_prompt_version(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        agent_type="triage",
        version="1.0",
        template="You are a triage agent. Classify: {title}\n{description}",
        description="Triage v1.0",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    pv = MagicMock(spec=PromptVersion)
    for k, v in defaults.items():
        setattr(pv, k, v)
    # Ensure len() works on template
    pv.template = defaults["template"]
    return pv


class TestListPromptVersions:
    def test_list_grouped(self, client, mock_db):
        pv1 = _make_prompt_version(agent_type="triage", version="1.0")
        pv2 = _make_prompt_version(agent_type="decision", version="1.0")
        mock_db.execute = AsyncMock(return_value=_mock_scalar_result([pv1, pv2]))
        resp = client.get("/api/v1/prompts/")
        assert resp.status_code == 200
        data = resp.json()
        assert "prompt_versions" in data
        assert "triage" in data["prompt_versions"]
        assert "decision" in data["prompt_versions"]


class TestGetPromptVersion:
    def test_get_existing(self, client, mock_db):
        pv = _make_prompt_version()
        mock_db.execute = AsyncMock(return_value=_mock_scalar_one(pv))
        resp = client.get(f"/api/v1/prompts/{pv.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_type"] == "triage"
        assert data["version"] == "1.0"

    def test_get_nonexistent(self, client, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_scalar_one(None))
        resp = client.get(f"/api/v1/prompts/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestGetActivePrompt:
    def test_get_active(self, client, mock_db):
        pv = _make_prompt_version(is_active=True)
        mock_db.execute = AsyncMock(return_value=_mock_scalar_one(pv))
        resp = client.get("/api/v1/prompts/active/triage")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_type"] == "triage"

    def test_no_active_prompt(self, client, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_scalar_one(None))
        resp = client.get("/api/v1/prompts/active/nonexistent")
        assert resp.status_code == 404


class TestDiffPromptVersions:
    def test_diff_two_versions(self, client, mock_db):
        pv_a = _make_prompt_version(version="0.9", template="Old template")
        pv_b = _make_prompt_version(version="1.0", template="New template")
        # Two sequential execute calls
        result_a = _mock_scalar_one(pv_a)
        result_b = _mock_scalar_one(pv_b)
        mock_db.execute = AsyncMock(side_effect=[result_a, result_b])
        resp = client.get(f"/api/v1/prompts/diff/{pv_a.id}/{pv_b.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_changes"] is True
        assert "diff" in data

    def test_diff_missing_version(self, client, mock_db):
        mock_db.execute = AsyncMock(side_effect=[_mock_scalar_one(None), _mock_scalar_one(None)])
        resp = client.get(f"/api/v1/prompts/diff/{uuid.uuid4()}/{uuid.uuid4()}")
        assert resp.status_code == 404
