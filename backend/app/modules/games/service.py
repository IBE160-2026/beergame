"""What other modules may use from `games`. Writes go through `games.commands` only."""

import uuid

from app.engine import GameSettings
from app.modules.games import repo
from app.modules.games.checks import rules_versions_without_package, verify_finished
from app.modules.games.policy import GamePolicy, PurposeNotSupportedError, policy
from app.modules.games.schemas import (
    DecidedBy,
    DecisionLogRow,
    GameCheck,
    GameOverview,
    Lifecycle,
    OccupantKind,
    OrderPlaced,
    Purpose,
    SeatOverview,
    SeatState,
    SessionRuntime,
    TurnOverview,
)
from app.modules.games.views import ViewError, decision_log, open_turn, seat_state
from app.platform.db import get_sessionmaker

__all__ = [
    "DecidedBy",
    "DecisionLogRow",
    "GameCheck",
    "GameOverview",
    "GamePolicy",
    "Lifecycle",
    "OccupantKind",
    "OrderPlaced",
    "Purpose",
    "PurposeNotSupportedError",
    "SeatOverview",
    "SeatState",
    "SessionRuntime",
    "TurnOverview",
    "ViewError",
    "decision_log",
    "get_game",
    "open_turn",
    "policy",
    "rules_versions_without_package",
    "seat_state",
    "verify_finished",
]


async def get_game(game_id: str) -> GameOverview | None:
    """The stored Game with each Seat's current occupant, or None when there is no such Game."""
    try:
        game_uuid = uuid.UUID(game_id)
    except ValueError, TypeError, AttributeError:
        return None
    async with get_sessionmaker()() as session:
        game = await repo.get_game(session, game_uuid)
        if game is None:
            return None
        seats = await repo.seats_with_occupant(session, game_uuid)
    return GameOverview(
        id=str(game["id"]),
        purpose=game["purpose"],
        lifecycle=game["lifecycle"],
        version=game["version"],
        demand_seed=game["demand_seed"],
        rules_version=game["rules_version"],
        settings=GameSettings.model_validate(game["settings"]),
        session_runtime=SessionRuntime.model_validate(game["session_runtime"]),
        seats=tuple(
            SeatOverview(
                id=str(seat["id"]),
                role=seat["role"],
                occupant_kind=seat["occupant_kind"],
                policy_id=seat["policy_id"],
            )
            for seat in seats
        ),
    )
