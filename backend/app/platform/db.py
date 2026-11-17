"""The one async SQLAlchemy engine per process."""

from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.platform.config import get_settings


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


async def ping() -> None:
    """Raise if the database cannot be reached."""
    async with get_engine().connect() as conn:
        await conn.execute(text("SELECT 1"))


async def dispose() -> None:
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
