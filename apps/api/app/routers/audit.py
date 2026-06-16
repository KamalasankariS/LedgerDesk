"""Audit trail endpoints."""

import uuid

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.agent import ToolInvocation
from app.models.audit import AuditEvent
from app.schemas.audit import (
    AuditEventListResponse,
    AuditEventResponse,
    ToolInvocationResponse,
)

logger = structlog.get_logger()
router = APIRouter()


@router.get("", response_model=AuditEventListResponse)
async def list_audit_events(
    case_id: uuid.UUID | None = None,
    event_type: str | None = None,
    actor_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditEvent)
    count_query = select(func.count(AuditEvent.id))

    if case_id:
        query = query.where(AuditEvent.case_id == case_id)
        count_query = count_query.where(AuditEvent.case_id == case_id)
    if event_type:
        query = query.where(AuditEvent.event_type == event_type)
        count_query = count_query.where(AuditEvent.event_type == event_type)
    if actor_type:
        query = query.where(AuditEvent.actor_type == actor_type)
        count_query = count_query.where(AuditEvent.actor_type == actor_type)

    total = (await db.execute(count_query)).scalar() or 0
    query = (
        query.order_by(AuditEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    result = await db.execute(query)
    events = result.scalars().all()

    return AuditEventListResponse(
        events=[AuditEventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/tools", response_model=list[ToolInvocationResponse])
async def list_tool_invocations(
    case_id: uuid.UUID | None = None,
    tool_name: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(ToolInvocation)
    if case_id:
        query = query.where(ToolInvocation.case_id == case_id)
    if tool_name:
        query = query.where(ToolInvocation.tool_name == tool_name)

    query = query.order_by(ToolInvocation.created_at.desc()).limit(100)
    result = await db.execute(query)
    invocations = result.scalars().all()
    return [ToolInvocationResponse.model_validate(i) for i in invocations]
