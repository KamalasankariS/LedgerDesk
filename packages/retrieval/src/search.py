"""Semantic search over policy chunks."""

from dataclasses import dataclass

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import PolicyChunk, PolicyDocument
from embeddings import get_embedding, cosine_similarity

logger = structlog.get_logger()


@dataclass
class RetrievalResult:
    chunk_id: str
    document_id: str
    document_title: str
    section_title: str | None
    content: str
    relevance_score: float
    rank: int
    metadata: dict | None = None


MIN_RELEVANCE_SCORE = 0.50


async def search_policies(
    db: AsyncSession,
    query: str,
    top_k: int = 5,
    category_filter: str | None = None,
    api_key: str | None = None,
    min_score: float = MIN_RELEVANCE_SCORE,
) -> list[RetrievalResult]:
    """Search policy chunks by semantic similarity."""
    query_embedding = await get_embedding(query, api_key=api_key, use_local=(not api_key))

    # Try pgvector similarity search first (use savepoint to avoid poisoning session)
    try:
        async with db.begin_nested():
            results = await _pgvector_search(
                db, query_embedding, top_k, category_filter
            )
            if results:
                filtered = [r for r in results if r.relevance_score >= min_score]
                logger.info(
                    "pgvector_search_complete",
                    total=len(results),
                    above_threshold=len(filtered),
                    threshold=min_score,
                )
                return filtered
    except Exception as e:
        logger.warning("pgvector_search_failed_using_fallback", error=str(e))

    # Fallback: load all chunks and compute similarity in Python
    results = await _fallback_search(db, query_embedding, top_k, category_filter)
    filtered = [r for r in results if r.relevance_score >= min_score]
    logger.info(
        "fallback_search_complete",
        total=len(results),
        above_threshold=len(filtered),
        threshold=min_score,
    )
    return filtered


async def _pgvector_search(
    db: AsyncSession,
    query_embedding: list[float],
    top_k: int,
    category_filter: str | None,
) -> list[RetrievalResult]:
    """Use pgvector's cosine distance operator for search."""
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    sql = """
        SELECT pc.id, pc.document_id, pc.content, pc.section_title, pc.metadata,
               pd.title as doc_title, pd.category,
               1 - (pc.embedding <=> CAST(:embedding AS vector)) as similarity
        FROM policy_chunks pc
        JOIN policy_documents pd ON pc.document_id = pd.id
        WHERE pc.embedding IS NOT NULL AND pd.is_active = true
    """

    if category_filter:
        sql += " AND pd.category = :category"

    sql += " ORDER BY pc.embedding <=> CAST(:embedding AS vector) LIMIT :top_k"

    params = {"embedding": embedding_str, "top_k": top_k}
    if category_filter:
        params["category"] = category_filter

    result = await db.execute(text(sql), params)
    rows = result.fetchall()

    results = []
    for rank, row in enumerate(rows):
        results.append(
            RetrievalResult(
                chunk_id=str(row[0]),
                document_id=str(row[1]),
                document_title=row[5],
                section_title=row[3],
                content=row[2],
                relevance_score=float(row[7]) if row[7] else 0.0,
                rank=rank + 1,
                metadata=row[4],
            )
        )

    return results


async def _fallback_search(
    db: AsyncSession,
    query_embedding: list[float],
    top_k: int,
    category_filter: str | None,
) -> list[RetrievalResult]:
    """Fallback search using Python-side cosine similarity."""
    query = (
        select(PolicyChunk, PolicyDocument)
        .join(PolicyDocument, PolicyChunk.document_id == PolicyDocument.id)
        .where(PolicyDocument.is_active)
    )

    if category_filter:
        query = query.where(PolicyDocument.category == category_filter)

    result = await db.execute(query)
    rows = result.all()

    scored = []
    for chunk, doc in rows:
        if chunk.embedding:
            score = cosine_similarity(query_embedding, list(chunk.embedding))
        else:
            # Simple keyword overlap fallback
            # query_words = set(query_embedding[:10]) if isinstance(query_embedding, list) else set()
            score = 0.1  # Base score for keyword matching

        scored.append((chunk, doc, score))

    scored.sort(key=lambda x: x[2], reverse=True)

    results = []
    for rank, (chunk, doc, score) in enumerate(scored[:top_k]):
        results.append(
            RetrievalResult(
                chunk_id=str(chunk.id),
                document_id=str(doc.id),
                document_title=doc.title,
                section_title=chunk.section_title,
                content=chunk.content,
                relevance_score=round(score, 4),
                rank=rank + 1,
                metadata=chunk.extra_data,
            )
        )

    return results


def package_citations(results: list[RetrievalResult]) -> list[dict]:
    """Package retrieval results as structured citations for the LLM and UI."""
    return [
        {
            "citation_id": f"CIT-{r.rank}",
            "document_title": r.document_title,
            "section": r.section_title,
            "content": r.content,
            "relevance_score": r.relevance_score,
            "source_chunk_id": r.chunk_id,
            "source_document_id": r.document_id,
        }
        for r in results
    ]
