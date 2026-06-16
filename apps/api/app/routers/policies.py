"""Policy document endpoints."""

import sys
import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.policy import PolicyChunk, PolicyDocument

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parent.parent.parent.parent.parent
        / "packages"
        / "retrieval"
        / "src"
    ),
)
from indexer import index_policy_document  # noqa: E402

logger = structlog.get_logger()
router = APIRouter()


class PolicyDocumentCreate(BaseModel):
    title: str
    category: str
    version: str = "1.0"
    content: str
    metadata: dict | None = None


class PolicyDocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    category: str
    version: str
    content: str
    metadata: dict | None
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


class PolicyChunkResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    section_title: str | None
    metadata: dict | None

    model_config = {"from_attributes": True}


@router.get("")
async def list_policies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PolicyDocument).where(PolicyDocument.is_active).order_by(PolicyDocument.title)
    )
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "title": d.title,
            "category": d.category,
            "version": d.version,
            "is_active": d.is_active,
            "created_at": str(d.created_at),
        }
        for d in docs
    ]


@router.post("", status_code=201)
async def create_policy(policy_in: PolicyDocumentCreate, db: AsyncSession = Depends(get_db)):
    doc = PolicyDocument(
        title=policy_in.title,
        category=policy_in.category,
        version=policy_in.version,
        content=policy_in.content,
        metadata=policy_in.metadata,
    )
    db.add(doc)
    await db.flush()
    await index_policy_document(db, doc.id, api_key=settings.openai_api_key or None)
    logger.info("policy_created", document_id=str(doc.id), title=doc.title)
    return {"id": str(doc.id), "title": doc.title}


@router.get("/{policy_id}")
async def get_policy(policy_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PolicyDocument).where(PolicyDocument.id == policy_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {
        "id": str(doc.id),
        "title": doc.title,
        "category": doc.category,
        "version": doc.version,
        "content": doc.content,
        "metadata": doc.extra_data,
        "is_active": doc.is_active,
    }


@router.put("/{policy_id}")
async def update_policy(
    policy_id: uuid.UUID,
    policy_in: PolicyDocumentCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PolicyDocument).where(PolicyDocument.id == policy_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Policy not found")
    doc.title = policy_in.title
    doc.category = policy_in.category
    doc.version = policy_in.version
    doc.content = policy_in.content
    if policy_in.metadata is not None:
        doc.extra_data = policy_in.metadata
    await db.flush()
    await index_policy_document(db, doc.id, api_key=settings.openai_api_key or None)
    logger.info("policy_updated", document_id=str(doc.id))
    return {"id": str(doc.id), "title": doc.title}


@router.delete("/{policy_id}", status_code=204)
async def deactivate_policy(policy_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PolicyDocument).where(PolicyDocument.id == policy_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Policy not found")
    doc.is_active = False
    await db.flush()
    logger.info("policy_deactivated", document_id=str(doc.id))


@router.get("/{policy_id}/chunks")
async def get_policy_chunks(policy_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PolicyChunk)
        .where(PolicyChunk.document_id == policy_id)
        .order_by(PolicyChunk.chunk_index)
    )
    chunks = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "chunk_index": c.chunk_index,
            "content": c.content,
            "section_title": c.section_title,
        }
        for c in chunks
    ]
