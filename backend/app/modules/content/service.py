"""Publish and read immutable, versioned content (Story 6.3, Story 9.1, AD-23).

A record is never changed: `publish` stores a new version (the next number of its kind) and a
trigger refuses every UPDATE. The lock pins the version a Class session uses (`starting_task_pin`,
`detected_patterns_pin`, `sentence_templates_pin`, `reflection_questions_pin` and
`moment_templates_pin`, registered by
`sessions`); readers ask for
that version, or the latest for a session locked before the pin existed. This module imports no
feature module."""

import uuid
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content.models import Kind, content_records
from app.modules.content.schemas import (
    MomentTemplates,
    PatternSet,
    ReflectionQuestion,
    ReflectionQuestions,
    SentenceTemplates,
    StartingTask,
)
from app.platform.db import get_sessionmaker

__all__ = [
    "ContentNotFound",
    "Kind",
    "MomentTemplates",
    "PatternSet",
    "ReflectionQuestion",
    "ReflectionQuestions",
    "SentenceTemplates",
    "StartingTask",
    "detected_patterns",
    "detected_patterns_pin",
    "get",
    "latest_version",
    "moment_templates",
    "moment_templates_pin",
    "pinned_version",
    "publish",
    "reflection_questions",
    "reflection_questions_pin",
    "sentence_templates",
    "sentence_templates_pin",
    "starting_task",
    "starting_task_pin",
]

type Body = StartingTask | PatternSet | SentenceTemplates | ReflectionQuestions | MomentTemplates

_SCHEMAS: dict[
    Kind,
    type[StartingTask]
    | type[PatternSet]
    | type[SentenceTemplates]
    | type[ReflectionQuestions]
    | type[MomentTemplates],
] = {
    Kind.STARTING_TASK: StartingTask,
    Kind.DETECTED_PATTERNS: PatternSet,
    Kind.SENTENCE_TEMPLATES: SentenceTemplates,
    Kind.REFLECTION_QUESTIONS: ReflectionQuestions,
    Kind.MOMENT_TEMPLATES: MomentTemplates,
}


class ContentNotFound(Exception):
    """No record of that kind and version."""


def _validated(kind: Kind, body: Any) -> Body:
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
    task: StartingTask = await get(Kind.STARTING_TASK, version)
    return version, task


async def detected_patterns(version: int | None) -> tuple[int, PatternSet]:
    """The Detected pattern definitions at the pinned `version`, or the latest when None:
    (version, body) (Story 9.1)."""
    if version is None:
        version = await latest_version(Kind.DETECTED_PATTERNS)
    patterns: PatternSet = await get(Kind.DETECTED_PATTERNS, version)
    return version, patterns


async def sentence_templates(version: int | None) -> tuple[int, SentenceTemplates]:
    """The sentence templates at the pinned `version`, or the latest when None: (version, body)
    (Story 9.4)."""
    if version is None:
        version = await latest_version(Kind.SENTENCE_TEMPLATES)
    templates: SentenceTemplates = await get(Kind.SENTENCE_TEMPLATES, version)
    return version, templates


async def reflection_questions(version: int | None) -> tuple[int, ReflectionQuestions]:
    """The reflection questions at the pinned `version`, or the latest when None: (version, body)
    (Story 9.6)."""
    if version is None:
        version = await latest_version(Kind.REFLECTION_QUESTIONS)
    questions: ReflectionQuestions = await get(Kind.REFLECTION_QUESTIONS, version)
    return version, questions


async def moment_templates(version: int | None) -> tuple[int, MomentTemplates]:
    """The own moments' templates at the pinned `version`, or the latest when None: (version,
    body) (Story 9.7)."""
    if version is None:
        version = await latest_version(Kind.MOMENT_TEMPLATES)
    templates: MomentTemplates = await get(Kind.MOMENT_TEMPLATES, version)
    return version, templates


async def starting_task_pin(session: AsyncSession, _class_session: Any) -> dict[str, int]:
    """The lock's pin provider (Story 6.3, AD-23): the Starting task version a Class session
    uses from its lock on, under `SessionRuntime.pins["starting_task"]`."""
    return {"version": await latest_version(Kind.STARTING_TASK, session)}


async def detected_patterns_pin(session: AsyncSession, _class_session: Any) -> dict[str, int]:
    """The lock's pin provider (Story 9.1, AD-23): the Detected pattern version a Class session
    uses from its lock on, under `SessionRuntime.pins["detected_patterns"]`."""
    return {"version": await latest_version(Kind.DETECTED_PATTERNS, session)}


async def sentence_templates_pin(session: AsyncSession, _class_session: Any) -> dict[str, int]:
    """The lock's pin provider (Story 9.4, AD-23): the sentence-template version a Class session
    uses from its lock on, under `SessionRuntime.pins["sentence_templates"]`."""
    return {"version": await latest_version(Kind.SENTENCE_TEMPLATES, session)}


async def reflection_questions_pin(session: AsyncSession, _class_session: Any) -> dict[str, int]:
    """The lock's pin provider (Story 9.6, AD-23): the reflection-question version a Class
    session uses from its lock on, under `SessionRuntime.pins["reflection_questions"]`."""
    return {"version": await latest_version(Kind.REFLECTION_QUESTIONS, session)}


async def moment_templates_pin(session: AsyncSession, _class_session: Any) -> dict[str, int]:
    """The lock's pin provider (Story 9.7, AD-23): the moment-template version a Class session
    uses from its lock on, under `SessionRuntime.pins["moment_templates"]`."""
    return {"version": await latest_version(Kind.MOMENT_TEMPLATES, session)}


def pinned_version(pins: Any, kind: Kind | str = Kind.STARTING_TASK) -> int | None:
    """The version of `kind` (default: the Starting task) in a snapshot's `pins`; None when the
    session was locked before that pin existed, or the Game has no session (the reader then
    takes the latest)."""
    if not isinstance(pins, dict):
        return None
    found = pins.get(Kind(kind).value)
    version = found.get("version") if isinstance(found, dict) else None
    # `True` is an int too; a version is a whole number from 1.
    return version if type(version) is int and version >= 1 else None
