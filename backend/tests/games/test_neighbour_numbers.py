"""Information visibility in `seat_state` (Story 6.21, FR-83, AD-3, AD-17): with the flag on and a
view switched on in the Game's snapshot, every Seat's `SeatState` holds its direct neighbours'
inventory and backlog in the open Week, and nothing else of any other Seat; the Decision log
records what was visible, and the finished-game check accepts it with the flag on or off."""

from app.engine import GameSettings
from app.modules.games import commands, service
from app.platform.config import get_settings
from tests.games.helpers import classic_game, played_once, tamper

BOTH = {"upstream": True, "downstream": True}
NEIGHBOURS = {
    "retailer": ["wholesaler"],
    "wholesaler": ["distributor", "retailer"],
    "distributor": ["factory", "wholesaler"],
    "factory": ["distributor"],
}
"""Each Role's neighbours with both views on, upstream first."""


def flag(monkeypatch, on: bool) -> None:
    monkeypatch.setenv("FEATURE_INFO_VISIBILITY", "true" if on else "false")
    get_settings.cache_clear()


async def views_game(url: str, monkeypatch) -> str:
    """A finished 10-Week simulation Game of four Rule-based players with both views on, played once
    per run with the flag on; each call stores its own copy."""

    async def play() -> str:
        flag(monkeypatch, True)
        settings = GameSettings(weeks=10, info_visibility=BOTH)
        game_id = await commands.create("simulation", settings, seed=11)
        await commands.start(game_id)  # four Rule-based players: finished on return
        return game_id

    return await played_once(url, ("views", 11), play)


async def test_each_seat_sees_its_neighbours_inventory_and_backlog_and_nothing_else(
    games_db, monkeypatch
):
    game_id = await views_game(games_db, monkeypatch)
    flag(monkeypatch, True)
    week = 9
    own = {role: await service.seat_state(game_id, role, week) for role in NEIGHBOURS}
    for role, neighbours in NEIGHBOURS.items():
        numbers = [n.model_dump(mode="json") for n in own[role].neighbour_numbers]
        assert numbers == [
            {"role": neighbour, "week": week, "quantity": quantity, "value": value}
            for neighbour in neighbours
            for quantity, value in (
                ("inventory", own[neighbour].inventory),
                ("backlog", own[neighbour].backlog),
            )
        ], role
    assert any(n.value > 0 for state in own.values() for n in state.neighbour_numbers)
    # With the flag off the same snapshot shows no neighbour (AD-17).
    flag(monkeypatch, False)
    for role in NEIGHBOURS:
        assert (await service.seat_state(game_id, role, week)).neighbour_numbers == ()


async def test_the_decision_log_records_what_was_visible_and_the_check_accepts_it(
    games_db, monkeypatch
):
    game_id = await views_game(games_db, monkeypatch)
    rows = await service.decision_log(game_id)
    assert rows
    for row in rows:
        seen = row.state_seen
        assert [n.role for n in seen.neighbour_numbers][::2] == NEIGHBOURS[row.role]
        assert all(n.week == row.week for n in seen.neighbour_numbers)
    # Recorded with the flag on; checked with it off, and on for a second copy.
    flag(monkeypatch, False)
    assert (await service.verify_finished(game_id)).ok
    flag(monkeypatch, True)
    assert (await service.verify_finished(await views_game(games_db, monkeypatch))).ok


async def test_numbers_a_game_without_views_never_showed_fail_the_check(games_db, monkeypatch):
    flag(monkeypatch, True)
    game_id = await classic_game(games_db)
    extra = '[{"role": "retailer", "week": 5, "quantity": "inventory", "value": 3}]'
    tamper(
        games_db,
        "UPDATE seat_weeks SET state_seen = jsonb_set(state_seen, '{neighbour_numbers}', %s) "
        "WHERE game_id = %s AND week = 5 AND seat_id = "
        "(SELECT id FROM seats WHERE game_id = %s AND role = 'wholesaler')",
        (extra, game_id, game_id),
    )
    check = await service.verify_finished(game_id)
    assert not check.ok
    assert [(v.rule, v.week, v.role) for v in check.violations] == [
        ("decision_log", 5, "wholesaler")
    ]
