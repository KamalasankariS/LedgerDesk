"""Tests for metrics and dashboard endpoints."""

from unittest.mock import AsyncMock, MagicMock


def _mock_count(value):
    result = MagicMock()
    result.scalar.return_value = value
    return result


def _mock_grouped_result(rows):
    result = MagicMock()
    result.all.return_value = rows
    return result


def _mock_scalar_result(items):
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = items
    result.scalars.return_value = scalars
    return result


class TestDashboardMetrics:
    def test_dashboard_returns_metrics(self, client, mock_db):
        # Setup mock returns for the multiple queries in dashboard_metrics
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_grouped_result([]),  # status counts
                _mock_grouped_result([]),  # priority counts
                _mock_count(5),  # total cases
                _mock_grouped_result([]),  # action counts
                _mock_count(None),  # avg confidence
                _mock_count(0),  # tool count
                _mock_count(None),  # avg tool latency
                _mock_count(0),  # agent run count
                _mock_grouped_result([]),  # token usage
            ]
        )
        resp = client.get("/api/v1/metrics/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_cases" in data
        assert "cases_by_status" in data
        assert "cases_by_priority" in data
        assert data["total_cases"] == 5


class TestWorkflowMetrics:
    def test_workflow_metrics(self, client, mock_db):
        resp = client.get("/api/v1/metrics/workflow")
        assert resp.status_code == 200
        data = resp.json()
        assert "tracked_metrics" in data


class TestRequestMetrics:
    def test_request_metrics(self, client, mock_db):
        resp = client.get("/api/v1/metrics/requests")
        assert resp.status_code == 200


class TestPrometheusMetrics:
    def test_prometheus_endpoint(self, client, mock_db):
        resp = client.get("/api/v1/metrics/prometheus")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        # Should contain standard python metrics at minimum
        assert "python_gc" in resp.text


class TestByIssueType:
    def test_issue_type_breakdown(self, client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[
                _mock_grouped_result([]),  # issue counts
                _mock_grouped_result([]),  # confidence
                _mock_grouped_result([]),  # escalated
                _mock_grouped_result([]),  # completed
            ]
        )
        resp = client.get("/api/v1/metrics/by-issue-type")
        assert resp.status_code == 200
        data = resp.json()
        assert "issue_type_breakdown" in data


class TestEvaluations:
    def test_list_evaluations(self, client, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_scalar_result([]))
        resp = client.get("/api/v1/metrics/evaluations")
        assert resp.status_code == 200
        assert resp.json()["runs"] == []

    def test_run_evaluation_no_cases(self, client, mock_db):
        mock_db.execute = AsyncMock(return_value=_mock_scalar_result([]))
        mock_db.commit = AsyncMock()
        resp = client.post("/api/v1/metrics/evaluations/run")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_cases"] == 0
