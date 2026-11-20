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
HEAD_TABLES = PRE_SESSION_TABLES | SESSION_TABLES | {"progress_steps"}
HEAD = "0045"  # 0045 adds the steps a Student has done (Story 6.1)


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


def rows(url: str, sql: str, params: tuple | None = None) -> list[tuple]:
    with psycopg.connect(libpq_dsn(url)) as conn:
        return conn.execute(sql, params).fetchall()


def columns(url: str, table: str) -> set[str]:
    query = "SELECT column_name FROM information_schema.columns WHERE table_name = %s"
    return {name for (name,) in rows(url, query, (table,))}


def constraints(url: str, table: str) -> dict[str, str]:
    return dict(
        rows(
            url,
            "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conrelid = %s::regclass AND contype IN ('c', 'u')",
            (table,),
        )
    )


def definition(url: str, name: str) -> str:
    query = "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = %s"
    [(found,)] = rows(url, query, (name,))
    return found


def function_names(url: str, *names: str) -> set[str]:
    query = "SELECT proname FROM pg_proc WHERE proname = ANY(%s)"
    return {name for (name,) in rows(url, query, (list(names),))}


def test_head_from_empty_then_every_downgrade_step_to_the_baseline_and_back(migrations_database):
    """One walk instead of a fresh database per revision: from an empty schema to head (every
    module's tables, `alembic check` clean), then down revision by revision to the baseline,
    checking what each downgrade removes, and up to head again. The revisions that move data have
    tests of their own below."""
    url = migrations_database
    reset_schema(url)
    cfg = config(url)
    command.upgrade(cfg, "head")
    assert tables(url) == HEAD_TABLES
    assert current_version(url) == HEAD
    command.check(cfg)  # fails when a module table and the revisions disagree

    # At head. 0034 (Story 5.5): a Class session's Effort level, NULL unless its AI mode is `llm`.
    # 0035 (Story 5.6): a Lab hour ends after it starts and has a place. 0037 (Story 5.8): one
    # current draft per Class session, its revision from 1. 0038 (Story 5.9): a Game's snapshot
    # is all there or all NULL, a Class game has its session and a unique number, and only a
    # `student` occupant has a user id. 0039 (Story 5.10): a free-Seat row has no occupant kind
    # and the reason `moved`. 0040 (Story 5.11): a Class session's `locked_at` and `snapshot` are
    # set together. 0041 (Story 5.14): one reminder per deadline and time. 0042 (Story 5.17): the
    # allocation method is `random` or `student_choice`. 0043 (Story 5.18): a copy names its
    # source, and forgets it when the source goes. 0044 (GitHub issue 109): when the lock was
    # first refused. 0045 (Story 6.1): one row per User, Class session and step.
    assert "effort_level IS NULL" in definition(url, "ck_class_sessions_effort_level_llm_only")
    assert "ends_at > starts_at" in definition(url, "ck_lab_hours_order")
    assert "120" in definition(url, "ck_lab_hours_place")
    assert "lock_refused_at" in columns(url, "class_sessions")
    drafts = constraints(url, "allocation_drafts")
    assert "revision >= 1" in drafts["ck_allocation_drafts_revision"]
    assert "UNIQUE (class_session_id)" in drafts["uq_allocation_drafts_class_session"]
    games = constraints(url, "games")
    assert "num_nulls(settings, demand_series" in games["ck_games_snapshot"]
    assert "UNIQUE (class_session_id, game_number)" in games["uq_games_class_session_number"]
    assert "game_number IS NULL" in games["ck_games_class_session"]
    occupancy = constraints(url, "seat_occupancy")
    assert "user_id IS NULL" in occupancy["ck_seat_occupancy_user_student"]
    assert "'moved'" in occupancy["ck_seat_occupancy_free"]
    sessions = constraints(url, "class_sessions")
    assert "snapshot IS NULL" in sessions["ck_class_sessions_lock"]
    assert "'student_choice'" in sessions["ck_class_sessions_allocation_method"]
    reminders = constraints(url, "deadline_reminders")
    assert "'test_deadline'" in reminders["ck_deadline_reminders_deadline"]
    assert "deadline, deadline_at)" in reminders["uq_deadline_reminders_deadline"]
    assert "ON DELETE SET NULL" in definition(url, "fk_class_sessions_copied_from")
    steps = constraints(url, "progress_steps")
    assert "UNIQUE (user_id, class_session_id, step)" in steps["uq_progress_steps_step"]

    command.downgrade(cfg, "0044")
    assert "progress_steps" not in tables(url)
    command.downgrade(cfg, "0043")
    assert "lock_refused_at" not in columns(url, "class_sessions")
    command.downgrade(cfg, "0042")
    assert {"copied_from", "effort_level_replaced"}.isdisjoint(columns(url, "class_sessions"))
    command.downgrade(cfg, "0041")
    assert "ck_class_sessions_allocation_method" not in constraints(url, "class_sessions")
    command.downgrade(cfg, "0040")
    assert "deadline_reminders" not in tables(url)
    command.downgrade(cfg, "0039")
    assert "ck_class_sessions_lock" not in constraints(url, "class_sessions")
    command.downgrade(cfg, "0038")
    assert "ck_seat_occupancy_free" not in constraints(url, "seat_occupancy")
    assert "'moved'" not in constraints(url, "seat_occupancy")["ck_seat_occupancy_reason"]
    command.downgrade(cfg, "0037")
    assert "ck_games_snapshot" not in constraints(url, "games")
    command.downgrade(cfg, "0036")
    assert "allocation_drafts" not in tables(url)
    command.downgrade(cfg, "0034")
    assert "lab_hours" not in tables(url)
    command.downgrade(cfg, "0033")
    session_columns = columns(url, "class_sessions")
    assert "effort_level" not in session_columns and "start_at" in session_columns
    command.downgrade(cfg, "0031")
    assert tables(url) == PRE_SESSION_TABLES

    command.downgrade(cfg, "0027")
    delivery_columns = {"delivery_state", "bounce_class", "last_event_id"}
    assert not delivery_columns & columns(url, "mail_deliveries")
    roster = PRE_SESSION_TABLES - ROSTER_TABLES
    command.downgrade(cfg, "0023")
    assert tables(url) == roster
    assert current_version(url) == "0023"
    command.downgrade(cfg, "0022")
    assert tables(url) == roster - CLASS_TABLES
    command.downgrade(cfg, "0021")
    assert tables(url) == roster - CLASS_TABLES - ACCESS_REQUEST_TABLES
    command.downgrade(cfg, "0020")
    institutions = roster - CLASS_TABLES - ACCESS_REQUEST_TABLES - INSTITUTION_TABLES
    assert tables(url) == institutions
    assert current_version(url) == "0020"
    command.downgrade(cfg, "0019")
    assert "session_version" not in columns(url, "users")
    command.downgrade(cfg, "0017")
    assert tables(url) == institutions - INVITATION_TABLES
    assert function_names(url, "audit_events_append_only") == set()
    command.downgrade(cfg, "0016")
    assert tables(url) == institutions - INVITATION_TABLES - RESET_TABLES
    assert "stale" not in definition(url, "ck_mail_deliveries_skipped_reason")
    command.downgrade(cfg, "0015")
    mail = institutions - INVITATION_TABLES - RESET_TABLES - MAIL_TABLES
    assert tables(url) == mail
    command.downgrade(cfg, "0014")
    assert tables(url) == mail - IDENTITY_TABLES
    command.downgrade(cfg, "0013")
    assert tables(url) == mail - IDENTITY_TABLES - MEASUREMENT_TABLES
    assert function_names(url, "effort_measurements_append_only") == set()
    command.downgrade(cfg, "0012")
    assert tables(url) == mail - IDENTITY_TABLES - MEASUREMENT_TABLES - {"simulation_batches"}
    batch_columns = rows(
        url,
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE column_name IN ('batch_id', 'effort_level') AND table_name IN "
        "('games', 'seat_weeks')",
    )
    assert batch_columns == []
    assert function_names(url, "simulation_batches_append_only") == set()
    command.downgrade(cfg, "0011")
    near_optimal = rows(
        url,
        "SELECT table_name FROM information_schema.columns WHERE column_name LIKE 'near_optimal_%'",
    )
    near_checks = rows(url, "SELECT conname FROM pg_constraint WHERE conname LIKE '%near_optimal%'")
    trigger_query = "SELECT prosrc FROM pg_proc WHERE proname = 'seat_turns_keep_opening'"
    [(trigger,)] = rows(url, trigger_query)
    assert near_optimal == [] and near_checks == []
    assert "near_optimal" not in trigger and "ai_deadline_at" in trigger  # 0009's function
    command.downgrade(cfg, "0008")
    deadlines = rows(
        url,
        "SELECT table_name FROM information_schema.columns WHERE column_name = 'ai_deadline_at'",
    )
    [(trigger,)] = rows(url, trigger_query)
    assert deadlines == []
    assert "cancelled" not in definition(url, "ck_llm_call_outcome")
    assert "ai_deadline_at" not in trigger
    command.downgrade(cfg, "0007")
    assert tables(url) == AI_HEAD_TABLES
    leftovers = rows(
        url,
        "SELECT proname FROM pg_proc WHERE proname LIKE 'procrastinate%%' UNION ALL "
        "SELECT typname FROM pg_type WHERE typname LIKE 'procrastinate%%'",
    )
    assert leftovers == []
    assert "llm_call_ids" not in columns(url, "seat_weeks")
    assert "provider_error" not in definition(url, "ck_seat_weeks_fallback")
    command.downgrade(cfg, "0004")
    assert tables(url) == GAMES_HEAD_TABLES - {"game_checks"}
    assert current_version(url) == "0004"
    # The way down passes 0006, which drops the AI tables and their trigger function.
    assert function_names(url, "game_checks_append_only", "ai_model_configs_immutable") == set()
    command.downgrade(cfg, "0003")
    assert tables(url) == GAMES_HEAD_TABLES - {"seat_weeks", "game_checks"}
    assert current_version(url) == "0003"
    week_functions = function_names(
        url, "seat_weeks_append_only", "game_weeks_append_only", "seat_turns_keep_opening"
    )
    assert week_functions == {"seat_turns_keep_opening"}
    assert definition(url, "game_weeks_pkey") == "PRIMARY KEY (game_id, week)"
    assert "finished" not in columns(url, "game_weeks")
    command.downgrade(cfg, "0002")
    assert tables(url) == {"alembic_version", "games", "seats", "seat_occupancy"}
    assert current_version(url) == "0002"
    assert function_names(url, "seat_turns_keep_opening") == set()
    command.downgrade(cfg, "0001")
    assert tables(url) == {"alembic_version"}
    assert current_version(url) == "0001"
    assert function_names(url, "seat_occupancy_append_only") == set()

    command.upgrade(cfg, "head")
    assert tables(url) == HEAD_TABLES
    assert current_version(url) == HEAD
    assert delivery_columns <= columns(url, "mail_deliveries")


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


def test_the_check_constraints_list_exactly_the_enum_values(test_database):
    """`alembic check` does not compare CHECK contents, so compare them with the enums here, on
    the session's test database, which is at head."""
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
    from app.modules.progress.models import Step

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
        "ck_progress_steps_step": {step.value for step in Step},
    }
    with psycopg.connect(libpq_dsn(test_database)) as conn:
        rows = dict(
            conn.execute(
                "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = ANY(%s)",
                ([*CHECKS, *ai_checks],),
            ).fetchall()
        )
    assert set(rows) == set(CHECKS) | set(ai_checks)
    # 0033 (Story 5.2): every pair of the four dates that is set keeps their order. Its downgrade
    # runs in `test_head_from_empty_then_every_downgrade_step_to_the_baseline_and_back`.
    with psycopg.connect(libpq_dsn(test_database)) as conn:
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
