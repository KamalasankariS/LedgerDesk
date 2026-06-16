"""Case and related models."""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuditMixin, Base


class CaseStatus(enum.StrEnum):
    CREATED = "created"
    TRIAGED = "triaged"
    CONTEXT_RETRIEVED = "context_retrieved"
    TOOLS_SELECTED = "tools_selected"
    TOOLS_EXECUTED = "tools_executed"
    RECOMMENDATION_GENERATED = "recommendation_generated"
    SAFETY_CHECKED = "safety_checked"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    FAILED_SAFE = "failed_safe"


class CasePriority(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueType(enum.StrEnum):
    DUPLICATE_CHARGE = "duplicate_charge"
    PENDING_AUTH = "pending_authorization"
    SETTLEMENT_DELAY = "settlement_delay"
    REFUND_MISMATCH = "refund_mismatch"
    REVERSAL_CONFUSION = "reversal_confusion"
    MERCHANT_MISMATCH = "merchant_reference_mismatch"
    TIMELINE_INCONSISTENCY = "timeline_inconsistency"
    POLICY_ELIGIBILITY = "policy_eligibility"
    ACCOUNT_EXCEPTION = "account_servicing_exception"
    UNKNOWN = "unknown"


class Case(AuditMixin, Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, values_callable=lambda e: [x.value for x in e]),
        default=CaseStatus.CREATED,
        nullable=False,
    )
    priority: Mapped[CasePriority] = mapped_column(
        Enum(CasePriority, values_callable=lambda e: [x.value for x in e]),
        default=CasePriority.MEDIUM,
        nullable=False,
    )
    issue_type: Mapped[IssueType | None] = mapped_column(
        Enum(IssueType, values_callable=lambda e: [x.value for x in e]), nullable=True
    )

    # Financial context
    transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    account_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    merchant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    merchant_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Assignment
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Agent metadata
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=True)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Extracted entities
    extracted_entities: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    assignee = relationship("User", back_populates="assigned_cases")
    status_history = relationship(
        "CaseStatusHistory",
        back_populates="case",
        order_by="CaseStatusHistory.created_at",
    )
    entities = relationship("CaseEntity", back_populates="case")
    retrieval_results = relationship("CaseRetrievalResult", back_populates="case")
    tool_invocations = relationship("ToolInvocation", back_populates="case")
    agent_runs = relationship("AgentRun", back_populates="case")
    recommendations = relationship("Recommendation", back_populates="case")
    analyst_actions = relationship("AnalystAction", back_populates="case")
    audit_events = relationship("AuditEvent", back_populates="case")
    notes = relationship("CaseNote", back_populates="case")


class CaseStatusHistory(Base):
    __tablename__ = "case_status_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    case = relationship("Case", back_populates="status_history")


class CaseEntity(Base):
    __tablename__ = "case_entities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_value: Mapped[str] = mapped_column(Text, nullable=False)
    extra_data: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    case = relationship("Case", back_populates="entities")


class CaseNote(AuditMixin, Base):
    __tablename__ = "case_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    note_type: Mapped[str] = mapped_column(
        String(50), default="general"
    )  # general, escalation, resolution, internal

    case = relationship("Case", back_populates="notes")
    author = relationship("User", back_populates="notes")
