"""Seed database with sample data."""

import asyncio
import json
import sys
import uuid
from pathlib import Path

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.auth import hash_password
from app.models import Base
from app.models.user import User
from app.models.case import Case, CaseStatus, CaseStatusHistory
from app.models.policy import PolicyDocument, PolicyChunk

logger = structlog.get_logger()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Make the retrieval package importable from seed context
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "retrieval" / "src"))
from indexer import index_all_policies  # noqa: E402

DATA_DIR = PROJECT_ROOT / "sample_data"


async def seed():
    engine = create_async_engine(settings.database_url)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        # HNSW index for fast approximate nearest-neighbour search on embeddings
        await conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS ix_policy_chunks_embedding_hnsw
            ON policy_chunks
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)
        )

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        # Seed users
        _pw = hash_password("demo123")
        demo_user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            email="admin@ledgerdesk.dev",
            full_name="System Admin",
            role="admin",
            password_hash=_pw,
        )
        analyst = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            email="analyst@ledgerdesk.dev",
            full_name="Jane Analyst",
            role="analyst",
            password_hash=_pw,
        )
        senior = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
            email="senior@ledgerdesk.dev",
            full_name="John Senior",
            role="senior_analyst",
            password_hash=_pw,
        )
        supervisor = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000004"),
            email="supervisor@ledgerdesk.dev",
            full_name="Maria Supervisor",
            role="supervisor",
            password_hash=_pw,
        )
        session.add_all([demo_user, analyst, senior, supervisor])

        # Seed cases
        cases_file = DATA_DIR / "cases" / "seed_cases.json"
        if cases_file.exists():
            cases_data = json.loads(cases_file.read_text())
            for cd in cases_data:
                case_id = uuid.uuid4()
                case = Case(
                    id=case_id,
                    case_number=cd["case_number"],
                    title=cd["title"],
                    description=cd["description"],
                    priority=cd.get("priority", "medium"),
                    issue_type=cd.get("issue_type"),
                    transaction_id=cd.get("transaction_id"),
                    account_id=cd.get("account_id"),
                    merchant_name=cd.get("merchant_name"),
                    merchant_ref=cd.get("merchant_ref"),
                    amount=cd.get("amount"),
                    currency=cd.get("currency", "USD"),
                    trace_id=str(uuid.uuid4()),
                    created_by="seed",
                )
                session.add(case)
                session.add(
                    CaseStatusHistory(
                        id=uuid.uuid4(),
                        case_id=case_id,
                        to_status=CaseStatus.CREATED.value,
                        changed_by="seed",
                    )
                )
            logger.info("cases_seeded", count=len(cases_data))

        # Seed policies
        policies_dir = DATA_DIR / "policies"
        if policies_dir.exists():
            count = 0
            for policy_file in policies_dir.glob("*.md"):
                content = policy_file.read_text()
                lines = content.strip().split("\n")
                title = lines[0].replace("# ", "").replace("Policy: ", "")

                category = "Transaction Exceptions"
                for line in lines:
                    if "Category:" in line:
                        category = line.split("Category:")[-1].strip()
                        break

                doc_id = uuid.uuid4()
                doc = PolicyDocument(
                    id=doc_id,
                    title=title,
                    category=category,
                    content=content,
                )
                session.add(doc)

                # Simple chunking by section
                sections = content.split("\n### ")
                for i, section in enumerate(sections):
                    section_title = section.split("\n")[0].strip().lstrip("# ")
                    chunk = PolicyChunk(
                        id=uuid.uuid4(),
                        document_id=doc_id,
                        chunk_index=i,
                        content=section.strip(),
                        section_title=section_title,
                    )
                    session.add(chunk)
                count += 1
            logger.info("policies_seeded", count=count)

        await session.commit()

        # Generate embeddings for all seeded policy chunks
        logger.info("generating_embeddings")
        api_key = settings.openai_api_key or None
        stats = await index_all_policies(session, api_key=api_key)
        await session.commit()
        logger.info(
            "indexing_complete",
            documents=stats["documents_indexed"],
            chunks=stats["total_chunks"],
        )
        logger.info("seeding_complete")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
