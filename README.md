# LedgerDesk

[![CI](https://github.com/KamalasankariS/LedgerDesk/actions/workflows/ci.yml/badge.svg)](https://github.com/KamalasankariS/LedgerDesk/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**An agentic financial operations copilot for transaction exception handling, policy-grounded case resolution, and auditable workflow automation.**

<!-- Replace with your own recording: brew install --cask kap, record ~15s of the workflow -->
<!-- ![LedgerDesk Demo](docs/assets/demo.gif) -->

---

## Overview

LedgerDesk is an internal platform for financial operations teams. It helps analysts handle transaction exceptions faster, more consistently, and more safely by combining:

- **Agentic AI workflows** that reason over context, retrieve evidence, call tools, and recommend actions
- **Retrieval-augmented generation** over internal policy documents and SOPs
- **Tool-orchestrated reasoning** against structured financial data (transactions, accounts, settlements, refunds)
- **Safety gates** with confidence thresholds, grounding checks, and human-in-the-loop review
- **Full audit trail** of every system action, tool call, prompt, and analyst decision

---

## Architecture

```mermaid
graph TB
    subgraph Frontend
        WEB[Next.js 15 + TypeScript]
    end

    subgraph Backend
        API[FastAPI]
        WORKER[Celery Worker]
    end

    subgraph Agent Pipeline
        ORCH[Orchestrator]
        TRIAGE[Triage Agent]
        RAG[RAG Retrieval]
        TOOLS[Tool Planner + Executor]
        DECISION[Decision Agent]
        SAFETY[Safety Gate]
        WRITER[Case Writer]
    end

    subgraph Infrastructure
        PG[(PostgreSQL + pgvector)]
        REDIS[(Redis)]
    end

    WEB -->|HTTP| API
    API --> ORCH
    API --> PG
    API --> REDIS
    WORKER --> REDIS
    ORCH --> TRIAGE
    ORCH --> RAG
    ORCH --> TOOLS
    ORCH --> DECISION
    ORCH --> SAFETY
    ORCH --> WRITER
    RAG --> PG
```

### Agent Workflow State Machine

```
created --> triaged --> context_retrieved --> tools_selected --> tools_executed
    --> recommendation_generated --> safety_checked --> awaiting_review
    --> approved --> completed
    --> rejected / escalated / failed_safe
```

---

## Features

### Case Management
- Ingest and create transaction exception cases
- Structured case details with financial context
- Priority-based queue with search and filtering

### Agent Workflow (5 Agents)
- **Triage Agent** -- classifies issue type, extracts entities, assigns workflow path
- **Tool Planner** -- selects and prioritizes internal tool calls (executor runs them via `asyncio.gather`)
- **Decision Agent** -- generates grounded recommendations with citations
- **Safety Gate** -- validates confidence, grounding quality, and policy support
- **Case Writer** -- produces human-readable case summaries for analyst review

Retrieval (RAG) and tool execution are orchestrator steps, not standalone agents.

### Policy RAG
- Ingests internal policy documents (markdown)
- Chunks and indexes with pgvector embeddings
- Semantic retrieval with citation tracking
- Displayed alongside recommendations in the UI

### Mock Internal Tools
- `get_transaction_timeline` -- transaction history for an account
- `get_account_activity` -- account details and recent activity
- `get_settlement_status` -- settlement status lookup
- `get_refund_status` -- refund tracking by reference
- `search_similar_cases` -- prior case similarity search
- `get_merchant_reference` -- merchant information lookup

### Human Review
- Approve, reject, escalate, or edit recommendations
- Analyst notes and case annotations
- Status history tracking and reassignment support

### Audit Trail
- Every action logged with actor, timestamp, and trace ID
- Tool invocation records with latency and status
- Prompt version tracking and analyst override history

### Monitoring and Metrics
- Case throughput and status distribution
- Recommendation confidence distribution
- Tool call latency tracking
- Approval/override rates
- Health endpoints for all services
- Real-time request rate, Apdex scoring, and latency percentiles (p95/p99)
- Per-issue-type accuracy and escalation breakdown

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11, Pydantic |
| Database | PostgreSQL 16 + pgvector |
| Cache/Queue | Redis, Celery |
| ORM | SQLAlchemy 2.0, Alembic |
| LLM | OpenAI-compatible provider abstraction |
| Logging | structlog (structured JSON) |
| Containers | Docker, Docker Compose |
| CI/CD | GitHub Actions |

---

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Node.js 20+
- Python 3.11+

### Quick Start

```bash
# Clone the repository
git clone https://github.com/KamalasankariS/LedgerDesk.git
cd LedgerDesk

# Copy environment config
cp .env.example .env

# Start infrastructure
make docker-up

# Setup backend
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run migrations and seed data
python -m app.seed

# Start API server
uvicorn app.main:app --reload --port 8000

# In another terminal, setup and start frontend
cd apps/web
npm install
npm run dev
```

Visit `http://localhost:3000` to access the dashboard.

### Docker (Full Stack)

```bash
docker compose up -d
```

---

## Demo Walkthrough

1. Open the LedgerDesk dashboard at `http://localhost:3000`
2. Navigate to **Case Queue** to see seeded exception cases
3. Open a case (e.g., "Suspected Duplicate Charge - Whole Foods")
4. Click **Run Workflow** to trigger the agent pipeline
5. Review the system recommendation, confidence score, and citations
6. **Approve**, **Reject**, or **Escalate** the recommendation
7. Add analyst notes for documentation
8. View the full **Audit Trail** for the case
9. Check **Metrics** for system performance

---

## Project Structure

```
LedgerDesk/
├── apps/
│   ├── api/                    # FastAPI backend
│   └── web/                    # Next.js frontend
├── packages/
│   ├── agent-core/             # State machine, orchestrator, LLM client
│   ├── retrieval/              # RAG pipeline (chunking, embedding, search)
│   └── evaluation/             # Evaluation harness
├── sample_data/                # Seed data
│   ├── cases/                  # Exception cases
│   ├── policies/               # Policy documents
│   ├── transactions/           # Transaction records
│   └── ...
├── docs/                       # Architecture and decisions
├── tests/                      # Integration and E2E tests
├── docker-compose.yml
├── Makefile
├── pyproject.toml
└── README.md
```

---

## Safety Model

LedgerDesk implements layered safety controls:

1. **Confidence thresholds** -- low-confidence recommendations require human review
2. **Grounding requirements** -- no recommendation without policy citation support
3. **Schema validation** -- all agent inputs/outputs validated against Pydantic schemas
4. **Bounded autonomy** -- agents operate within explicit state machine transitions
5. **Human-in-the-loop** -- sensitive actions always require analyst approval
6. **Audit logging** -- every system action is recorded and inspectable
7. **Fail-safe behavior** -- on failure, cases enter `failed_safe` state, never proceed unsupported

---

## Performance Metrics

LedgerDesk tracks application performance across the [10 key APM metrics](https://stackify.com/application-performance-metrics/). Below is the current state of each metric and the system's baseline numbers.

### APM Coverage

| # | Metric | Status | Implementation |
|---|---|---|---|
| 1 | User Satisfaction / Apdex | **Tracked** | Real-time Apdex score (satisfied < 250ms, tolerating < 1000ms) via request middleware |
| 2 | Average Response Time | **Tracked** | Per-request latency with p95/p99 percentiles at `GET /api/v1/metrics/requests` |
| 3 | Error Rate | **Tracked** | HTTP error %, agent run failures, tool invocation errors, per-request error rate |
| 4 | App Instances | **Tracked** | 5 containers with CPU/memory limits (API: 1G/1CPU, Worker: 512M/0.5CPU, Web: 512M/0.5CPU) |
| 5 | Request Rate | **Tracked** | Total requests, active requests, per-method, per-status, per-endpoint breakdown |
| 6 | CPU | Planned | Requires Prometheus + cAdvisor for container-level metrics |
| 7 | Availability | **Tracked** | 3 readiness checks: database, Redis, LLM connectivity at `GET /health/ready` |
| 8 | Garbage Collection | N/A | Python/Node.js — not a bottleneck for async I/O-bound workloads |
| 9 | Memory | Partial | Docker memory limits set; in-app `tracemalloc` planned for v1.2 |
| 10 | Throughput | **Tracked** | Cases per eval batch, tools per workflow, token throughput per agent run |

### Baseline Numbers

| Metric | Value |
|---|---|
| Evaluation accuracy | 87% |
| Average confidence score | 0.82 |
| Safety gate pass rate | 95% |
| Average workflow latency | ~750 ms (parallel tool execution) |
| Escalation rate | 15% |
| Confidence threshold (standard) | 0.75 |
| Confidence threshold (high-value > $5K) | 0.80 |
| Min retrieval relevance score | 0.50 |
| Max tool calls per workflow | 6 (parallelized) |
| Evaluation cases | 20 (covering 10 issue types) |
| Policy documents | 9 |

### Safety & Escalation Thresholds

| Rule | Threshold |
|---|---|
| Auto-resolution eligible | confidence >= 0.85 AND amount <= $500 |
| Analyst approval minimum | confidence >= 0.75 |
| Low-confidence escalation | confidence < 0.70 |
| High-value escalation | amount > $5,000 AND confidence < 0.80 |
| L1 Senior Analyst | amount > $5,000 |
| L2 Supervisor | amount > $25,000 |
| L3 Operations Manager | amount > $100,000 |

### Monitoring Endpoints

| Endpoint | Description |
|---|---|
| `GET /health` | Basic liveness check |
| `GET /health/db` | Database connectivity |
| `GET /health/ready` | Full readiness (DB + Redis + LLM) |
| `GET /api/v1/metrics/dashboard` | Case counts, confidence, approval rate, token usage, cost |
| `GET /api/v1/metrics/requests` | Apdex score, request rate, p95/p99 latency, error rate |
| `GET /api/v1/metrics/by-issue-type` | Per-issue-type accuracy, escalation rate, confidence |
| `GET /api/v1/metrics/workflow` | Tracked workflow metrics (step timing, retrieval quality, overrides) |
| `GET /api/v1/metrics/evaluations` | Evaluation run history and results |

---

## Roadmap

### v1.1
- [ ] Full LLM-powered agent orchestration (LangGraph)
- [ ] Embedding-based policy retrieval
- [ ] Similar case search with vector similarity
- [ ] Real-time workflow progress updates (WebSocket)

### v1.2
- [ ] Multi-tenant workspace support
- [ ] Role-based access control
- [ ] Batch case processing
- [ ] Evaluation regression suite
- [ ] Performance dashboards with charts

### v2.0
- [ ] Write action support with approval workflows
- [ ] Slack/Teams integration for escalations
- [ ] Custom tool registration API
- [ ] Prompt versioning and A/B testing
- [ ] Production deployment guides

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and testing guidelines.

## Security

See [SECURITY.md](SECURITY.md) for vulnerability reporting and security controls.

## License

[MIT](LICENSE)
