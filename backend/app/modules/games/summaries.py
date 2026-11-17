"""A finished Game in numbers for the simulation runner (AD-22, FR-30).

Every number is read from the stored tables: Total cost from the finished `game_weeks` row,
Order counts from the Decision log (`seat_weeks`) and the check from `game_checks`.
"""

import uuid
from decimal import Decimal

from app.engine import WeekState
from app.modules.games import repo
from app.modules.games.checks import as_game_check
from app.modules.games.schemas import DecidedBy, GameSummary, Lifecycle
from app.modules.games.views import ViewError
from app.platform.db import get_sessionmaker

__all__ = ["game_summary"]


async def game_summary(game_id: str) -> GameSummary:
    """The stored numbers of a finished Game. Refuses (`ViewError`): `game_not_found` 404,
    `game_not_finished` 409."""
    try:
        game_uuid = uuid.UUID(game_id)
    except ValueError, TypeError, AttributeError:
        raise ViewError("game_not_found", f"no Game {game_id!r}", 404) from None
    async with get_sessionmaker()() as session:
        game = await repo.get_game(session, game_uuid)
        if game is None:
            raise ViewError("game_not_found", f"no Game {game_id!r}", 404)
        finished = await repo.finished_state(session, game_uuid)
        if game["lifecycle"] != Lifecycle.FINISHED or finished is None:
            raise ViewError("game_not_finished", "only a finished Game is summarised", 409)
        counts = await repo.orders_by_decided_by(session, game_uuid)
        check = await repo.game_check(session, game_uuid)
    state = WeekState.model_validate(finished)
    total_cost = tuple((seat.role.value, seat.total_cost) for seat in state.seats)
    return GameSummary(
        game_id=str(game["id"]),
        demand_seed=game["demand_seed"],
        weeks=state.week,
        total_cost=total_cost,
        chain_cost=sum((cost for _, cost in total_cost), Decimal(0)),
        orders=tuple(
            (decided_by, counts[decided_by]) for decided_by in DecidedBy if counts.get(decided_by)
        ),
        check=as_game_check(check) if check is not None else None,
    )
