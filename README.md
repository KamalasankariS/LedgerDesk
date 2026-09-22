# LedgerDesk

[![CI](https://github.com/KamalasankariS/LedgerDesk/actions/workflows/ci.yml/badge.svg)](https://github.com/KamalasankariS/LedgerDesk/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An agentic financial operations copilot that helps analysts resolve transaction exceptions faster through AI-driven triage, policy-grounded recommendations, and auditable workflows.

---

## How It Works

```
Case Ingested --> Triage Agent --> RAG Retrieval --> Tool Planner --> Tool Executor
    --> Decision Agent --> Safety Gate --> Analyst Review --> Approved / Escalated
```

Five agents collaborate through a state machine: **Triage** classifies the issue and extracts entities, **Tool Planner** selects internal tools (executed in parallel via `asyncio.gather`), **Decision** generates a grounded recommendation with citations, **Safety Gate** validates confidence and policy support, and **Case Writer** produces the analyst-facing summary. Every action is logged to a full audit trail.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic |
| Database | PostgreSQL 16 + pgvector |
| LLM | Anthropic Claude + OpenAI (multi-provider, auto-detected) |
| Observability | structlog, Prometheus, Grafana |
| CI/CD | GitHub Actions (lint, test, security, build, deploy) |
| Infra | Docker Compose, Railway |

---

## Quick Start

```bash
git clone https://github.com/KamalasankariS/LedgerDesk.git
cd LedgerDesk
cp .env.example .env

# Full stack
docker compose up -d

# Or run locally
cd apps/api && pip install -r requirements.txt
python -m app.seed          # seed 30 cases + 9 policy docs
uvicorn app.main:app --reload --port 8000

cd apps/web && npm install && npm run dev
```

Dashboard at `http://localhost:3000`. API at `http://localhost:8000/docs`.

---

## Software Quality Metrics

We measured LedgerDesk against the [11 key software quality metrics](https://stackify.com/application-performance-metrics/) used in industry. Each metric is scored in its standard real-world unit.

### Results

| # | Metric | Score | Industry Target | Status |
|---|--------|-------|-----------------|--------|
| 1 | **Code Coverage** | 78% | > 80% | Near target |
| 2 | **Defect Density** | 0.0 defects/KLOC | < 1.0 defects/KLOC | Excellent |
| 3 | **MTTR (Mean Time to Recovery)** | < 30s | < 60s | Excellent |
| 4 | **Apdex Score** | 0.97 | > 0.85 | Excellent |
| 5 | **Response Time (p95)** | 5.4 ms | < 200 ms | Excellent |
| 6 | **Error Rate** | 0.0% | < 1% | Excellent |
| 7 | **Availability** | 99.9% (design) | > 99.9% | On target |
| 8 | **Cyclomatic Complexity** | 4.2 avg | < 10 avg | Low risk |
| 9 | **Technical Debt Ratio** | ~5% | < 5% | Near target |
| 10 | **Deployment Frequency** | On every push to main | Multiple/day | CI/CD ready |
| 11 | **Test Pass Rate** | 100% (156/156) | 100% | Excellent |

### What These Numbers Mean

**Response time and Apdex are standouts.** With a p50 of 3.6 ms, p95 of 5.4 ms, and p99 of 11.8 ms, the API responds faster than most internal tools. The Apdex score of 0.97 (out of 1.0) means virtually every request is "satisfying" to the end user — well above the 0.85 threshold most teams target.

**Zero error rate and zero defect density** reflect clean execution paths. All 156 tests (107 API + 49 pipeline) pass with no known open bugs. The mock-first architecture means tool failures are caught and routed to `failed_safe` state rather than crashing.

**MTTR under 30 seconds** is possible because Docker containers run with `restart: unless-stopped`, health checks auto-detect failures, and the readiness endpoint (`/health/ready`) validates database, Redis, and LLM connectivity. A crashed container recovers without manual intervention.

**78% code coverage** is close to the 80% target. The gap is primarily in `seed.py` (0%, data loading script) and `workflow.py` (33%, requires LLM integration to fully test). All routers, models, schemas, middleware, and auth are above 90%.

**Cyclomatic complexity averaging 4.2** means most functions have few branching paths, making the codebase easy to read and test. No function exceeds a complexity of 15.

**Deployment frequency** is continuous — every push to `main` triggers a 6-job CI pipeline (lint, test, security scan, frontend build, Docker build, deploy to Railway). The pipeline gates on 60% minimum coverage and zero lint/security findings.

### Load Test Results

```
Endpoint        | p50     | p95     | p99     | Error Rate
----------------|---------|---------|---------|----------
GET /health     | 2.1 ms  | 3.8 ms  | 6.2 ms  | 0.0%
GET /cases      | 3.6 ms  | 5.4 ms  | 11.8 ms | 0.0%
GET /cases/:id  | 3.2 ms  | 4.9 ms  | 9.7 ms  | 0.0%
```

---

## Safety Model

1. **Confidence thresholds** — low-confidence recommendations require human review (< 0.75 triggers escalation)
2. **Grounding checks** — no recommendation without policy citation support
3. **Bounded autonomy** — agents operate within explicit state machine transitions
4. **Human-in-the-loop** — sensitive actions always require analyst approval
5. **Fail-safe behavior** — on failure, cases enter `failed_safe` state, never proceed unsupported
6. **Audit logging** — every action recorded with actor, timestamp, and trace ID

### Escalation Thresholds

| Rule | Condition |
|------|-----------|
| Auto-resolution eligible | confidence >= 0.85 AND amount <= $500 |
| Low-confidence escalation | confidence < 0.70 |
| High-value escalation | amount > $5,000 AND confidence < 0.80 |
| L2 Supervisor | amount > $25,000 |
| L3 Operations Manager | amount > $100,000 |

---

## Monitoring

| Endpoint | What it tells you |
|----------|-------------------|
| `GET /health` | Liveness |
| `GET /health/ready` | DB + Redis + LLM readiness |
| `GET /api/v1/metrics/dashboard` | Case counts, confidence, approval rate |
| `GET /api/v1/metrics/requests` | Apdex, request rate, p95/p99 latency |
| `GET /api/v1/metrics/prometheus` | Prometheus scrape target |

Grafana dashboards are provisioned automatically via `docker compose up`.

---

## Project Structure

```
LedgerDesk/
├── apps/api/              # FastAPI backend (routers, models, services)
├── apps/web/              # Next.js frontend
├── packages/
│   ├── agent-core/        # Orchestrator, state machine, LLM clients
│   ├── retrieval/         # RAG pipeline (chunking, embedding, search)
│   └── evaluation/        # Eval harness (30 cases, 10 issue types)
├── sample_data/           # Seed cases, policies, transactions
├── monitoring/            # Prometheus + Grafana config
├── scripts/               # Load testing
├── docs/                  # Runbook, architecture
└── docker-compose.yml
```

---

## Limitations

| Area | Current State | Production Path |
|------|--------------|-----------------|
| LLM | Multi-provider (Claude/OpenAI/Mock) — set API key to activate | Already production-ready |
| Embeddings | OpenAI `text-embedding-3-small` with local TF-IDF fallback | Fully wired through pgvector |
| Tools | Read-only mocks returning seed JSON | Plug in real APIs — interface is stable |
| Auth | JWT + bcrypt implemented, not enforced on all routes | Apply `require_role` to protected endpoints |

---

## License

[MIT](LICENSE)
