"""Story 2.8: at the cost limit every LLM Seat of the scope becomes a Rule-based player for the
rest of the scope's life (FR-69, AD-5, AD-6)."""

from decimal import Decimal

from structlog.testing import capture_logs

from app.ai import budget
from app.engine import GameSettings
from app.modules.games import commands, service
from app.modules.players import jobs as player_jobs
from app.modules.players import service as players
from app.platform import jobs
from tests.ai.helpers import stored_config
from tests.games.helpers import query
from tests.players.test_llm_jobs import FIRST, SHORT, calls, llm_game, rows, seat_id


def occupancy(url: str, game_id: str) -> list[tuple]:
    """(role, from_week, occupant_kind, reason) of every occupancy row, in order."""
    return query(
        url,
        "SELECT s.role, o.from_week, o.occupant_kind, o.reason FROM seat_occupancy o "
        "JOIN seats s ON s.id = o.seat_id WHERE s.game_id = %s ORDER BY s.position, o.id",
        (game_id,),
    )


async def test_the_job_at_the_limit_switches_every_llm_seat_of_the_scope(games_db, ai_db):
    config_id = await stored_config(limit="0")
    first = await llm_game(("retailer", "wholesaler"), config_id=config_id)
    second = await llm_game(("factory",), config_id=config_id)
    waiting = await commands.create(
        "simulation", GameSettings(**SHORT), seed=3, model_config_id=config_id
    )
    await commands.assign_seat(waiting, "distributor", "llm")  # before the limit: an LLM player
    done = await commands.create(  # finished at once: all Rule-based, no Student
        "simulation", GameSettings(**SHORT), seed=3, model_config_id=config_id
    )
    await commands.start(done)
    assert (await service.get_game(done)).lifecycle == "finished"
    assert await service.games_charged_to(await service.budget_scope(first)) == [first, second]

    retailer = seat_id(games_db, first, "retailer")
    await player_jobs.place_llm_order(game_id=first, seat_id=retailer, week=FIRST)

    week = [r for r in rows(games_db, first) if r[0] == FIRST]
    by_role = {
        role: (order, by, fallback, ids, ref) for _, role, order, by, fallback, ids, ref in week
    }
    order, by, fallback, ids, reference = by_role["retailer"]
    assert (order, by, fallback, ids) == (reference, "rule_based", "budget_exhausted", [])
    # The wholesaler had not ordered yet: it switched in this Week and ordered at once.
    assert by_role["wholesaler"][1:4] == ("rule_based", "none", [])
    assert ("retailer", FIRST + 1, "rule_based", "cost_limit") in occupancy(games_db, first)
    assert ("wholesaler", FIRST, "rule_based", "cost_limit") in occupancy(games_db, first)
    assert ("factory", FIRST, "rule_based", "cost_limit") in occupancy(games_db, second)
    state = await budget.state(budget.BudgetScope.evaluation(config_id))
    assert state.players_exhausted_at is not None and state.spent == 0

    # The rest of each Game is played by Rule-based players: no further call, no fallback.
    await jobs.run_until_idle([jobs.AI_ORDERS])
    for game_id in (first, second):
        assert (await service.get_game(game_id)).lifecycle == "finished"
        later = [r for r in rows(games_db, game_id) if r[0] > FIRST]
        assert {(by, fallback) for _, _, _, by, fallback, *_ in later} == {("rule_based", "none")}
    assert calls(games_db) == 0

    # A Game that had not started gets Rule-based players when it starts; a new LLM Seat too.
    await commands.assign_seat(waiting, "factory", "llm")
    await commands.start(waiting)
    assert occupancy(games_db, waiting)[-3:] == [
        ("distributor", 1, "llm", "initial"),
        ("distributor", 1, "rule_based", "cost_limit"),
        ("factory", 1, "rule_based", "cost_limit"),
    ]
    await jobs.run_until_idle([jobs.AI_ORDERS])
    assert (await service.get_game(waiting)).lifecycle == "finished"
    assert calls(games_db) == 0
    # Applying the limit again switches nothing more.
    assert await players.apply_cost_limit(first) == 0


async def test_a_failed_switch_is_logged_and_the_order_still_stands(games_db, ai_db, monkeypatch):
    game_id = await llm_game(("retailer",), config_id=await stored_config(limit="0"))

    async def broken(_):
        raise RuntimeError("database gone")

    monkeypatch.setattr(players, "apply_cost_limit", broken)
    seat = seat_id(games_db, game_id, "retailer")
    with capture_logs() as logs:
        await player_jobs.place_llm_order(game_id=game_id, seat_id=seat, week=FIRST)
    assert "cost_limit_switch_failed" in [entry["event"] for entry in logs]
    ((by, mark),) = [(r[3], r[4]) for r in rows(games_db, game_id) if r[0] == FIRST][:1]
    assert (by, mark) == ("rule_based", "budget_exhausted")
    assert (await budget.state(await service.budget_scope(game_id))).spent == Decimal(0)
