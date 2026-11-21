"""Change events: push invalidates, pull reads (AD-8).

A mutating transaction calls `emit(session, topic, id, version)` before it commits. Postgres
delivers the `NOTIFY` only when the transaction commits, so a rolled-back change announces
nothing. The payload is `{topic, id, version}` and never data.
"""

import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)

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


HeartbeatHook = Callable[[uuid.UUID], Awaitable[None]]
"""`(user_id)`: called on each heartbeat of the User's open event stream (Story 9.12)."""

_heartbeat_hooks: list[HeartbeatHook] = []


def on_heartbeat(callback: HeartbeatHook) -> None:
    """Register a presence hook (Story 9.12, AD-8): a module registers at import, so `platform`
    imports no module. Registering the same callback again changes nothing."""
    if callback not in _heartbeat_hooks:
        _heartbeat_hooks.append(callback)


HEARTBEAT_HOOK_TIMEOUT_S = 5.0
"""The longest a presence hook may hold up the stream's heartbeat."""


async def heartbeat(user_id: uuid.UUID) -> None:
    """Run every presence hook for `user_id`, the stream's 15-second heartbeat. Each hook opens
    its own short database session; one that fails or takes longer than
    `HEARTBEAT_HOOK_TIMEOUT_S` is logged (its type only) and the rest run, so the stream never
    ends or stalls for it."""
    for hook in list(_heartbeat_hooks):
        try:
            await asyncio.wait_for(hook(user_id), HEARTBEAT_HOOK_TIMEOUT_S)
        except Exception as exc:  # the type only: an exception's text may hold personal data
            log.warning("heartbeat_hook_failed", exc_type=type(exc).__name__)
