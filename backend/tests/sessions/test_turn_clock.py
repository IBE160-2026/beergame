"""Story 8.1: the game's own clock (FR-35, FR-36, FR-24, AD-13, AD-15, AD-20).

Every opened Week has one `seat_turns` row per Seat with `opened_at`; the first Student who orders
(or opens a Guided Week) starts the wait for the Seats that have not, and `games.commands` stores
the Student-held ones' `takeover_due_at` and `insert_allowed_at` from the Inactivity limit the
Class session froze, in the same transaction. A placed Order copies the turn's times into its
write-once Decision log row. The play envelope and the Oversikt point `next_change_at` at the
nearest stored due time. Only `games.commands` (through `games.repo`) writes these columns."""

import importlib.util
import re
from datetime import datetime, timedelta
from pathlib import Path

from app.engine import GameSettings
from app.modules.games import commands
from tests.classes.test_classes import LECTURER
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import call
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import query, seat_student, view
from tests.sessions.test_guided_weeks import view as view_as
from tests.sessions.test_orders import free_week, order
from tests.sessions.test_play import play, running
from tests.sessions.test_student_home import _empty, clock, klass

__all__ = ["_empty", "clock", "klass"]

CLASSIC = GameSettings()


def turns(game_id: str, week: int) -> dict[str, tuple]:
    """(opened_at, ordered_at, wait_started_at, takeover_due_at, insert_allowed_at) by Role."""
    found = query(
        TEST_DATABASE_URL,
        "SELECT s.role, t.opened_at, t.ordered_at, t.wait_started_at, t.takeover_due_at, "
        "t.insert_allowed_at FROM seat_turns t JOIN seats s ON s.id = t.seat_id "
        "WHERE t.game_id = %s AND t.week = %s",
        (game_id, week),
    )
    return {role: tuple(rest) for role, *rest in found}


def limit(game_id: str) -> timedelta:
    """The Inactivity limit the Class session's lock froze into the Game (Story 5.11)."""
    [(hours,)] = query(
        TEST_DATABASE_URL,
        "SELECT (session_runtime->>'inactivity_limit_hours')::int FROM games WHERE id = %s",
        (game_id,),
    )
    return timedelta(hours=hours)


def logged(game_id: str, week: int, role: str) -> tuple:
    [found] = query(
        TEST_DATABASE_URL,
        "SELECT w.opened_at, w.ordered_at, w.wait_started_at, w.takeover_due_at, "
        "w.insert_allowed_at FROM seat_weeks w JOIN seats s ON s.id = w.seat_id "
        "WHERE w.game_id = %s AND w.week = %s AND s.role = %s",
        (game_id, week, role),
    )
    return tuple(found)


async def test_the_first_order_sets_the_due_times_of_the_students_who_have_not(klass):
    game_id, by_role = await free_week(klass, students=3)
    week = CLASSIC.guided_weeks + 1
    first, second, third = by_role
    [ai] = {"factory", "distributor", "wholesaler", "retailer"} - set(by_role)
    hours = limit(game_id)
    assert hours == timedelta(hours=24)  # the Class session's default
    # The Week has opened: one turn per Seat with `opened_at`, and no clock yet.
    opened = turns(game_id, week)
    assert set(opened) == {first, second, third, ai}
    assert all(row[0] is not None for row in opened.values())
    assert {row[2:] for role, row in opened.items() if role != ai} == {(None, None, None)}
    assert (await play(by_role[second], game_id)).json()["next_change_at"] is None

    assert (await order(by_role[first], game_id, week, {"order": 9})).status_code == 204
    stored = turns(game_id, week)
    started = stored[first][1]  # the first Order's transaction time
    assert stored[first][2:] == (None, None, None)
    for role in (second, third):
        assert stored[role][2:] == (started, started + hours, started + hours)
    assert stored[ai][3:] == (None, None)  # an AI player has no Inactivity clock
    # The play envelope is read again at the nearest stored due time.
    body = (await play(by_role[second], game_id)).json()
    assert datetime.fromisoformat(body["next_change_at"]) == started + hours

    # The second Order copies its turn's times into its write-once Decision log row.
    assert (await order(by_role[second], game_id, week, {"order": 5})).status_code == 204
    second_turn = turns(game_id, week)[second]
    assert logged(game_id, week, second) == (second_turn[0], second_turn[1], *second_turn[2:])
    assert logged(game_id, week, first)[2:] == (None, None, None)
    # The third Student is still waited for, from the first Order's moment.
    assert turns(game_id, week)[third][2:] == (started, started + hours, started + hours)


async def test_in_a_guided_week_the_first_view_sets_the_due_time_of_the_absent_student(klass):
    _, game_id, by_role = await running(klass, students=2)
    first, absent = by_role
    assert {row[3] for row in turns(game_id, 1).values()} == {None}
    assert (await view_as(by_role[first], game_id, 1)).status_code == 204
    [(viewed,)] = query(
        TEST_DATABASE_URL,
        "SELECT t.viewed_at FROM seat_turns t JOIN seats s ON s.id = t.seat_id "
        "WHERE t.game_id = %s AND t.week = 1 AND s.role = %s",
        (game_id, first),
    )
    hours = limit(game_id)
    assert turns(game_id, 1)[absent][2:] == (viewed, viewed + hours, viewed + hours)
    assert turns(game_id, 1)[first][3:] == (None, None)


async def test_the_overview_reads_again_at_the_nearest_takeover_due_time(klass):
    session_id, game_id, by_role = await running(klass, students=2)
    first, absent = by_role
    body = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}/overview")).json()
    assert body["next_change_at"] is None
    assert (await view_as(by_role[first], game_id, 1)).status_code == 204
    due = turns(game_id, 1)[absent][3]
    body = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}/overview")).json()
    assert datetime.fromisoformat(body["next_change_at"]) == due
    [(stored,)] = query(
        TEST_DATABASE_URL,
        "SELECT takeover_due_at FROM game_summaries WHERE game_id = %s",
        (game_id,),
    )
    assert stored == due
    # A due time already passed is no time to read again at (8.2's sweep acts on it).
    execute(
        "UPDATE game_summaries SET takeover_due_at = now() - interval '1 minute' "
        "WHERE game_id = %s",
        game_id,
    )
    body = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}/overview")).json()
    assert body["next_change_at"] is None
    # Revision 0053 gives a wait that started before it the same due times, and its summary the
    # same nearest one.
    execute(
        "UPDATE seat_turns SET takeover_due_at = NULL, insert_allowed_at = NULL WHERE game_id = %s",
        game_id,
    )
    execute("UPDATE game_summaries SET takeover_due_at = NULL WHERE game_id = %s", game_id)
    for statement in _backfill().split(";"):
        if statement.strip():
            execute(statement)
    assert turns(game_id, 1)[absent][3:] == (due, due)
    assert turns(game_id, 1)[first][3:] == (None, None)
    assert query(
        TEST_DATABASE_URL,
        "SELECT takeover_due_at FROM game_summaries WHERE game_id = %s",
        (game_id,),
    ) == [(due,)]
    # The Week completes: nothing is waited for, so nothing is due.
    assert (await view_as(by_role[absent], game_id, 1)).status_code == 204
    body = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}/overview")).json()
    assert body["next_change_at"] is None


def _backfill() -> str:
    path = Path(__file__).parents[2] / "migrations" / "versions" / "0053_seat_turns_due_times.py"
    spec = importlib.util.spec_from_file_location("revision_0053", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BACKFILL


def test_only_a_game_whose_policy_has_inactivity_takeover_gets_a_limit():
    """AD-13: the policy decides, also for a Game that froze a limit."""
    base = commands.default_runtime(model_config_id=None, effort_level=None)
    runtime = base.model_copy(update={"inactivity_limit_hours": 30}).model_dump(mode="json")
    limit_of = commands._inactivity_limit
    assert limit_of({"purpose": "class", "session_runtime": runtime}) == timedelta(hours=30)
    for purpose in ("lecturer_test", "simulation"):
        assert limit_of({"purpose": purpose, "session_runtime": runtime}) is None
    assert limit_of({"purpose": "class", "session_runtime": None}) is None
    assert limit_of({"purpose": "class", "session_runtime": base.model_dump(mode="json")}) is None


async def test_a_game_without_inactivity_takeover_records_the_times_and_sets_no_due_time(
    identity_db,
):
    """A simulation Game (`games.policy`: no inactivity Takeover, AD-13) with two Student Seats."""
    game_id = await commands.create("simulation", CLASSIC, seed=11)
    seat_student(TEST_DATABASE_URL, game_id, "retailer", "factory")
    await commands.start(game_id)
    assert await view(game_id, "retailer", 1)
    stored = turns(game_id, 1)
    assert all(row[0] is not None and row[1] is not None for row in stored.values())
    assert stored["factory"][2] is not None  # the wait is still told (Story 6.14)
    assert {row[3:] for row in stored.values()} == {(None, None)}


def test_only_games_commands_writes_the_turn_times():
    """AD-20: `seat_turns` is written only in `games/repo.py`, and its time writers are called
    only from `games/commands.py`."""
    app = Path(__file__).resolve().parents[2] / "app"
    writes = re.compile(r"(update|insert)\(\s*seat_turns\b|seat_turns\.(update|insert)\(")
    writers = re.compile(r"\b(set_wait_times|set_viewed_at|set_ordered_at|insert_turns)\(")
    for path in app.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(app).as_posix()
        if writes.search(text):
            assert relative == "modules/games/repo.py", relative
        if writers.search(text) and relative != "modules/games/repo.py":
            assert relative == "modules/games/commands.py", relative
    for column in ("takeover_due_at", "insert_allowed_at"):
        setters = [
            path.relative_to(app).as_posix()
            for path in app.rglob("*.py")
            if re.search(rf"\b{column}\s*=(?!=)", path.read_text(encoding="utf-8"))
        ]
        # Keyword arguments naming the column: the repo writer, its one caller, the pure rule
        # and the read models that copy the stored value.
        assert set(setters) <= {
            "modules/games/repo.py",
            "modules/games/commands.py",
            "modules/games/rules.py",
            "modules/games/service.py",
            # The overview's band copies the stored value (Story 8.3).
            "modules/sessions/overview.py",
        }, setters
