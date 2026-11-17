"""Async Alembic environment. The URL comes from app settings (DATABASE_URL)."""

import asyncio
import sys

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.platform.config import get_settings
from app.platform.logging import configure_logging

config = context.config

if config.attributes.get("configure_logger", True):
    configure_logging(get_settings().log_level)

# No ORM metadata yet; each story adds its own explicit revision.
target_metadata = None


def database_url() -> str:
    return config.attributes.get("database_url") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(url=database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(database_url(), poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_async(coro) -> None:
    # psycopg's async mode cannot run on Windows' default Proactor loop.
    factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    asyncio.run(coro, loop_factory=factory)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_async(run_migrations_online())
