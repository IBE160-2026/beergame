"""Publish and read immutable, versioned content (Story 6.3, Story 9.1, AD-23).

A record is never changed: `publish` stores a new version (the next number of its kind) and a
trigger refuses every UPDATE. The lock pins the version a Class session uses (`starting_task_pin`,
`detected_patterns_pin`, `sentence_templates_pin`, `reflection_questions_pin` and
`moment_templates_pin`, `debrief_quiz_pin` and `narration_templates_pin`, registered by
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
    ITEM_TYPES,
    DebriefQuiz,
    MomentTemplates,
    NarrationTemplates,
    PatternSet,
    QuestionSet,
    ReflectionQuestion,
    ReflectionQuestions,
    SentenceTemplates,
    StartingTask,
)
from app.platform.db import get_sessionmaker

__all__ = [
    "ContentNotFound",
    "ContentRejected",
    "DebriefQuiz",
    "Kind",
    "MomentTemplates",
    "NarrationTemplates",
    "PatternSet",
    "QuestionSet",
    "ReflectionQuestion",
    "ReflectionQuestions",
    "SentenceTemplates",
    "StartingTask",
    "debrief_quiz",
    "debrief_quiz_pin",
    "detected_patterns",
    "detected_patterns_pin",
    "get",
    "latest_body",
    "stored_version_of",
    "latest_version",
    "moment_templates",
    "moment_templates_pin",
    "narration_templates",
    "narration_templates_pin",
    "normalised",
    "pinned_version",
    "publish",
    "question_set",
    "reflection_questions",
    "reflection_questions_pin",
    "sentence_templates",
    "sentence_templates_pin",
    "starting_task",
    "starting_task_pin",
]

type Body = (
    StartingTask
    | PatternSet
    | SentenceTemplates
    | ReflectionQuestions
    | MomentTemplates
    | DebriefQuiz
    | NarrationTemplates
    | QuestionSet
)

_SCHEMAS: dict[
    Kind,
    type[StartingTask]
    | type[PatternSet]
    | type[SentenceTemplates]
    | type[ReflectionQuestions]
    | type[MomentTemplates]
    | type[DebriefQuiz]
    | type[NarrationTemplates]
    | type[QuestionSet],
] = {
    Kind.STARTING_TASK: StartingTask,
    Kind.DETECTED_PATTERNS: PatternSet,
    Kind.SENTENCE_TEMPLATES: SentenceTemplates,
    Kind.REFLECTION_QUESTIONS: ReflectionQuestions,
    Kind.MOMENT_TEMPLATES: MomentTemplates,
    Kind.DEBRIEF_QUIZ: DebriefQuiz,
    Kind.NARRATION_TEMPLATES: NarrationTemplates,
    Kind.QUESTION_SET: QuestionSet,
}


class ContentNotFound(Exception):
    """No record of that kind and version."""


class ContentRejected(Exception):
    """A body refused with a stable code (Story 11.1): `unknown_item_type` for a question-set
    item whose type the product does not know, `starting_task_items_missing` for a question set
    that does not reference every item of the latest Starting task. Nothing is stored."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _item_types_known(body: Any) -> None:
    """A question-set item of an unknown type is refused by its own code, before the schema."""
    if not isinstance(body, dict):
        return
    for group in ("items", "replacements"):
        items = body.get(group)
        if not isinstance(items, list):
            continue  # the schema refuses it (`invalid_record`)
        for item in items:
            if not isinstance(item, dict) or "type" not in item:
                continue
            if item["type"] not in ITEM_TYPES:
                raise ContentRejected("unknown_item_type", f"{group}: {item['type']!r}")


async def _starting_task_referenced(session: AsyncSession, question_set: QuestionSet) -> None:
    """Every item of the latest Starting task is referenced by the question set (FR-52)."""
    version = await _latest(session, Kind.STARTING_TASK)
    body = await session.scalar(
        select(content_records.c.body).where(
            content_records.c.kind == Kind.STARTING_TASK.value,
            content_records.c.version == version,
        )
    )
    task = StartingTask.model_validate(body)
    referenced = {item.starting_task_item for item in question_set.items}
    missing = [item.id for item in task.items if item.id not in referenced]
    unknown = sorted(referenced - {item.id for item in task.items} - {None})
    if missing or unknown:
        raise ContentRejected(
            "starting_task_items_missing", f"missing {missing}, unknown {unknown}"
        )


def _validated(kind: Kind, body: Any) -> Body:
    return _SCHEMAS[kind].model_validate(body)


async def publish(kind: Kind | str, body: Any) -> int:
    """Validate `body` and store it as the next version of `kind`; the new version number."""
    kind = Kind(kind)
    if kind == Kind.QUESTION_SET:
        _item_types_known(body)
    validated = _validated(kind, body)
    stored = validated.model_dump(mode="json")
    async with get_sessionmaker().begin() as session:
        # One publisher of a kind at a time, so two never take the same number.
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"content:{kind}"}
        )
        if isinstance(validated, QuestionSet):
            await _starting_task_referenced(session, validated)
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


async def debrief_quiz(version: int | None) -> tuple[int, DebriefQuiz]:
    """The Debrief quiz at the pinned `version`, or the latest when None: (version, body)
    (Story 9.9)."""
    if version is None:
        version = await latest_version(Kind.DEBRIEF_QUIZ)
    quiz: DebriefQuiz = await get(Kind.DEBRIEF_QUIZ, version)
    return version, quiz


async def narration_templates(version: int | None) -> tuple[int, NarrationTemplates]:
    """The narration templates at the pinned `version`, or the latest when None: (version, body)
    (Story 9.14)."""
    if version is None:
        version = await latest_version(Kind.NARRATION_TEMPLATES)
    templates: NarrationTemplates = await get(Kind.NARRATION_TEMPLATES, version)
    return version, templates


async def latest_body(kind: Kind | str) -> Any | None:
    """The stored JSON of the newest version of `kind`, None when none is stored: what the
    content load compares a file with (Story 11.1)."""
    kind = Kind(kind)
    async with get_sessionmaker()() as session:
        version = await _latest(session, kind)
        if version is None:
            return None
        return await session.scalar(
            select(content_records.c.body).where(
                content_records.c.kind == kind.value, content_records.c.version == version
            )
        )


def normalised(kind: Kind | str, body: Any) -> Any:
    """`body` validated and dumped as `publish` would store it (Story 11.1)."""
    kind = Kind(kind)
    if kind == Kind.QUESTION_SET:
        _item_types_known(body)
    return _validated(kind, body).model_dump(mode="json")


async def stored_version_of(kind: Kind | str, body: Any) -> int | None:
    """The version of `kind` whose stored body equals `body` (as stored), the newest such; None
    when none does. The content load never publishes a body that is stored already (Story
    11.1), so an older file never supersedes a newer version."""
    kind = Kind(kind)
    async with get_sessionmaker()() as session:
        return await session.scalar(
            select(func.max(content_records.c.version)).where(
                content_records.c.kind == kind.value,
                content_records.c.body == body,
            )
        )


async def question_set(version: int | None) -> tuple[int, QuestionSet]:
    """The question set at `version`, or the latest when None: (version, body) (Story 11.1)."""
    if version is None:
        version = await latest_version(Kind.QUESTION_SET)
    found: QuestionSet = await get(Kind.QUESTION_SET, version)
    return version, found


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


async def debrief_quiz_pin(session: AsyncSession, _class_session: Any) -> dict[str, int]:
    """The lock's pin provider (Story 9.9, AD-23): the Debrief quiz version a Class session uses
    from its lock on, under `SessionRuntime.pins["debrief_quiz"]`."""
    return {"version": await latest_version(Kind.DEBRIEF_QUIZ, session)}


async def narration_templates_pin(session: AsyncSession, _class_session: Any) -> dict[str, int]:
    """The lock's pin provider (Story 9.14, AD-23): the narration-template version a Class
    session uses from its lock on, under `SessionRuntime.pins["narration_templates"]`."""
    return {"version": await latest_version(Kind.NARRATION_TEMPLATES, session)}


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
