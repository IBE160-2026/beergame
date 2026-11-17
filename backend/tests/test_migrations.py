import os
import subprocess
import sys
from pathlib import Path

import psycopg
from alembic import command
from alembic.config import Config

from tests.conftest import libpq_dsn

API_ROOT = Path(__file__).resolve().parents[1]
HEAD_TABLES = {
    "alembic_version",
    "games",
    "seats",
    "seat_occupancy",
    "game_weeks",
    "seat_turns",
    "seat_weeks",
    "game_checks",
}


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


def config(url: str) -> Config:
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.attributes["database_url"] = url
    cfg.attributes["configure_logger"] = False
    return cfg


def current_version(url: str) -> str:
    with psycopg.connect(libpq_dsn(url)) as conn:
        (version,) = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    return version


def test_upgrade_head_from_empty_creates_the_games_tables(migrations_database):
    reset_schema(migrations_database)
    command.upgrade(config(migrations_database), "head")
    assert tables(migrations_database) == HEAD_TABLES
    assert current_version(migrations_database) == "0005"


def test_the_revisions_match_the_module_tables(migrations_database):
    """`alembic check` fails when a module table and the revisions disagree."""
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.check(cfg)


def test_downgrade_to_the_baseline_removes_the_games_tables(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0001")
    assert tables(migrations_database) == {"alembic_version"}
    assert current_version(migrations_database) == "0001"
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        functions = conn.execute(
            "SELECT 1 FROM pg_proc WHERE proname = 'seat_occupancy_append_only'"
        ).fetchall()
    assert functions == []


def test_downgrade_to_0002_removes_the_week_tables(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0002")
    assert tables(migrations_database) == {"alembic_version", "games", "seats", "seat_occupancy"}
    assert current_version(migrations_database) == "0002"
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        functions = conn.execute(
            "SELECT 1 FROM pg_proc WHERE proname = 'seat_turns_keep_opening'"
        ).fetchall()
    assert functions == []
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == "0005"


def test_downgrade_to_0003_restores_the_week_tables_of_story_1_8(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0003")
    assert tables(migrations_database) == HEAD_TABLES - {"seat_weeks", "game_checks"}
    assert current_version(migrations_database) == "0003"
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        functions = {
            row[0]
            for row in conn.execute(
                "SELECT proname FROM pg_proc WHERE proname IN "
                "('seat_weeks_append_only', 'game_weeks_append_only', 'seat_turns_keep_opening')"
            ).fetchall()
        }
        primary_key = conn.execute(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'game_weeks_pkey'"
        ).fetchone()
        columns = {
            row[0]
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'game_weeks'"
            ).fetchall()
        }
    assert functions == {"seat_turns_keep_opening"}
    assert primary_key == ("PRIMARY KEY (game_id, week)",)
    assert "finished" not in columns
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == "0005"


def test_downgrade_to_0004_removes_the_check_table(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0004")
    assert tables(migrations_database) == HEAD_TABLES - {"game_checks"}
    assert current_version(migrations_database) == "0004"
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        functions = conn.execute(
            "SELECT 1 FROM pg_proc WHERE proname = 'game_checks_append_only'"
        ).fetchall()
    assert functions == []
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == "0005"


def test_alembic_cli_uses_database_url_from_environment(migrations_database):
    """The container entrypoint path: plain `alembic upgrade head`, no overrides."""
    reset_schema(migrations_database)
    env = {**os.environ, "DATABASE_URL": migrations_database, "APP_ENV": "test"}
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
    assert tables(migrations_database) == HEAD_TABLES


CHECKS = {
    "ck_games_purpose": "Purpose",
    "ck_games_lifecycle": "Lifecycle",
    "ck_seat_occupancy_kind": "OccupantKind",
    "ck_seat_occupancy_reason": "OccupancyReason",
    "ck_seat_weeks_decided_by": "DecidedBy",
    "ck_seat_weeks_fallback": "Fallback",
    "ck_seat_weeks_occupant_kind": "OccupantKind",
    "ck_seat_weeks_reason": "OccupancyReason",
}


def test_the_check_constraints_list_exactly_the_enum_values(migrations_database):
    """`alembic check` does not compare CHECK contents, so compare them with the enums here."""
    import re

    from app.modules.games import schemas

    reset_schema(migrations_database)
    command.upgrade(config(migrations_database), "head")
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        rows = dict(
            conn.execute(
                "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = ANY(%s)",
                (list(CHECKS),),
            ).fetchall()
        )
    assert set(rows) == set(CHECKS)
    for name, enum in CHECKS.items():
        listed = set(re.findall(r"'([a-z_]+)'", rows[name]))
        assert listed == {member.value for member in getattr(schemas, enum)}, name
