"""Case management endpoints."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.case import Case, CaseStatus, CaseStatusHistory, CaseNote
from app.models.audit import AuditEvent
from app.models.agent import Recommendation
from app.schemas.case import (
    CaseCreate,
    CaseUpdate,
    CaseResponse,
    CaseListResponse,
    CaseNoteCreate,
    CaseNoteResponse,
    StatusHistoryResponse,
)
from app.schemas.audit import AnalystActionCreate
from app.schemas.recommendation import RecommendationResponse
from app.services.case_service import CaseService

from app.core.config import settings

logger = structlog.get_logger()
router = APIRouter()

DEMO_USER_ID = uuid.UUID(settings.demo_user_id)
DEMO_ANALYST_ID = uuid.UUID(settings.demo_analyst_id)


def _generate_case_number() -> str:
    import random

    return f"CSE-2024-{random.randint(10000, 99999):05d}"


@router.get("", response_model=CaseListResponse)
async def list_cases(
    status: str | None = None,
    priority: str | None = None,
    issue_type: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Case)
    count_query = select(func.count(Case.id))

    if status:
        query = query.where(Case.status == status)
        count_query = count_query.where(Case.status == status)
    if priority:
        query = query.where(Case.priority == priority)
        count_query = count_query.where(Case.priority == priority)
    if issue_type:
        query = query.where(Case.issue_type == issue_type)
        count_query = count_query.where(Case.issue_type == issue_type)
    if search:
        search_filter = Case.title.ilike(f"%{search}%") | Case.case_number.ilike(
            f"%{search}%"
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = (await db.execute(count_query)).scalar() or 0
    query = (
        query.order_by(Case.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    cases = result.scalars().all()

    return CaseListResponse(
        cases=[CaseResponse.model_validate(c) for c in cases],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=CaseResponse, status_code=201)
async def create_case(
    case_in: CaseCreate,
    db: AsyncSession = Depends(get_db),
):
    case = Case(
        case_number=_generate_case_number(),
        title=case_in.title,
        description=case_in.description,
        priority=case_in.priority,
        issue_type=case_in.issue_type,
        transaction_id=case_in.transaction_id,
        account_id=case_in.account_id,
        merchant_name=case_in.merchant_name,
        merchant_ref=case_in.merchant_ref,
        amount=case_in.amount,
        currency=case_in.currency,
        trace_id=str(uuid.uuid4()),
        created_by="system",
    )
    db.add(case)

    # Record status history
    history = CaseStatusHistory(
        case_id=case.id,
        from_status=None,
        to_status=CaseStatus.CREATED.value,
        changed_by="system",
    )
    db.add(history)

    # Audit event
    audit = AuditEvent(
        case_id=case.id,
        event_type="case_created",
        actor_type="system",
        action="create",
        resource_type="case",
        resource_id=str(case.id),
        trace_id=case.trace_id,
    )
    db.add(audit)

    await db.flush()
    logger.info("case_created", case_id=str(case.id), case_number=case.case_number)
    return CaseResponse.model_validate(case)


@router.get("/escalated", response_model=CaseListResponse)
async def list_escalated_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Case).where(Case.status == CaseStatus.ESCALATED)
    count_query = select(func.count(Case.id)).where(Case.status == CaseStatus.ESCALATED)
    total = (await db.execute(count_query)).scalar() or 0
    query = (
        query.order_by(Case.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    cases = result.scalars().all()
    return CaseListResponse(
        cases=[CaseResponse.model_validate(c) for c in cases],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(case_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseResponse.model_validate(case)


@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: uuid.UUID,
    case_in: CaseUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    update_data = case_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(case, field, value)

    await db.flush()
    return CaseResponse.model_validate(case)


@router.get("/{case_id}/history", response_model=list[StatusHistoryResponse])
async def get_case_history(case_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CaseStatusHistory)
        .where(CaseStatusHistory.case_id == case_id)
        .order_by(CaseStatusHistory.created_at)
    )
    return [StatusHistoryResponse.model_validate(h) for h in result.scalars().all()]


@router.get("/{case_id}/recommendations", response_model=list[RecommendationResponse])
async def get_case_recommendations(
    case_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Recommendation)
        .where(Recommendation.case_id == case_id)
        .order_by(Recommendation.created_at.desc())
    )
    return [RecommendationResponse.model_validate(r) for r in result.scalars().all()]


@router.post("/{case_id}/notes", response_model=CaseNoteResponse, status_code=201)
async def add_case_note(
    case_id: uuid.UUID,
    note_in: CaseNoteCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    note = CaseNote(
        case_id=case_id,
        author_id=DEMO_ANALYST_ID,
        content=note_in.content,
        note_type=note_in.note_type,
        created_by=str(DEMO_ANALYST_ID),
    )
    db.add(note)
    await db.flush()
    return CaseNoteResponse.model_validate(note)


@router.get("/{case_id}/notes", response_model=list[CaseNoteResponse])
async def get_case_notes(case_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CaseNote)
        .where(CaseNote.case_id == case_id)
        .order_by(CaseNote.created_at.desc())
    )
    return [CaseNoteResponse.model_validate(n) for n in result.scalars().all()]


@router.post("/{case_id}/actions", status_code=201)
async def perform_analyst_action(
    case_id: uuid.UUID,
    action_in: AnalystActionCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    service = CaseService(db)
    return await service.perform_action(case, action_in, DEMO_ANALYST_ID)
