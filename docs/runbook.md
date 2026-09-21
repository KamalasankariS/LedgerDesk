# LedgerDesk Incident Response Runbook

## Service Architecture

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| PostgreSQL + pgvector | ledgerdesk-postgres | 5434 | Primary database |
| Redis | ledgerdesk-redis | 6379 | Task queue, caching |
| API | ledgerdesk-api | 8000 | FastAPI backend |
| Worker | ledgerdesk-worker | — | Celery async tasks |
| Web | ledgerdesk-web | 3000 | Next.js frontend |
| Prometheus | ledgerdesk-prometheus | 9090 | Metrics collection |
| Grafana | ledgerdesk-grafana | 3001 | Dashboards & alerting |

## Health Check Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Basic liveness check |
| `GET /health/db` | Database connectivity |
| `GET /health/ready` | Full readiness (DB + Redis + LLM) |
| `GET /api/v1/metrics/prometheus` | Prometheus scrape endpoint |
| `GET /api/v1/metrics/requests` | Real-time request rate and latency |

## Common Issues & Fixes

### 1. asyncpg InvalidCachedStatementError
**Symptom:** API returns 500s after schema changes or seed operations.
**Cause:** asyncpg's prepared statement cache is invalidated by DDL.
**Fix:**
```bash
docker compose restart api
```

### 2. Container Crash Loop
**Symptom:** Container continuously restarts.
**Fix:**
```bash
docker logs <container-name> --tail 50
docker compose stop <service>
docker compose up -d <service>
```

### 3. Database Connection Refused
**Symptom:** API logs show "connection refused" to postgres.
**Fix:**
```bash
docker compose ps postgres  # Check if healthy
docker compose restart postgres
sleep 5
docker compose restart api worker
```

### 4. Redis Connection Failed
**Symptom:** Worker fails to start or task queue stalls.
**Fix:**
```bash
docker exec ledgerdesk-redis redis-cli ping  # Should return PONG
docker compose restart redis
docker compose restart worker
```

### 5. High Memory Usage
**Symptom:** Containers OOM killed.
**Fix:** Check resource limits in docker-compose.yml and increase if needed.

## Recovery Procedures

### Restart Individual Service
```bash
docker compose restart <service-name>
```

### Full Stack Restart
```bash
docker compose down
docker compose up -d
```

### Re-seed Database (destructive)
```bash
docker compose restart api
sleep 3
curl -X POST http://localhost:8000/api/v1/seed
docker compose restart api  # Clear asyncpg cache after seed
```

### Rebuild After Code Changes
```bash
docker compose build api web
docker compose up -d
```

## Monitoring Dashboards

- **Grafana:** http://localhost:3001 (admin/admin)
- **Prometheus:** http://localhost:9090

### Key Metrics to Watch

| Metric | Warning | Critical |
|--------|---------|----------|
| Error rate (5xx) | > 1% | > 5% |
| p95 latency | > 500ms | > 2s |
| Active requests | > 50 | > 100 |
| DB health | unhealthy | — |

## Alerting Rules

Configure in Grafana (Alerting > Alert rules):

1. **High Error Rate:** `sum(rate(ledgerdesk_http_requests_total{status=~"5.."}[5m])) / sum(rate(ledgerdesk_http_requests_total[5m])) > 0.05`
2. **Slow Responses:** `histogram_quantile(0.95, rate(ledgerdesk_http_request_duration_seconds_bucket[5m])) > 2`
3. **Service Down:** `up{job="ledgerdesk-api"} == 0`

## Escalation Process

1. **L1 (Auto-recovery):** Docker `restart: unless-stopped` handles transient crashes
2. **L2 (Manual):** Check logs, restart specific service, verify with health endpoints
3. **L3 (Full recovery):** Full stack restart, re-seed if data corruption
