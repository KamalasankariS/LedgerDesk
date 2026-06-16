"""Test Pydantic schema validation."""

import uuid
from datetime import datetime
from decimal import Decimal

import pytest
from app.schemas.audit import AnalystActionCreate
from app.schemas.case import CaseCreate, CaseNoteCreate
from app.schemas.recommendation import RecommendationResponse


class TestCaseCreate:
    def test_valid_minimal(self):
        case = CaseCreate(title="Test case", description="Test description")
        assert case.title == "Test case"
        assert case.priority == "medium"
        assert case.currency == "USD"

    def test_valid_full(self):
        case = CaseCreate(
            title="Duplicate charge",
            description="Two charges for same amount",
            priority="high",
            issue_type="duplicate_charge",
            transaction_id="TXN-123",
            account_id="ACCT-456",
            merchant_name="Store",
            amount=Decimal("127.43"),
        )
        assert case.amount == Decimal("127.43")
        assert case.issue_type == "duplicate_charge"

    def test_title_required(self):
        with pytest.raises(Exception):
            CaseCreate(description="No title")


class TestCaseNoteCreate:
    def test_valid(self):
        note = CaseNoteCreate(content="This is a note")
        assert note.note_type == "general"

    def test_custom_type(self):
        note = CaseNoteCreate(content="Escalation note", note_type="escalation")
        assert note.note_type == "escalation"


class TestAnalystActionCreate:
    def test_approve(self):
        action = AnalystActionCreate(action_type="approve")
        assert action.recommendation_id is None

    def test_reject_with_reason(self):
        action = AnalystActionCreate(
            action_type="reject",
            reason="Insufficient evidence",
        )
        assert action.reason == "Insufficient evidence"

    def test_escalate_with_recommendation(self):
        rec_id = uuid.uuid4()
        action = AnalystActionCreate(
            action_type="escalate",
            recommendation_id=rec_id,
            reason="Amount too high",
        )
        assert action.recommendation_id == rec_id


class TestRecommendationResponse:
    def test_valid(self):
        rec = RecommendationResponse(
            id=uuid.uuid4(),
            case_id=uuid.uuid4(),
            recommended_action="initiate_merchant_dispute",
            rationale="Evidence supports duplicate charge",
            confidence_score=0.85,
            policy_citations=[{"doc": "POL-001", "section": "4.1"}],
            evidence_summary={"supporting": ["two charges found"]},
            structured_decision={"action": "dispute"},
            required_approval_level="analyst",
            safety_gate_passed=True,
            safety_gate_details={"flags": []},
            created_at=datetime.now(),
        )
        assert rec.confidence_score == 0.85
        assert rec.safety_gate_passed is True
