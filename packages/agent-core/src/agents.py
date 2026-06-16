"""Individual agent implementations."""

import json
import time
import uuid
from dataclasses import dataclass, field

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentRun
from llm import LLMClient, MockLLMClient
from prompts import (
    TRIAGE_PROMPT,
    TOOL_PLANNER_PROMPT,
    DECISION_PROMPT,
    SAFETY_GATE_PROMPT,
    CASE_WRITER_PROMPT,
)

logger = structlog.get_logger()


@dataclass
class AgentResult:
    agent_type: str
    status: str  # completed, failed
    output: dict
    duration_ms: int
    run_id: str
    token_usage: dict = field(default_factory=dict)


async def _run_agent(
    db: AsyncSession,
    case_id: uuid.UUID,
    agent_type: str,
    prompt: str,
    llm: LLMClient | MockLLMClient,
    trace_id: str,
    prompt_version: str = "1.0",
) -> AgentResult:
    """Execute an agent and record the run."""
    run_id = uuid.uuid4()
    start = time.time()

    run = AgentRun(
        id=run_id,
        case_id=case_id,
        agent_type=agent_type,
        status="running",
        input_data={"prompt_preview": prompt[:500]},
        prompt_version=prompt_version,
        trace_id=trace_id,
    )
    db.add(run)
    await db.flush()

    try:
        output = await llm.complete_json(prompt)
        duration_ms = int((time.time() - start) * 1000)

        # Track token usage (estimates based on prompt/output size)
        prompt_tokens = len(prompt.split()) * 2
        completion_tokens = len(json.dumps(output).split()) * 2
        token_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

        run.status = "completed"
        run.output_data = output
        run.duration_ms = duration_ms
        run.token_usage = token_usage
        await db.flush()

        logger.info(
            "agent_completed",
            agent_type=agent_type,
            case_id=str(case_id),
            duration_ms=duration_ms,
            tokens=token_usage["total_tokens"],
        )

        return AgentResult(
            agent_type=agent_type,
            status="completed",
            output=output,
            duration_ms=duration_ms,
            run_id=str(run_id),
            token_usage=token_usage,
        )
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        run.status = "failed"
        run.error_message = str(e)
        run.duration_ms = duration_ms
        await db.flush()

        logger.error("agent_failed", agent_type=agent_type, error=str(e))

        return AgentResult(
            agent_type=agent_type,
            status="failed",
            output={"error": str(e)},
            duration_ms=duration_ms,
            run_id=str(run_id),
        )


async def run_triage_agent(
    db: AsyncSession,
    case_id: uuid.UUID,
    case_data: dict,
    llm: LLMClient | MockLLMClient,
    trace_id: str,
) -> AgentResult:
    """Run the triage agent to classify a case."""
    prompt = TRIAGE_PROMPT.format(
        title=case_data.get("title", ""),
        description=case_data.get("description", ""),
        transaction_id=case_data.get("transaction_id", "N/A"),
        account_id=case_data.get("account_id", "N/A"),
        merchant_name=case_data.get("merchant_name", "N/A"),
        amount=case_data.get("amount", "N/A"),
        currency=case_data.get("currency", "USD"),
    )
    return await _run_agent(db, case_id, "triage", prompt, llm, trace_id)


async def run_tool_planner(
    db: AsyncSession,
    case_id: uuid.UUID,
    case_data: dict,
    retrieval_context: str,
    llm: LLMClient | MockLLMClient,
    trace_id: str,
) -> AgentResult:
    """Run the tool planner to decide which tools to call."""
    prompt = TOOL_PLANNER_PROMPT.format(
        issue_type=case_data.get("issue_type", "unknown"),
        description=case_data.get("description", ""),
        transaction_id=case_data.get("transaction_id", "N/A"),
        account_id=case_data.get("account_id", "N/A"),
        merchant_name=case_data.get("merchant_name", "N/A"),
        merchant_ref=case_data.get("merchant_ref", "N/A"),
        retrieval_context=retrieval_context,
    )
    return await _run_agent(db, case_id, "tool_planner", prompt, llm, trace_id)


async def run_decision_agent(
    db: AsyncSession,
    case_id: uuid.UUID,
    case_data: dict,
    policy_citations: str,
    tool_evidence: str,
    llm: LLMClient | MockLLMClient,
    trace_id: str,
) -> AgentResult:
    """Run the decision agent to generate a recommendation."""
    prompt = DECISION_PROMPT.format(
        case_number=case_data.get("case_number", ""),
        issue_type=case_data.get("issue_type", "unknown"),
        title=case_data.get("title", ""),
        description=case_data.get("description", ""),
        amount=case_data.get("amount", "N/A"),
        currency=case_data.get("currency", "USD"),
        policy_citations=policy_citations,
        tool_evidence=tool_evidence,
    )
    return await _run_agent(db, case_id, "decision", prompt, llm, trace_id)


async def run_safety_gate(
    db: AsyncSession,
    case_id: uuid.UUID,
    recommendation: dict,
    amount: float | None,
    llm: LLMClient | MockLLMClient,
    trace_id: str,
) -> AgentResult:
    """Run the safety gate to validate a recommendation."""
    prompt = SAFETY_GATE_PROMPT.format(
        recommended_action=recommendation.get("recommended_action", ""),
        confidence_score=recommendation.get("confidence_score", 0),
        rationale=recommendation.get("rationale", ""),
        amount=amount or "N/A",
        required_approval_level=recommendation.get(
            "required_approval_level", "analyst"
        ),
        num_citations=len(recommendation.get("policy_citations", [])),
        num_evidence=len(
            recommendation.get("evidence_summary", {}).get("supporting", [])
        ),
    )
    return await _run_agent(db, case_id, "safety_gate", prompt, llm, trace_id)


async def run_case_writer(
    db: AsyncSession,
    case_id: uuid.UUID,
    case_data: dict,
    recommendation: dict,
    evidence_summary: str,
    llm: LLMClient | MockLLMClient,
    trace_id: str,
) -> AgentResult:
    """Run the case writer to generate notes and summaries."""
    prompt = CASE_WRITER_PROMPT.format(
        case_number=case_data.get("case_number", ""),
        issue_type=case_data.get("issue_type", "unknown"),
        title=case_data.get("title", ""),
        description=case_data.get("description", ""),
        recommended_action=recommendation.get("recommended_action", ""),
        confidence_score=recommendation.get("confidence_score", 0),
        rationale=recommendation.get("rationale", ""),
        evidence_summary=evidence_summary,
    )
    return await _run_agent(db, case_id, "case_writer", prompt, llm, trace_id)
