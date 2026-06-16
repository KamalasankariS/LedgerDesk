"""Retrieval and indexing endpoints."""

# Add packages to path
import sys
import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parent.parent.parent.parent.parent
        / "packages"
        / "retrieval"
        / "src"
    ),
)

from indexer import index_all_policies, index_policy_document
from search import package_citations, search_policies

logger = structlog.get_logger()
router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    category: str | None = None


class IndexRequest(BaseModel):
    document_id: uuid.UUID | None = None


@router.post("/search")
async def search(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    """Search policy documents by semantic similarity."""
    results = await search_policies(
        db,
        query=req.query,
        top_k=req.top_k,
        category_filter=req.category,
        api_key=settings.openai_api_key or None,
    )
    citations = package_citations(results)

    return {
        "query": req.query,
        "results": citations,
        "total": len(citations),
    }


@router.post("/index")
async def index_documents(req: IndexRequest, db: AsyncSession = Depends(get_db)):
    """Index policy documents for retrieval."""
    if req.document_id:
        count = await index_policy_document(
            db, req.document_id, api_key=settings.openai_api_key or None
        )
        return {
            "status": "indexed",
            "document_id": str(req.document_id),
            "chunks": count,
        }
    else:
        result = await index_all_policies(db, api_key=settings.openai_api_key or None)
        return {"status": "indexed", **result}
