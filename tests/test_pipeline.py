"""Standalone pipeline tests — validates MockLLMClient produces correct outputs
for all agent stages without requiring a running server or database.

Run with: python -m pytest tests/test_pipeline.py -v
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT / "packages" / "agent-core" / "src"))

from llm import MockLLMClient  # noqa: E402
from prompts import (  # noqa: E402
    CASE_WRITER_PROMPT,
    DECISION_PROMPT,
    SAFETY_GATE_PROMPT,
    TOOL_PLANNER_PROMPT,
    TRIAGE_PROMPT,
)

SAMPLE_DATA = PROJECT / "sample_data"


@pytest.fixture
def llm():
    return MockLLMClient()


def _load_seed_cases() -> list[dict]:
    return json.loads((SAMPLE_DATA / "cases" / "seed_cases.json").read_text())


# ── Triage Agent ─────────────────────────────────────────────────────────────


class TestTriageClassification:
    """Verify MockLLMClient classifies each issue type from prompt keywords."""

    KEYWORD_MAP = {
        "duplicate_charge": "cardholder was charged twice for the same grocery purchase",
        "pending_authorization": "pending authorization hold not releasing",
        "settlement_delay": "settlement has not arrived after expected window",
        "refund_mismatch": "refund amount does not match original charge",
        "reversal_confusion": "reversal and partial credit confusion",
        "merchant_reference_mismatch": "cardholder does not recognize the merchant descriptor on statement",
        "timeline_inconsistency": "timeline shows events in wrong sequence order",
        "policy_eligibility": "multiple policies may apply, need eligibility determination",
        "account_servicing_exception": "late fee charged despite on-time payment, credit limit",
    }

    @pytest.mark.parametrize("issue_type,keywords", KEYWORD_MAP.items())
    async def test_classifies_issue_type(self, llm, issue_type, keywords):
        prompt = TRIAGE_PROMPT.format(
            title=f"Test case for {issue_type}",
            description=keywords,
            transaction_id="TXN-TEST",
            account_id="ACCT-TEST",
            merchant_name="Test Merchant",
            amount="100.00",
            currency="USD",
        )
        result = await llm.complete_json(prompt)
        assert result["issue_type"] == issue_type

    async def test_triage_output_schema(self, llm):
        prompt = TRIAGE_PROMPT.format(
            title="Duplicate charge",
            description="Charged twice for the same purchase",
            transaction_id="TXN-001",
            account_id="ACCT-001",
            merchant_name="Store",
            amount="50.00",
            currency="USD",
        )
        result = await llm.complete_json(prompt)
        assert "issue_type" in result
        assert "confidence" in result
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0
        assert "entities" in result
        entities = result["entities"]
        for key in ("transaction_ids", "amounts", "dates", "merchants", "key_facts"):
            assert key in entities
        assert "reasoning" in result


# ── Tool Planner ─────────────────────────────────────────────────────────────


class TestToolPlanning:
    async def test_baseline_tools_always_present(self, llm):
        prompt = TOOL_PLANNER_PROMPT.format(
            issue_type="duplicate_charge",
            description="Two identical charges",
            transaction_id="TXN-001",
            account_id="ACCT-001",
            merchant_name="Store",
            merchant_ref="REF-001",
            retrieval_context="Policy section 3.1",
        )
        result = await llm.complete_json(prompt)
        tool_names = [t["tool_name"] for t in result["tools"]]
        assert "get_transaction_timeline" in tool_names
        assert "get_account_activity" in tool_names

    async def test_refund_case_includes_refund_tool(self, llm):
        prompt = TOOL_PLANNER_PROMPT.format(
            issue_type="refund_mismatch",
            description="Refund amount wrong",
            transaction_id="TXN-001",
            account_id="ACCT-001",
            merchant_name="Store",
            merchant_ref="REF-001",
            retrieval_context="",
        )
        result = await llm.complete_json(prompt)
        tool_names = [t["tool_name"] for t in result["tools"]]
        assert "get_refund_status" in tool_names

    async def test_settlement_case_includes_settlement_tool(self, llm):
        prompt = TOOL_PLANNER_PROMPT.format(
            issue_type="settlement_delay",
            description="Settlement delayed",
            transaction_id="TXN-001",
            account_id="ACCT-001",
            merchant_name="Store",
            merchant_ref="REF-001",
            retrieval_context="",
        )
        result = await llm.complete_json(prompt)
        tool_names = [t["tool_name"] for t in result["tools"]]
        assert "get_settlement_status" in tool_names

    async def test_tool_plan_output_schema(self, llm):
        prompt = TOOL_PLANNER_PROMPT.format(
            issue_type="duplicate_charge",
            description="Charged twice",
            transaction_id="TXN-001",
            account_id="ACCT-001",
            merchant_name="Store",
            merchant_ref="REF-001",
            retrieval_context="",
        )
        result = await llm.complete_json(prompt)
        assert "tools" in result
        assert "reasoning" in result
        for tool in result["tools"]:
            assert "tool_name" in tool
            assert "params" in tool
            assert "priority" in tool
            assert "reason" in tool


# ── Decision Agent ───────────────────────────────────────────────────────────


class TestDecisionAgent:
    DECISION_CASES = [
        ("duplicate_charge", "duplicate charge, charged twice", "initiate_merchant_dispute"),
        ("pending_authorization", "pending authorization hold not releasing", "release_authorization"),
        ("settlement_delay", "settlement delay, funds not arrived", "initiate_refund_tracer"),
        (
            "refund_mismatch",
            "refund exceeds the original charge, greater than the original amount",
            "initiate_merchant_dispute",
        ),
        ("timeline_inconsistency", "timeline inconsistency, settlement before authorization", "request_additional_info"),
        ("policy_eligibility", "policy eligibility unclear, multiple policies apply", "escalate_to_senior"),
        ("account_servicing_exception", "late fee charged despite on-time payment", "reverse_fee"),
    ]

    @pytest.mark.parametrize("issue_type,desc,expected_action", DECISION_CASES)
    async def test_decision_action(self, llm, issue_type, desc, expected_action):
        prompt = DECISION_PROMPT.format(
            case_number="CSE-TEST",
            issue_type=issue_type,
            title=f"Test {issue_type}",
            description=desc,
            amount="100.00",
            currency="USD",
            policy_citations="Test policy section 1.1",
            tool_evidence='{"transaction": "found"}',
        )
        result = await llm.complete_json(prompt)
        assert result["recommended_action"] == expected_action

    async def test_low_confidence_escalates(self, llm):
        """Ambiguous case should get escalation with low confidence."""
        prompt = DECISION_PROMPT.format(
            case_number="CSE-TEST",
            issue_type="unknown",
            title="Unclear case",
            description="Something happened with the account but unclear what.",
            amount="100.00",
            currency="USD",
            policy_citations="No clear policy match.",
            tool_evidence="{}",
        )
        result = await llm.complete_json(prompt)
        assert result["recommended_action"] == "escalate_to_senior"
        assert result["confidence_score"] < 0.70

    async def test_decision_output_schema(self, llm):
        prompt = DECISION_PROMPT.format(
            case_number="CSE-TEST",
            issue_type="duplicate_charge",
            title="Test",
            description="Charged twice at store",
            amount="50.00",
            currency="USD",
            policy_citations="Section 3.1",
            tool_evidence="{}",
        )
        result = await llm.complete_json(prompt)
        # Top-level keys
        for key in (
            "recommended_action",
            "rationale",
            "confidence_score",
            "policy_citations",
            "evidence_summary",
            "structured_decision",
            "required_approval_level",
            "analyst_summary",
        ):
            assert key in result, f"Missing key: {key}"
        # Rationale is a substantial string
        assert len(result["rationale"]) > 100
        # Confidence is a valid float
        assert 0.0 <= result["confidence_score"] <= 1.0
        # Citations are a list of dicts
        assert isinstance(result["policy_citations"], list)
        assert len(result["policy_citations"]) >= 1
        for cite in result["policy_citations"]:
            assert "document" in cite
            assert "section" in cite
            assert "quote" in cite
        # Evidence summary has all sub-keys
        ev = result["evidence_summary"]
        for key in ("supporting", "concerning", "missing"):
            assert key in ev
            assert isinstance(ev[key], list)
        # Structured decision
        sd = result["structured_decision"]
        assert "action" in sd
        assert "risk_level" in sd


# ── Safety Gate ──────────────────────────────────────────────────────────────


class TestSafetyGate:
    async def test_normal_confidence_passes(self, llm):
        prompt = SAFETY_GATE_PROMPT.format(
            recommended_action="initiate_merchant_dispute",
            confidence_score=0.85,
            rationale="Well-grounded recommendation",
            amount=127.43,
            required_approval_level="analyst",
            num_citations=2,
            num_evidence=3,
        )
        result = await llm.complete_json(prompt)
        assert result["safe_to_present"] is True

    async def test_low_confidence_flags(self, llm):
        prompt = SAFETY_GATE_PROMPT.format(
            recommended_action="escalate_to_senior",
            confidence_score=0.65,
            rationale="Uncertain recommendation",
            amount=100,
            required_approval_level="analyst",
            num_citations=1,
            num_evidence=1,
        )
        result = await llm.complete_json(prompt)
        assert "low_confidence_below_threshold" in result["flags"]

    async def test_critically_low_confidence_unsafe(self, llm):
        prompt = SAFETY_GATE_PROMPT.format(
            recommended_action="close_no_action",
            confidence_score=0.45,
            rationale="Very uncertain",
            amount=50,
            required_approval_level="analyst",
            num_citations=0,
            num_evidence=0,
        )
        result = await llm.complete_json(prompt)
        assert result["safe_to_present"] is False
        assert "critically_low_confidence" in result["flags"]

    async def test_high_value_flags(self, llm):
        prompt = SAFETY_GATE_PROMPT.format(
            recommended_action="initiate_merchant_dispute",
            confidence_score=0.85,
            rationale="Good recommendation",
            amount=8000,
            required_approval_level="analyst",
            num_citations=2,
            num_evidence=2,
        )
        result = await llm.complete_json(prompt)
        assert "high_value_case" in result["flags"]

    async def test_very_high_value_supervisor(self, llm):
        prompt = SAFETY_GATE_PROMPT.format(
            recommended_action="initiate_merchant_dispute",
            confidence_score=0.85,
            rationale="Good recommendation",
            amount=30000,
            required_approval_level="analyst",
            num_citations=2,
            num_evidence=2,
        )
        result = await llm.complete_json(prompt)
        assert result["approval_level_override"] == "supervisor"

    async def test_extreme_value_operations_manager(self, llm):
        prompt = SAFETY_GATE_PROMPT.format(
            recommended_action="escalate_to_senior",
            confidence_score=0.65,
            rationale="High value case",
            amount=150000,
            required_approval_level="analyst",
            num_citations=1,
            num_evidence=1,
        )
        result = await llm.complete_json(prompt)
        assert result["approval_level_override"] == "operations_manager"

    async def test_safety_output_schema(self, llm):
        prompt = SAFETY_GATE_PROMPT.format(
            recommended_action="close_no_action",
            confidence_score=0.80,
            rationale="OK",
            amount=100,
            required_approval_level="analyst",
            num_citations=1,
            num_evidence=1,
        )
        result = await llm.complete_json(prompt)
        for key in ("safe_to_present", "requires_human_review", "flags", "reasoning"):
            assert key in result


# ── Case Writer ──────────────────────────────────────────────────────────────


class TestCaseWriter:
    async def test_case_writer_output(self, llm):
        prompt = CASE_WRITER_PROMPT.format(
            case_number="CSE-TEST",
            issue_type="duplicate_charge",
            title="Test case",
            description="Charged twice",
            recommended_action="initiate_merchant_dispute",
            confidence_score=0.88,
            rationale="Policy supports dispute",
            evidence_summary="Transaction timeline confirms duplicate",
        )
        result = await llm.complete_json(prompt)
        for key in ("case_summary", "analyst_notes", "closure_template"):
            assert key in result
            assert isinstance(result[key], str)
            assert len(result[key]) > 10


# ── End-to-End Pipeline ─────────────────────────────────────────────────────


class TestEndToEndPipeline:
    """Run the full mock pipeline for representative cases and verify consistency."""

    E2E_CASES = [
        {
            "case_number": "CSE-2024-00147",
            "title": "Suspected Duplicate Charge",
            "description": "Cardholder reports being charged twice for a grocery purchase",
            "issue_type": "duplicate_charge",
            "transaction_id": "TXN-9382741",
            "account_id": "ACCT-4421889",
            "merchant_name": "Whole Foods",
            "merchant_ref": "WFM-1042",
            "amount": "127.43",
            "currency": "USD",
            "expected_action": "initiate_merchant_dispute",
        },
        {
            "case_number": "CSE-2024-00149",
            "title": "Pending Authorization Hold",
            "description": "Authorization hold not releasing after 5 days, pending hold still showing",
            "issue_type": "pending_authorization",
            "transaction_id": "TXN-9382856",
            "account_id": "ACCT-5517234",
            "merchant_name": "Hilton",
            "merchant_ref": "HGI-ATX",
            "amount": "450.00",
            "currency": "USD",
            "expected_action": "release_authorization",
        },
        {
            "case_number": "CSE-2024-00169",
            "title": "Extreme High Value - Unknown",
            "description": "Unauthorized charge, unknown merchant, no relationship",
            "issue_type": "unknown",
            "transaction_id": "TXN-9385503",
            "account_id": "ACCT-8834521",
            "merchant_name": "HEAVY EQUIP",
            "merchant_ref": "HEL-001",
            "amount": "150000.00",
            "currency": "USD",
            "expected_action": "escalate_to_senior",
        },
    ]

    @pytest.mark.parametrize(
        "case",
        E2E_CASES,
        ids=[c["case_number"] for c in E2E_CASES],
    )
    async def test_full_pipeline(self, llm, case):
        # Step 1: Triage
        triage_prompt = TRIAGE_PROMPT.format(
            title=case["title"],
            description=case["description"],
            transaction_id=case["transaction_id"],
            account_id=case["account_id"],
            merchant_name=case["merchant_name"],
            amount=case["amount"],
            currency=case["currency"],
        )
        triage = await llm.complete_json(triage_prompt)
        assert "issue_type" in triage

        # Step 2: Tool Planning
        tool_prompt = TOOL_PLANNER_PROMPT.format(
            issue_type=triage["issue_type"],
            description=case["description"],
            transaction_id=case["transaction_id"],
            account_id=case["account_id"],
            merchant_name=case["merchant_name"],
            merchant_ref=case["merchant_ref"],
            retrieval_context="Mock policy context",
        )
        tool_plan = await llm.complete_json(tool_prompt)
        assert len(tool_plan["tools"]) >= 1

        # Step 3: Decision
        decision_prompt = DECISION_PROMPT.format(
            case_number=case["case_number"],
            issue_type=triage["issue_type"],
            title=case["title"],
            description=case["description"],
            amount=case["amount"],
            currency=case["currency"],
            policy_citations="Policy section applicable",
            tool_evidence='{"data": "mock evidence"}',
        )
        decision = await llm.complete_json(decision_prompt)
        assert decision["recommended_action"] == case["expected_action"]
        assert 0.0 <= decision["confidence_score"] <= 1.0
        assert len(decision["rationale"]) > 50

        # Step 4: Safety Gate
        safety_prompt = SAFETY_GATE_PROMPT.format(
            recommended_action=decision["recommended_action"],
            confidence_score=decision["confidence_score"],
            rationale=decision["rationale"][:200],
            amount=case["amount"],
            required_approval_level=decision["required_approval_level"],
            num_citations=len(decision["policy_citations"]),
            num_evidence=len(decision["evidence_summary"]["supporting"]),
        )
        safety = await llm.complete_json(safety_prompt)
        assert "safe_to_present" in safety
        assert "requires_human_review" in safety

        # Step 5: Case Writer
        writer_prompt = CASE_WRITER_PROMPT.format(
            case_number=case["case_number"],
            issue_type=triage["issue_type"],
            title=case["title"],
            description=case["description"],
            recommended_action=decision["recommended_action"],
            confidence_score=decision["confidence_score"],
            rationale=decision["rationale"][:200],
            evidence_summary="Mock evidence summary",
        )
        writer = await llm.complete_json(writer_prompt)
        assert "case_summary" in writer
