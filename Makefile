.PHONY: help setup dev build test lint format clean docker-up docker-down db-migrate db-seed demo

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Initial project setup
	cp -n .env.example .env 2>/dev/null || true
	cd apps/api && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
	cd apps/web && npm install

dev-api: ## Start API server
	cd apps/api && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

dev-web: ## Start frontend dev server
	cd apps/web && npm run dev

dev: ## Start all services
	$(MAKE) docker-up
	$(MAKE) -j2 dev-api dev-web

build: ## Build all services
	cd apps/web && npm run build
	cd apps/api && echo "API ready"

test-api: ## Run backend tests
	cd apps/api && . .venv/bin/activate && pytest -v

test-web: ## Run frontend tests
	cd apps/web && npm test

test: test-api test-web ## Run all tests

lint: ## Run linters
	cd apps/api && . .venv/bin/activate && ruff check . && ruff format --check .
	cd apps/web && npm run lint

format: ## Auto-format code
	cd apps/api && . .venv/bin/activate && ruff check --fix . && ruff format .

docker-up: ## Start infrastructure services
	docker compose up -d postgres redis

docker-down: ## Stop infrastructure services
	docker compose down

docker-build: ## Build all Docker images
	docker compose build

docker-all: ## Start everything in Docker
	docker compose up -d

db-migrate: ## Run database migrations
	cd apps/api && . .venv/bin/activate && alembic upgrade head

db-seed: ## Seed sample data
	cd apps/api && . .venv/bin/activate && python -m app.seed

demo: ## One-command demo setup (infra + seed + servers)
	@echo "Starting LedgerDesk demo environment..."
	$(MAKE) docker-up
	@echo "Waiting for services to be healthy..."
	@sleep 3
	cd apps/api && . .venv/bin/activate && python -m app.seed
	@echo "Starting servers..."
	$(MAKE) -j2 dev-api dev-web

clean: ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .next -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
