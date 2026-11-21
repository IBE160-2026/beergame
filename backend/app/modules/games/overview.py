"""`game_summaries`, the Lecturer overview's read model (Story 7.1, AD-25, FR-39).

`games.commands` calls `refresh` in the transaction of every change, after the Game's version
has risen (`commands._commit_change`), so the row always matches the game tables as that
transaction commits them. The status comes from `rules.game_status` only (AD-2). Revision 0051
stored the rows of the Games that existed before; its SQL mirrors `recompute`.
"""

import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import GameSettings
from app.modules.games import repo, rules
from app.modules.games.policy import policy
from app.modules.games.schemas import GameStatus, Lifecycle, OccupantKind

__all__ = ["recompute", "refresh"]


async def recompute(
    session: AsyncSession, game: Mapping[str, Any], version: int | None = None
) -> dict[str, Any]:
    """The `game_summaries` values of `game` (a `games` row) from the game tables as they stand
    in `session`: who holds each Seat, the status, whom the Game waits for and since when, the
    Week and the chain Total cost, and the nearest stored Takeover due time of the Seats it waits
    for (Story 8.1); each waited-for Seat its own due time and each Seat its occupancy reason
    (Story 8.3); the Pause in force (Story 8.6), when the Game waits for no one. `version` is the
    Game's version, the row's own by default."""
    game_id = game["id"]
    seats = await repo.seats_with_occupant(session, game_id)
    newest = await repo.newest_week(session, game_id)
    started = game["lifecycle"] != Lifecycle.NOT_STARTED and newest is not None
    turns: list[Mapping[str, Any]] = []
    if game["lifecycle"] in (Lifecycle.RUNNING, Lifecycle.PLAYING_OUT) and newest is not None:
        turns = list(await repo.week_turns_with_occupant(session, game_id, newest["week"]))
    status = rules.game_status(game, turns)
    waiting_for: list[dict[str, Any]] = []
    since: list[datetime] = []
    due: list[datetime] = []
    if status is GameStatus.WAITING:
        guided = rules.guided_week(
            policy(str(game["purpose"])),
            GameSettings.model_validate(game["settings"]),
            newest["week"],
        )
        by_seat = {turn["seat_id"]: turn for turn in turns}
        for seat in seats:  # chain order
            turn = by_seat.get(seat["id"])
            if (
                turn is None
                or turn["occupant_kind"] != OccupantKind.STUDENT
                or turn["wait_started_at"] is None
                or rules.has_ordered(turn, guided=guided)
            ):
                continue
            since.append(turn["wait_started_at"])
            if turn["takeover_due_at"] is not None:
                due.append(turn["takeover_due_at"])
            waiting_for.append(
                {
                    "role": seat["role"],
                    "user_id": _text(turn["user_id"]),
                    "since": turn["wait_started_at"].isoformat(),
                    # The Seat's own due time (Story 8.3): Seats of one game may differ.
                    "takeover_due_at": _iso(turn["takeover_due_at"]),
                }
            )
    return {
        "game_id": game_id,
        "class_session_id": game["class_session_id"],
        "game_number": game["game_number"],
        "purpose": str(game["purpose"]),
        "status": status.value,
        "week": newest["week"] if started else None,
        "wait_started_at": min(since) if since else None,
        "takeover_due_at": min(due) if due else None,
        "waiting_for": waiting_for,
        "occupants": [
            {
                "role": seat["role"],
                "occupant_kind": seat["occupant_kind"],
                "user_id": _text(seat["user_id"]),
                # The latest occupancy row's reason (Story 8.3): the AD-15 mark is read from it.
                "reason": _text(seat["reason"]),
                # Who triggered that row (Story 8.5): the Oversikt names them, read at read time.
                "actor_user_id": _text(seat["actor_user_id"]),
            }
            for seat in seats
        ],
        "chain_cost": newest["chain_cost"] if started else None,
        "version": game["version"] if version is None else version,
        # The Pause in force (Story 8.6): the Oversikt shows since when and by whom. Only while the
        # status is `paused`: a Game that finished under a Pause (its Students' Seats all AI-held)
        # carries none.
        "paused_at": game.get("paused_at") if status is GameStatus.PAUSED else None,
        "paused_by": game.get("paused_by") if status is GameStatus.PAUSED else None,
    }


async def refresh(session: AsyncSession, game: Mapping[str, Any], version: int) -> None:
    """Write `game`'s `game_summaries` row in the caller's command transaction; `game` is the
    Game row as the command leaves it, `version` its version after the bump."""
    await repo.upsert_summary(session, await recompute(session, game, version))


def _text(value: uuid.UUID | str | None) -> str | None:
    return None if value is None else str(value)


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()
