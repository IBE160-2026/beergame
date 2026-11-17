"""Story 1.11: `game_summary` reads a finished Game's numbers from the stored tables."""

from decimal import Decimal

import pytest

from app.engine import GameSettings
from app.modules.games import commands, service
from tests.games.helpers import classic_game, query, tamper


async def finished_game(url: str, *, check: bool = True) -> str:
    game_id = await classic_game(url)
    if check:
        await service.verify_finished(game_id)
    return game_id


async def test_summary_numbers_equal_the_stored_tables(games_db):
    game_id = await finished_game(games_db)
    summary = await service.game_summary(game_id)
    assert (summary.game_id, summary.demand_seed, summary.weeks) == (game_id, 7, 36)
    stored = query(
        games_db,
        "SELECT seat->>'role', (seat->>'total_cost')::numeric FROM game_weeks, "
        "jsonb_array_elements(state->'seats') WITH ORDINALITY AS t(seat, n) "
        "WHERE game_id = %s AND finished ORDER BY n",
        (game_id,),
    )
    assert list(summary.total_cost) == stored
    assert [role for role, _ in summary.total_cost] == [
        "retailer",
        "wholesaler",
        "distributor",
        "factory",
    ]
    assert summary.chain_cost == sum(cost for _, cost in stored)
    # The same Total cost is the sum of the Week costs in the Decision log.
    ((logged,),) = query(
        games_db,
        "SELECT sum((state_seen->>'week_cost')::numeric) FROM seat_weeks WHERE game_id = %s",
        (game_id,),
    )
    assert summary.chain_cost == logged
    counted = query(
        games_db,
        "SELECT decided_by, count(*) FROM seat_weeks WHERE game_id = %s GROUP BY decided_by",
        (game_id,),
    )
    assert dict(summary.orders) == dict(counted)
    # In `DecidedBy` order, zero counts left out.
    assert [(by.value, count) for by, count in summary.orders] == [
        ("rule_based", 32 * 4),
        ("guided", 4 * 4),
    ]
    assert summary.check is not None and summary.check.ok
    assert isinstance(summary.chain_cost, Decimal)


async def test_summary_without_a_check_reports_none(games_db):
    game_id = await finished_game(games_db, check=False)
    assert (await service.game_summary(game_id)).check is None


async def test_summary_shows_a_failed_check(games_db):
    game_id = await finished_game(games_db, check=False)
    tamper(
        games_db,
        "UPDATE game_weeks SET state = jsonb_set(state, '{seats,0,inventory}', '99') "
        "WHERE game_id = %s AND week = 10 AND NOT finished",
        (game_id,),
    )
    await service.verify_finished(game_id)
    check = (await service.game_summary(game_id)).check
    assert check is not None and not check.ok and check.violations


@pytest.mark.parametrize("game_id", ["nope", "01a1eb10-f299-75a6-8ec2-a251c50791e1"])
async def test_summary_of_an_unknown_game_is_refused(games_db, game_id):
    with pytest.raises(service.ViewError) as caught:
        await service.game_summary(game_id)
    assert (caught.value.code, caught.value.status) == ("game_not_found", 404)


async def test_summary_of_a_running_game_is_refused(games_db):
    from tests.games.helpers import seat_student

    game_id = await commands.create("simulation", GameSettings(), seed=7)
    seat_student(games_db, game_id, "retailer")  # the Game waits for the Student
    await commands.start(game_id)
    with pytest.raises(service.ViewError) as caught:
        await service.game_summary(game_id)
    assert (caught.value.code, caught.value.status) == ("game_not_finished", 409)
