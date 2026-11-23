"""The print route's read of a report snapshot (Story 13.7, AD-14, AD-18).

`read(snapshot_id, token)` answers the snapshot's data once: one UPDATE marks it used, and only
while it is unused, unexpired and the token's SHA-256 matches. Every other case answers None,
the same for an unknown id, a used, an expired and a wrong token."""

import uuid
from datetime import datetime

from app.modules.reports import repo
from app.modules.reports.render import token_hash
from app.platform import auth
from app.platform.db import get_sessionmaker

__all__ = ["purge_expired", "read"]


async def read(snapshot_id: str, token: str) -> dict | None:
    try:
        wanted = uuid.UUID(snapshot_id)
    except ValueError:
        return None
    if not token:
        return None
    async with get_sessionmaker().begin() as s:
        return await repo.use_snapshot(s, wanted, token_hash(token), auth.utcnow())


async def purge_expired(now: datetime) -> int:
    """Delete the snapshots whose token has expired (a render killed before its `finally`): the
    sweep's `reports.purge_snapshots` (AD-14)."""
    async with get_sessionmaker().begin() as s:
        return await repo.delete_expired_snapshots(s, now)
