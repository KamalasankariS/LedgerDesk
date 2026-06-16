# Contributing to LedgerDesk

## Development Setup

See [docs/runbooks/local-setup.md](docs/runbooks/local-setup.md) for full setup instructions.

### Quick Start

```bash
# One-command setup
make setup
make demo
```

Or manually:

```bash
# Start infrastructure
make docker-up

# Setup and start backend
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload --port 8000

# Setup and start frontend (new terminal)
cd apps/web
npm install
npm run dev
```

## Project Structure

- `apps/api/` -- FastAPI backend
- `apps/web/` -- Next.js frontend
- `packages/agent-core/` -- Agent orchestration and LLM integration
- `packages/retrieval/` -- RAG pipeline (chunking, embedding, search)
- `packages/evaluation/` -- Evaluation harness
- `sample_data/` -- Seed data for cases, policies, transactions
- `tests/` -- Integration and E2E tests

## Running Tests

```bash
# All tests
make test

# Backend unit tests
make test-api

# Frontend tests
make test-web

# Integration tests (requires running API)
cd apps/api && source .venv/bin/activate && pytest tests/ -v

# E2E tests (requires running API with seeded data)
pytest tests/e2e/ -v
```

## Code Style

- Backend: Python formatted with `ruff` (run `make format` to auto-fix)
- Frontend: TypeScript with ESLint + Next.js defaults
- Commit messages: conventional commits (`feat:`, `fix:`, `docs:`, etc.)

## Linting

```bash
make lint     # Check for issues
make format   # Auto-fix formatting
```

## Architecture Decisions

See [docs/decisions/](docs/decisions/) for ADRs explaining key architectural choices.
