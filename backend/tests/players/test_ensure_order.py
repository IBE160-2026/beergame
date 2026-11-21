"""Story 2.1: `players.ensure_order` is the one order source; `advance` and
`switch_to_rule_based` keep every Game moving one Week per transaction (AD-2, AD-5, AD-9)."""

import uuid

import pytest
from sqlalchemy import event

from app.engine import GameSettings
from app.modules.games import commands, service
from app.modules.players import service as players
from app.platform.db import get_engine, get_sessionmaker
from tests.games.helpers import listening, query, seat_student, view

ROLES = ("retailer", "wholesaler", "distributor", "factory")
SHORT = {"weeks": 8, "guided_weeks": 2}
"""A short Game for the tests that do not need the Classic 36 Weeks."""


async def created(url: str, students=(), occupants=None, **settings) -> str:
    game_id = await commands.create("simulation", GameSettings(**settings), seed=1)
    for role, (kind, policy_id) in (occupants or {}).items():
        await commands.assign_seat(game_id, role, kind, policy_id)
    seat_student(url, game_id, *students)
    return game_id


def version(url: str, game_id: str) -> int:
    ((value,),) = query(url, "SELECT version FROM games WHERE id = %s", (game_id,))
    return value


def lifecycle(url: str, game_id: str) -> str:
    ((value,),) = query(url, "SELECT lifecycle FROM games WHERE id = %s", (game_id,))
    return value


def log(url: str, game_id: str, week: int | None = None) -> list[tuple]:
    """(week, role, order, decided_by, occupant_kind, reason, reference) per Decision log row."""
    rows = query(
        url,
        "SELECT w.week, s.role, w.order, w.decided_by, w.occupant_kind, w.reason, "
        "w.rule_based_reference_order FROM seat_weeks w JOIN seats s ON s.id = w.seat_id "
        "WHERE w.game_id = %s ORDER BY w.week, s.position",
        (game_id,),
    )
    return [row for row in rows if week is None or row[0] == week]


def occupancy(url: str, game_id: str, role: str) -> list[tuple]:
    return query(
        url,
        "SELECT o.from_week, o.occupant_kind, o.reason FROM seat_occupancy o "
        "JOIN seats s ON s.id = o.seat_id WHERE s.game_id = %s AND s.role = %s ORDER BY o.id",
        (game_id, role),
    )


async def student_orders(game_id: str, role: str, until_week: int) -> None:
    """Play the Student's Weeks until `until_week` is open: view a Guided Week (its Order was
    placed when it opened, Story 6.10), else place the reference Order."""
    while True:
        state = await service.seat_state(game_id, role)
        if state.week >= until_week:
            return
        turn = await service.open_turn(game_id, role, state.week)
        if turn.guided:
            await view(game_id, role, state.week)
        else:
            await commands.place_order(
                game_id, role, state.week, turn.rule_based_reference_order, "student"
            )


async def test_start_plays_a_game_of_four_rule_based_players_one_week_per_transaction(games_db):
    weeks, guided = SHORT["weeks"], SHORT["guided_weeks"]
    game_id = await created(games_db, **SHORT)
    commits: list[bool] = []
    sync_engine = get_engine().sync_engine

    def commit(conn) -> None:
        commits.append(True)

    event.listen(sync_engine, "commit", commit)
    try:
        with listening(games_db) as events:
            assert await commands.start(game_id) == 1
            received = events.drain()
    finally:
        event.remove(sync_engine, "commit", commit)
    assert lifecycle(games_db, game_id) == "finished"
    # `start`, then an advance per Week that opens the next one and one that finishes the Game.
    assert len(commits) == 1 + weeks
    assert [item["version"] for item in received] == list(range(2, 2 + weeks + 1))
    stored = query(
        games_db,
        "SELECT week, finished FROM game_weeks WHERE game_id = %s ORDER BY week, finished",
        (game_id,),
    )
    assert stored == [(w, False) for w in range(1, weeks + 1)] + [(weeks, True)]
    rows = log(games_db, game_id)
    assert len(rows) == weeks * 4
    assert all(row[3] == "guided" for row in rows if row[0] <= guided)
    assert all(row[3] == "rule_based" and row[2] == row[6] for row in rows if row[0] > guided)


async def test_advance_finishes_a_game_stopped_between_two_advances(games_db, monkeypatch):
    game_id = await created(games_db, **SHORT)
    real = commands._advance_once
    calls: list[str] = []

    async def stop_after_three(game: str) -> None:
        while len(calls) < 3 and await real(game):
            calls.append(game)

    monkeypatch.setattr(commands, "_settle", stop_after_three)
    await commands.start(game_id)
    assert lifecycle(games_db, game_id) == "running"
    assert len(log(games_db, game_id, week=4)) == 4  # Week 4 is complete but still open
    monkeypatch.setattr(commands, "_settle", lambda game: _settle(real, game))
    before = version(games_db, game_id)
    assert await commands.advance(game_id) is True
    assert lifecycle(games_db, game_id) == "finished"
    assert version(games_db, game_id) == before + 5  # Weeks 4 to 7 opened the next, 8 finished
    assert await commands.advance(game_id) is False


async def _settle(step, game_id: str) -> None:
    while await step(game_id):
        pass


async def test_advance_does_nothing_when_there_is_nothing_to_advance(games_db):
    game_id = await created(games_db, students=["retailer"], **SHORT)
    with listening(games_db) as events:
        assert await commands.advance(game_id) is False  # not started
        await commands.start(game_id)
        before = version(games_db, game_id)
        assert await commands.advance(game_id) is False  # Week 1 waits for the Student
        assert version(games_db, game_id) == before
        # The start only: the Game and its one Student (Story 6.5).
        assert [item["topic"] for item in events.drain()] == ["game", "user"]
    with pytest.raises(commands.CommandError) as caught:
        await commands.advance(str(uuid.uuid7()))
    assert caught.value.code == "game_not_found"


async def test_a_student_week_waits_and_the_ai_seats_order_when_it_opens(games_db):
    game_id = await created(
        games_db,
        students=["retailer"],
        occupants={"wholesaler": ("scripted", "order-incoming")},
        **SHORT,
    )
    await commands.start(game_id)
    week_1 = log(games_db, game_id, week=1)
    # Every Seat's Guided Order, the Student's too (Story 6.10); the Week waits for the view.
    assert [(row[1], row[3]) for row in week_1] == [
        ("retailer", "guided"),
        ("wholesaler", "guided"),
        ("distributor", "guided"),
        ("factory", "guided"),
    ]
    assert await commands.advance(game_id) is False
    assert await view(game_id, "retailer", 1)
    assert (await service.seat_state(game_id, "retailer")).week == 2
    assert len(log(games_db, game_id, week=2)) == 4  # the next Week's Guided Orders are placed
    await student_orders(game_id, "retailer", 4)
    week_3 = {row[1]: row for row in log(games_db, game_id, week=3)}
    assert week_3["distributor"][3] == "rule_based"
    assert week_3["distributor"][2] == week_3["distributor"][6]
    seen = query(
        games_db,
        "SELECT w.order, (w.state_seen->>'incoming_order')::int, w.decided_by FROM seat_weeks w "
        "JOIN seats s ON s.id = w.seat_id WHERE w.game_id = %s AND s.role = 'wholesaler' "
        "AND w.week = 3",
        (game_id,),
    )
    assert seen == [(seen[0][1], seen[0][1], "scripted")]


async def test_ensure_order_called_again_does_nothing(games_db):
    game_id = await created(games_db, students=["retailer"], **SHORT)
    await commands.start(game_id)
    game = await service.get_game(game_id)
    before = (len(log(games_db, game_id)), version(games_db, game_id))
    async with get_sessionmaker().begin() as session:
        open_game = service.OpenGame(session=session, game_id=uuid.UUID(game_id))
        for seat in game.seats:  # all four have ordered: a Guided Week (Story 6.10)
            await players.ensure_order(open_game, seat.id)
    assert (len(log(games_db, game_id)), version(games_db, game_id)) == before


async def test_switch_mid_week_places_the_reference_order_and_the_game_moves_on(games_db):
    game_id = await created(games_db, students=["retailer"], **SHORT)
    await commands.start(game_id)
    await student_orders(game_id, "retailer", 3)
    before = version(games_db, game_id)
    with listening(games_db) as events:
        await commands.switch_to_rule_based(game_id, "retailer", "takeover_staff")
        received = events.drain()
    assert occupancy(games_db, game_id, "retailer") == [
        (1, "student", "initial"),
        (3, "rule_based", "takeover_staff"),
    ]
    retailer_3 = [row for row in log(games_db, game_id, week=3) if row[1] == "retailer"]
    assert retailer_3 == [
        (
            3,
            "retailer",
            retailer_3[0][6],
            "rule_based",
            "rule_based",
            "takeover_staff",
            retailer_3[0][6],
        )
    ]
    assert lifecycle(games_db, game_id) == "finished"
    # The switch, then Weeks 3 to 7 opening the next Week and Week 8 finishing the Game.
    assert [item["version"] for item in received] == list(range(before + 1, before + 1 + 7))


async def test_switch_after_the_order_starts_next_week_and_places_nothing(games_db):
    game_id = await created(games_db, students=["retailer", "wholesaler"], weeks=8, guided_weeks=0)
    await commands.start(game_id)
    await commands.place_order(game_id, "retailer", 1, 4, "student")
    rows, before = len(log(games_db, game_id)), version(games_db, game_id)
    with listening(games_db) as events:
        await commands.switch_to_rule_based(game_id, "retailer", "guard_switch")
        assert len(events.drain()) == 1
    assert occupancy(games_db, game_id, "retailer")[-1] == (2, "rule_based", "guard_switch")
    assert (len(log(games_db, game_id)), version(games_db, game_id)) == (rows, before + 1)
    await commands.place_order(game_id, "wholesaler", 1, 4, "student")
    week_2 = {row[1]: row for row in log(games_db, game_id, week=2)}
    assert week_2["retailer"][3:6] == ("rule_based", "rule_based", "guard_switch")


async def test_in_a_guided_week_the_view_counts_as_the_order_for_a_switch(games_db):
    """Story 6.10: a Student who has viewed the Guided Week has ordered, so a switch starts next
    Week; one who has not switches this Week, and the Week no longer waits for them."""
    game_id = await created(games_db, students=["retailer", "wholesaler"], **SHORT)
    await commands.start(game_id)
    await view(game_id, "retailer", 1)
    await commands.switch_to_rule_based(game_id, "retailer", "guard_switch")
    assert occupancy(games_db, game_id, "retailer")[-1] == (2, "rule_based", "guard_switch")
    assert (await service.seat_state(game_id, "retailer")).week == 1  # waits for the Grossist
    await commands.switch_to_rule_based(game_id, "wholesaler", "takeover_staff")
    assert occupancy(games_db, game_id, "wholesaler")[-1] == (1, "rule_based", "takeover_staff")
    # Week 1 completed without the Grossist's view; its Guided Order stays the one placed.
    assert lifecycle(games_db, game_id) == "finished"  # no Student left: the Game plays out
    week_1 = {row[1]: row for row in log(games_db, game_id, week=1)}
    assert week_1["wholesaler"][3:5] == ("guided", "student")


@pytest.mark.parametrize(
    ("args", "code", "status"),
    [
        (("retailer", "initial"), "reason_invalid", 422),
        (("retailer", "bogus"), "reason_invalid", 422),
        (("nobody", "cost_limit"), "seat_not_found", 404),
    ],
)
async def test_switch_refusals_store_nothing(games_db, args, code, status):
    game_id = await created(games_db, students=["retailer"], **SHORT)
    await commands.start(game_id)
    before = (version(games_db, game_id), occupancy(games_db, game_id, "retailer"))
    with listening(games_db) as events:
        with pytest.raises(commands.CommandError) as caught:
            await commands.switch_to_rule_based(game_id, *args)
        assert events.drain() == []
    assert (caught.value.code, caught.value.status) == (code, status)
    assert (version(games_db, game_id), occupancy(games_db, game_id, "retailer")) == before


async def test_switch_needs_a_running_game(games_db):
    game_id = await created(games_db, **SHORT)
    with pytest.raises(commands.CommandError) as caught:
        await commands.switch_to_rule_based(game_id, "retailer", "cost_limit")
    assert (caught.value.code, caught.value.status) == ("game_not_started", 409)
    await commands.start(game_id)  # four Rule-based players: finished on return
    with pytest.raises(commands.CommandError) as caught:
        await commands.switch_to_rule_based(game_id, "retailer", "cost_limit")
    assert (caught.value.code, caught.value.status) == ("game_finished", 409)
    with pytest.raises(commands.CommandError) as caught:
        await commands.switch_to_rule_based(str(uuid.uuid7()), "retailer", "cost_limit")
    assert caught.value.code == "game_not_found"


async def test_place_order_within_another_games_transaction_is_refused(games_db):
    game_id = await created(games_db, students=["retailer"], **SHORT)
    await commands.start(game_id)
    async with get_sessionmaker().begin() as session:
        other = service.OpenGame(session=session, game_id=uuid.uuid7())
        with pytest.raises(ValueError):
            await commands.place_order(game_id, "retailer", 1, 4, "guided", within=other)


async def test_a_scripted_occupant_without_a_known_policy_is_refused(games_db):
    from tests.games.helpers import execute

    game_id = await created(games_db, weeks=8, guided_weeks=0)  # Week 1 needs the policy
    execute(
        games_db,
        "INSERT INTO seat_occupancy (id, seat_id, from_week, occupant_kind, policy_id, reason) "
        "SELECT %s, id, 1, 'scripted', 'gone', 'initial' FROM seats "
        "WHERE game_id = %s AND role = 'retailer'",
        (uuid.uuid7(), game_id),
    )
    before = version(games_db, game_id)
    with pytest.raises(commands.CommandError) as caught:
        await commands.start(game_id)
    assert (caught.value.code, caught.value.status) == ("occupant_not_playable", 422)
    assert (lifecycle(games_db, game_id), version(games_db, game_id)) == ("not_started", before)


async def test_a_failed_advance_after_the_commit_leaves_the_command_standing(games_db, monkeypatch):
    game_id = await created(games_db, students=["retailer"], weeks=8, guided_weeks=0)
    await commands.start(game_id)

    async def broken(game: str) -> bool:
        raise RuntimeError("database gone")

    monkeypatch.setattr(commands, "_advance_once", broken)
    placed = await commands.place_order(game_id, "retailer", 1, 4, "student")
    assert (placed.week, placed.open_week) == (1, 2)  # its own transaction committed
    monkeypatch.undo()
    assert len(log(games_db, game_id, week=1)) == 4


async def test_two_advances_at_once_advance_each_week_once(games_db, monkeypatch):
    import asyncio

    async def no_settle(game: str) -> None:
        return None

    game_id = await created(games_db, **SHORT)
    monkeypatch.setattr(commands, "_settle", no_settle)
    await commands.start(game_id)
    monkeypatch.undo()
    before = version(games_db, game_id)
    results = await asyncio.gather(commands.advance(game_id), commands.advance(game_id))
    assert True in results
    assert lifecycle(games_db, game_id) == "finished"
    weeks = query(
        games_db,
        "SELECT week, finished FROM game_weeks WHERE game_id = %s ORDER BY week, finished",
        (game_id,),
    )
    assert weeks == [(w, False) for w in range(1, 9)] + [(8, True)]
    assert version(games_db, game_id) == before + 8  # one version per advance
    assert len(log(games_db, game_id)) == 8 * 4
