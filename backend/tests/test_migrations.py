import os
import subprocess
import sys
import uuid
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config

from tests.conftest import libpq_dsn

API_ROOT = Path(__file__).resolve().parents[1]
GAMES_HEAD_TABLES = {
    "alembic_version",
    "games",
    "seats",
    "seat_occupancy",
    "game_weeks",
    "seat_turns",
    "seat_weeks",
    "game_checks",
}
"""The tables at revision 0005, the last games revision."""
AI_HEAD_TABLES = GAMES_HEAD_TABLES | {"ai_model_configs", "ai_budgets", "llm_call"}
"""The tables at revision 0007."""
JOB_TABLES = {
    "procrastinate_jobs",
    "procrastinate_events",
    "procrastinate_periodic_defers",
    "procrastinate_workers",
}
"""procrastinate's tables, from the SQL it ships (revision 0008, Story 2.5)."""
MEASUREMENT_TABLES = {"effort_measurements", "ai_default_pins"}
"""The tables of revision 0014 (Story 2.12)."""
IDENTITY_TABLES = {"users", "user_roles", "rate_limit_counters"}
"""The tables of revision 0015 (Story 3.2)."""
MAIL_TABLES = {"notices", "mail_deliveries"}
"""The tables of revision 0016 (Story 3.5)."""
RESET_TABLES = {"password_resets"}
"""The table of revision 0017 (Story 3.6)."""
INVITATION_TABLES = {"invitations", "audit_events"}
"""The tables of revision 0018 (Story 3.7)."""
INSTITUTION_TABLES = {"institutions"}
"""The table of revision 0021 (Story 3.11)."""
ACCESS_REQUEST_TABLES = {"access_requests"}
"""The table of revision 0022 (Story 3.13)."""
CLASS_TABLES = {"classes", "class_staff"}
"""The tables of revision 0023 (Story 4.1)."""
ROSTER_TABLES = {"roster_uploads", "roster_upload_rows", "roster_entries"}
"""The tables of revisions 0024 (Story 4.2) and 0026 (Story 4.4)."""
SESSION_TABLES = {"class_sessions", "lab_hours", "allocation_drafts", "deadline_reminders"}
"""The tables of `sessions`: revisions 0032 (Story 5.1), 0035 (Story 5.6), 0037 (Story 5.8) and
0041 (Story 5.14)."""
PRE_SESSION_TABLES = (
    AI_HEAD_TABLES
    | JOB_TABLES
    | {"simulation_batches"}
    | MEASUREMENT_TABLES
    | IDENTITY_TABLES
    | MAIL_TABLES
    | RESET_TABLES
    | INVITATION_TABLES
    | INSTITUTION_TABLES
    | ACCESS_REQUEST_TABLES
    | CLASS_TABLES
    | ROSTER_TABLES
)
HEAD_TABLES = PRE_SESSION_TABLES | SESSION_TABLES
HEAD = "0044"  # 0044 adds when the lock of a Class session was refused (GitHub issue 109)


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
    assert current_version(migrations_database) == HEAD


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
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0003_restores_the_week_tables_of_story_1_8(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0003")
    assert tables(migrations_database) == GAMES_HEAD_TABLES - {"seat_weeks", "game_checks"}
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
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0004_removes_the_check_table(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0004")
    assert tables(migrations_database) == GAMES_HEAD_TABLES - {"game_checks"}
    assert current_version(migrations_database) == "0004"
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        # The way down passes 0006, which drops the AI tables and their trigger function.
        functions = conn.execute(
            "SELECT 1 FROM pg_proc WHERE proname IN "
            "('game_checks_append_only', 'ai_model_configs_immutable')"
        ).fetchall()
    assert functions == []
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0007_removes_the_job_schema_and_the_llm_columns(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0007")
    assert tables(migrations_database) == AI_HEAD_TABLES
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        leftovers = conn.execute(
            "SELECT proname FROM pg_proc WHERE proname LIKE 'procrastinate%%' UNION ALL "
            "SELECT typname FROM pg_type WHERE typname LIKE 'procrastinate%%'"
        ).fetchall()
        columns = {
            row[0]
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'seat_weeks'"
            ).fetchall()
        }
        (fallback,) = conn.execute(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'ck_seat_weeks_fallback'"
        ).fetchone()
    assert leftovers == []
    assert "llm_call_ids" not in columns
    assert "provider_error" not in fallback
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0008_removes_the_ai_deadlines(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0008")
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        columns = conn.execute(
            "SELECT table_name FROM information_schema.columns WHERE column_name = 'ai_deadline_at'"
        ).fetchall()
        (outcome,) = conn.execute(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'ck_llm_call_outcome'"
        ).fetchone()
        (trigger,) = conn.execute(
            "SELECT prosrc FROM pg_proc WHERE proname = 'seat_turns_keep_opening'"
        ).fetchone()
    assert columns == []
    assert "cancelled" not in outcome
    assert "ai_deadline_at" not in trigger
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0011_removes_the_near_optimal_reference(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0011")
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        columns = conn.execute(
            "SELECT table_name FROM information_schema.columns "
            "WHERE column_name LIKE 'near_optimal_%'"
        ).fetchall()
        checks = conn.execute(
            "SELECT conname FROM pg_constraint WHERE conname LIKE '%near_optimal%'"
        ).fetchall()
        (trigger,) = conn.execute(
            "SELECT prosrc FROM pg_proc WHERE proname = 'seat_turns_keep_opening'"
        ).fetchone()
    assert columns == [] and checks == []
    assert "near_optimal" not in trigger and "ai_deadline_at" in trigger  # 0009's function
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0012_removes_the_simulation_batches(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0012")
    assert tables(migrations_database) == (
        PRE_SESSION_TABLES
        - {"simulation_batches"}
        - MEASUREMENT_TABLES
        - IDENTITY_TABLES
        - MAIL_TABLES
        - RESET_TABLES
        - INVITATION_TABLES
        - INSTITUTION_TABLES
        - ACCESS_REQUEST_TABLES
        - CLASS_TABLES
        - ROSTER_TABLES
    )
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        columns = conn.execute(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE column_name IN ('batch_id', 'effort_level') AND table_name IN "
            "('games', 'seat_weeks')"
        ).fetchall()
        functions = conn.execute(
            "SELECT 1 FROM pg_proc WHERE proname = 'simulation_batches_append_only'"
        ).fetchall()
    assert columns == [] and functions == []
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0013_removes_the_effort_measurements_and_pins(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0013")
    assert tables(migrations_database) == (
        PRE_SESSION_TABLES
        - MEASUREMENT_TABLES
        - IDENTITY_TABLES
        - MAIL_TABLES
        - RESET_TABLES
        - INVITATION_TABLES
        - INSTITUTION_TABLES
        - ACCESS_REQUEST_TABLES
        - CLASS_TABLES
        - ROSTER_TABLES
    )
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        functions = conn.execute(
            "SELECT 1 FROM pg_proc WHERE proname = 'effort_measurements_append_only'"
        ).fetchall()
    assert functions == []
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0014_removes_the_identity_and_rate_limit_tables(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0014")
    assert tables(migrations_database) == (
        PRE_SESSION_TABLES
        - IDENTITY_TABLES
        - MAIL_TABLES
        - RESET_TABLES
        - INVITATION_TABLES
        - INSTITUTION_TABLES
        - ACCESS_REQUEST_TABLES
        - CLASS_TABLES
        - ROSTER_TABLES
    )
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0015_removes_the_notice_and_delivery_tables(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0015")
    assert tables(migrations_database) == (
        PRE_SESSION_TABLES
        - MAIL_TABLES
        - RESET_TABLES
        - INVITATION_TABLES
        - INSTITUTION_TABLES
        - ACCESS_REQUEST_TABLES
        - CLASS_TABLES
        - ROSTER_TABLES
    )
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0016_removes_the_reset_table_and_the_stale_reason(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0016")
    assert tables(migrations_database) == (
        PRE_SESSION_TABLES
        - RESET_TABLES
        - INVITATION_TABLES
        - INSTITUTION_TABLES
        - ACCESS_REQUEST_TABLES
        - CLASS_TABLES
        - ROSTER_TABLES
    )
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        check = conn.execute(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'ck_mail_deliveries_skipped_reason'"
        ).fetchone()[0]
    assert "stale" not in check
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0017_removes_the_invitation_and_audit_tables(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0017")
    assert (
        tables(migrations_database)
        == PRE_SESSION_TABLES
        - INVITATION_TABLES
        - INSTITUTION_TABLES
        - ACCESS_REQUEST_TABLES
        - CLASS_TABLES
        - ROSTER_TABLES
    )
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        functions = conn.execute(
            "SELECT 1 FROM pg_proc WHERE proname = 'audit_events_append_only'"
        ).fetchall()
    assert functions == []
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0019_removes_the_session_version(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0019")
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        columns = conn.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'users' AND column_name = 'session_version'"
        ).fetchall()
    assert columns == []
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0020_removes_the_institutions(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0020")
    assert (
        tables(migrations_database)
        == PRE_SESSION_TABLES
        - INSTITUTION_TABLES
        - ACCESS_REQUEST_TABLES
        - CLASS_TABLES
        - ROSTER_TABLES
    )
    assert current_version(migrations_database) == "0020"
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0021_removes_the_access_requests(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0021")
    assert (
        tables(migrations_database)
        == PRE_SESSION_TABLES - ACCESS_REQUEST_TABLES - CLASS_TABLES - ROSTER_TABLES
    )
    assert current_version(migrations_database) == "0021"
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0022_removes_the_classes(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0022")
    assert tables(migrations_database) == PRE_SESSION_TABLES - CLASS_TABLES - ROSTER_TABLES
    assert current_version(migrations_database) == "0022"
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0023_removes_the_roster_uploads(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0023")
    assert tables(migrations_database) == PRE_SESSION_TABLES - ROSTER_TABLES
    assert current_version(migrations_database) == "0023"
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0025_removes_the_roster_and_keeps_role_invitations(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    with psycopg.connect(libpq_dsn(migrations_database), autocommit=True) as conn:
        conn.execute(
            "INSERT INTO invitations (id, email, role, token_hash, created_at, expires_at) "
            "VALUES (gen_random_uuid(), 'a@x.no', 'lecturer', 'h', now(), now())"
        )
        # A sent Student Invitation, with its Class and Roster entry (Story 4.4).
        conn.execute(
            "INSERT INTO institutions (id, name, created_at, updated_at) "
            "VALUES ('00000000-0000-0000-0000-000000000001', 'USN', now(), now())"
        )
        conn.execute(
            "INSERT INTO classes (id, name, institution_id, created_at) VALUES "
            "('00000000-0000-0000-0000-000000000002', 'k', "
            "'00000000-0000-0000-0000-000000000001', now())"
        )
        conn.execute(
            "INSERT INTO roster_entries (id, class_id, email, registration, added_at) VALUES "
            "('00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000002', "
            "'s@x.no', 'invited', now())"
        )
        conn.execute(
            "INSERT INTO invitations (id, email, kind, class_id, roster_entry_id, token_hash, "
            "created_at, expires_at) VALUES (gen_random_uuid(), 's@x.no', 'student', "
            "'00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000003', "
            "'h2', now(), now())"
        )
    command.downgrade(cfg, "0025")
    assert tables(migrations_database) == PRE_SESSION_TABLES - {"roster_entries"}
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        assert conn.execute("SELECT email, role FROM invitations").fetchall() == [
            ("a@x.no", "lecturer")
        ]
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0027_removes_the_delivery_event_columns(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0027")

    def columns() -> set[str]:
        with psycopg.connect(libpq_dsn(migrations_database)) as conn:
            return {
                row[0]
                for row in conn.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'mail_deliveries'"
                ).fetchall()
            }

    assert not {"delivery_state", "bounce_class", "last_event_id"} & columns()
    command.upgrade(cfg, "head")
    assert {"delivery_state", "bounce_class", "last_event_id"} <= columns()
    assert current_version(migrations_database) == HEAD


def test_0029_allows_manual_registration_and_its_downgrade_keeps_the_entry(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    with psycopg.connect(libpq_dsn(migrations_database), autocommit=True) as conn:
        conn.execute(
            "INSERT INTO institutions (id, name, created_at, updated_at) VALUES "
            "('00000000-0000-0000-0000-000000000009', 'I', now(), now())"
        )
        conn.execute(
            "INSERT INTO classes (id, name, institution_id, created_at) VALUES "
            "('00000000-0000-0000-0000-000000000002', 'K', "
            "'00000000-0000-0000-0000-000000000009', now())"
        )
        conn.execute(
            "INSERT INTO roster_entries (id, class_id, email, registration, added_at) VALUES "
            "(gen_random_uuid(), '00000000-0000-0000-0000-000000000002', 'm@x.no', "
            "'registered_manually', now())"
        )
    command.downgrade(cfg, "0028")
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        assert conn.execute("SELECT registration FROM roster_entries").fetchall() == [
            ("registered",)
        ]
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_0030_allows_a_user_without_password_and_its_downgrade_locks_it(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    with psycopg.connect(libpq_dsn(migrations_database), autocommit=True) as conn:
        conn.execute(
            "INSERT INTO users (id, email, name, password_hash) VALUES "
            "(gen_random_uuid(), 'm@x.no', 'M', NULL)"
        )
    command.downgrade(cfg, "0029")
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        assert conn.execute("SELECT password_hash FROM users").fetchall() == [("!",)]
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_0031_admits_assistants_and_its_downgrade_removes_them(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    with psycopg.connect(libpq_dsn(migrations_database), autocommit=True) as conn:
        conn.execute(
            "INSERT INTO users (id, email, name, password_hash) VALUES "
            "('00000000-0000-0000-0000-000000000001', 'a@x.no', 'A', NULL)"
        )
        conn.execute(
            "INSERT INTO institutions (id, name, created_at, updated_at) VALUES "
            "('00000000-0000-0000-0000-000000000002', 'I', now(), now())"
        )
        conn.execute(
            "INSERT INTO classes (id, name, institution_id, created_at) VALUES "
            "('00000000-0000-0000-0000-000000000003', 'K', "
            "'00000000-0000-0000-0000-000000000002', now())"
        )
        conn.execute(
            "INSERT INTO class_staff (class_id, user_id, role, added_at) VALUES "
            "('00000000-0000-0000-0000-000000000003', "
            "'00000000-0000-0000-0000-000000000001', 'assistant', now())"
        )
        conn.execute(
            "INSERT INTO invitations (id, email, token_hash, created_at, expires_at, kind, "
            "class_id) VALUES (gen_random_uuid(), 'b@x.no', 'h', now(), now(), 'assistant', "
            "'00000000-0000-0000-0000-000000000003')"
        )
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute(
                "INSERT INTO invitations (id, email, token_hash, created_at, expires_at, kind, "
                "class_id) VALUES (gen_random_uuid(), 'b@x.no', 'h2', now(), now(), "
                "'assistant', '00000000-0000-0000-0000-000000000003')"
            )
    command.downgrade(cfg, "0030")
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        assert conn.execute("SELECT count(*) FROM class_staff").fetchone() == (0,)
        assert conn.execute("SELECT count(*) FROM invitations").fetchone() == (0,)
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0031_removes_the_class_sessions(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0031")
    assert tables(migrations_database) == PRE_SESSION_TABLES
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_0034_keeps_the_effort_level_to_llm_players_and_its_downgrade_drops_it(
    migrations_database,
):
    """0034 (Story 5.5): a Class session's Effort level, NULL unless its AI mode is `llm`."""
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        (check,) = conn.execute(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'ck_class_sessions_effort_level_llm_only'"
        ).fetchone()
    assert "effort_level IS NULL" in check
    command.downgrade(cfg, "0033")
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        columns = {
            name
            for (name,) in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'class_sessions'"
            ).fetchall()
        }
    assert "effort_level" not in columns and "start_at" in columns
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_0035_keeps_a_lab_hour_in_order_and_its_downgrade_drops_the_table(migrations_database):
    """0035 (Story 5.6): a Lab hour ends after it starts and has a place."""
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        checks = dict(
            conn.execute(
                "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conrelid = 'lab_hours'::regclass AND contype = 'c'"
            ).fetchall()
        )
    assert "ends_at > starts_at" in checks["ck_lab_hours_order"]
    assert "120" in checks["ck_lab_hours_place"]
    command.downgrade(cfg, "0034")
    assert "lab_hours" not in tables(migrations_database)
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_0036_backfills_80_keeps_the_share_in_range_and_its_downgrade_drops_it(
    migrations_database,
):
    """0036 (Story 5.7): a whole percent from 1 to 100, 80 for rows stored before, and no
    database default afterwards."""
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "0035")
    session = "00000000-0000-0000-0000-000000000036"
    insert = (
        "INSERT INTO class_sessions (id, class_id, game_settings, ai_mode, debrief_mode, "
        "inactivity_limit_hours, obligatory, created_at{share}) VALUES (%s, "
        "'00000000-0000-0000-0000-000000000002', '{{}}', 'rule_based', 'group', 24, false, "
        "now(){value})"
    )
    with psycopg.connect(libpq_dsn(migrations_database), autocommit=True) as conn:
        conn.execute(
            "INSERT INTO institutions (id, name, created_at, updated_at) VALUES "
            "('00000000-0000-0000-0000-000000000009', 'I', now(), now())"
        )
        conn.execute(
            "INSERT INTO classes (id, name, institution_id, created_at) VALUES "
            "('00000000-0000-0000-0000-000000000002', 'K', "
            "'00000000-0000-0000-0000-000000000009', now())"
        )
        conn.execute(insert.format(share="", value=""), (session,))
    command.upgrade(cfg, "head")
    query = (
        "SELECT column_default FROM information_schema.columns "
        "WHERE table_name = 'class_sessions' AND column_name = 'required_share_percent'"
    )
    with psycopg.connect(libpq_dsn(migrations_database), autocommit=True) as conn:
        assert conn.execute(
            "SELECT required_share_percent FROM class_sessions WHERE id = %s", (session,)
        ).fetchall() == [(80,)]
        assert conn.execute(query).fetchall() == [(None,)]
        for value, allowed in ((0, False), (1, True), (100, True), (101, False)):
            row = str(uuid.uuid4())
            statement = insert.format(share=", required_share_percent", value=f", {value}")
            if allowed:
                conn.execute(statement, (row,))
            else:
                with pytest.raises(psycopg.errors.CheckViolation):
                    conn.execute(statement, (row,))
    command.downgrade(cfg, "0035")
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        assert conn.execute(query).fetchall() == []
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_0037_to_0043_keep_drafts_class_games_free_seats_the_lock_reminders_method_and_copy(
    migrations_database,
):
    """0037 (Story 5.8): one current draft per Class session, its revision from 1. 0038 (Story
    5.9): a Game's snapshot is all there or all NULL, a Class game has its session and a unique
    number, and only a `student` occupant has a user id. 0039 (Story 5.10): a free-Seat row has
    no occupant kind and the reason `moved`. 0040 (Story 5.11): a Class session's `locked_at` and
    `snapshot` are set together. 0041 (Story 5.14): one reminder per deadline and time. 0042
    (Story 5.17): the allocation method is `random` or `student_choice`. 0043 (Story 5.18): a
    copy names its source, and forgets it when the source goes."""
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")

    def constraints(table: str) -> dict[str, str]:
        with psycopg.connect(libpq_dsn(migrations_database)) as conn:
            return dict(
                conn.execute(
                    "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conrelid = %s::regclass AND contype IN ('c', 'u')",
                    (table,),
                ).fetchall()
            )

    def class_session_columns() -> set[str]:
        with psycopg.connect(libpq_dsn(migrations_database)) as conn:
            return {
                name
                for (name,) in conn.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'class_sessions'"
                ).fetchall()
            }

    # 0044 (GitHub issue 109): when the lock was first refused.
    assert "lock_refused_at" in class_session_columns()
    drafts = constraints("allocation_drafts")
    assert "revision >= 1" in drafts["ck_allocation_drafts_revision"]
    assert "UNIQUE (class_session_id)" in drafts["uq_allocation_drafts_class_session"]
    games = constraints("games")
    assert "num_nulls(settings, demand_series" in games["ck_games_snapshot"]
    assert "UNIQUE (class_session_id, game_number)" in games["uq_games_class_session_number"]
    assert "game_number IS NULL" in games["ck_games_class_session"]
    occupancy = constraints("seat_occupancy")
    assert "user_id IS NULL" in occupancy["ck_seat_occupancy_user_student"]
    assert "'moved'" in occupancy["ck_seat_occupancy_free"]
    assert "snapshot IS NULL" in constraints("class_sessions")["ck_class_sessions_lock"]
    reminders = constraints("deadline_reminders")
    assert "'test_deadline'" in reminders["ck_deadline_reminders_deadline"]
    assert "deadline, deadline_at)" in reminders["uq_deadline_reminders_deadline"]
    method = constraints("class_sessions")["ck_class_sessions_allocation_method"]
    assert "'student_choice'" in method
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        (copied,) = conn.execute(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'fk_class_sessions_copied_from'"
        ).fetchone()
    assert "ON DELETE SET NULL" in copied
    command.downgrade(cfg, "0043")
    assert "lock_refused_at" not in class_session_columns()
    command.downgrade(cfg, "0042")
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        columns = {
            name
            for (name,) in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'class_sessions'"
            ).fetchall()
        }
    assert {"copied_from", "effort_level_replaced"}.isdisjoint(columns)
    command.downgrade(cfg, "0041")
    assert "ck_class_sessions_allocation_method" not in constraints("class_sessions")
    command.downgrade(cfg, "0040")
    assert "deadline_reminders" not in tables(migrations_database)
    command.downgrade(cfg, "0039")
    assert "ck_class_sessions_lock" not in constraints("class_sessions")
    command.downgrade(cfg, "0038")
    assert "ck_seat_occupancy_free" not in constraints("seat_occupancy")
    assert "'moved'" not in constraints("seat_occupancy")["ck_seat_occupancy_reason"]
    command.downgrade(cfg, "0037")
    assert "ck_games_snapshot" not in constraints("games")
    command.downgrade(cfg, "0036")
    assert "allocation_drafts" not in tables(migrations_database)
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_the_procrastinate_schema_of_0008_is_the_one_the_installed_version_ships():
    """Revision 0008 keeps procrastinate 3.11.0's `schema.sql`. When procrastinate is upgraded
    this fails: add a revision with the upgrade's migration SQL and the new schema file."""
    from procrastinate.schema import SchemaManager

    kept = API_ROOT / "migrations" / "sql" / "procrastinate-3.11.0-schema.sql"
    assert kept.read_text(encoding="utf-8") == SchemaManager.get_schema()


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
    from typing import get_args

    from app.ai import budget as ai_budget
    from app.ai import models as ai_models
    from app.modules.classes.schemas import StaffRole
    from app.modules.games import schemas
    from app.modules.identity.schemas import (
        AccountRole,
        InvitationKind,
        RosterRegistration,
        RosterSource,
    )
    from app.modules.messaging import models as mail_models

    ai_checks = {
        "ck_ai_budgets_scope_kind": set(get_args(ai_budget.ScopeKind)),
        "ck_llm_call_outcome": set(ai_models.OUTCOMES),
        "ck_llm_call_scope_kind": set(get_args(ai_budget.ScopeKind)),
        "ck_user_roles_role": {role.value for role in AccountRole},
        "ck_invitations_role": {role.value for role in AccountRole},
        "ck_class_staff_role": {role.value for role in StaffRole},
        "ck_roster_uploads_source": {source.value for source in RosterSource},
        "ck_invitations_kind": {kind.value for kind in InvitationKind},
        "ck_roster_entries_registration": {r.value for r in RosterRegistration},
        "ck_mail_deliveries_mode": set(mail_models.MODES),
        "ck_mail_deliveries_skipped_reason": set(mail_models.SKIP_REASONS),
        "ck_mail_deliveries_delivery_state": set(mail_models.DELIVERY_STATES),
        "ck_mail_deliveries_bounce_class": set(mail_models.BOUNCE_CLASSES),
    }
    reset_schema(migrations_database)
    command.upgrade(config(migrations_database), "head")
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        rows = dict(
            conn.execute(
                "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = ANY(%s)",
                ([*CHECKS, *ai_checks],),
            ).fetchall()
        )
    assert set(rows) == set(CHECKS) | set(ai_checks)
    # 0033 (Story 5.2): every pair of the four dates that is set keeps their order. Its downgrade
    # runs in `test_downgrade_to_0031_removes_the_class_sessions`.
    with psycopg.connect(libpq_dsn(migrations_database)) as conn:
        (order,) = conn.execute(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'ck_class_sessions_date_order'"
        ).fetchone()
    for pair in ("start_at < play_deadline", "debrief_deadline < test_deadline"):
        assert pair in order
    for name, enum in CHECKS.items():
        listed = set(re.findall(r"'([a-z_]+)'", rows[name]))
        assert listed == {member.value for member in getattr(schemas, enum)}, name
    for name, values in ai_checks.items():
        assert set(re.findall(r"'([a-z_]+)'", rows[name])) == values, name
