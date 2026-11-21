"""Publish and read immutable, versioned content (Story 6.3, AD-23).

A record is never changed: `publish` stores a new version (the next number of its kind) and a
trigger refuses every UPDATE. The lock pins the version a Class session uses (`starting_task_pin`,
registered by `sessions`); readers ask for that version, or the latest for a session locked
before the pin existed. This module imports no feature module."""

import uuid
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content.models import Kind, content_records
from app.modules.content.schemas import StartingTask
from app.platform.db import get_sessionmaker

__all__ = [
    "ContentNotFound",
    "Kind",
    "StartingTask",
    "get",
    "latest_version",
    "pinned_version",
    "publish",
    "starting_task",
    "starting_task_pin",
]

_SCHEMAS = {Kind.STARTING_TASK: StartingTask}


class ContentNotFound(Exception):
    """No record of that kind and version."""


def _validated(kind: Kind, body: Any) -> StartingTask:
    return _SCHEMAS[kind].model_validate(body)


async def publish(kind: Kind | str, body: Any) -> int:
    """Validate `body` and store it as the next version of `kind`; the new version number."""
    kind = Kind(kind)
    stored = _validated(kind, body).model_dump(mode="json")
    async with get_sessionmaker().begin() as session:
        # One publisher of a kind at a time, so two never take the same number.
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"content:{kind}"}
        )
        version = (await _latest(session, kind) or 0) + 1
        await session.execute(
            insert(content_records).values(
                id=uuid.uuid7(), kind=kind.value, version=version, body=stored
            )
        )
    return version


async def _latest(session: AsyncSession, kind: Kind) -> int | None:
    return await session.scalar(
        select(func.max(content_records.c.version)).where(content_records.c.kind == kind.value)
    )


async def latest_version(kind: Kind | str, session: AsyncSession | None = None) -> int:
    """The newest version of `kind`; `ContentNotFound` when none is stored."""
    kind = Kind(kind)
    if session is None:
        async with get_sessionmaker()() as own:
            return await latest_version(kind, own)
    found = await _latest(session, kind)
    if found is None:
        raise ContentNotFound(kind.value)
    return found


async def get(kind: Kind | str, version: int) -> Any:
    """The validated body of `kind` at `version`; `ContentNotFound` when there is none."""
    kind = Kind(kind)
    async with get_sessionmaker()() as session:
        body = await session.scalar(
            select(content_records.c.body).where(
                content_records.c.kind == kind.value, content_records.c.version == version
            )
        )
    if body is None:
        raise ContentNotFound(f"{kind.value} v{version}")
    return _validated(kind, body)


async def starting_task(version: int | None) -> tuple[int, StartingTask]:
    """The Starting task at the pinned `version`, or the latest when None: (version, body)."""
    if version is None:
        version = await latest_version(Kind.STARTING_TASK)
    return version, await get(Kind.STARTING_TASK, version)


async def starting_task_pin(session: AsyncSession, _class_session: Any) -> dict[str, int]:
    """The lock's pin provider (Story 6.3, AD-23): the Starting task version a Class session
    uses from its lock on, under `SessionRuntime.pins["starting_task"]`."""
    return {"version": await latest_version(Kind.STARTING_TASK, session)}


def pinned_version(pins: Any) -> int | None:
    """The Starting task version in a snapshot's `pins`; None when the session was locked before
    the pin existed (the reader then takes the latest)."""
    if not isinstance(pins, dict):
        return None
    found = pins.get(Kind.STARTING_TASK.value)
    version = found.get("version") if isinstance(found, dict) else None
    # `True` is an int too; a version is a whole number from 1.
    return version if type(version) is int and version >= 1 else None
