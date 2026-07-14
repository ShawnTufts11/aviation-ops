"""
Pytest configuration — monkeypatches the app's DB URL to a test file.
"""

from __future__ import annotations

import os
import sys
import tempfile
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# BEFORE importing anything from the app, set the DB URL
TEST_DB_PATH = tempfile.mktemp(suffix="_pararig_test.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

from app.core.database import Base, get_db, engine as app_engine
from app.core.security import hash_password
from app.main import create_app
from app.models.organization import Organization
from app.models.user import User
from app.core.permissions import Role

TestSessionLocal = async_sessionmaker(
    bind=app_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(autouse=True)
async def _setup_db():
    """Ensure tables exist before each test, clean data after."""
    async with app_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with app_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f"DELETE FROM {table.name}"))


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean test DB session."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client using the test DB (app engine is already pointed at test file)."""
    app = create_app()
    async def _override() -> AsyncGenerator[AsyncSession, None]:
        yield db
    app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def org(db: AsyncSession) -> Organization:
    """Create a test organization."""
    o = Organization(
        id=str(uuid.uuid4()), name="Test Charter", slug="test-charter",
        timezone="America/Nassau", currency="USD", country="BS",
        regs=[], settings={},
    )
    db.add(o)
    await db.flush()
    return o


@pytest_asyncio.fixture
async def user(db: AsyncSession, org: Organization) -> User:
    """Create a test admin user."""
    u = User(
        id=str(uuid.uuid4()), organization_id=org.id,
        email="admin@test.aero", password_hash=hash_password("testpass123"),
        display_name="Test Admin", role=Role.ADMIN, is_active=True,
    )
    db.add(u)
    await db.flush()
    return u


@pytest_asyncio.fixture
async def token(user: User) -> str:
    """Generate a valid JWT for the test user."""
    from app.core.security import create_access_token
    return create_access_token(
        data={"sub": user.id, "org_id": user.organization_id, "role": user.role.value}
    )
