"""`python -m app.ops.verify_restore <database_url>` against a copy of the test database (Story
15.11, NFR-4, AD-4): it replays each finished Game at its stored `rules_version`, says whether the
stored Week states verify, changes no data and prints no secret.

The copy is a real one: `CREATE DATABASE … TEMPLATE` of this worker's test database, made after
this process's connections to it are closed, and dropped afterwards. It is never a shared test
database (those are never dropped)."""

import asyncio
import atexit
import threading
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from sqlalchemy.engine import make_url

from app.ops import verify_restore
from app.ops.verify_restore import CANNOT, FAIL, PASS, GameResult, RestoreCheck
from tests import conftest
from tests.conftest import TEST_DATABASE_URL, libpq_dsn
from tests.games.helpers import classic_game

_CHECKSUM_TABLES = ("games", "game_weeks", "seat_weeks", "seat_turns", "game_checks")


def _admin_dsn() -> str:
    return libpq_dsn(make_url(TEST_DATABASE_URL).set(database="postgres").render_as_string(False))


async def _close_connections_to(url: str) -> None:
    """Close every connection this process holds to `url`'s database, so it can be a template."""
    for key, conn in list(conftest._kept.items()):
        if make_url(key).database == make_url(url).database:
            conn.close()
            del conftest._kept[key]
    for engine in conftest._engines.values():
        await engine.dispose()


def _copy_name() -> str:
    return f"verify_restore_copy_{make_url(TEST_DATABASE_URL).database}"


def _drop(name: str) -> None:
    with psycopg.connect(_admin_dsn(), autocommit=True, connect_timeout=5) as admin:
        admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


@pytest.fixture
async def restored(games_db) -> Iterator[tuple[str, str, str]]:
    """`(the copy's URL, a finished Game, a newer finished Game)`: a copy of the test database
    with two finished Classic Games, as a restore into a separate database would give. One copy
    per run: making and dropping a database is the slow part."""
    older = await classic_game(TEST_DATABASE_URL)
    newer = await classic_game(TEST_DATABASE_URL)
    name = _copy_name()
    _drop(name)  # a copy left by an interrupted run
    source = make_url(TEST_DATABASE_URL).database
    await _close_connections_to(TEST_DATABASE_URL)
    with psycopg.connect(_admin_dsn(), autocommit=True, connect_timeout=5) as admin:
        for attempt in range(50):  # a closed connection leaves the server a moment later
            try:
                admin.execute(f'CREATE DATABASE "{name}" TEMPLATE "{source}"')
                break
            except psycopg.errors.ObjectInUse:
                if attempt == 49:
                    raise
                if attempt == 20:
                    # Only this pytest worker uses its test database: a connection still open
                    # after 2 s is one of ours that the closing above missed (an event listener).
                    admin.execute(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname = %s AND pid <> pg_backend_pid()",
                        (source,),
                    )
                await asyncio.sleep(0.1)
    url = make_url(TEST_DATABASE_URL).set(database=name).render_as_string(hide_password=False)
    try:
        yield url, older, newer
    finally:
        # The drop waits for the server's checkpoint, which takes long under a full parallel run;
        # it runs beside the next tests. A copy an interrupted run leaves is dropped next time.
        dropping = threading.Thread(target=_drop, args=(name,), daemon=True)
        dropping.start()
        atexit.register(dropping.join, 120)  # the worker waits for it before it ends


def _checksum(url: str) -> dict[str, str]:
    with psycopg.connect(libpq_dsn(url), autocommit=True) as conn:
        return {
            table: conn.execute(
                f"SELECT count(*) || ':' || coalesce(md5(string_agg(t::text, ',' "
                f"ORDER BY t::text)), '') FROM {table} t"
            ).fetchone()[0]
            for table in _CHECKSUM_TABLES
        }


async def _main(*argv: str) -> tuple[int, list[str]]:
    lines: list[str] = []
    status = await asyncio.to_thread(verify_restore.main, list(argv), out=lines.append)
    return status, lines


async def test_a_restored_copy_verifies_its_finished_games_changes_nothing_and_fails_on_a_tamper(
    restored, monkeypatch
):
    url, older, newer = restored
    before = _checksum(url)
    status, lines = await _main(url)
    assert status == PASS
    assert lines[0].startswith("database revision: 0")
    assert lines[1:] == [
        f"game {older} rules_version 1: verified",
        f"game {newer} rules_version 1: verified",
        "result: pass: 2 of 2 finished Games verify",
    ]
    password = make_url(url).password
    assert not any(password in line or _copy_name() in line for line in lines)  # no secret
    assert _checksum(url) == before  # read only: no check row stored, nothing changed

    replay = verify_restore.games.replay_check

    async def broken_for_older(session, game_id):
        if str(game_id) == older:
            raise KeyError("a row the replay needs is missing")
        return await replay(session, game_id)

    with monkeypatch.context() as patched:  # a Game that cannot be replayed fails alone
        patched.setattr(verify_restore.games, "replay_check", broken_for_older)
        status, lines = await _main(url)
    assert status == FAIL
    assert lines[1:] == [
        f"game {older} rules_version ?: FAILED (KeyError)",
        f"game {newer} rules_version 1: verified",
        "result: FAIL: 1 of 2 finished Games verify",
    ]

    with psycopg.connect(libpq_dsn(url)) as conn:  # one transaction, committed on exit
        conn.execute("SET LOCAL session_replication_role = replica")  # past the append-only rule
        conn.execute(
            "UPDATE game_weeks SET state = jsonb_set(state, '{seats,0,inventory}', "
            "to_jsonb((state #>> '{seats,0,inventory}')::int + 1)) "
            "WHERE game_id = %s AND week = 10 AND NOT finished",
            (newer,),
        )
    status, lines = await _main(url, "--limit", "1")  # the newest finished Game only
    assert status == FAIL
    assert lines[1].startswith(f"game {newer} rules_version 1: FAILED (")
    assert lines[-1] == "result: FAIL: 0 of 1 finished Games verify"
    status, lines = await _main(url, "--game", older, "--game", older)  # named twice: once
    assert (status, lines[1:]) == (
        PASS,
        [f"game {older} rules_version 1: verified", "result: pass: 1 of 1 finished Games verify"],
    )


async def test_nothing_to_check_exits_2_and_names_no_secret(unreachable_database, games_db):
    no_schema = make_url(TEST_DATABASE_URL).set(database="postgres").render_as_string(False)
    unknown_game = str(uuid.uuid7())
    for argv, problem in (
        ([unreachable_database], "cannot read the database ("),
        ([no_schema], "the database has no schema of this app"),
        ([TEST_DATABASE_URL, "--game", unknown_game], f"no finished Game {unknown_game}"),
        ([TEST_DATABASE_URL, "--game", "not-an-id"], "a --game value is not a Game id"),
        ([TEST_DATABASE_URL, "--limit", "0"], "--limit must be at least 1"),
        ([TEST_DATABASE_URL, "--limit", "1", "--game", unknown_game], "not both"),
    ):
        status, lines = await _main(*argv)
        assert status == CANNOT, argv
        assert lines[-1].startswith("result: cannot verify: ") and problem in lines[-1]
        assert not any(make_url(argv[0]).password in line for line in lines)


def test_the_verdict_needs_one_game_and_every_game_to_verify():
    ok = GameResult("g1", 1, ())
    bad = GameResult("g2", 1, ("replay",))
    refused = GameResult("g3", None, (), refused="rules_version_unsupported")
    assert RestoreCheck("r", ()).status == CANNOT
    assert RestoreCheck("r", (ok,)).status == PASS
    assert RestoreCheck("r", (ok, bad)).status == FAIL
    assert RestoreCheck("r", (refused,)).status == FAIL
    lines = verify_restore.report_lines(RestoreCheck("r", (ok, bad, refused)))
    assert lines == [
        "database revision: r",
        "game g1 rules_version 1: verified",
        "game g2 rules_version 1: FAILED (replay)",
        "game g3 rules_version ?: FAILED (rules_version_unsupported)",
        "result: FAIL: 1 of 3 finished Games verify",
    ]
    assert verify_restore.engine_url("postgres://u:p@h/d") == "postgresql+psycopg://u:p@h/d"
