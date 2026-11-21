"""The stored facts set of each Seat of a finished Game (Story 9.1, FR-44, AD-7, AD-14).

`get_or_create(game, seat)` builds the set once with `analysis.facts` from the Decision log and
the Detected pattern definitions the Game pinned at its lock (`SessionRuntime.pins`, AD-23; the
latest version for a Game without the pin), stores it in `fact_sets` and returns the stored row
from then on, never rebuilding it. `compute(game, seat)` builds the same set without storing it,
for the simulation runner (`python -m app.sim facts`, AD-22).

The payload holds ids, values and Roles only: no names and no user or Seat ids (AD-14)."""

import uuid
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from app.analysis import facts as analysis
from app.engine import GameSettings
from app.modules.content import service as content
from app.modules.games import repo
from app.modules.games.schemas import Lifecycle, SeatState
from app.modules.games.views import ViewError
from app.platform.db import get_sessionmaker

__all__ = ["StoredFactSet", "compute", "get_or_create"]


class StoredFactSet(BaseModel):
    """One `fact_sets` row: the id later citations store, and the set itself."""

    model_config = ConfigDict(frozen=True)

    id: str
    game_id: str
    seat_id: str
    analysis_version: int
    patterns_version: int
    facts: analysis.FactSet


def _uuid(value: object) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _seat_id(seats: Sequence[Mapping[str, Any]], seat: object) -> uuid.UUID:
    """The id of the Seat named by its Role or its id; `seat_not_found` 404 otherwise."""
    wanted = _uuid(seat)
    for row in seats:
        if str(seat) == row["role"] or wanted == row["id"]:
            return uuid.UUID(str(row["id"]))
    raise ViewError("seat_not_found", f"the Game has no Seat {seat!r}", 404)


def _cost(state: SeatState, kind: str) -> Decimal:
    return sum((line.amount for line in state.cost_lines if line.kind == kind), Decimal(0))


def _logged(row: Mapping[str, Any]) -> analysis.LoggedOrder:
    state = SeatState.model_validate(row["state_seen"])
    return analysis.LoggedOrder(
        week=row["week"],
        role=row["role"],
        order=row["order"],
        decided_by=row["decided_by"],
        occupant_kind=row["occupant_kind"],
        incoming_order=state.incoming_order,
        incoming_delivery=state.incoming_delivery,
        shipped=state.shipped,
        inventory=state.inventory,
        backlog=state.backlog,
        supply_line=state.supply_line,
        holding_cost=_cost(state, "holding"),
        backorder_cost=_cost(state, "backorder"),
        week_cost=state.week_cost,
    )


async def _finished(game_id: str) -> tuple[uuid.UUID, Mapping[str, Any], list[Any]]:
    """The finished Game's id, row and Seats; refuses `game_not_found` 404 and
    `game_not_finished` 409."""
    game_uuid = _uuid(game_id)
    async with get_sessionmaker()() as session:
        game = await repo.get_game(session, game_uuid) if game_uuid else None
        if game is None or game_uuid is None:
            raise ViewError("game_not_found", f"no Game {game_id!r}", 404)
        if game["lifecycle"] != Lifecycle.FINISHED:
            raise ViewError("game_not_finished", "only a finished Game has facts", 409)
        seats = await repo.seats_with_occupant(session, game_uuid)
    return game_uuid, game, seats


async def _build(
    game_uuid: uuid.UUID, game: Mapping[str, Any], seat_id: uuid.UUID, seats: Sequence[Any]
) -> tuple[int, analysis.FactSet]:
    runtime = game["session_runtime"] or {}
    pinned = content.pinned_version(runtime.get("pins"), content.Kind.DETECTED_PATTERNS)
    try:
        version, patterns = await content.detected_patterns(pinned)
        async with get_sessionmaker()() as session:
            rows = await repo.decision_log(session, game_uuid)
        log = analysis.DecisionLog(
            roles=GameSettings.model_validate(game["settings"]).roles,
            rows=tuple(_logged(row) for row in rows),
        )
    except (content.ContentNotFound, ValidationError) as exc:
        # A pinned version gone, or a Decision log that is not a complete, consistent Game.
        raise ViewError("facts_unavailable", f"no facts can be built: {exc}", 409) from None
    role = next(row["role"] for row in seats if row["id"] == seat_id)
    return version, analysis.facts(log, role, patterns)


def _stored(row: Mapping[str, Any]) -> StoredFactSet:
    return StoredFactSet(
        id=str(row["id"]),
        game_id=str(row["game_id"]),
        seat_id=str(row["seat_id"]),
        analysis_version=row["analysis_version"],
        patterns_version=row["payload"]["patterns_version"],
        facts=analysis.FactSet.model_validate(row["payload"]["facts"]),
    )


async def compute(game_id: str, seat: str) -> tuple[int, analysis.FactSet]:
    """The facts set of the Seat (its Role or id) of the finished Game and the Detected pattern
    version it used, built now and not stored."""
    game_uuid, game, seats = await _finished(game_id)
    return await _build(game_uuid, game, _seat_id(seats, seat), seats)


async def get_or_create(game_id: str, seat: str) -> StoredFactSet:
    """The stored facts set of the Seat (its Role or id) of the finished Game: built and stored
    by the first call, returned as stored by every later one (AD-7). Refuses (`ViewError`):
    `game_not_found` 404, `game_not_finished` 409, `seat_not_found` 404, `facts_unavailable`
    409. A stored row is returned whatever its `analysis_version` (never rebuilt, AD-7)."""
    game_uuid, game, seats = await _finished(game_id)
    seat_id = _seat_id(seats, seat)
    async with get_sessionmaker()() as session:
        found = await repo.fact_set(session, game_uuid, seat_id)
    if found is not None:
        return _stored(found)
    version, built = await _build(game_uuid, game, seat_id, seats)
    async with get_sessionmaker().begin() as session:
        await repo.insert_fact_set(
            session,
            {
                "id": uuid.uuid7(),
                "game_id": game_uuid,
                "seat_id": seat_id,
                "analysis_version": built.analysis_version,
                "payload": {"patterns_version": version, "facts": built.model_dump(mode="json")},
            },
        )
        stored = await repo.fact_set(session, game_uuid, seat_id)
    assert stored is not None  # inserted now, or by the racing call that won
    return _stored(stored)
