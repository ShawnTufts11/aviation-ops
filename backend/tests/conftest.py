"""
Pytest configuration and fixtures for the ParaRig Ops test suite.

Provides:
- async client fixture (httpx.AsyncClient against the FastAPI app)
- test database fixture (SQLite in-memory, isolated per test)
- test user fixture (pre-created user with known credentials)
"""

from __future__ import annotations

import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import create_app
from app.models.organization import Organization
from app.models.user import User
from app.core.permissions import Role

# ── Test database ──────────────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db() -> AsyncGenerator[None, None]:
    """Create tables before each test, drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a fresh test DB session."""
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Yield an HTTP client that uses the test DB session."""

    app = create_app()

    async def _get_db_override() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Test data helpers ──────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def test_org(db_session: AsyncSession) -> Organization:
    """Create and return a test organization."""
    org = Organization(
        id=str(uuid.uuid4()),
        name="Test Charter",
        slug="test-charter",
        timezone="America/Nassau",
        currency="USD",
        country="BS",
        regs=[],
        settings={},
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_org: Organization) -> User:
    """Create and return a test admin user."""
    user = User(
        id=str(uuid.uuid4()),
        organization_id=test_org.id,
        email="admin@testcharter.com",
        password_hash=hash_password("testpass123"),
        display_name="Test Admin",
        phone="+12420000000",
        role=Role.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_user_token(test_user: User) -> str:
    """Generate a valid JWT for the test user."""
    from app.core.security import create_access_token

    return create_access_token(
        data={
            "sub": test_user.id,
            "org_id": test_user.organization_id,
            "role": test_user.role.value,
        }
    )
