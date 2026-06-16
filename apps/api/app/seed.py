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
from app.models.audit import PromptVersion

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

        # Seed prompt versions (v0.9 inactive, v1.0 active)
        prompt_versions = [
            ("triage", "0.9", False, "Initial triage classifier",
             "You are a triage agent. Classify the case issue type.\n\nCASE: {title}\n{description}\n\nRespond with JSON: {{\"issue_type\": \"...\", \"confidence\": 0.8}}"),
            ("triage", "1.0", True, "Enhanced triage with entity extraction",
             "You are a financial operations triage agent for a transaction exception handling system.\n\nAnalyze the following case and classify it.\n\nCASE DETAILS:\n- Title: {title}\n- Description: {description}\n- Transaction ID: {transaction_id}\n- Account ID: {account_id}\n- Merchant: {merchant_name}\n- Amount: {amount} {currency}\n\nTASK:\n1. Classify the issue type\n2. Extract key entities\n3. Assess initial confidence (0.0-1.0)\n4. Determine priority adjustment if needed\n\nRespond in JSON format with issue_type, confidence, entities, priority_adjustment, and reasoning."),
            ("tool_planner", "0.9", False, "Basic tool selector",
             "Select tools to investigate the case.\n\nCase type: {issue_type}\nDescription: {description}\n\nAvailable tools: get_transaction_timeline, get_account_activity, get_settlement_status, get_refund_status\n\nRespond with JSON: {{\"tools\": [...]}}"),
            ("tool_planner", "1.0", True, "Context-aware tool planner with prioritization",
             "You are a tool planning agent for a financial operations system.\n\nGiven a case and its context, determine which internal tools to call to gather evidence.\n\nCASE:\n- Type: {issue_type}\n- Description: {description}\n- Transaction ID: {transaction_id}\n- Account ID: {account_id}\n- Merchant: {merchant_name}\n- Merchant Ref: {merchant_ref}\n\nRETRIEVAL CONTEXT:\n{retrieval_context}\n\nSelect the tools needed and their parameters. Prioritize tools that will provide the most relevant evidence.\n\nRespond in JSON with tools array (tool_name, params, priority, reason) and reasoning."),
            ("decision", "0.9", False, "Basic recommendation generator",
             "Generate a recommendation for case {case_number}.\n\nType: {issue_type}\nAmount: {amount} {currency}\n\nProvide recommended_action, rationale, and confidence_score as JSON."),
            ("decision", "1.0", True, "Policy-grounded decision agent with structured output",
             "You are a senior financial operations decision agent. Produce a thorough, policy-grounded recommendation.\n\nCASE:\n- Case Number: {case_number}\n- Type: {issue_type}\n- Title: {title}\n- Description: {description}\n- Amount: {amount} {currency}\n\nPOLICY EVIDENCE:\n{policy_citations}\n\nTOOL EVIDENCE:\n{tool_evidence}\n\nRULES:\n1. rationale MUST be 3-5 paragraphs\n2. Cite every policy section referenced\n3. evidence_summary must list ALL supporting facts, concerns, and missing evidence\n4. analyst_summary must be a clear 2-3 sentence briefing\n5. If confidence < 0.70, recommend escalation\n6. Amount sensitivity: >$5,000 senior review, >$25,000 supervisor\n\nRespond with recommended_action, rationale, confidence_score, policy_citations, evidence_summary, structured_decision, required_approval_level, and analyst_summary."),
            ("safety_gate", "0.9", False, "Basic safety check",
             "Check if the recommendation is safe to present.\n\nAction: {recommended_action}\nConfidence: {confidence_score}\n\nRespond with JSON: {{\"safe_to_present\": true, \"requires_human_review\": true}}"),
            ("safety_gate", "1.0", True, "Multi-criteria safety validation",
             "You are a safety validation agent.\n\nRECOMMENDATION:\n- Action: {recommended_action}\n- Confidence: {confidence_score}\n- Rationale: {rationale}\n- Amount: {amount}\n- Required Approval: {required_approval_level}\n\nPOLICY CITATIONS: {num_citations}\nTOOL EVIDENCE ITEMS: {num_evidence}\n\nSAFETY CHECKS:\n1. Confidence threshold: >= 0.70 for analyst, >= 0.85 for auto-eligible\n2. Grounding: At least 1 policy citation must support the action\n3. Proportionality: Action proportional to issue\n4. Amount sensitivity: >$5000 senior, >$25000 supervisor\n5. Missing evidence flagging\n\nRespond with safe_to_present, requires_human_review, approval_level_override, flags, and reasoning."),
            ("case_writer", "0.9", False, "Basic case summary writer",
             "Summarize case {case_number} ({issue_type}).\n\nRecommended action: {recommended_action}\n\nRespond with JSON: {{\"case_summary\": \"...\", \"analyst_notes\": \"...\"}}"),
            ("case_writer", "1.0", True, "Comprehensive case documentation agent",
             "You are a case documentation agent.\n\nCASE:\n- Case Number: {case_number}\n- Type: {issue_type}\n- Title: {title}\n- Description: {description}\n\nRECOMMENDATION:\n- Action: {recommended_action}\n- Confidence: {confidence_score}\n- Rationale: {rationale}\n\nEVIDENCE:\n{evidence_summary}\n\nGenerate:\n1. Concise internal case summary (3-5 sentences)\n2. Structured analyst notes\n3. Closure note template\n\nRespond with case_summary, analyst_notes, and closure_template."),
        ]
        for agent_type, version, is_active, description, template in prompt_versions:
            session.add(
                PromptVersion(
                    id=uuid.uuid4(),
                    agent_type=agent_type,
                    version=version,
                    template=template,
                    description=description,
                    is_active=is_active,
                )
            )
        logger.info("prompt_versions_seeded", count=len(prompt_versions))

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
