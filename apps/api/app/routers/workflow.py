"""Workflow orchestration endpoints."""

import asyncio
import json
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session, get_db
from app.models.case import Case, CaseStatus

logger = structlog.get_logger()
router = APIRouter()

# Map case statuses to friendly step names for SSE
_STATUS_STEPS: dict[str, str] = {
    "triaged": "Triage",
    "context_retrieved": "Retrieval",
    "tools_selected": "Tool Planning",
    "tools_executed": "Tool Execution",
    "recommendation_generated": "Decision",
    "safety_checked": "Safety Gate",
    "awaiting_review": "Complete",
}

_TERMINAL_STATUSES = {"awaiting_review", "failed_safe", "completed"}


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


@router.post("/run/stream")
async def run_workflow_stream(req: WorkflowRunRequest):
    """Run workflow with SSE streaming of step progress."""
    _ensure_package_paths()

    case_id = req.case_id

    # Verify case exists
    async with async_session() as db:
        result = await db.execute(select(Case).where(Case.id == case_id))
        case = result.scalar_one_or_none()
        if not case:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    async def sse_generator():
        from orchestrator import run_full_workflow

        # Launch the workflow in a background task with its own session
        workflow_error = None

        async def _run():
            nonlocal workflow_error
            try:
                async with async_session() as wf_db:
                    await run_full_workflow(wf_db, case_id)
                    await wf_db.commit()
            except Exception as e:
                workflow_error = str(e)

        task = asyncio.create_task(_run())

        last_status = "created"
        seen_steps: set[str] = set()

        try:
            while not task.done():
                await asyncio.sleep(0.5)

                # Poll current case status
                async with async_session() as poll_db:
                    result = await poll_db.execute(
                        select(Case.status).where(Case.id == case_id)
                    )
                    row = result.scalar_one_or_none()
                    if row is None:
                        break
                    current = row.value if hasattr(row, "value") else str(row)

                if current != last_status:
                    # Emit events for any steps we haven't seen
                    for status_key, step_name in _STATUS_STEPS.items():
                        if status_key not in seen_steps and _status_reached(
                            current, status_key
                        ):
                            seen_steps.add(status_key)
                            event = {
                                "step": step_name,
                                "status": "completed",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                            yield f"data: {json.dumps(event)}\n\n"

                    last_status = current

                    if current in _TERMINAL_STATUSES:
                        break

            # Wait for task to finish
            if not task.done():
                await task

            # Final event
            final = {
                "step": "done",
                "status": "failed" if workflow_error else "completed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": workflow_error,
            }
            yield f"data: {json.dumps(final)}\n\n"

        except Exception as e:
            error_event = {
                "step": "done",
                "status": "failed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


def _status_reached(current: str, target: str) -> bool:
    """Check if `current` status is at or past `target` in the workflow."""
    order = [
        "created",
        "triaged",
        "context_retrieved",
        "tools_selected",
        "tools_executed",
        "recommendation_generated",
        "safety_checked",
        "awaiting_review",
        "completed",
    ]
    try:
        return order.index(current) >= order.index(target)
    except ValueError:
        return False


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
