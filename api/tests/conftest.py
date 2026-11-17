"""Test setup.

Tests that need Postgres read DATABASE_URL from the environment (the CI
service, or locally the compose `postgres` on localhost). They run against
a dedicated `<db>_test` database, created here if missing, so a test reset
never touches the development database.
"""

import asyncio
import os
import sys
import warnings

import psycopg
import pytest
from sqlalchemy.engine import make_url

from app.platform import db
from app.platform.config import LOCAL_DATABASE_URL, get_settings

if sys.platform == "win32":
    # psycopg's async mode cannot run on the default Proactor loop.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_base_url = make_url(os.environ.get("DATABASE_URL", LOCAL_DATABASE_URL))
TEST_DATABASE_URL = _base_url.set(database=f"{_base_url.database}_test").render_as_string(
    hide_password=False
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("APP_ENV", "test")


def libpq_dsn(url: str) -> str:
    return make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)


def _ensure_test_database() -> None:
    admin = _base_url.set(drivername="postgresql").render_as_string(hide_password=False)
    with psycopg.connect(admin, autocommit=True, connect_timeout=5) as conn:
        name = make_url(TEST_DATABASE_URL).database
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{name}"')


@pytest.fixture(scope="session")
def test_database() -> str:
    _ensure_test_database()
    return TEST_DATABASE_URL


def reset_caches() -> None:
    get_settings.cache_clear()
    db.get_engine.cache_clear()
    db.get_sessionmaker.cache_clear()


@pytest.fixture(autouse=True)
async def _fresh_settings():
    reset_caches()
    yield
    await db.dispose()  # close pooled connections before the engine is dropped
    reset_caches()
