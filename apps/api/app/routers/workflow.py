"""Workflow orchestration endpoints."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.case import CaseStatus

logger = structlog.get_logger()
router = APIRouter()


class WorkflowRunRequest(BaseModel):
    case_id: uuid.UUID


class WorkflowStepResult(BaseModel):
    step: str
    status: str
    details: dict | None = None


def _ensure_package_paths():
    """Add package source directories to sys.path if not already present."""
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    for pkg in ("agent-core", "retrieval"):
        pkg_path = str(project_root / "packages" / pkg / "src")
        if pkg_path not in sys.path:
            sys.path.insert(0, pkg_path)


@router.post("/run")
async def run_workflow(req: WorkflowRunRequest, db: AsyncSession = Depends(get_db)):
    """Run the full agent workflow on a case."""
    _ensure_package_paths()
    from orchestrator import run_full_workflow

    try:
        result = await run_full_workflow(db, req.case_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("workflow_run_failed", error=str(e), case_id=str(req.case_id))
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")


@router.get("/states")
async def get_workflow_states():
    """Return the workflow state machine definition."""
    return {
        "states": [s.value for s in CaseStatus],
        "transitions": {
            "created": ["triaged", "escalated"],
            "triaged": ["context_retrieved", "escalated"],
            "context_retrieved": ["tools_selected"],
            "tools_selected": ["tools_executed"],
            "tools_executed": ["recommendation_generated"],
            "recommendation_generated": ["safety_checked"],
            "safety_checked": ["awaiting_review", "approved", "escalated"],
            "awaiting_review": ["approved", "rejected", "escalated"],
            "approved": ["completed", "created"],
            "rejected": ["created"],
            "escalated": ["created", "completed"],
            "completed": [],
            "failed_safe": ["created"],
        },
    }
