"""Test setup.

Tests that need Postgres read DATABASE_URL from the environment (the CI
service, or locally the compose `postgres` on localhost). They run against
a dedicated `<db>_test` database, created here if missing, so a test reset
never touches the development database. Under pytest-xdist each worker uses
`<db>_test_<worker>` (for example `olspillet_test_gw0`).
"""

import asyncio
import atexit
import os
import socket
import sys
import threading
import warnings
from collections.abc import Iterator
from pathlib import Path

import httpx2
import psycopg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

from app.ai import adapters, ratelimit
from app.platform import db
from app.platform.config import LOCAL_DATABASE_URL, Settings, get_settings

if sys.platform == "win32":
    # psycopg's async mode cannot run on the default Proactor loop.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# The controller process rewrites DATABASE_URL below, and xdist workers inherit that, so the
# original URL is kept in its own variable and every process derives its names from it.
os.environ.setdefault(
    "OLSPILLET_BASE_DATABASE_URL", os.environ.get("DATABASE_URL", LOCAL_DATABASE_URL)
)
_base_url = make_url(os.environ["OLSPILLET_BASE_DATABASE_URL"])
if _base_url.host == "localhost":
    # On Windows `localhost` tries IPv6 first, which makes every new connection (each test
    # opens several) about 15 ms slower than going to the same server by its IPv4 address.
    _base_url = _base_url.set(host="127.0.0.1")
_worker = os.environ.get("PYTEST_XDIST_WORKER")
"""`gw0`, `gw1`, … under pytest-xdist: each worker gets databases of its own."""
_suffix = f"_{_worker}" if _worker else ""
TEST_DATABASE_URL = _base_url.set(database=f"{_base_url.database}_test{_suffix}").render_as_string(
    hide_password=False
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("BCRYPT_ROUNDS", "4")  # bcrypt's minimum cost: hashing stays cheap
# No test sends real mail: without a key every mail goes to the `[email:mock]` sender (Story 3.5).
os.environ.pop("RESEND_API_KEY", None)


def libpq_dsn(url: str) -> str:
    return make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)


_kept: dict[str, psycopg.Connection] = {}


def kept_connection(url: str) -> psycopg.Connection:
    """One autocommit connection per database for the test helpers' own SQL, kept open for the
    process: a new connection to the local Docker database costs about 20 ms, and the helpers
    run thousands of statements. It never holds a transaction open between calls; a helper that
    needs several statements in one uses `conn.transaction()`. No prepared statements, so a
    plan never outlives a schema change."""
    conn = _kept.get(url)
    if conn is None or conn.closed or conn.broken:
        conn = _kept[url] = psycopg.connect(libpq_dsn(url), autocommit=True, prepare_threshold=None)
    return conn


@atexit.register
def _close_kept() -> None:
    for conn in _kept.values():
        conn.close()


MIGRATIONS_DATABASE_URL = (
    make_url(TEST_DATABASE_URL)
    .set(database=f"{_base_url.database}_test_migrations{_suffix}")
    .render_as_string(hide_password=False)
)
"""The migration tests drop and rebuild the schema, so they get a database of their own and the
`<db>_test` schema is migrated once per session."""


def _ensure_database(url: str) -> None:
    # Connect to the server's maintenance database: the test databases may not exist yet.
    admin = _base_url.set(drivername="postgresql", database="postgres").render_as_string(
        hide_password=False
    )
    with psycopg.connect(admin, autocommit=True, connect_timeout=5) as conn:
        name = make_url(url).database
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{name}"')
        # A test database never has to survive a crash: commits return without waiting for the
        # WAL flush, which every Week of a played Game and every fixture reset otherwise does.
        conn.execute(f'ALTER DATABASE "{name}" SET synchronous_commit = off')


def migrate(url: str, revision: str = "head") -> None:
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.attributes["database_url"] = url
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, revision)


@pytest.fixture(scope="session")
def test_database() -> str:
    """The `<db>_test` database at the latest revision, migrated once per session."""
    _ensure_database(TEST_DATABASE_URL)
    migrate(TEST_DATABASE_URL)
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
def migrations_database() -> str:
    """A database only the migration tests use; each of them resets its schema."""
    _ensure_database(MIGRATIONS_DATABASE_URL)
    return MIGRATIONS_DATABASE_URL


GAMES_TABLES = (
    "games, seats, seat_occupancy, game_weeks, seat_turns, seat_weeks, game_checks, "
    "simulation_batches, procrastinate_jobs"
)
"""The games tables and the job queue, whose jobs name Games (Story 2.5)."""


@pytest.fixture
def games_db(test_database) -> str:
    """The test database at the latest revision with empty games tables."""
    kept_connection(test_database).execute(f"TRUNCATE {GAMES_TABLES} CASCADE")
    return test_database


AI_TABLES = "effort_measurements, ai_default_pins, llm_call, ai_budgets, ai_model_configs"


@pytest.fixture
def ai_db(test_database) -> str:
    """The test database at the latest revision with empty model config, budget and `llm_call`
    tables (TRUNCATE fires no row trigger, so referenced configs go too)."""
    kept_connection(test_database).execute(f"TRUNCATE {AI_TABLES}")
    return test_database


IDENTITY_TABLES = (
    "users, user_roles, rate_limit_counters, invitations, audit_events, institutions, "
    "access_requests, classes, class_staff, roster_uploads, roster_upload_rows, roster_entries"
)


@pytest.fixture
def identity_db(test_database) -> str:
    """The test database at the latest revision with no Users and no rate-limit counts."""
    kept_connection(test_database).execute(f"TRUNCATE {IDENTITY_TABLES} CASCADE")
    return test_database


MAIL_TABLES = (
    "notices, mail_deliveries, procrastinate_jobs, users, user_roles, invitations, audit_events"
)


@pytest.fixture
def mail_db(test_database) -> Iterator[str]:
    """The test database with no Users, notices, deliveries or jobs, and an empty mock outbox
    (Story 3.5)."""
    from app.platform.email import senders

    kept_connection(test_database).execute(f"TRUNCATE {MAIL_TABLES} CASCADE")
    senders.MOCK.sent.clear()
    yield test_database
    senders.MOCK.sent.clear()


@pytest.fixture(scope="session")
def unreachable_database() -> Iterator[str]:
    """A database URL whose server hangs up on every connection, so the app cannot reach a
    database. A closed port would do the same on Linux, but Windows retries a refused
    connection until `connect_timeout` (5 s)."""
    server = socket.create_server(("127.0.0.1", 0))

    def hang_up() -> None:
        while True:
            try:
                conn, _ = server.accept()
            except OSError:
                return
            conn.close()

    threading.Thread(target=hang_up, daemon=True).start()
    port = server.getsockname()[1]
    yield f"postgresql+psycopg://nobody:secretpw@127.0.0.1:{port}/none"
    server.close()


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


def enter_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """`APP_ENV=production` from here on, for tests of production behaviour (no AI mock, no dev
    mailbox, the bootstrap Admin, no demo seed). They run on the local test database, which has
    no TLS, so the startup guard is set aside; `test_config.py` and `test_production_startup.py`
    test the guard itself (Story 3.14)."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(Settings, "production_problems", lambda self: [])
    get_settings.cache_clear()


def _refuse(request: httpx2.Request) -> httpx2.Response:
    raise httpx2.ConnectError(f"tests never call a real endpoint ({request.url.host})")


REFUSE = httpx2.MockTransport(_refuse)
"""The adapter transport of every test: a test that wants answers injects its own."""


@pytest.fixture(autouse=True)
def _no_real_endpoint() -> Iterator[None]:
    """No test reaches a real provider (Story 2.7). Each starts with a fresh limiter and a
    skipping clock, so rate-limit waits and 429 back-off never sleep for real."""
    ratelimit.limiter.reset()
    with adapters.use_transport(REFUSE), ratelimit.use_clock(ratelimit.SkippingClock()):
        yield
    ratelimit.limiter.reset()
