"""Agent run, tool invocation, recommendation, and retrieval models."""

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class AgentRun(TimestampMixin, Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False
    )
    agent_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # triage, retrieval, tool_planner, decision, safety, writer
    status: Mapped[str] = mapped_column(
        String(50), default="running"
    )  # running, completed, failed, timeout
    input_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_usage: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    case = relationship("Case", back_populates="agent_runs")


class ToolInvocation(TimestampMixin, Base):
    __tablename__ = "tool_invocations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False
    )
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id"), nullable=True
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_type: Mapped[str] = mapped_column(String(20), default="read")  # read, write
    input_params: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending, success, error, timeout
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    case = relationship("Case", back_populates="tool_invocations")
    agent_run = relationship("AgentRun")


class CaseRetrievalResult(TimestampMixin, Base):
    __tablename__ = "case_retrieval_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False
    )
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id"), nullable=True
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_chunks.id"), nullable=False
    )
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)

    case = relationship("Case", back_populates="retrieval_results")
    chunk = relationship("PolicyChunk")


class Recommendation(TimestampMixin, Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False
    )
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id"), nullable=True
    )
    recommended_action: Mapped[str] = mapped_column(String(100), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    policy_citations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    evidence_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    structured_decision: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    required_approval_level: Mapped[str] = mapped_column(
        String(50), default="analyst"
    )  # analyst, senior_analyst, supervisor
    safety_gate_passed: Mapped[bool | None] = mapped_column(nullable=True)
    safety_gate_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    case = relationship("Case", back_populates="recommendations")
