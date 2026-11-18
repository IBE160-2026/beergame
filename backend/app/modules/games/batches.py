"""Simulation batches (Story 2.11, AD-22): one row per `python -m app.sim run`, written once.

`create_batch` is the only writer of `simulation_batches`; a Game joins a batch through
`games.commands.create(..., batch_id=...)`. Both are reached through `games.service`.
"""

import uuid
from collections.abc import Mapping
from typing import Any

import structlog

from app.modules.games import repo
from app.modules.games.schemas import SimulationBatch
from app.modules.games.views import ViewError
from app.platform.db import get_sessionmaker

__all__ = ["create_batch", "get_batch"]

log = structlog.get_logger(__name__)


async def create_batch(
    batch_file: Mapping[str, Any], pass_lines: Mapping[str, Any], *, mock: bool
) -> str:
    """Store a batch with its file and its pass lines, which can never change after (the row is
    append-only); returns its id. `started_at` is the database clock."""
    batch_id = uuid.uuid7()
    async with get_sessionmaker().begin() as session:
        await repo.insert_batch(
            session,
            {
                "id": batch_id,
                "batch_file": dict(batch_file),
                "pass_lines": dict(pass_lines),
                "mock": mock,
            },
        )
    log.info("simulation_batch_created", batch_id=str(batch_id), mock=mock)
    return str(batch_id)


async def get_batch(batch_id: str) -> SimulationBatch:
    """The stored batch and its Games, oldest first. Refuses (`ViewError`) `batch_not_found`
    404."""
    try:
        batch_uuid = uuid.UUID(batch_id)
    except ValueError, TypeError, AttributeError:
        raise ViewError("batch_not_found", f"no simulation batch {batch_id!r}", 404) from None
    async with get_sessionmaker()() as session:
        row = await repo.get_batch(session, batch_uuid)
        if row is None:
            raise ViewError("batch_not_found", f"no simulation batch {batch_id!r}", 404)
        game_ids = await repo.batch_game_ids(session, batch_uuid)
    return SimulationBatch(
        id=str(row["id"]),
        batch_file=row["batch_file"],
        pass_lines=row["pass_lines"],
        mock=row["mock"],
        started_at=row["started_at"],
        game_ids=tuple(str(game_id) for game_id in game_ids),
    )
