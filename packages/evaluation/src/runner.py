"""Evaluation test runner."""

import asyncio
import logging
from pathlib import Path

from .evaluator import (
    EvalCase,
    EvalResult,
    EvalSummary,
    compute_summary,
    format_eval_report,
    load_eval_cases,
)

logger = logging.getLogger(__name__)


async def _evaluate_single_case(
    client,
    eval_case: EvalCase,
    api_case: dict,
) -> EvalResult:
    """Evaluate a single case against the API."""
    result = EvalResult(
        case_number=eval_case.case_number,
        issue_type=eval_case.issue_type,
        expected_action=eval_case.expected_action,
    )
    case_id = api_case["id"]

    try:
        # Run workflow if case is in 'created' status
        if api_case["status"] == "created":
            wf_resp = await client.post(
                "/api/v1/workflow/run",
                json={"case_id": case_id},
            )
            if wf_resp.status_code == 200:
                wf_data = wf_resp.json()
                result.workflow_completed = True
                result.duration_ms = wf_data.get("total_duration_ms", 0)
                result.tool_calls_made = wf_data.get("tools_executed", 0)
            else:
                result.errors.append(f"Workflow failed: {wf_resp.status_code}")

        # Get updated case
        case_resp = await client.get(f"/api/v1/cases/{case_id}")
        updated_case = case_resp.json()

        # Check classification
        result.classification_correct = (
            updated_case.get("issue_type") == eval_case.expected_issue_type
        )

        # Check recommendations
        rec_resp = await client.get(f"/api/v1/cases/{case_id}/recommendations")
        recs = rec_resp.json()
        if recs:
            result.recommendation_present = True
            latest = recs[0]
            result.actual_action = latest.get("recommended_action")
            result.confidence_score = latest.get("confidence_score")
            result.citations_present = bool(latest.get("policy_citations"))
            result.safety_gate_passed = latest.get("safety_gate_passed")
            # Check action correctness
            if eval_case.expected_action:
                result.action_correct = result.actual_action == eval_case.expected_action

    except Exception as e:
        result.errors.append(str(e))

    logger.info(
        "Evaluated: %s - %s",
        eval_case.case_number,
        "OK" if not result.errors else "ERRORS",
    )
    return result


async def run_evaluation_batch(
    api_base_url: str = "http://localhost:8000",
    data_dir: str | Path = None,
    concurrency: int = 5,
) -> EvalSummary:
    """Run evaluation against a running API instance with concurrent case processing."""
    import httpx

    if data_dir is None:
        data_dir = Path(__file__).parent.parent.parent.parent / "sample_data"

    eval_cases = load_eval_cases(data_dir)
    if not eval_cases:
        logger.warning("No evaluation cases found")
        return EvalSummary()

    results: list[EvalResult] = []
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(base_url=api_base_url, timeout=120) as client:
        # Get all cases from API
        resp = await client.get("/api/v1/cases", params={"page_size": "100"})
        api_cases = resp.json().get("cases", [])

        case_map = {c["case_number"]: c for c in api_cases}

        async def _bounded_eval(eval_case):
            api_case = case_map.get(eval_case.case_number)
            if not api_case:
                return EvalResult(
                    case_number=eval_case.case_number,
                    errors=["Case not found in API"],
                )
            async with semaphore:
                return await _evaluate_single_case(client, eval_case, api_case)

        # Run all evaluations concurrently (bounded by semaphore)
        eval_results = await asyncio.gather(
            *[_bounded_eval(ec) for ec in eval_cases],
            return_exceptions=True,
        )

        for i, r in enumerate(eval_results):
            if isinstance(r, Exception):
                results.append(
                    EvalResult(
                        case_number=eval_cases[i].case_number,
                        errors=[str(r)],
                    )
                )
            else:
                results.append(r)

    summary = compute_summary(results)
    logger.info(format_eval_report(summary))
    return summary


if __name__ == "__main__":
    asyncio.run(run_evaluation_batch())
