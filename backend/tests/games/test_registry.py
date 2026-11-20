"""AD-2 / AD-8: every command is one locked, version-bumping transaction that emits exactly the
topics the events registry lists for it."""

import ast
import inspect
import uuid
from pathlib import Path

from sqlalchemy import event

from app.engine import GameSettings
from app.modules.games import commands
from app.platform.db import get_engine
from app.platform.events.registry import COMMAND_TOPICS
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import listening, play_to_end, seat_student

SHORT = GameSettings(weeks=8, guided_weeks=2)


def public_commands() -> set[str]:
    return {
        name
        for name, value in vars(commands).items()
        if not name.startswith("_")
        and inspect.iscoroutinefunction(value)
        and value.__module__ == commands.__name__
    }


async def _run_create() -> str:
    return await commands.create("simulation", SHORT, seed=1)


async def _run_assign_seat() -> str:
    game_id = await _run_create()
    await commands.assign_seat(game_id, "retailer", "rule_based")
    return game_id


async def _run_start() -> str:
    """A Student holds every Seat, so the Game waits in Week 1."""
    game_id = await _run_create()
    seat_student(TEST_DATABASE_URL, game_id, *(role.value for role in SHORT.roles))
    await commands.start(game_id)
    return game_id


async def _run_place_order() -> str:
    game_id = await _run_start()
    await commands.place_order(game_id, "retailer", 1, 4, "guided")
    return game_id


async def _run_finish() -> str:
    """`finish` runs inside the `place_order` that completes the last Week."""
    game_id = await _run_start()
    await play_to_end(game_id)
    return game_id


async def _run_advance() -> str:
    """`start` leaves Week 1 complete but open when its own advances are held back."""
    game_id = await _run_create()
    settle = commands._settle
    commands._settle = _no_settle
    try:
        await commands.start(game_id)
    finally:
        commands._settle = settle
    assert await commands.advance(game_id)
    return game_id


async def _no_settle(game_id: str) -> None:
    return None


async def _run_switch_to_rule_based() -> str:
    game_id = await _run_start()
    await commands.switch_to_rule_based(game_id, "retailer", "takeover_staff")
    return game_id


async def _run_move_seat() -> str:
    """A Student of a Class game moves to its free Factory Seat (Story 5.10)."""
    game_id = await commands.create("class", class_session_id=uuid.uuid7(), game_number=1)
    await commands.assign_seat(game_id, "retailer", "student", user_id=uuid.uuid7())
    await commands.move_seat(game_id, "retailer", game_id, "factory")
    return game_id


async def _run_set_snapshot() -> str:
    """A Class game takes a snapshot; its three free Seats get Rule-based players (Story 5.12)."""
    from tests.games.test_set_snapshot import snapshot

    game_id = await commands.create("class", class_session_id=uuid.uuid7(), game_number=1)
    await commands.assign_seat(game_id, "retailer", "student", user_id=uuid.uuid7())
    await commands.set_snapshot(game_id, snapshot(), keep_students=[])
    return game_id


RUNNERS = {
    "create": _run_create,
    "assign_seat": _run_assign_seat,
    "start": _run_start,
    "place_order": _run_place_order,
    "finish": _run_finish,
    "advance": _run_advance,
    "switch_to_rule_based": _run_switch_to_rule_based,
    "move_seat": _run_move_seat,
    "set_snapshot": _run_set_snapshot,
}
"""How to run each command once; a command added without a runner fails the test below."""


def test_every_command_is_exported_and_registered():
    found = public_commands()
    assert (
        found
        == {
            "create",
            "assign_seat",
            "start",
            "place_order",
            "finish",
            "advance",
            "switch_to_rule_based",
            "move_seat",
            "set_snapshot",
        }
        == set(RUNNERS)
    )
    assert found <= set(commands.__all__)
    games_entries = {
        key.removeprefix("games.") for key in COMMAND_TOPICS if key.startswith("games.")
    }
    assert games_entries == found


async def test_each_command_emits_exactly_its_registered_topics(games_db):
    for name, runner in RUNNERS.items():
        with listening(games_db) as events:
            game_id = await runner()
            received = events.drain()
        if name in ("move_seat", "set_snapshot"):
            # A Class game (its Class session hears of each command): only this command's events.
            received = received[4:]
            assert {item["topic"] for item in received} == COMMAND_TOPICS[f"games.{name}"]
            assert {item["id"] for item in received if item["topic"] == "game"} == {game_id}
            continue
        if name != "create":
            received = received[1:]  # the first event is the setup's create
        assert {item["topic"] for item in received} == COMMAND_TOPICS[f"games.{name}"]
        assert all(item["id"] == game_id for item in received)
        assert "session" not in {item["topic"] for item in received}  # simulation Games


async def test_each_command_locks_bumps_and_notifies_in_one_transaction(games_db):
    await _run_create()  # warm the pool so connection setup is not recorded
    statements: list[str] = []
    commits: list[bool] = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(" ".join(statement.split()))

    def commit(conn):
        commits.append(True)

    sync_engine = get_engine().sync_engine
    event.listen(sync_engine, "before_cursor_execute", record)
    event.listen(sync_engine, "commit", commit)
    try:
        game_id = await _run_create()
        assert len(commits) == 1
        assert_locked_bump_notify(statements)
        statements.clear()
        commits.clear()
        await commands.assign_seat(game_id, "retailer", "rule_based")
        assert len(commits) == 1
        assert_locked_bump_notify(statements)
        statements.clear()
        commits.clear()
        seat_student(TEST_DATABASE_URL, game_id, "wholesaler")  # the Game waits in Week 1
        await commands.start(game_id)
        assert len(commits) == 1
        assert_locked_bump_notify(statements)
        writes = [s for s in statements if s.startswith("INSERT INTO")]
        assert any("seat_occupancy" in s for s in writes)  # three free Seats filled
        assert any("game_weeks" in s for s in writes) and any("seat_turns" in s for s in writes)
        statements.clear()
        commits.clear()
        settle = commands._settle
        commands._settle = _no_settle  # the switch completes Week 1; count only its own commit
        try:
            await commands.switch_to_rule_based(game_id, "wholesaler", "takeover_staff")
            assert len(commits) == 1
            assert_locked_bump_notify(statements)
            game_id = await _run_create()
            await commands.start(game_id)
        finally:
            commands._settle = settle
        statements.clear()
        commits.clear()
        assert await commands._advance_once(game_id)
        assert len(commits) == 1
        assert_locked_bump_notify(statements)
    finally:
        event.remove(sync_engine, "before_cursor_execute", record)
        event.remove(sync_engine, "commit", commit)


def assert_locked_bump_notify(statements: list[str]) -> None:
    lock = next(i for i, s in enumerate(statements) if s.endswith("FOR UPDATE"))
    bump = next(i for i, s in enumerate(statements) if s.startswith("UPDATE games SET version"))
    notify = next(i for i, s in enumerate(statements) if "pg_notify" in s)
    assert lock < bump < notify


def test_commands_never_branch_on_purpose():
    """AD-13: purposes are compared only inside `games.policy`."""
    source = Path(commands.__file__).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Compare):
            text = ast.unparse(node)
            assert "purpose" not in text.lower(), text
        if isinstance(node, ast.Constant):
            assert node.value not in {"class", "replay", "makeup", "lecturer_test"}
    assert '"simulation"' not in source
