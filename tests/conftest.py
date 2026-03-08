"""
Shared test fixtures.

Uses an async in-memory SQLite database so tests run without PostgreSQL.
Overrides the FastAPI `get_db` and `get_current_user` dependencies.
Maps PostgreSQL-specific types (JSONB, UUID) to SQLite-compatible equivalents.
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.types import TypeDecorator, CHAR

from app.database import Base, get_db
from app.main import app
from app.models.users import User
from app.utils.auth import get_current_user


# ── Patch JSONB → JSON and PG_UUID → CHAR(32) for SQLite ─────────────────
@event.listens_for(Base.metadata, "column_reflect")
def _remap_pg_types(inspector, table, column_info):
    if isinstance(column_info["type"], JSONB):
        column_info["type"] = JSON()

# Monkey-patch at the DDL level: replace JSONB with JSON in compile
from sqlalchemy.dialects.sqlite import base as sqlite_base
_orig_get_colspec = sqlite_base.SQLiteTypeCompiler

if not hasattr(sqlite_base.SQLiteTypeCompiler, "visit_JSONB"):
    sqlite_base.SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"

if not hasattr(sqlite_base.SQLiteTypeCompiler, "visit_UUID"):
    sqlite_base.SQLiteTypeCompiler.visit_UUID = lambda self, type_, **kw: "CHAR(32)"


# ── Async SQLite engine ──────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)

# Register custom SQLite functions that emulate PostgreSQL
@event.listens_for(engine.sync_engine, "connect")
def _register_sqlite_functions(dbapi_conn, connection_record):
    """Register date_trunc and coalesce for SQLite compatibility."""
    import sqlite3
    def _date_trunc(part, value):
        if value is None:
            return None
        # Simple implementation for day truncation
        return value[:10]  # YYYY-MM-DD
    dbapi_conn.create_function("date_trunc", 2, _date_trunc)

TestSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create all tables before each test and drop them after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    """Yield a fresh async session for direct DB manipulation in tests."""
    async with TestSessionLocal() as session:
        yield session
        await session.commit()


@pytest_asyncio.fixture
async def owner_user(db_session: AsyncSession) -> User:
    """Pre-seed an owner user."""
    user = User(
        id=uuid.uuid4(),
        name="Test Owner",
        email="owner@test.com",
        phone="+910000000000",
        password_hash="$2b$12$dummyhash",
        role="owner",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def client(owner_user: User, db_session: AsyncSession) -> AsyncClient:
    """
    Async HTTP client wired to the FastAPI app with overridden dependencies.
    All requests are authenticated as `owner_user`.
    """

    async def _override_get_db():
        async with TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _override_get_current_user():
        # Re-fetch from DB to work within the request session
        async with TestSessionLocal() as session:
            result = await session.execute(
                __import__("sqlalchemy").select(User).where(User.id == owner_user.id)
            )
            return result.scalar_one()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
