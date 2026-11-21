"""The one async SQLAlchemy engine per process."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.platform.config import get_settings

metadata = MetaData()
"""Every module's Core tables; Alembic compares its revisions against it."""


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=0,
        pool_timeout=5,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


@asynccontextmanager
async def reading(session: AsyncSession | None = None) -> AsyncIterator[AsyncSession]:
    """A read in the caller's `session` when it gives one, else in a session of its own. A request
    holds one pooled connection at a time: the pool has no overflow and a 5-second timeout
    (docs/ops/connection-budget.md), so reads that each held one connection while they waited for
    a second could fill the pool together and all fail at the timeout. A read called from inside
    another read takes the caller's session."""
    if session is not None:
        yield session
        return
    async with get_sessionmaker()() as own:
        yield own


async def ping() -> None:
    """Raise if the database cannot be reached."""
    async with get_engine().connect() as conn:
        await conn.execute(text("SELECT 1"))


async def dispose() -> None:
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
