import os
import subprocess
import sys
from pathlib import Path

import psycopg
from alembic import command
from alembic.config import Config

from tests.conftest import libpq_dsn

API_ROOT = Path(__file__).resolve().parents[1]


def reset_schema(url: str) -> None:
    with psycopg.connect(libpq_dsn(url), autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")


def tables(url: str) -> set[str]:
    with psycopg.connect(libpq_dsn(url)) as conn:
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        ).fetchall()
    return {r[0] for r in rows}


def test_upgrade_head_from_empty_leaves_only_alembic_version(test_database):
    reset_schema(test_database)
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.attributes["database_url"] = test_database
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")
    assert tables(test_database) == {"alembic_version"}
    with psycopg.connect(libpq_dsn(test_database)) as conn:
        (version,) = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    assert version == "0001"


def test_alembic_cli_uses_database_url_from_environment(test_database):
    """The container entrypoint path: plain `alembic upgrade head`, no overrides."""
    reset_schema(test_database)
    env = {**os.environ, "DATABASE_URL": test_database, "APP_ENV": "test"}
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=API_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert tables(test_database) == {"alembic_version"}
