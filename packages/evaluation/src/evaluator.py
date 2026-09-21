"""Evaluation harness for the agent system."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class EvalCase:
    case_number: str
    title: str
    description: str
    issue_type: str
    expected_action: str | None = None
    expected_issue_type: str | None = None
    amount: float | None = None
    priority: str = "medium"


@dataclass
class EvalResult:
    case_number: str
    issue_type: str | None = None
    classification_correct: bool | None = None
    action_correct: bool | None = None
    expected_action: str | None = None
    actual_action: str | None = None
    recommendation_present: bool = False
    citations_present: bool = False
    confidence_score: float | None = None
    tool_calls_made: int = 0
    workflow_completed: bool = False
    safety_gate_passed: bool | None = None
    duration_ms: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class EvalSummary:
    total_cases: int = 0
    classification_accuracy: float = 0.0
    action_accuracy: float = 0.0
    recommendation_rate: float = 0.0
    citation_rate: float = 0.0
    avg_confidence: float = 0.0
    avg_tool_calls: float = 0.0
    workflow_completion_rate: float = 0.0
    safety_gate_pass_rate: float = 0.0
    avg_duration_ms: float = 0.0
    error_rate: float = 0.0
    per_issue_type: dict = field(default_factory=dict)


def load_eval_cases(data_dir: str | Path) -> list[EvalCase]:
    """Load evaluation cases from seed data."""
    data_dir = Path(data_dir)
    cases_file = data_dir / "cases" / "seed_cases.json"
    if not cases_file.exists():
        return []

    cases_data = json.loads(cases_file.read_text())

    # Define expected outcomes for evaluation
    expected_actions = {
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

    eval_cases = []
    for cd in cases_data:
        issue_type = cd.get("issue_type", "unknown")
        eval_cases.append(
            EvalCase(
                case_number=cd["case_number"],
                title=cd["title"],
                description=cd["description"],
                issue_type=issue_type,
                expected_issue_type=issue_type,
                expected_action=expected_actions.get(issue_type, "escalate_to_senior"),
                amount=cd.get("amount"),
                priority=cd.get("priority", "medium"),
            )
        )

    return eval_cases


def compute_summary(results: list[EvalResult]) -> EvalSummary:
    """Compute aggregate metrics from evaluation results."""
    if not results:
        return EvalSummary()

    n = len(results)
    classification_correct = sum(1 for r in results if r.classification_correct is True)
    action_correct = sum(1 for r in results if r.action_correct is True)
    with_recommendation = sum(1 for r in results if r.recommendation_present)
    with_citations = sum(1 for r in results if r.citations_present)
    confidences = [r.confidence_score for r in results if r.confidence_score is not None]
    total_tools = sum(r.tool_calls_made for r in results)
    completed = sum(1 for r in results if r.workflow_completed)
    safety_passed = [r for r in results if r.safety_gate_passed is not None]
    safety_pass_count = sum(1 for r in safety_passed if r.safety_gate_passed)
    durations = [r.duration_ms for r in results if r.duration_ms > 0]
    with_errors = sum(1 for r in results if r.errors)

    # Per-issue-type breakdown
    by_type: dict[str, list[EvalResult]] = {}
    for r in results:
        t = r.issue_type or "unknown"
        by_type.setdefault(t, []).append(r)

    per_issue_type = {}
    for issue_type, type_results in by_type.items():
        tn = len(type_results)
        tc = sum(1 for r in type_results if r.classification_correct is True)
        ta = sum(1 for r in type_results if r.action_correct is True)
        tconf = [r.confidence_score for r in type_results if r.confidence_score is not None]
        per_issue_type[issue_type] = {
            "total": tn,
            "classification_accuracy": round(tc / tn, 3) if tn else 0.0,
            "action_accuracy": round(ta / tn, 3) if tn else 0.0,
            "avg_confidence": round(sum(tconf) / len(tconf), 3) if tconf else 0.0,
        }

    return EvalSummary(
        total_cases=n,
        classification_accuracy=classification_correct / n if n else 0,
        action_accuracy=action_correct / n if n else 0,
        recommendation_rate=with_recommendation / n if n else 0,
        citation_rate=with_citations / n if n else 0,
        avg_confidence=sum(confidences) / len(confidences) if confidences else 0,
        avg_tool_calls=total_tools / n if n else 0,
        workflow_completion_rate=completed / n if n else 0,
        safety_gate_pass_rate=safety_pass_count / len(safety_passed) if safety_passed else 0,
        avg_duration_ms=sum(durations) / len(durations) if durations else 0,
        error_rate=with_errors / n if n else 0,
        per_issue_type=per_issue_type,
    )


def format_eval_report(summary: EvalSummary) -> str:
    """Format evaluation summary as a readable report."""
    lines = [
        "",
        "=== LedgerDesk Evaluation Report ===",
        f"Date: {datetime.now().isoformat()}",
        "",
        f"Cases Evaluated: {summary.total_cases}",
        "",
        "Classification:",
        f"  Accuracy: {summary.classification_accuracy:.1%}",
        f"  Action Accuracy: {summary.action_accuracy:.1%}",
        "",
        "Recommendations:",
        f"  Generation Rate: {summary.recommendation_rate:.1%}",
        f"  Citation Rate: {summary.citation_rate:.1%}",
        f"  Avg Confidence: {summary.avg_confidence:.3f}",
        "",
        "Workflow:",
        f"  Completion Rate: {summary.workflow_completion_rate:.1%}",
        f"  Avg Tool Calls: {summary.avg_tool_calls:.1f}",
        f"  Avg Duration: {summary.avg_duration_ms:.0f}ms",
        "",
        "Safety:",
        f"  Gate Pass Rate: {summary.safety_gate_pass_rate:.1%}",
        "",
        "Errors:",
        f"  Error Rate: {summary.error_rate:.1%}",
    ]

    if summary.per_issue_type:
        lines.append("")
        lines.append("Per Issue Type:")
        for issue_type, data in sorted(summary.per_issue_type.items()):
            lines.append(
                f"  {issue_type}: "
                f"n={data['total']} "
                f"class={data['classification_accuracy']:.0%} "
                f"action={data['action_accuracy']:.0%} "
                f"conf={data['avg_confidence']:.3f}"
            )

    lines.append("===================================")
    return "\n".join(lines)
