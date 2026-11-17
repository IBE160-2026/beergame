"""Change events: push invalidates, pull reads (AD-8).

A mutating transaction calls `emit(session, topic, id, version)` before it commits. Postgres
delivers the `NOTIFY` only when the transaction commits, so a rolled-back change announces
nothing. The payload is `{topic, id, version}` and never data.
"""

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

CHANNEL = "events"
"""The one Postgres channel every event goes out on."""

TOPICS = frozenset({"game", "session", "debrief", "user"})
"""The closed catalogue of topics (AD-8). `game:<id>` alone carries a version."""


def payload(topic: str, id: str, version: int | None = None) -> str:
    """The NOTIFY payload for `topic:id`; raises ValueError for a topic or version AD-8 forbids."""
    if topic not in TOPICS:
        raise ValueError(f"unknown event topic {topic!r}")
    if topic == "game" and version is None:
        raise ValueError("a game event carries the Game's version")
    if topic != "game" and version is not None:
        raise ValueError(f"a {topic} event carries no version")
    return json.dumps({"topic": topic, "id": id, "version": version}, separators=(",", ":"))


async def emit(session: AsyncSession, topic: str, id: str, version: int | None = None) -> None:
    """Announce `topic:id` when the caller's transaction commits."""
    await session.execute(
        text("SELECT pg_notify(:channel, :payload)"),
        {"channel": CHANNEL, "payload": payload(topic, id, version)},
    )
