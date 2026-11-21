"""AD-2 / AD-8: every command is one locked, version-bumping transaction that emits exactly the
topics the events registry lists for it."""

import ast
import inspect
import uuid
from pathlib import Path

from sqlalchemy import event

from app.engine import GameSettings
from app.modules.games import commands
from app.modules.games.service import OpenGame
from app.platform.db import get_engine, get_sessionmaker
from app.platform.events.registry import COMMAND_TOPICS
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import execute, listening, play_to_end, query, seat_student

SHORT = GameSettings(weeks=8, guided_weeks=2)
FREE = GameSettings(weeks=8, guided_weeks=0)
"""No Guided Weeks: the Students' own Orders complete each Week (Story 6.10)."""


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


async def _started_simulation() -> str:
    """A Student holds every Seat, so the Game waits in Week 1; with no Student ids, its start
    tells no Student (`user:`) and only the commands' own topics remain."""
    game_id = await commands.create("simulation", FREE, seed=1)
    seat_student(TEST_DATABASE_URL, game_id, *(role.value for role in FREE.roles), anonymous=True)
    await commands.start(game_id)
    return game_id


async def _run_start() -> str:
    """A Class game with its snapshot and one Student starts (Story 6.5): its Class session and
    the Student hear of it. The setup emits seven events (create 2, assign 2, snapshot 3)."""
    from tests.games.test_set_snapshot import snapshot

    game_id = await commands.create("class", class_session_id=uuid.uuid7(), game_number=1)
    student = uuid.uuid7()
    await commands.assign_seat(game_id, "retailer", "student", user_id=student)
    await commands.set_snapshot(game_id, snapshot(), keep_students=[student])
    await commands.start(game_id)
    return game_id


async def _run_place_order() -> str:
    """The one Student of a started Class game without Guided Weeks orders in Week 1 (Story
    6.12): the Week completes and advances, so the Class session and the Student hear of it."""
    from tests.games.test_set_snapshot import snapshot

    game_id = await commands.create("class", class_session_id=uuid.uuid7(), game_number=1)
    student = uuid.uuid7()
    await commands.assign_seat(game_id, "retailer", "student", user_id=student)
    from tests.games.test_set_snapshot import SETTINGS

    free = {
        **snapshot(),
        "settings": SETTINGS.model_copy(update={"guided_weeks": 0}).model_dump(mode="json"),
    }
    await commands.set_snapshot(game_id, free, keep_students=[student])
    await commands.start(game_id)
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=student)
    return game_id


async def _run_finish() -> str:
    """`finish` runs inside the `place_order` that completes the last Week."""
    game_id = await _started_simulation()
    await play_to_end(game_id)
    return game_id


async def _run_advance() -> str:
    """The one Student's Order of a started Class game is written in a caller's transaction,
    which advances nothing (the order source's way), so `advance` runs Week 1: its Class session
    and the Student, who waits on Week 2, hear of it."""
    from tests.games.test_set_snapshot import SETTINGS, snapshot

    game_id = await commands.create("class", class_session_id=uuid.uuid7(), game_number=1)
    student = uuid.uuid7()
    await commands.assign_seat(game_id, "retailer", "student", user_id=student)
    free = {
        **snapshot(),
        "settings": SETTINGS.model_copy(update={"guided_weeks": 0}).model_dump(mode="json"),
    }
    await commands.set_snapshot(game_id, free, keep_students=[student])
    await commands.start(game_id)
    async with get_sessionmaker().begin() as session:
        await commands.place_order(
            game_id,
            "retailer",
            1,
            4,
            "student",
            within=OpenGame(session=session, game_id=uuid.UUID(game_id)),
        )
    assert await commands.advance(game_id)
    return game_id


async def _no_settle(game_id: str) -> None:
    return None


async def _run_switch_to_rule_based() -> str:
    game_id = await _started_simulation()
    await commands.switch_to_rule_based(game_id, "retailer", "takeover_staff")
    return game_id


async def _run_view_week() -> str:
    """The one Student of a started Class game opens Guided Week 1 (Story 6.10): the Week
    completes and advances, so the Class session and the Student hear of it."""
    from tests.games.test_set_snapshot import snapshot

    game_id = await commands.create("class", class_session_id=uuid.uuid7(), game_number=1)
    student = uuid.uuid7()
    await commands.assign_seat(game_id, "retailer", "student", user_id=student)
    await commands.set_snapshot(game_id, snapshot(), keep_students=[student])
    await commands.start(game_id)
    assert await commands.view_week(game_id, "retailer", 1, actor=student)
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


TOMORROW = "SELECT now() + interval '1 day'"
"""A time to propose, read from the database clock (Issue #63)."""


async def _two_students() -> tuple[str, uuid.UUID, uuid.UUID]:
    """A Class game with two Students seated, not started: the scheduling aid works from the
    Start date on, whether or not the game has started (Story 6.19)."""
    game_id = await commands.create("class", class_session_id=uuid.uuid7(), game_number=1)
    first, second = uuid.uuid7(), uuid.uuid7()
    for user in (first, second):  # a notice names a User that exists
        execute(
            TEST_DATABASE_URL,
            "INSERT INTO users (id, email, name, password_hash) VALUES (%s, %s, 'S', NULL)",
            (user, f"registry-{user}@x.no"),
        )
    await commands.assign_seat(game_id, "retailer", "student", user_id=first)
    await commands.assign_seat(game_id, "factory", "student", user_id=second)
    return game_id, first, second


async def _run_propose_time() -> str:
    """One Student proposes a time (Story 6.19): the other's notice emits `user`."""
    game_id, first, _ = await _two_students()
    [(at,)] = query(TEST_DATABASE_URL, TOMORROW)
    await commands.propose_time(game_id, at, actor=first, latest=None)
    return game_id


async def _run_accept_time() -> str:
    """The other Student accepts it: every seated Student hears of it."""
    game_id, first, second = await _two_students()
    [(at,)] = query(TEST_DATABASE_URL, TOMORROW)
    proposal_id = await commands.propose_time(game_id, at, actor=first, latest=None)
    assert await commands.accept_time(game_id, proposal_id, actor=second)
    return game_id


async def _run_takeover() -> str:
    """The absent Student's Seat of a started Class game is taken over at its due time (Story
    8.2): its Class session and both Students hear of it (each also through a notice)."""
    from tests.games.test_takeover import class_game, due_of

    game_id, students = await class_game()
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    with_settle = commands._settle
    commands._settle = _no_settle  # only the command's own events: no advance after it
    try:
        due = due_of(game_id, "factory")
        assert due is not None
        await commands.takeover(game_id, "factory", actor="system", now=due)
    finally:
        commands._settle = with_settle
    return game_id


async def _run_request_reclaim() -> str:
    """The Student whose Seat was taken over asks for it back (Story 8.4): its Class session and
    that Student hear of it."""
    from tests.games.test_reclaim import taken_over

    game_id, students = await taken_over()
    await commands.request_reclaim(game_id, "factory", actor=students["factory"])
    return game_id


async def _run_pause() -> str:
    """A Student pauses a started Class game (Story 8.6): its Class session and both Students
    hear of it."""
    from tests.games.test_takeover import class_game

    game_id, students = await class_game()
    await commands.pause(game_id, actor=students["retailer"])
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
    "view_week": _run_view_week,
    "propose_time": _run_propose_time,
    "accept_time": _run_accept_time,
    "takeover": _run_takeover,
    "request_reclaim": _run_request_reclaim,
    "pause": _run_pause,
}
"""How to run each command once; a command added without a runner fails the test below."""

TAKEOVER_SETUP = 17
"""create 2, two Student Seats 2 each, snapshot 4, start 4, the first Order 3."""

RECLAIM_SETUP = -3
"""Counted from the end: `request_reclaim` emits exactly `game`, `session` and the Student's
`user`; its setup's Takeover also settles a Week, whose events vary with the order source."""

CLASS_SETUP_EVENTS = {
    "move_seat": 4,
    "set_snapshot": 4,
    "start": 7,
    "view_week": 10,
    "place_order": 10,
    "advance": 10,
    # create 2 + two Student Seats 2 each; `accept_time` also runs `propose_time` (4: game,
    # session, the proposer, the other Student's notice).
    "propose_time": 6,
    "accept_time": 10,
    "takeover": TAKEOVER_SETUP,
    "request_reclaim": RECLAIM_SETUP,
    # Counted from the end: `pause` emits `game`, `session` and both Students' `user`.
    "pause": -4,
}
"""Runners on a Class game, and how many events their setup emits before the command's own."""


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
            "view_week",
            "propose_time",
            "accept_time",
            "takeover",
            "request_reclaim",
            "pause",
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
        if name in CLASS_SETUP_EVENTS:
            # A Class game (its Class session hears of each command): only this command's events.
            received = received[CLASS_SETUP_EVENTS[name] :]
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
