"""Async Alembic environment. The URL comes from app settings (DATABASE_URL)."""

import asyncio
import sys

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

import app.ai.models  # noqa: F401  (registers the model config and budget tables)
import app.modules.games.models  # noqa: F401  (registers the games tables on the metadata)
import app.modules.identity.models  # noqa: F401  (users, user_roles)
import app.modules.messaging.models  # noqa: F401  (mail_deliveries)
import app.platform.audit  # noqa: F401  (audit_events)
import app.platform.notify  # noqa: F401  (notices)
import app.platform.ratelimit  # noqa: F401  (rate_limit_counters)
from app.platform.config import get_settings
from app.platform.db import metadata
from app.platform.logging import configure_logging

config = context.config

if config.attributes.get("configure_logger", True):
    configure_logging(get_settings().log_level)

# Each story still writes its own explicit revision; the metadata lets `alembic check` (and a
# test) prove the revisions and the module tables agree.
target_metadata = metadata


def include_name(name: str | None, type_: str, parent_names: object) -> bool:
    """procrastinate's tables and indexes come from the SQL it ships (revision 0008), not from
    the module tables, so `alembic check` leaves them out."""
    return not (name or "").startswith(("procrastinate_", "idx_procrastinate_"))


def database_url() -> str:
    return config.attributes.get("database_url") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        include_name=include_name,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection, target_metadata=target_metadata, include_name=include_name
    )
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
