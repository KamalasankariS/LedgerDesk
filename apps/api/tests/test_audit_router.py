"""Tests for audit trail endpoints."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from app.models.agent import ToolInvocation
from app.models.audit import AuditEvent


def _mock_count(value):
    result = MagicMock()
    result.scalar.return_value = value
    return result


def _mock_scalar_result(items):
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = items
    result.scalars.return_value = scalars
    return result


def _make_audit_event(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        event_type="case_created",
        actor_type="system",
        actor_id=None,
        action="create",
        resource_type="case",
        resource_id=str(uuid.uuid4()),
        details=None,
        trace_id=str(uuid.uuid4()),
        created_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    event = MagicMock(spec=AuditEvent)
    for k, v in defaults.items():
        setattr(event, k, v)
    return event


def _make_tool_invocation(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        tool_name="get_transaction_timeline",
        tool_type="read",
        input_params={"transaction_id": "TXN-001"},
        output_data={"timeline": []},
        status="success",
        error_message=None,
        duration_ms=15,
        trace_id=str(uuid.uuid4()),
        created_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    inv = MagicMock(spec=ToolInvocation)
    for k, v in defaults.items():
        setattr(inv, k, v)
    return inv


class TestListAuditEvents:
    def test_list_all(self, client, mock_db):
        event = _make_audit_event()
        mock_db.execute = AsyncMock(side_effect=[_mock_count(1), _mock_scalar_result([event])])
        resp = client.get("/api/v1/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["events"]) == 1

    def test_list_empty(self, client, mock_db):
        mock_db.execute = AsyncMock(side_effect=[_mock_count(0), _mock_scalar_result([])])
        resp = client.get("/api/v1/audit")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_filter_by_case_id(self, client, mock_db):
        mock_db.execute = AsyncMock(side_effect=[_mock_count(0), _mock_scalar_result([])])
        case_id = uuid.uuid4()
        resp = client.get(f"/api/v1/audit?case_id={case_id}")
        assert resp.status_code == 200

    def test_filter_by_event_type(self, client, mock_db):
        mock_db.execute = AsyncMock(side_effect=[_mock_count(0), _mock_scalar_result([])])
        resp = client.get("/api/v1/audit?event_type=case_created")
        assert resp.status_code == 200


class TestListToolInvocations:
    def test_list_tools(self, client, mock_db):
        inv = _make_tool_invocation()
        mock_db.execute = AsyncMock(return_value=_mock_scalar_result([inv]))
        resp = client.get("/api/v1/audit/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

    def test_list_tools_empty(self, client, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_scalar_result([]))
        resp = client.get("/api/v1/audit/tools")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_filter_by_tool_name(self, client, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_scalar_result([]))
        resp = client.get("/api/v1/audit/tools?tool_name=get_transaction_timeline")
        assert resp.status_code == 200
