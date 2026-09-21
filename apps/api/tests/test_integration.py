"""Integration tests — run against a real PostgreSQL database.

These tests require a running database. In CI they use the postgres service
container. Locally you can run them with `make docker-up` first.

Run with: pytest tests/test_integration.py -v
"""

import uuid

import pytest
from app.core.config import settings
from app.models.base import Base
from app.models.case import Case, CasePriority, CaseStatus, CaseStatusHistory, IssueType
from app.models.user import User
from app.services.case_service import CaseService
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _db_reachable() -> bool:
    """Check if the database is reachable (sync probe)."""
    try:
        import sqlalchemy

        engine = sqlalchemy.create_engine(
            settings.database_url.replace("+asyncpg", ""),
            connect_args={"connect_timeout": 2},
        )
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_reachable(), reason="PostgreSQL not available")

# Use a dedicated test engine so we don't pollute the dev database
TEST_ENGINE = create_async_engine(settings.database_url, echo=False)
TestSession = async_sessionmaker(TEST_ENGINE, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_db():
    """Create all tables before tests, drop after."""
    async with TEST_ENGINE.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db():
    async with TestSession() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def demo_user(db: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="analyst@ledgerdesk.test",
        full_name="Test Analyst",
        role="analyst",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def sample_case(db: AsyncSession) -> Case:
    case = Case(
        id=uuid.uuid4(),
        case_number=f"CSE-TEST-{uuid.uuid4().hex[:5]}",
        title="Integration Test Duplicate Charge",
        description="Cardholder was charged twice for the same grocery purchase at Whole Foods.",
        status=CaseStatus.CREATED,
        priority=CasePriority.MEDIUM,
        issue_type=IssueType.DUPLICATE_CHARGE,
        transaction_id="TXN-INT-001",
        account_id="ACCT-INT-001",
        merchant_name="Whole Foods",
        amount=127.43,
        currency="USD",
        trace_id=str(uuid.uuid4()),
        created_by="test",
    )
    db.add(case)
    history = CaseStatusHistory(
        case_id=case.id,
        from_status=None,
        to_status=CaseStatus.CREATED.value,
        changed_by="test",
    )
    db.add(history)
    await db.flush()
    return case


# ── Database connectivity ────────────────────────────────────────────────────


class TestDatabaseConnectivity:
    async def test_can_connect(self, db: AsyncSession):
        result = await db.execute(text("SELECT 1"))
        assert result.scalar() == 1

    async def test_pgvector_extension_loaded(self, db: AsyncSession):
        result = await db.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
        assert result.scalar() == "vector"


# ── Case CRUD ────────────────────────────────────────────────────────────────


class TestCaseCRUD:
    async def test_create_case(self, db: AsyncSession):
        case = Case(
            case_number="CSE-CRUD-001",
            title="CRUD Test Case",
            description="Testing case creation",
            status=CaseStatus.CREATED,
            priority=CasePriority.HIGH,
            amount=500.00,
            trace_id=str(uuid.uuid4()),
            created_by="test",
        )
        db.add(case)
        await db.flush()

        result = await db.execute(select(Case).where(Case.id == case.id))
        persisted = result.scalar_one()
        assert persisted.case_number == "CSE-CRUD-001"
        assert persisted.status == CaseStatus.CREATED
        assert persisted.priority == CasePriority.HIGH
        assert float(persisted.amount) == 500.00

    async def test_case_number_unique(self, db: AsyncSession):
        case1 = Case(
            case_number="CSE-UNIQ-001",
            title="First",
            description="First case",
            trace_id=str(uuid.uuid4()),
            created_by="test",
        )
        db.add(case1)
        await db.flush()

        case2 = Case(
            case_number="CSE-UNIQ-001",
            title="Duplicate",
            description="Same number",
            trace_id=str(uuid.uuid4()),
            created_by="test",
        )
        db.add(case2)
        with pytest.raises(Exception):
            await db.flush()

    async def test_query_by_status(self, db: AsyncSession, sample_case: Case):
        result = await db.execute(select(Case).where(Case.status == CaseStatus.CREATED))
        cases = result.scalars().all()
        assert any(c.id == sample_case.id for c in cases)

    async def test_query_by_issue_type(self, db: AsyncSession, sample_case: Case):
        result = await db.execute(select(Case).where(Case.issue_type == IssueType.DUPLICATE_CHARGE))
        cases = result.scalars().all()
        assert any(c.id == sample_case.id for c in cases)


# ── Status transitions ───────────────────────────────────────────────────────


class TestStatusTransitionsDB:
    async def test_happy_path_transition(self, db: AsyncSession, sample_case: Case):
        service = CaseService(db)

        await service.transition_status(
            sample_case, CaseStatus.TRIAGED, "system", "Triage complete"
        )
        assert sample_case.status == CaseStatus.TRIAGED

        await service.transition_status(sample_case, CaseStatus.CONTEXT_RETRIEVED, "system")
        assert sample_case.status == CaseStatus.CONTEXT_RETRIEVED

    async def test_status_history_recorded(self, db: AsyncSession, sample_case: Case):
        service = CaseService(db)
        await service.transition_status(sample_case, CaseStatus.TRIAGED, "system")
        await db.flush()

        result = await db.execute(
            select(CaseStatusHistory).where(CaseStatusHistory.case_id == sample_case.id)
        )
        histories = result.scalars().all()
        # Initial creation + triage transition
        assert len(histories) >= 2
        latest = sorted(histories, key=lambda h: h.created_at)[-1]
        assert latest.to_status == CaseStatus.TRIAGED.value

    async def test_invalid_transition_rejected(self, db: AsyncSession, sample_case: Case):
        service = CaseService(db)
        with pytest.raises(ValueError, match="Invalid"):
            await service.transition_status(sample_case, CaseStatus.COMPLETED, "system")

    async def test_full_workflow_transitions(self, db: AsyncSession, sample_case: Case):
        """Walk a case through the entire happy path."""
        service = CaseService(db)
        path = [
            CaseStatus.TRIAGED,
            CaseStatus.CONTEXT_RETRIEVED,
            CaseStatus.TOOLS_SELECTED,
            CaseStatus.TOOLS_EXECUTED,
            CaseStatus.RECOMMENDATION_GENERATED,
            CaseStatus.SAFETY_CHECKED,
            CaseStatus.AWAITING_REVIEW,
        ]
        for target in path:
            await service.transition_status(sample_case, target, "system")
            assert sample_case.status == target

        await db.flush()

        # Verify all transitions were recorded
        result = await db.execute(
            select(CaseStatusHistory).where(CaseStatusHistory.case_id == sample_case.id)
        )
        histories = result.scalars().all()
        # 1 initial creation + 7 transitions
        assert len(histories) >= 8


# ── User model ────────────────────────────────────────────────────────────────


class TestUserModel:
    async def test_create_user(self, db: AsyncSession):
        user = User(
            email="newuser@ledgerdesk.test",
            full_name="New User",
            role="analyst",
        )
        db.add(user)
        await db.flush()

        result = await db.execute(select(User).where(User.id == user.id))
        persisted = result.scalar_one()
        assert persisted.email == "newuser@ledgerdesk.test"
        assert persisted.role == "analyst"
        assert persisted.is_active is True

    async def test_assign_case_to_user(self, db: AsyncSession, demo_user: User, sample_case: Case):
        sample_case.assigned_to = demo_user.id
        await db.flush()

        result = await db.execute(select(Case).where(Case.id == sample_case.id))
        case = result.scalar_one()
        assert case.assigned_to == demo_user.id
