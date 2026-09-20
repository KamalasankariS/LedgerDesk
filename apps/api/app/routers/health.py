"""Health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ledgerdesk-api", "version": "0.1.0"}


@router.get("/health/db")
async def db_health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "component": "database"}
    except Exception as e:
        return {"status": "unhealthy", "component": "database", "error": str(e)}


@router.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    checks = {}

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception:
        checks["database"] = "unhealthy"

    # Redis check
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
        checks["redis"] = "healthy"
    except Exception:
        checks["redis"] = "unhealthy"

    # LLM connectivity check
    provider = settings.llm_provider
    if provider == "anthropic" or (provider == "auto" and settings.anthropic_api_key):
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={
                        "x-api-key": settings.anthropic_api_key,
                        "anthropic-version": "2023-06-01",
                    },
                )
                checks["llm"] = "healthy" if resp.status_code == 200 else "degraded"
                checks["llm_provider"] = "anthropic"
        except Exception:
            checks["llm"] = "unhealthy"
            checks["llm_provider"] = "anthropic"
    elif provider == "openai" or (provider == "auto" and settings.openai_api_key):
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"{settings.openai_base_url}/models",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                )
                checks["llm"] = "healthy" if resp.status_code == 200 else "degraded"
                checks["llm_provider"] = "openai"
        except Exception:
            checks["llm"] = "unhealthy"
            checks["llm_provider"] = "openai"
    else:
        checks["llm"] = "mock_mode"
        checks["llm_provider"] = "mock"

    all_healthy = all(v in ("healthy", "mock_mode") for v in checks.values())
    return {"status": "ready" if all_healthy else "not_ready", "checks": checks}
