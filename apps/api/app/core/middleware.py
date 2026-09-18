"""Request tracking middleware for APM metrics."""

import time
from collections import defaultdict
from threading import Lock

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


class RequestMetrics:
    """Thread-safe in-memory request metrics collector."""

    def __init__(self):
        self._lock = Lock()
        self.total_requests: int = 0
        self.active_requests: int = 0
        self.requests_by_method: dict[str, int] = defaultdict(int)
        self.requests_by_status: dict[int, int] = defaultdict(int)
        self.requests_by_path: dict[str, int] = defaultdict(int)
        self.total_response_time_ms: float = 0.0
        self.error_count: int = 0
        self._recent_latencies: list[float] = []
        self._max_recent: int = 1000

    def record_request(self, method: str, path: str, status_code: int, duration_ms: float):
        with self._lock:
            self.total_requests += 1
            self.requests_by_method[method] += 1
            self.requests_by_status[status_code] += 1
            self.total_response_time_ms += duration_ms

            # Normalize path (strip UUIDs and IDs for grouping)
            normalized = self._normalize_path(path)
            self.requests_by_path[normalized] += 1

            if status_code >= 400:
                self.error_count += 1

            self._recent_latencies.append(duration_ms)
            if len(self._recent_latencies) > self._max_recent:
                self._recent_latencies = self._recent_latencies[-self._max_recent :]

    def snapshot(self) -> dict:
        with self._lock:
            avg_latency = (
                self.total_response_time_ms / self.total_requests
                if self.total_requests > 0
                else 0.0
            )
            p95 = self._percentile(95) if self._recent_latencies else 0.0
            p99 = self._percentile(99) if self._recent_latencies else 0.0
            error_rate = self.error_count / self.total_requests if self.total_requests > 0 else 0.0

            # Apdex: satisfied < 250ms, tolerating < 1000ms, frustrated >= 1000ms
            satisfied = sum(1 for lat in self._recent_latencies if lat < 250)
            tolerating = sum(1 for lat in self._recent_latencies if 250 <= lat < 1000)
            total_sample = len(self._recent_latencies)
            apdex = (satisfied + tolerating * 0.5) / total_sample if total_sample > 0 else 1.0

            return {
                "total_requests": self.total_requests,
                "active_requests": self.active_requests,
                "avg_response_time_ms": round(avg_latency, 2),
                "p95_response_time_ms": round(p95, 2),
                "p99_response_time_ms": round(p99, 2),
                "error_rate": round(error_rate, 4),
                "error_count": self.error_count,
                "apdex_score": round(apdex, 3),
                "requests_by_method": dict(self.requests_by_method),
                "requests_by_status": dict(self.requests_by_status),
                "top_endpoints": dict(
                    sorted(
                        self.requests_by_path.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:20]
                ),
            }

    def _percentile(self, p: float) -> float:
        sorted_latencies = sorted(self._recent_latencies)
        idx = int(len(sorted_latencies) * p / 100)
        idx = min(idx, len(sorted_latencies) - 1)
        return sorted_latencies[idx]

    @staticmethod
    def _normalize_path(path: str) -> str:
        import re

        # Replace UUIDs with {id}
        path = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "{id}",
            path,
        )
        return path


# Singleton instance
request_metrics = RequestMetrics()


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware that tracks request rate, latency, and error rates."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        request_metrics.active_requests += 1

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start) * 1000
            request_metrics.record_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            return response
        except Exception:
            duration_ms = (time.time() - start) * 1000
            request_metrics.record_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=duration_ms,
            )
            raise
        finally:
            request_metrics.active_requests -= 1
