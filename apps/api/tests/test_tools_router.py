"""Tests for mock tool service endpoints."""

import uuid


class TestExecuteTool:
    def test_get_transaction_timeline(self, client, mock_db):
        resp = client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "get_transaction_timeline",
                "params": {"transaction_id": "TXN-9382741"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tool_name"] == "get_transaction_timeline"
        assert data["status"] == "success"
        assert "data" in data

    def test_get_account_activity(self, client, mock_db):
        resp = client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "get_account_activity",
                "params": {"account_id": "ACCT-4421889"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

    def test_get_settlement_status(self, client, mock_db):
        resp = client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "get_settlement_status",
                "params": {"transaction_id": "TXN-9382741"},
            },
        )
        assert resp.status_code == 200

    def test_get_refund_status(self, client, mock_db):
        resp = client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "get_refund_status",
                "params": {"transaction_id": "TXN-9382741"},
            },
        )
        assert resp.status_code == 200

    def test_search_similar_cases(self, client, mock_db):
        resp = client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "search_similar_cases",
                "params": {"query": "duplicate charge"},
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_get_merchant_reference(self, client, mock_db):
        resp = client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "get_merchant_reference",
                "params": {"merchant_ref": "WFM-1042"},
            },
        )
        assert resp.status_code == 200

    def test_unknown_tool(self, client, mock_db):
        resp = client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "nonexistent_tool",
                "params": {},
            },
        )
        assert resp.status_code == 400

    def test_missing_required_param(self, client, mock_db):
        resp = client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "get_transaction_timeline",
                "params": {},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"

    def test_with_case_id(self, client, mock_db):
        case_id = str(uuid.uuid4())
        resp = client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "search_similar_cases",
                "params": {"query": "test"},
                "case_id": case_id,
            },
        )
        assert resp.status_code == 200

    def test_response_includes_trace_id(self, client, mock_db):
        resp = client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "search_similar_cases",
                "params": {"query": "test"},
            },
        )
        data = resp.json()
        assert "trace_id" in data
        assert "duration_ms" in data
