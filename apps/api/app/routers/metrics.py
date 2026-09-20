"""Metrics and dashboard endpoints."""

import uuid
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.middleware import request_metrics
from app.models.agent import AgentRun, Recommendation, ToolInvocation
from app.models.audit import AnalystAction, EvaluationRun
from app.models.case import Case

logger = structlog.get_logger()
router = APIRouter()


@router.get("/dashboard")
async def dashboard_metrics(db: AsyncSession = Depends(get_db)):
    # Case counts by status
    status_result = await db.execute(select(Case.status, func.count(Case.id)).group_by(Case.status))
    status_counts = {
        row[0].value if hasattr(row[0], "value") else row[0]: row[1] for row in status_result.all()
    }

    # Priority distribution
    priority_result = await db.execute(
        select(Case.priority, func.count(Case.id)).group_by(Case.priority)
    )
    priority_counts = {
        row[0].value if hasattr(row[0], "value") else row[0]: row[1]
        for row in priority_result.all()
    }

    # Total cases
    total = (await db.execute(select(func.count(Case.id)))).scalar() or 0

    # Action counts
    action_result = await db.execute(
        select(AnalystAction.action_type, func.count(AnalystAction.id)).group_by(
            AnalystAction.action_type
        )
    )
    action_counts = dict(action_result.all())

    # Average confidence
    avg_confidence = (await db.execute(select(func.avg(Recommendation.confidence_score)))).scalar()

    # Tool invocation stats
    tool_count = (await db.execute(select(func.count(ToolInvocation.id)))).scalar() or 0
    avg_tool_latency = (await db.execute(select(func.avg(ToolInvocation.duration_ms)))).scalar()

    # Agent run + token stats
    agent_run_count = (await db.execute(select(func.count(AgentRun.id)))).scalar() or 0

    # Aggregate token usage from JSON column
    all_runs = await db.execute(
        select(AgentRun.token_usage).where(AgentRun.token_usage.isnot(None))
    )
    prompt_total = 0
    completion_total = 0
    for (usage,) in all_runs.all():
        if usage:
            prompt_total += usage.get("prompt_tokens", 0)
            completion_total += usage.get("completion_tokens", 0)
    total_tokens = prompt_total + completion_total
    # Cost estimation (GPT-4o pricing: $5/1M input, $15/1M output)
    estimated_cost = (prompt_total * 5 + completion_total * 15) / 1_000_000

    return {
        "total_cases": total,
        "cases_by_status": status_counts,
        "cases_by_priority": priority_counts,
        "analyst_actions": action_counts,
        "average_confidence": round(avg_confidence, 3) if avg_confidence else None,
        "total_tool_invocations": tool_count,
        "average_tool_latency_ms": round(avg_tool_latency, 1) if avg_tool_latency else None,
        "approval_rate": _calc_rate(
            action_counts.get("approve", 0), action_counts.get("reject", 0)
        ),
        "total_agent_runs": agent_run_count,
        "total_tokens": total_tokens,
        "estimated_cost_usd": round(estimated_cost, 4),
    }


def _calc_rate(approved: int, rejected: int) -> float | None:
    total = approved + rejected
    if total == 0:
        return None
    return round(approved / total, 3)


@router.get("/workflow")
async def workflow_metrics(db: AsyncSession = Depends(get_db)):
    return {
        "message": "Workflow metrics available after cases are processed",
        "tracked_metrics": [
            "workflow_step_timing",
            "tool_call_latency",
            "retrieval_quality",
            "fallback_frequency",
            "confidence_distribution",
            "override_rate",
            "recommendation_acceptance_rate",
        ],
    }


@router.get("/by-issue-type")
async def metrics_by_issue_type(db: AsyncSession = Depends(get_db)):
    """Breakdown of accuracy, confidence, and escalation rate per issue type."""
    # Cases per issue type
    issue_result = await db.execute(
        select(Case.issue_type, func.count(Case.id)).group_by(Case.issue_type)
    )
    issue_counts = {
        (row[0].value if hasattr(row[0], "value") else str(row[0])): row[1]
        for row in issue_result.all()
        if row[0] is not None
    }

    # Avg confidence per issue type
    conf_result = await db.execute(
        select(Case.issue_type, func.avg(Case.confidence_score))
        .where(Case.confidence_score.isnot(None))
        .group_by(Case.issue_type)
    )
    confidence_by_type = {
        (row[0].value if hasattr(row[0], "value") else str(row[0])): round(row[1], 3)
        for row in conf_result.all()
        if row[0] is not None
    }

    # Escalation count per issue type
    esc_result = await db.execute(
        select(Case.issue_type, func.count(Case.id))
        .where(Case.status == "escalated")
        .group_by(Case.issue_type)
    )
    escalated_by_type = {
        (row[0].value if hasattr(row[0], "value") else str(row[0])): row[1]
        for row in esc_result.all()
        if row[0] is not None
    }

    # Completed (approved) per issue type
    completed_result = await db.execute(
        select(Case.issue_type, func.count(Case.id))
        .where(Case.status.in_(["completed", "approved"]))
        .group_by(Case.issue_type)
    )
    completed_by_type = {
        (row[0].value if hasattr(row[0], "value") else str(row[0])): row[1]
        for row in completed_result.all()
        if row[0] is not None
    }

    # Build per-type summary
    breakdown = {}
    for issue_type, count in issue_counts.items():
        completed = completed_by_type.get(issue_type, 0)
        escalated = escalated_by_type.get(issue_type, 0)
        breakdown[issue_type] = {
            "total_cases": count,
            "avg_confidence": confidence_by_type.get(issue_type),
            "completed": completed,
            "escalated": escalated,
            "escalation_rate": round(escalated / count, 3) if count > 0 else 0.0,
            "completion_rate": round(completed / count, 3) if count > 0 else 0.0,
        }

    return {"issue_type_breakdown": breakdown}


@router.get("/requests")
async def request_rate_metrics():
    """Real-time request rate, latency percentiles, Apdex score, and error rate."""
    return request_metrics.snapshot()


@router.get("/prometheus")
async def prometheus_metrics():
    """Export metrics in Prometheus text format for scraping."""
    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/evaluations")
async def list_evaluations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EvaluationRun).order_by(EvaluationRun.started_at.desc()).limit(20)
    )
    runs = result.scalars().all()
    return {
        "runs": [
            {
                "id": str(r.id),
                "run_type": r.run_type,
                "status": r.status,
                "total_cases": r.total_cases,
                "completed_cases": r.completed_cases,
                "results_summary": r.results_summary,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in runs
        ]
    }


@router.post("/evaluations/run")
async def run_evaluation(db: AsyncSession = Depends(get_db)):
    """Run evaluation by computing real metrics from DB data.

    Compares each case's recommendation against expected actions
    derived from issue-type heuristics, and computes per-issue-type
    accuracy, confidence, and escalation metrics.
    """
    # Expected action mapping (mirrors packages/evaluation/src/evaluator.py)
    expected_actions: dict[str, str] = {
        "duplicate_charge": "initiate_merchant_dispute",
        "pending_authorization": "release_authorization",
        "refund_mismatch": "initiate_refund_tracer",
        "settlement_delay": "close_no_action",
        "reversal_confusion": "close_no_action",
        "merchant_reference_mismatch": "request_additional_info",
        "timeline_inconsistency": "request_additional_info",
        "policy_eligibility": "escalate_to_senior",
        "account_servicing_exception": "escalate_to_senior",
        "unknown": "escalate_to_senior",
    }

    # Load all cases that have been processed (have recommendations)
    cases_result = await db.execute(select(Case).where(Case.status.notin_(["created"])))
    cases = cases_result.scalars().all()
    total = len(cases)

    if total == 0:
        run = EvaluationRun(
            id=uuid.uuid4(),
            run_type="regression",
            status="completed",
            total_cases=0,
            completed_cases=0,
            results_summary={"message": "No processed cases to evaluate"},
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        db.add(run)
        await db.commit()
        return {"id": str(run.id), "status": "completed", "total_cases": 0}

    # Load recommendations keyed by case_id
    rec_result = await db.execute(select(Recommendation))
    recs_by_case: dict[uuid.UUID, Recommendation] = {}
    for rec in rec_result.scalars().all():
        recs_by_case[rec.case_id] = rec

    # Compute metrics
    correct = 0
    escalated = 0
    confidences: list[float] = []
    safety_passed = 0
    safety_total = 0
    per_type: dict[str, dict] = {}

    for case in cases:
        issue = case.issue_type.value if case.issue_type else "unknown"
        rec = recs_by_case.get(case.id)

        if issue not in per_type:
            per_type[issue] = {"total": 0, "correct": 0, "escalated": 0, "confidences": []}
        per_type[issue]["total"] += 1

        if rec:
            expected = expected_actions.get(issue, "escalate_to_senior")
            if rec.recommended_action == expected:
                correct += 1
                per_type[issue]["correct"] += 1
            if rec.confidence_score is not None:
                confidences.append(rec.confidence_score)
                per_type[issue]["confidences"].append(rec.confidence_score)
            if rec.safety_gate_passed is not None:
                safety_total += 1
                if rec.safety_gate_passed:
                    safety_passed += 1
            if rec.recommended_action in ("escalate_to_senior", "escalate_to_supervisor"):
                escalated += 1
                per_type[issue]["escalated"] += 1

    accuracy = correct / total if total else 0.0
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    safety_rate = safety_passed / safety_total if safety_total else 0.0
    escalation_rate = escalated / total if total else 0.0

    # Per-issue-type summary
    per_type_summary = {}
    for issue, data in per_type.items():
        t = data["total"]
        per_type_summary[issue] = {
            "total": t,
            "correct": data["correct"],
            "accuracy": round(data["correct"] / t, 3) if t else 0.0,
            "escalated": data["escalated"],
            "avg_confidence": round(sum(data["confidences"]) / len(data["confidences"]), 3)
            if data["confidences"]
            else None,
        }

    # Agent run latency
    agent_latency_result = await db.execute(
        select(func.avg(AgentRun.duration_ms)).where(AgentRun.status == "completed")
    )
    avg_latency = agent_latency_result.scalar() or 0

    results_summary = {
        "accuracy": round(accuracy, 3),
        "avg_confidence": round(avg_conf, 3),
        "safety_gate_pass_rate": round(safety_rate, 3),
        "avg_latency_ms": round(float(avg_latency), 1),
        "correct_actions": correct,
        "incorrect_actions": total - correct,
        "escalation_rate": round(escalation_rate, 3),
        "per_issue_type": per_type_summary,
    }

    run = EvaluationRun(
        id=uuid.uuid4(),
        run_type="regression",
        status="completed",
        total_cases=total,
        completed_cases=total,
        results_summary=results_summary,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    db.add(run)
    await db.commit()

    return {
        "id": str(run.id),
        "status": "completed",
        "total_cases": total,
        "results": results_summary,
    }
