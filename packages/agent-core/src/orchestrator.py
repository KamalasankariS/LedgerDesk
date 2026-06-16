"""Main workflow orchestrator - coordinates all agents through the state machine."""

import json
import time
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.case import Case, CaseStatus
from app.models.agent import Recommendation, ToolInvocation, CaseRetrievalResult
from app.models.audit import AuditEvent
from app.services.case_service import CaseService

from agents import (
    run_triage_agent,
    run_tool_planner,
    run_decision_agent,
    run_safety_gate,
    run_case_writer,
)
from llm import LLMClient, MockLLMClient

logger = structlog.get_logger()


def _get_llm_client() -> LLMClient | MockLLMClient:
    """Get the appropriate LLM client."""
    if settings.openai_api_key:
        return LLMClient(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.llm_model,
        )
    return MockLLMClient()


async def run_full_workflow(db: AsyncSession, case_id: uuid.UUID) -> dict:
    """Execute the complete agent workflow for a case."""
    start_time = time.time()

    # Load case
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise ValueError(f"Case {case_id} not found")

    trace_id = case.trace_id or str(uuid.uuid4())
    case_service = CaseService(db)
    llm = _get_llm_client()
    steps = []

    case_data = {
        "case_number": case.case_number,
        "title": case.title,
        "description": case.description,
        "transaction_id": case.transaction_id,
        "account_id": case.account_id,
        "merchant_name": case.merchant_name,
        "merchant_ref": case.merchant_ref,
        "amount": str(case.amount) if case.amount else None,
        "currency": case.currency,
        "issue_type": case.issue_type.value if case.issue_type else "unknown",
    }

    try:
        # === STEP 1: TRIAGE ===
        triage_result = await run_triage_agent(db, case_id, case_data, llm, trace_id)
        if triage_result.status == "completed":
            triage_output = triage_result.output
            # Update case with triage results
            if triage_output.get("issue_type"):
                try:
                    from app.models.case import IssueType

                    case.issue_type = IssueType(triage_output["issue_type"])
                except (ValueError, KeyError):
                    case.issue_type = IssueType.UNKNOWN
            if triage_output.get("entities"):
                case.extracted_entities = triage_output["entities"]
            case_data["issue_type"] = triage_output.get(
                "issue_type", case_data["issue_type"]
            )

        await case_service.transition_status(
            case, CaseStatus.TRIAGED, "system", "Triage agent completed"
        )
        steps.append(
            {
                "step": "triage",
                "status": triage_result.status,
                "agent_run_id": triage_result.run_id,
                "duration_ms": triage_result.duration_ms,
            }
        )

        # === STEP 2: RETRIEVAL ===
        retrieval_results = []
        try:
            import sys
            from pathlib import Path

            retrieval_path = str(
                Path(__file__).resolve().parent.parent.parent / "retrieval" / "src"
            )
            if retrieval_path not in sys.path:
                sys.path.insert(0, retrieval_path)
            from search import search_policies, package_citations

            retrieval_results = await search_policies(
                db,
                query=f"{case_data['issue_type']} {case.title} {case.description[:200]}",
                top_k=5,
                api_key=settings.openai_api_key or None,
            )
            citations = package_citations(retrieval_results)

            # Save retrieval results
            for rr in retrieval_results:
                db.add(
                    CaseRetrievalResult(
                        id=uuid.uuid4(),
                        case_id=case_id,
                        chunk_id=uuid.UUID(rr.chunk_id),
                        relevance_score=rr.relevance_score,
                        query_text=f"{case_data['issue_type']} {case.title}",
                        rank=rr.rank,
                    )
                )
        except Exception as e:
            logger.warning("retrieval_failed", error=str(e))
            citations = []

        await case_service.transition_status(
            case, CaseStatus.CONTEXT_RETRIEVED, "system"
        )
        retrieval_context = (
            "\n\n".join(
                f"[{c.get('document_title', 'Policy')} - {c.get('section', 'N/A')}]\n{c.get('content', '')[:500]}"
                for c in citations
            )
            if citations
            else "No policy documents retrieved."
        )
        steps.append(
            {"step": "retrieval", "status": "completed", "citations": len(citations)}
        )

        # === STEP 3: TOOL PLANNING ===
        tool_plan_result = await run_tool_planner(
            db, case_id, case_data, retrieval_context, llm, trace_id
        )
        await case_service.transition_status(case, CaseStatus.TOOLS_SELECTED, "system")
        steps.append(
            {
                "step": "tool_planning",
                "status": tool_plan_result.status,
                "agent_run_id": tool_plan_result.run_id,
            }
        )

        # === STEP 4: TOOL EXECUTION ===
        tool_outputs = {}
        if tool_plan_result.status == "completed":
            planned_tools = tool_plan_result.output.get("tools", [])
            for tool_spec in planned_tools[: settings.max_tool_calls]:
                tool_name = tool_spec.get("tool_name", "")
                params = tool_spec.get("params", {})

                # Replace placeholder params with actual case data
                resolved_params = _resolve_tool_params(params, case_data)

                # Execute tool
                tool_output = await _execute_tool(
                    db, case_id, tool_name, resolved_params, trace_id
                )
                tool_outputs[tool_name] = tool_output

        await case_service.transition_status(case, CaseStatus.TOOLS_EXECUTED, "system")
        steps.append(
            {
                "step": "tool_execution",
                "status": "completed",
                "tools_executed": len(tool_outputs),
            }
        )

        # === STEP 5: DECISION ===
        policy_citations_str = (
            json.dumps(citations, indent=2)
            if citations
            else "No policy citations available."
        )
        tool_evidence_str = (
            json.dumps(tool_outputs, indent=2, default=str)
            if tool_outputs
            else "No tool evidence available."
        )

        decision_result = await run_decision_agent(
            db,
            case_id,
            case_data,
            policy_citations_str,
            tool_evidence_str,
            llm,
            trace_id,
        )

        recommendation_data = {}
        if decision_result.status == "completed":
            recommendation_data = decision_result.output

            # Save recommendation
            rec = Recommendation(
                id=uuid.uuid4(),
                case_id=case_id,
                recommended_action=recommendation_data.get(
                    "recommended_action", "escalate_to_senior"
                ),
                rationale=recommendation_data.get("rationale", ""),
                confidence_score=recommendation_data.get("confidence_score", 0.0),
                policy_citations=recommendation_data.get("policy_citations"),
                evidence_summary=recommendation_data.get("evidence_summary"),
                structured_decision=recommendation_data.get("structured_decision"),
                required_approval_level=recommendation_data.get(
                    "required_approval_level", "analyst"
                ),
            )
            db.add(rec)

            case.confidence_score = recommendation_data.get("confidence_score", 0.0)

        await case_service.transition_status(
            case, CaseStatus.RECOMMENDATION_GENERATED, "system"
        )
        steps.append(
            {
                "step": "decision",
                "status": decision_result.status,
                "agent_run_id": decision_result.run_id,
            }
        )

        # === STEP 6: SAFETY GATE ===
        safety_result = await run_safety_gate(
            db,
            case_id,
            recommendation_data,
            float(case.amount) if case.amount else None,
            llm,
            trace_id,
        )

        if safety_result.status == "completed":
            safety_output = safety_result.output
            # Update recommendation with safety gate results
            if recommendation_data:
                rec.safety_gate_passed = safety_output.get("safe_to_present", False)
                rec.safety_gate_details = safety_output

            case.requires_human_review = safety_output.get(
                "requires_human_review", True
            )

            # Override approval level if safety gate says so
            override = safety_output.get("approval_level_override")
            if override and recommendation_data:
                rec.required_approval_level = override

        await case_service.transition_status(case, CaseStatus.SAFETY_CHECKED, "system")
        steps.append(
            {
                "step": "safety_gate",
                "status": safety_result.status,
                "agent_run_id": safety_result.run_id,
            }
        )

        # === STEP 7: CASE WRITER ===
        writer_result = await run_case_writer(
            db,
            case_id,
            case_data,
            recommendation_data,
            tool_evidence_str[:1000],
            llm,
            trace_id,
        )
        steps.append(
            {
                "step": "case_writer",
                "status": writer_result.status,
                "agent_run_id": writer_result.run_id,
            }
        )

        # === STEP 8: AWAIT REVIEW ===
        await case_service.transition_status(case, CaseStatus.AWAITING_REVIEW, "system")
        steps.append({"step": "awaiting_review", "status": "completed"})

        await db.flush()

        total_duration = int((time.time() - start_time) * 1000)

        # Log audit event for workflow completion
        db.add(
            AuditEvent(
                id=uuid.uuid4(),
                case_id=case_id,
                event_type="workflow_completed",
                actor_type="system",
                action="full_workflow_run",
                resource_type="case",
                resource_id=str(case_id),
                details={
                    "steps": len(steps),
                    "total_duration_ms": total_duration,
                    "citations": len(citations),
                    "tools_executed": len(tool_outputs),
                },
                trace_id=trace_id,
            )
        )
        await db.flush()

        logger.info(
            "workflow_completed",
            case_id=str(case_id),
            steps=len(steps),
            duration_ms=total_duration,
        )

        return {
            "case_id": str(case_id),
            "status": case.status.value,
            "steps": steps,
            "trace_id": trace_id,
            "total_duration_ms": total_duration,
            "recommendation": recommendation_data if recommendation_data else None,
            "citations_count": len(citations),
            "tools_executed": len(tool_outputs),
        }

    except Exception as e:
        logger.error("workflow_failed", case_id=str(case_id), error=str(e))
        try:
            await case_service.transition_status(
                case, CaseStatus.FAILED_SAFE, "system", str(e)
            )
        except Exception:
            pass
        await db.flush()
        raise


def _resolve_tool_params(params: dict, case_data: dict) -> dict:
    """Replace placeholder values in tool params with actual case data."""
    resolved = {}
    for key, value in params.items():
        if isinstance(value, str) and value == "from_case":
            # Map param keys to case data
            mappings = {
                "transaction_id": case_data.get("transaction_id"),
                "account_id": case_data.get("account_id"),
                "reference_id": case_data.get("transaction_id"),
                "merchant_ref": case_data.get("merchant_ref"),
                "merchant_id": case_data.get("merchant_ref"),
                "case_id": case_data.get("case_number"),
                "issue_type": case_data.get("issue_type"),
                "merchant": case_data.get("merchant_name"),
            }
            resolved[key] = mappings.get(key, value)
        else:
            resolved[key] = value
    return resolved


async def _execute_tool(
    db: AsyncSession,
    case_id: uuid.UUID,
    tool_name: str,
    params: dict,
    trace_id: str,
) -> dict:
    """Execute a mock tool and record the invocation."""
    import json as json_lib
    from pathlib import Path

    start = time.time()

    DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "sample_data"

    def load_json(subdir, filename):
        fp = DATA_DIR / subdir / filename
        return json_lib.loads(fp.read_text()) if fp.exists() else []

    try:
        transactions = load_json("transactions", "seed_transactions.json")
        accounts = load_json("accounts", "seed_accounts.json")
        settlements = load_json("settlements", "seed_settlements.json")
        refunds = load_json("refunds", "seed_refunds.json")
        merchants = load_json("merchants", "seed_merchants.json")

        result = None
        if tool_name == "get_transaction_timeline":
            txn_id = params.get("transaction_id")
            acct_id = None
            for t in transactions:
                if t["transaction_id"] == txn_id:
                    acct_id = t["account_id"]
                    break
            acct_txns = (
                [t for t in transactions if t.get("account_id") == acct_id]
                if acct_id
                else []
            )
            result = {
                "transaction_id": txn_id,
                "timeline": acct_txns,
                "total": len(acct_txns),
            }

        elif tool_name == "get_account_activity":
            acct_id = params.get("account_id")
            account = next((a for a in accounts if a["account_id"] == acct_id), None)
            acct_txns = [t for t in transactions if t.get("account_id") == acct_id]
            result = {
                "account": account,
                "transactions": acct_txns,
                "count": len(acct_txns),
            }

        elif tool_name == "get_settlement_status":
            ref = params.get("reference_id") or params.get("transaction_id")
            matches = [s for s in settlements if s.get("transaction_id") == ref]
            result = {
                "reference": ref,
                "settlements": matches,
                "found": len(matches) > 0,
            }

        elif tool_name == "get_refund_status":
            ref = params.get("reference_id") or params.get("transaction_id")
            matches = [
                r
                for r in refunds
                if r.get("original_transaction_id") == ref or r.get("arn") == ref
            ]
            result = {"reference": ref, "refunds": matches, "found": len(matches) > 0}

        elif tool_name == "get_merchant_reference":
            ref = params.get("merchant_ref") or params.get("merchant_id")
            match = next(
                (
                    m
                    for m in merchants
                    if ref and (m.get("merchant_id") == ref or ref in m.get("name", ""))
                ),
                None,
            )
            result = {
                "merchant_ref": ref,
                "merchant": match,
                "found": match is not None,
            }

        elif tool_name == "search_similar_cases":
            result = {
                "query": params,
                "similar_cases": [],
                "message": "No similar cases found in history",
            }

        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        status = "success"
        error = None
    except Exception as e:
        result = None
        status = "error"
        error = str(e)

    duration_ms = int((time.time() - start) * 1000)

    invocation = ToolInvocation(
        id=uuid.uuid4(),
        case_id=case_id,
        tool_name=tool_name,
        tool_type="read",
        input_params=params,
        output_data=result,
        status=status,
        error_message=error,
        duration_ms=duration_ms,
        trace_id=trace_id,
    )
    db.add(invocation)

    return result or {"error": error}
