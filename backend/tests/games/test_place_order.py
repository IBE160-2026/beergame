"""Story 1.9: `games.commands.place_order` writes the Decision log and advances the Week."""

import asyncio
import json
import threading
import uuid

import psycopg
import pytest
from sqlalchemy import event

from app.engine import (
    GameSettings,
    WeekState,
    advance,
    guided_order,
    initial_state,
    rule_based,
    seat_view,
)
from app.modules.games import commands, rules, service
from app.platform.db import get_engine
from app.platform.parameter_sets import read_parameter_set
from tests.conftest import TEST_DATABASE_URL, libpq_dsn
from tests.games.helpers import (
    execute,
    listening,
    play_to_end,
    play_week,
    query,
    seat_student,
)

ROLES = ("retailer", "wholesaler", "distributor", "factory")
SETTINGS = GameSettings(demand_seed=1)


async def started(*occupants: tuple[str, str | None], **settings) -> str:
    """A started Game whose Seats get `occupants` in chain order; every other Seat gets a
    Student, whose Orders the test places itself (Story 2.1: the order source places the
    others' Orders when each Week opens)."""
    game_id = await commands.create("simulation", GameSettings(**settings), seed=1)
    students = list(ROLES[len(occupants) :])
    for role, (kind, policy_id) in zip(ROLES, occupants, strict=False):
        if kind == "student":
            students.append(role)
        else:
            await commands.assign_seat(game_id, role, kind, policy_id)
    seat_student(TEST_DATABASE_URL, game_id, *students)
    await commands.start(game_id)
    return game_id


def counts(url: str, game_id: str) -> tuple:
    """Version, Decision log rows, stored Week states, turns and ordered turns."""
    (row,) = query(
        url,
        "SELECT (SELECT version FROM games WHERE id = %s), "
        "(SELECT count(*) FROM seat_weeks WHERE game_id = %s), "
        "(SELECT count(*) FROM game_weeks WHERE game_id = %s), "
        "(SELECT count(*) FROM seat_turns WHERE game_id = %s), "
        "(SELECT count(*) FROM seat_turns WHERE game_id = %s AND ordered_at IS NOT NULL)",
        (game_id,) * 5,
    )
    return row


def log_rows(url: str, game_id: str) -> list[dict]:
    with psycopg.connect(libpq_dsn(url)) as conn:
        cur = conn.execute(
            "SELECT w.*, s.role FROM seat_weeks w JOIN seats s ON s.id = w.seat_id "
            "WHERE w.game_id = %s ORDER BY w.week, s.position",
            (game_id,),
        )
        names = [c.name for c in cur.description]
        return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]


async def to_week(game_id: str, week: int) -> None:
    while (await service.seat_state(game_id, "retailer")).week < week:
        await play_week(game_id)


async def assert_refused(url: str, game_id: str, call, code: str, status: int) -> None:
    before = counts(url, game_id)
    with listening(url) as events:
        with pytest.raises(commands.CommandError) as caught:
            await call
        assert events.drain() == []
    assert (caught.value.code, caught.value.status) == (code, status)
    assert counts(url, game_id) == before


async def test_an_order_writes_one_decision_log_row_with_the_state_seen(games_db):
    game_id = await started()
    seen = await service.seat_state(game_id, "retailer")
    turn = await service.open_turn(game_id, "retailer")
    with listening(games_db) as events:
        placed = await commands.place_order(game_id, "retailer", 1, 4, "guided")
        received = events.drain()
    assert received == [{"topic": "game", "id": game_id, "version": 3}]
    assert (placed.week, placed.open_week, placed.lifecycle) == (1, 1, "running")
    assert counts(games_db, game_id) == (3, 1, 1, 4, 1)  # no advance
    (row,) = log_rows(games_db, game_id)
    assert str(row["id"]) == placed.seat_week_id and uuid.UUID(placed.seat_week_id).version == 7
    assert (row["role"], row["week"], row["order"], row["decided_by"], row["fallback"]) == (
        "retailer",
        1,
        4,
        "guided",
        "none",
    )
    assert (row["occupant_kind"], row["reason"]) == ("student", "initial")
    assert row["opened_at"] == turn.opened_at
    assert row["rule_based_reference_order"] == turn.rule_based_reference_order
    assert row["state_seen"] == json.loads(seen.model_dump_json())
    after = await service.open_turn(game_id, "retailer")
    assert after.ordered_at == row["ordered_at"] and row["ordered_at"] >= row["opened_at"]
    (log,) = await service.decision_log(game_id)
    assert log.state_seen == seen and log.decided_by == "guided" and log.role == "retailer"


async def test_a_seat_id_works_like_a_role(games_db):
    game_id = await started()
    game = await service.get_game(game_id)
    await commands.place_order(game_id, game.seats[3].id, 1, 4, "guided")
    assert [row["role"] for row in log_rows(games_db, game_id)] == ["factory"]


async def test_the_order_that_completes_the_week_advances_it_in_the_same_transaction(games_db):
    game_id = await started()
    for role in ROLES[:3]:
        await commands.place_order(game_id, role, 1, 4, "guided")
    assert counts(games_db, game_id)[2:] == (1, 4, 3)
    statements: list[str] = []
    commits: list[bool] = []
    engine = get_engine().sync_engine
    record = lambda conn, cursor, statement, *rest: statements.append(" ".join(statement.split()))  # noqa: E731
    commit = lambda conn: commits.append(True)  # noqa: E731
    event.listen(engine, "before_cursor_execute", record)
    event.listen(engine, "commit", commit)
    try:
        with listening(games_db) as events:
            placed = await commands.place_order(game_id, "factory", 1, 4, "guided")
            received = events.drain()
    finally:
        event.remove(engine, "before_cursor_execute", record)
        event.remove(engine, "commit", commit)
    assert len(commits) == 1
    assert received == [{"topic": "game", "id": game_id, "version": 6}]
    assert (placed.week, placed.open_week) == (1, 2)
    assert counts(games_db, game_id) == (6, 4, 2, 8, 4)
    lock = next(i for i, s in enumerate(statements) if s.endswith("FOR UPDATE"))
    writes = [i for i, s in enumerate(statements) if s.startswith("INSERT INTO")]
    bump = next(i for i, s in enumerate(statements) if s.startswith("UPDATE games SET version"))
    notify = next(i for i, s in enumerate(statements) if "pg_notify" in s)
    assert lock < min(writes) and max(writes) < bump < notify
    inserted = {s.split()[2] for s in statements if s.startswith("INSERT INTO")}
    assert inserted == {"seat_weeks", "game_weeks", "seat_turns"}
    stored = query(
        games_db, "SELECT state FROM game_weeks WHERE game_id = %s AND week = 2", (game_id,)
    )
    first = initial_state(SETTINGS)
    week_2 = advance(SETTINGS, first, dict.fromkeys(ROLES, 4))
    assert WeekState.model_validate(stored[0][0]) == week_2
    references = query(
        games_db,
        "SELECT t.rule_based_reference_order FROM seat_turns t JOIN seats s ON s.id = t.seat_id "
        "WHERE t.game_id = %s AND t.week = 2 ORDER BY s.position",
        (game_id,),
    )
    rule = rule_based.parse_params(
        read_parameter_set("rule_based", rule_based.DEFAULT_SET_ID), rule_based.DEFAULT_SET_ID
    )
    orders = [dict.fromkeys(ROLES, 4)]
    assert [r[0] for r in references] == [
        rule_based.order(SETTINGS, seat_view(SETTINGS, [first, week_2], orders, role), rule)
        for role in ROLES
    ]


@pytest.mark.parametrize(
    "occupant",
    [("rule_based", None), ("scripted", "constant-4")],
    ids=["rule_based", "scripted"],
)
async def test_guided_weeks_take_only_the_guided_order_for_every_occupant(games_db, occupant):
    """The Student's Guided Orders are refused unless guided; the order source places the
    other Seats' Guided Orders."""
    game_id = await started(("student", None), occupant, occupant, occupant)
    for week in range(1, SETTINGS.guided_weeks + 1):
        await assert_refused(
            games_db,
            game_id,
            commands.place_order(game_id, "retailer", week, 5, "guided"),
            "guided_order_required",
            422,
        )
        for decided_by in ("rule_based", "scripted", "student", "llm"):
            await assert_refused(
                games_db,
                game_id,
                commands.place_order(game_id, "retailer", week, 4, decided_by),
                "guided_order_required",
                422,
            )
        await commands.place_order(game_id, "retailer", week, guided_order(SETTINGS), "guided")
    rows = [r for r in log_rows(games_db, game_id) if r["week"] <= SETTINGS.guided_weeks]
    assert len(rows) == 4 * SETTINGS.guided_weeks
    assert {(r["order"], r["decided_by"]) for r in rows} == {(4, "guided")}
    assert {r["occupant_kind"] for r in rows if r["role"] != "retailer"} == {occupant[0]}
    assert {r["occupant_kind"] for r in rows if r["role"] == "retailer"} == {"student"}


async def test_guided_is_refused_after_the_guided_weeks(games_db):
    game_id = await started()
    await to_week(game_id, 5)
    await assert_refused(
        games_db,
        game_id,
        commands.place_order(game_id, "retailer", 5, 4, "guided"),
        "decided_by_invalid",
        422,
    )
    placed = await commands.place_order(game_id, "retailer", 5, 9, "student")
    assert placed.week == 5


@pytest.mark.parametrize("order", [-1, 1000, 4.0, True, "4", None])
async def test_an_invalid_order_is_refused(games_db, order):
    game_id = await started()
    await to_week(game_id, 5)
    await assert_refused(
        games_db,
        game_id,
        commands.place_order(game_id, "retailer", 5, order, "rule_based"),
        "order_invalid",
        422,
    )


async def test_the_bounds_are_valid_orders(games_db):
    game_id = await started()
    await to_week(game_id, 5)
    await commands.place_order(game_id, "retailer", 5, 0, "rule_based")
    await commands.place_order(game_id, "factory", 5, 999, "rule_based")
    assert [r["order"] for r in log_rows(games_db, game_id)][-2:] == [0, 999]


async def test_an_unknown_decider_is_refused(games_db):
    game_id = await started()
    await assert_refused(
        games_db,
        game_id,
        commands.place_order(game_id, "retailer", 1, 4, "robot"),
        "decided_by_invalid",
        422,
    )


@pytest.mark.parametrize("week", [0, 2, 3, "1", True, None])
async def test_an_order_outside_the_open_week_is_refused(games_db, week):
    game_id = await started()
    await assert_refused(
        games_db,
        game_id,
        commands.place_order(game_id, "retailer", week, 4, "guided"),
        "week_not_open",
        409,
    )


async def test_an_earlier_week_is_no_longer_open(games_db):
    game_id = await started()
    await play_week(game_id)
    await assert_refused(
        games_db,
        game_id,
        commands.place_order(game_id, "retailer", 1, 4, "guided"),
        "week_not_open",
        409,
    )


async def test_a_second_order_is_refused_and_the_key_backs_it_up(games_db):
    game_id = await started()
    await commands.place_order(game_id, "retailer", 1, 4, "guided")
    await assert_refused(
        games_db,
        game_id,
        commands.place_order(game_id, "retailer", 1, 4, "guided"),
        "order_exists",
        409,
    )
    with pytest.raises(psycopg.errors.UniqueViolation, match="uq_seat_weeks_game_week_seat"):
        execute(
            games_db,
            "INSERT INTO seat_weeks SELECT gen_random_uuid(), game_id, seat_id, week, state_seen, "
            '"order", decided_by, fallback, occupant_kind, reason, opened_at, ordered_at, '
            "rule_based_reference_order FROM seat_weeks WHERE game_id = %s",
            (game_id,),
        )


async def test_unknown_games_and_seats_are_refused(games_db):
    game_id = await started()
    for bad_game in ("nope", str(uuid.uuid7()), None):
        with pytest.raises(commands.CommandError) as caught:
            await commands.place_order(bad_game, "retailer", 1, 4, "guided")  # type: ignore[arg-type]
        assert (caught.value.code, caught.value.status) == ("game_not_found", 404)
    for bad_seat in ("brewer", str(uuid.uuid7())):
        await assert_refused(
            games_db,
            game_id,
            commands.place_order(game_id, bad_seat, 1, 4, "guided"),
            "seat_not_found",
            404,
        )


async def test_a_game_not_started_takes_no_order(games_db):
    game_id = await commands.create("simulation", SETTINGS, seed=1)
    await assert_refused(
        games_db,
        game_id,
        commands.place_order(game_id, "retailer", 1, 4, "guided"),
        "game_not_started",
        409,
    )


async def test_the_last_week_finishes_the_game(games_db):
    last = 8  # a short Game: the length is not the point
    game_id = await started(weeks=last)
    await to_week(game_id, last)
    for role in ROLES[:3]:
        await commands.place_order(
            game_id,
            role,
            last,
            (await service.open_turn(game_id, role)).rule_based_reference_order,
            "rule_based",
        )
    with listening(games_db) as events:
        placed = await commands.place_order(
            game_id,
            "factory",
            last,
            (await service.open_turn(game_id, "factory")).rule_based_reference_order,
            "rule_based",
        )
        received = events.drain()
    assert (placed.open_week, placed.lifecycle) == (None, "finished")
    assert len(received) == 1
    game = await service.get_game(game_id)
    assert game.lifecycle == "finished"
    weeks = query(
        games_db,
        "SELECT week, finished, state FROM game_weeks WHERE game_id = %s ORDER BY week, finished",
        (game_id,),
    )
    assert [(w, f) for w, f, _ in weeks] == [(w, False) for w in range(1, last + 1)] + [
        (last, True)
    ]
    final = WeekState.model_validate(weeks[-1][2])
    assert final.finished and final.week == last
    # No turn for the Week after the last.
    assert counts(games_db, game_id)[1:] == (4 * last, last + 1, 4 * last, 4 * last)
    await assert_refused(
        games_db,
        game_id,
        commands.place_order(game_id, "retailer", last, 4, "rule_based"),
        "game_finished",
        409,
    )
    await assert_refused(
        games_db,
        game_id,
        commands.place_order(game_id, "retailer", last + 1, 4, "rule_based"),
        "game_finished",
        409,
    )
    # What each Seat saw in the last Week stays readable.
    assert (await service.seat_state(game_id, "retailer")).week == last


async def test_finish_needs_the_finished_state():
    with pytest.raises(ValueError, match="finished state"):
        await commands.finish(None, uuid.uuid7(), initial_state(SETTINGS))  # type: ignore[arg-type]


async def test_the_decision_log_and_week_states_can_never_change(games_db):
    game_id = await started()
    await play_week(game_id)
    for statement in (
        'UPDATE seat_weeks SET "order" = "order" + 1',
        "UPDATE seat_weeks SET state_seen = '{}'::jsonb",
        "DELETE FROM seat_weeks",
    ):
        with pytest.raises(psycopg.errors.RestrictViolation, match="seat_weeks is append-only"):
            execute(games_db, statement)
    for statement in (
        "UPDATE game_weeks SET state = '{}'::jsonb",
        "UPDATE game_weeks SET finished = true",
        "DELETE FROM game_weeks",
    ):
        with pytest.raises(psycopg.errors.RestrictViolation, match="game_weeks is append-only"):
            execute(games_db, statement)
    assert counts(games_db, game_id)[1:3] == (4, 2)


async def test_the_last_two_orders_at_once_advance_exactly_once(games_db):
    for _ in range(5):
        game_id = await started()
        for role in ROLES[:2]:
            await commands.place_order(game_id, role, 1, 4, "guided")
        results = await asyncio.gather(
            commands.place_order(game_id, "distributor", 1, 4, "guided"),
            commands.place_order(game_id, "factory", 1, 4, "guided"),
        )
        assert sorted(r.open_week for r in results) == [1, 2]
        assert counts(games_db, game_id) == (6, 4, 2, 8, 4)


async def test_a_reader_never_sees_a_week_without_its_state(games_db):
    """Every committed version shows a newest open Week with its state and all four turns."""
    game_id = await started()
    seen: list[tuple] = []
    stop = threading.Event()

    def read() -> None:
        with psycopg.connect(libpq_dsn(games_db), autocommit=True) as conn:
            while not stop.is_set():
                ((weeks, turns),) = conn.execute(
                    "SELECT (SELECT max(week) FROM game_weeks WHERE game_id = %s), "
                    "(SELECT count(*) FROM seat_turns WHERE game_id = %s AND week = "
                    "(SELECT max(week) FROM game_weeks WHERE game_id = %s))",
                    (game_id,) * 3,
                ).fetchall()
                seen.append((weeks, turns))

    reader = threading.Thread(target=read)
    reader.start()
    try:
        for _ in range(6):
            await play_week(game_id)
    finally:
        stop.set()
        reader.join(timeout=10)
    assert len({weeks for weeks, _ in seen}) > 1  # the reader saw several Weeks
    assert all(turns == 4 for _, turns in seen)


def test_week_complete_is_true_only_when_every_turn_has_an_order():
    assert not rules.week_complete([])
    assert not rules.week_complete([{"ordered_at": 1}, {"ordered_at": None}])
    assert rules.week_complete([{"ordered_at": 1}, {"ordered_at": 2}])


async def test_play_to_end_matches_the_engine_only_game(games_db):
    """Four Rule-based players through the commands give the engine-only Orders and costs. A
    12-Week Game: past the Guided Weeks and the demand step; `test_sim.py` compares a whole
    Classic Game with the engine-only trace."""
    settings = SETTINGS.model_copy(update={"weeks": 12})
    game_id = await started(weeks=settings.weeks)
    await play_to_end(game_id)
    rule = rule_based.parse_params(
        read_parameter_set("rule_based", rule_based.DEFAULT_SET_ID), rule_based.DEFAULT_SET_ID
    )
    states = [initial_state(settings)]
    orders: list[dict] = []
    expected = []
    while not states[-1].finished:
        state = states[-1]
        if state.week <= settings.guided_weeks:
            placed = dict.fromkeys(ROLES, guided_order(settings))
        else:
            placed = {
                r: rule_based.order(settings, seat_view(settings, states, orders, r), rule)
                for r in ROLES
            }
        expected += [(state.week, r, placed[r], state.seat(r).cost) for r in ROLES]
        orders.append(placed)
        states.append(advance(settings, state, placed))
    log = await service.decision_log(game_id)
    assert [(r.week, r.role, r.order, r.state_seen.week_cost) for r in log] == expected
    assert {r.decided_by for r in log if r.week > 4} == {"rule_based"}
    assert all(r.order == r.rule_based_reference_order for r in log if r.week > 4)
