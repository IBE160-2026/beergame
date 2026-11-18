"""The transaction helper shared by `ai.config` and `ai.budget`."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.db import get_sessionmaker


@asynccontextmanager
async def transaction(session: AsyncSession | None) -> AsyncIterator[AsyncSession]:
    """Join the caller's transaction when it passes one, else run in a new one that commits."""
    if session is not None:
        yield session
        return
    async with get_sessionmaker().begin() as own:
        yield own
