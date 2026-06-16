"""LedgerDesk API - Agentic Financial Operations Copilot."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.routers import (
    cases,
    policies,
    tools,
    workflow,
    audit,
    health,
    metrics,
    retrieval,
    auth,
    users,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("ledgerdesk_api_starting", environment=settings.environment)
    yield
    logger.info("ledgerdesk_api_shutting_down")


app = FastAPI(
    title="LedgerDesk API",
    description="Agentic Financial Operations Copilot for Transaction Exception Handling",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(cases.router, prefix="/api/v1/cases", tags=["Cases"])
app.include_router(policies.router, prefix="/api/v1/policies", tags=["Policies"])
app.include_router(tools.router, prefix="/api/v1/tools", tags=["Tools"])
app.include_router(workflow.router, prefix="/api/v1/workflow", tags=["Workflow"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["Audit"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["Metrics"])
app.include_router(retrieval.router, prefix="/api/v1/retrieval", tags=["Retrieval"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
