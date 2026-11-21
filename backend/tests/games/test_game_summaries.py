"""`game_summaries` (Story 7.1, AD-25, AD-2): every `games.commands` command rewrites the Game's
row in its own transaction, so the stored row always equals a fresh recomputation from the game
tables; and the status comes from `games.rules.game_status` only. Revision 0051's backfill gives
the rows `recompute` gives."""

import importlib.util
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from app.engine import GameSettings
from app.modules.games import commands, overview, repo, rules
from app.modules.games.schemas import GameStatus
from app.platform.db import get_sessionmaker
from tests.games.helpers import execute, query, seat_student
from tests.games.test_class_games import SESSION, class_game
from tests.games.test_set_snapshot import snapshot

A = uuid.UUID("01900000-0000-7000-8000-0000000000a1")
B = uuid.UUID("01900000-0000-7000-8000-0000000000b2")
NOT_STORED = {"updated_at"}


async def stored_and_fresh(game_id: str) -> tuple[dict, dict]:
    """The stored row and a recomputation from the game tables, in one fresh read."""
    async with get_sessionmaker()() as session:
        game = await repo.get_game(session, uuid.UUID(game_id))
        assert game is not None
        row = await repo.summary(session, game["id"])
        fresh = await overview.recompute(session, game)
    assert row is not None, "every Game has its row"
    return {k: v for k, v in row.items() if k not in NOT_STORED}, fresh


async def check(*game_ids: str) -> dict:
    """Assert each Game's stored row equals its recomputation; returns the first one's row."""
    rows = []
    for game_id in game_ids:
        stored, fresh = await stored_and_fresh(game_id)
        assert stored == fresh, game_id
        rows.append(stored)
    return rows[0]


async def view(game_id: str, role: str, week: int, student: uuid.UUID) -> None:
    await commands.view_week(game_id, role, week, actor=student)


async def test_every_command_leaves_the_row_equal_to_a_recomputation(games_db):
    first, second = await class_game(1), await class_game(2)
    row = await check(first, second)  # create
    assert (row["status"], row["week"], row["chain_cost"], row["waiting_for"]) == (
        "not_started",
        None,
        None,
        [],
    )
    assert (row["class_session_id"], row["game_number"], row["purpose"]) == (SESSION, 1, "class")
    assert [o["occupant_kind"] for o in row["occupants"]] == [None] * 4

    await commands.assign_seat(first, "retailer", "student", user_id=A)
    await commands.assign_seat(first, "factory", "student", user_id=B)
    row = await check(first)  # assign_seat
    assert row["occupants"][0] == {
        "role": "retailer",
        "occupant_kind": "student",
        "user_id": str(A),
        "reason": "initial",
    }

    await commands.move_seat(first, "factory", second, "wholesaler")
    await check(first, second)  # move_seat, both Games
    await commands.move_seat(second, "wholesaler", first, "factory")
    await check(first, second)

    assert await commands.set_snapshot(first, snapshot(), keep_students=[A, B])
    row = await check(first)  # set_snapshot
    assert [o["occupant_kind"] for o in row["occupants"]] == [
        "student",
        "rule_based",
        "rule_based",
        "student",
    ]

    await commands.start(first)  # Week 1 is a Guided Week (`SETTINGS.guided_weeks` is 2)
    row = await check(first)
    assert (row["status"], row["week"]) == ("running", 1)
    assert row["chain_cost"] == Decimal(0)

    await view(first, "retailer", 1, A)  # one Student has ordered, the other has not
    row = await check(first)  # view_week
    assert row["status"] == "waiting"
    assert [(w["role"], w["user_id"]) for w in row["waiting_for"]] == [("factory", str(B))]
    assert row["wait_started_at"] == datetime.fromisoformat(row["waiting_for"][0]["since"])

    await view(first, "factory", 1, B)  # completes Week 1: advances in its transaction
    row = await check(first)
    assert (row["status"], row["week"], row["waiting_for"], row["wait_started_at"]) == (
        "running",
        2,
        [],
        None,
    )
    await view(first, "retailer", 2, A)
    await view(first, "factory", 2, B)
    row = await check(first)
    assert (row["status"], row["week"]) == ("running", 3)

    await commands.place_order(first, "retailer", 3, 4, "student", actor=A)
    row = await check(first)  # place_order
    assert row["status"] == "waiting"

    await commands.switch_to_rule_based(first, "factory", "takeover_staff")
    row = await check(first)  # switch_to_rule_based: the Week completes, the Game moves on
    assert (row["status"], row["week"]) == ("running", 4)
    assert row["occupants"][3]["occupant_kind"] == "rule_based"

    assert not await commands.advance(first)  # nothing to do: no write
    await check(first)
    for week in range(4, 8):
        await commands.place_order(first, "retailer", week, 4, "student", actor=A)
        await check(first)  # each Order completes its Week: the advance runs in its transaction
    (version,) = query(games_db, "SELECT version FROM games WHERE id = %s", (first,))[0]
    assert (await check(first))["version"] == version


async def test_finish_leaves_the_row_equal_to_a_recomputation(games_db):
    # A Class game's finish records a `progress` step for real Users of a real Class session, so
    # the finish is shown on a simulation Game with one Student Seat.
    game_id = await commands.create("simulation", GameSettings(weeks=8, guided_weeks=0), seed=2)
    seat_student(games_db, game_id, "retailer")
    await commands.start(game_id)
    for week in range(1, 9):
        await commands.place_order(game_id, "retailer", week, 4, "student")
        row = await check(game_id)  # the last Order finishes the Game in its transaction
    assert (row["status"], row["week"], row["waiting_for"]) == ("finished", 8, [])
    ((finished,),) = query(
        games_db, "SELECT state FROM game_weeks WHERE game_id = %s AND finished", (game_id,)
    )
    assert row["chain_cost"] == sum(Decimal(s["total_cost"]) for s in finished["seats"])


async def test_a_takeover_leaves_the_row_equal_to_a_recomputation(games_db, mail_db):
    """Story 8.2: `takeover` joins the recomputation test; in a Week with a third Student still
    waited for, the Seat taken over leaves `waiting_for`."""
    from tests.games.test_takeover import class_game as started
    from tests.games.test_takeover import due_of

    game_id, students = await started(("retailer", "wholesaler", "factory"))
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    row = await check(game_id)
    assert {w["role"] for w in row["waiting_for"]} == {"wholesaler", "factory"}
    due = due_of(game_id, "factory")
    assert due is not None
    # Story 8.3: each waited-for Seat carries its own due time, the row the nearest.
    dues = {w["role"]: datetime.fromisoformat(w["takeover_due_at"]) for w in row["waiting_for"]}
    assert dues["factory"] == due
    assert row["takeover_due_at"] == min(
        datetime.fromisoformat(w["takeover_due_at"]) for w in row["waiting_for"]
    )
    await commands.takeover(game_id, "factory", actor="system", now=due)
    row = await check(game_id)  # takeover: still waiting for the wholesaler
    assert (row["status"], [w["role"] for w in row["waiting_for"]]) == ("waiting", ["wholesaler"])
    # The Seat's reason, from which the Oversikt's mark is read (Story 8.3, AD-15).
    assert [o["reason"] for o in row["occupants"] if o["role"] == "factory"] == [
        "takeover_inactivity"
    ]


async def test_a_reclaim_leaves_the_row_equal_to_a_recomputation(games_db, mail_db):
    """Story 8.4: `request_reclaim` joins the recomputation test, and the Week opening that hands
    the Seat back rewrites the row with the Student in it."""
    from tests.games.test_reclaim import taken_over

    game_id, students = await taken_over()
    await commands.request_reclaim(game_id, "factory", actor=students["factory"])
    row = await check(game_id)  # request_reclaim: nothing changes hands yet
    assert [o["occupant_kind"] for o in row["occupants"] if o["role"] == "factory"] == [
        "rule_based"
    ]
    await commands.place_order(game_id, "retailer", 2, 4, "student", actor=students["retailer"])
    row = await check(game_id)
    [factory] = [o for o in row["occupants"] if o["role"] == "factory"]
    assert (factory["occupant_kind"], factory["reason"]) == ("student", "reclaim")


async def test_a_command_that_changes_nothing_writes_no_row(games_db):
    game_id = await class_game(1)
    await commands.assign_seat(game_id, "retailer", "student", user_id=A)
    await commands.assign_seat(game_id, "factory", "student", user_id=B)
    await commands.set_snapshot(game_id, snapshot(), keep_students=[A, B])
    await commands.start(game_id)
    await view(game_id, "retailer", 1, A)
    read = "SELECT updated_at, version FROM game_summaries WHERE game_id = %s"
    (before,) = query(games_db, read, (game_id,))
    assert not await commands.view_week(game_id, "retailer", 1, actor=A)  # viewed already
    assert query(games_db, read, (game_id,)) == [before]


def _backfill_sql() -> str:
    path = Path(__file__).parents[2] / "migrations" / "versions" / "0051_game_summaries.py"
    spec = importlib.util.spec_from_file_location("revision_0051", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BACKFILL


def _comparable(row: dict) -> dict:
    """A row with its wait times as datetimes: Postgres and Python write them differently."""
    waiting = [{**w, "since": datetime.fromisoformat(w["since"])} for w in row["waiting_for"]]
    return {**row, "waiting_for": waiting}


def _before_8_3(row: dict) -> dict:
    """A row without the keys Story 8.3 added: each wait's due time and each Seat's reason, which
    revision 0051 predates; the readers take a missing key as None."""
    return {
        **row,
        "waiting_for": [
            {k: v for k, v in w.items() if k != "takeover_due_at"} for w in row["waiting_for"]
        ],
        "occupants": [{k: v for k, v in o.items() if k != "reason"} for o in row["occupants"]],
    }


async def test_the_backfill_gives_the_rows_recompute_gives(games_db):
    finished = await commands.create("simulation", GameSettings(weeks=8), seed=5)
    await commands.start(finished)  # four Rule-based players: finished on return
    waiting = await class_game(1)
    await commands.assign_seat(waiting, "retailer", "student", user_id=A)
    await commands.assign_seat(waiting, "factory", "student", user_id=B)
    await commands.set_snapshot(waiting, snapshot(), keep_students=[A, B])
    await commands.start(waiting)
    await view(waiting, "retailer", 1, A)
    unstarted = await class_game(2)
    running = await commands.create("simulation", GameSettings(weeks=6), seed=3)
    execute(
        games_db,
        "INSERT INTO seat_occupancy (id, seat_id, from_week, occupant_kind, reason, user_id) "
        "SELECT %s, id, 1, 'student', 'initial', %s FROM seats WHERE game_id = %s "
        "AND role = 'wholesaler'",
        (uuid.uuid7(), A, running),
    )
    await commands.start(running)  # the Student has not ordered: running, no wait
    # A Student Seat taken over in the open Week after the other Student ordered: the occupant in
    # force by `from_week`, not the latest row, decides who is waited for.
    switched = await commands.create("simulation", GameSettings(weeks=8, guided_weeks=0), seed=4)
    seat_student(games_db, switched, "retailer", "wholesaler", "factory")
    await commands.start(switched)
    await commands.place_order(switched, "retailer", 1, 4, "student")
    await commands.switch_to_rule_based(switched, "factory", "takeover_staff")
    games = [finished, waiting, unstarted, running, switched]
    before = {game_id: (await stored_and_fresh(game_id))[0] for game_id in games}
    execute(games_db, "DELETE FROM game_summaries")
    ids = ", ".join(f"'{game_id}'" for game_id in games)
    execute(games_db, _backfill_sql().format(where=f"WHERE g.id IN ({ids})"))
    # The Class game's absent Student is due for Takeover (Story 8.1); the others have no clock.
    assert before[waiting]["takeover_due_at"] is not None
    assert {before[g]["takeover_due_at"] for g in games if g != waiting} == {None}
    statuses = {}
    for game_id in games:
        stored, fresh = await stored_and_fresh(game_id)
        assert _comparable(fresh) == _comparable(before[game_id]), game_id
        # Revision 0051 predates the due times; 0053 added the column empty, as no turn had one.
        assert _comparable(stored) == {
            **_comparable(_before_8_3(fresh)),
            "takeover_due_at": None,
        }, game_id
        statuses[game_id] = stored["status"]
    assert statuses == {
        finished: "finished",
        waiting: "waiting",
        unstarted: "not_started",
        running: "running",
        switched: "waiting",
    }


def test_game_status_reads_the_lifecycle_and_the_students_turns():
    game = {"lifecycle": "running", "purpose": "class", "settings": GameSettings().model_dump()}
    guided_week = GameSettings().guided_weeks

    def turn(kind: str, ordered: bool, viewed: bool = False, week: int = guided_week + 1) -> dict:
        return {
            "occupant_kind": kind,
            "ordered_at": datetime(2026, 1, 1) if ordered else None,
            "viewed_at": datetime(2026, 1, 1) if viewed else None,
            "week": week,
        }

    status = rules.game_status
    assert status({**game, "lifecycle": "not_started"}, []) is GameStatus.NOT_STARTED
    assert status({**game, "lifecycle": "finished"}, []) is GameStatus.FINISHED
    assert status(game, []) is GameStatus.RUNNING
    # One Student ordered and another has not: waiting.
    assert status(game, [turn("student", True), turn("student", False)]) is GameStatus.WAITING
    # Nobody ordered yet, or every Student has: running.
    assert status(game, [turn("student", False), turn("student", False)]) is GameStatus.RUNNING
    assert status(game, [turn("student", True), turn("llm", False)]) is GameStatus.RUNNING
    # AI players alone never make a Game wait.
    assert status(game, [turn("rule_based", True), turn("llm", False)]) is GameStatus.RUNNING
    # In a Guided Week viewing counts as ordering (FR-24): the Guided Order alone is not enough.
    guided = [
        turn("student", True, viewed=True, week=1),
        turn("student", True, viewed=False, week=1),
    ]
    assert status(game, guided) is GameStatus.WAITING
    assert status(game, [{**t, "viewed_at": None} for t in guided]) is GameStatus.RUNNING
    # Epic 8's playout still runs.
    playing_out = {**game, "lifecycle": "playing_out"}
    assert status(playing_out, [turn("student", True), turn("student", False)]) is (
        GameStatus.WAITING
    )
