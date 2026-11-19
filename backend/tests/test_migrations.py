import os
import subprocess
import sys
from pathlib import Path

import psycopg
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
HEAD_TABLES = (
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
HEAD = "0029"  # 0029 lets a Roster entry be registered manually (Story 4.7)


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
        HEAD_TABLES
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
        HEAD_TABLES
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
        HEAD_TABLES
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
        HEAD_TABLES
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
        HEAD_TABLES
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
        == HEAD_TABLES
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
        == HEAD_TABLES - INSTITUTION_TABLES - ACCESS_REQUEST_TABLES - CLASS_TABLES - ROSTER_TABLES
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
        == HEAD_TABLES - ACCESS_REQUEST_TABLES - CLASS_TABLES - ROSTER_TABLES
    )
    assert current_version(migrations_database) == "0021"
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0022_removes_the_classes(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0022")
    assert tables(migrations_database) == HEAD_TABLES - CLASS_TABLES - ROSTER_TABLES
    assert current_version(migrations_database) == "0022"
    command.upgrade(cfg, "head")
    assert current_version(migrations_database) == HEAD


def test_downgrade_to_0023_removes_the_roster_uploads(migrations_database):
    reset_schema(migrations_database)
    cfg = config(migrations_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0023")
    assert tables(migrations_database) == HEAD_TABLES - ROSTER_TABLES
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
    assert tables(migrations_database) == HEAD_TABLES - {"roster_entries"}
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
    for name, enum in CHECKS.items():
        listed = set(re.findall(r"'([a-z_]+)'", rows[name]))
        assert listed == {member.value for member in getattr(schemas, enum)}, name
    for name, values in ai_checks.items():
        assert set(re.findall(r"'([a-z_]+)'", rows[name])) == values, name
