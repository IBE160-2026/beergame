"""Publish and read immutable, versioned content (Story 6.3, Story 9.1, Story 11.2, AD-23).

A record is never changed: `publish` stores a new version (the next number of its kind) and a
trigger refuses every UPDATE. A default is a record without a Class session; a Lecturer's edited
Scoring guide (Story 11.2) is a version made for one Class session (`publish_in` with
`class_session_id`), which takes the kind's next number but is never the latest default. The
lock pins the version a Class session uses (`starting_task_pin`, `detected_patterns_pin`,
`sentence_templates_pin`, `reflection_questions_pin` and `moment_templates_pin`,
`debrief_quiz_pin` and `narration_templates_pin`, registered by `sessions`); readers ask for
that version, or the latest for a session locked before the pin existed. Whether a Scoring guide
version is checked by a Control test is asked of `is_checked` only (AD-27). This module imports no
feature module."""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content.models import Kind, content_records
from app.modules.content.schemas import (
    CRITERIA_MAX,
    CRITERIA_MIN,
    ITEM_TYPES,
    DebriefQuiz,
    MomentTemplates,
    NarrationTemplates,
    PatternSet,
    QuestionSet,
    ReflectionQuestion,
    ReflectionQuestions,
    ScoringGuide,
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
    "ScoringGuide",
    "ScoringGuideRecord",
    "SentenceTemplates",
    "StartingTask",
    "debrief_quiz",
    "debrief_quiz_pin",
    "detected_patterns",
    "detected_patterns_pin",
    "get",
    "is_checked",
    "latest_body",
    "latest_scoring_guide",
    "stored_version_of",
    "latest_version",
    "moment_templates",
    "moment_templates_pin",
    "narration_templates",
    "narration_templates_pin",
    "normalised",
    "pinned_version",
    "publish",
    "publish_in",
    "question_set",
    "reflection_questions",
    "reflection_questions_pin",
    "scoring_guide_record",
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
    | ScoringGuide
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
    | type[QuestionSet]
    | type[ScoringGuide],
] = {
    Kind.STARTING_TASK: StartingTask,
    Kind.DETECTED_PATTERNS: PatternSet,
    Kind.SENTENCE_TEMPLATES: SentenceTemplates,
    Kind.REFLECTION_QUESTIONS: ReflectionQuestions,
    Kind.MOMENT_TEMPLATES: MomentTemplates,
    Kind.DEBRIEF_QUIZ: DebriefQuiz,
    Kind.NARRATION_TEMPLATES: NarrationTemplates,
    Kind.QUESTION_SET: QuestionSet,
    Kind.SCORING_GUIDE: ScoringGuide,
}


class ContentNotFound(Exception):
    """No record of that kind and version."""


class ContentRejected(Exception):
    """A body refused with a stable code (Story 11.1): `unknown_item_type` for a question-set
    item whose type the product does not know, `starting_task_items_missing` for a question set
    that does not reference every item of the latest Starting task, and (Story 11.2)
    `criteria_count` for a Scoring guide question with fewer than 5 or more than 8 criteria.
    Nothing is stored."""

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


def _criteria_counted(body: Any) -> None:
    """A Scoring guide question with fewer than 5 or more than 8 criteria is refused by its own
    code, before the schema (Story 11.2, FR-81)."""
    if not isinstance(body, dict) or not isinstance(body.get("questions"), list):
        return  # the schema refuses it (`invalid_record`)
    for question in body["questions"]:
        if not isinstance(question, dict) or not isinstance(question.get("criteria"), list):
            continue
        count = len(question["criteria"])
        if not CRITERIA_MIN <= count <= CRITERIA_MAX:
            raise ContentRejected(
                "criteria_count",
                f"question {question.get('id')!r} has {count} criteria, not "
                f"{CRITERIA_MIN} to {CRITERIA_MAX}",
            )


def _checked_first(kind: Kind, body: Any) -> None:
    """The checks with a stable code of their own, before the schema."""
    if kind == Kind.QUESTION_SET:
        _item_types_known(body)
    elif kind == Kind.SCORING_GUIDE:
        _criteria_counted(body)


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
    """Validate `body` and store it as the next version of `kind`, a default; the new version
    number."""
    async with get_sessionmaker().begin() as session:
        _, version = await publish_in(session, kind, body)
    return version


async def publish_in(
    session: AsyncSession,
    kind: Kind | str,
    body: Any,
    *,
    class_session_id: uuid.UUID | None = None,
) -> tuple[uuid.UUID, int]:
    """Validate `body` and store it as the next version of `kind` in the caller's transaction:
    (its id, its version number). With `class_session_id` it is a version made for that Class
    session (a Lecturer's edited Scoring guide, Story 11.2), which is never the latest default.
    Raises `ContentRejected` or `pydantic.ValidationError`; nothing is stored then."""
    kind = Kind(kind)
    _checked_first(kind, body)
    validated = _validated(kind, body)
    stored = validated.model_dump(mode="json")
    # One publisher of a kind at a time, so two never take the same number.
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"content:{kind}"}
    )
    if isinstance(validated, QuestionSet):
        await _starting_task_referenced(session, validated)
    newest = await session.scalar(
        select(func.max(content_records.c.version)).where(content_records.c.kind == kind.value)
    )
    version = (newest or 0) + 1
    record_id = uuid.uuid7()
    await session.execute(
        insert(content_records).values(
            id=record_id,
            kind=kind.value,
            version=version,
            body=stored,
            class_session_id=class_session_id,
        )
    )
    return record_id, version


async def _latest(session: AsyncSession, kind: Kind) -> int | None:
    """The newest default of `kind` (a version made for one Class session never is)."""
    return await session.scalar(
        select(func.max(content_records.c.version)).where(
            content_records.c.kind == kind.value, content_records.c.class_session_id.is_(None)
        )
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
    """`body` validated and dumped as `publish` would store it (Story 11.1): the load's checks,
    which a Lecturer's Scoring guide save runs too (Story 11.2)."""
    kind = Kind(kind)
    _checked_first(kind, body)
    return _validated(kind, body).model_dump(mode="json")


async def stored_version_of(kind: Kind | str, body: Any) -> int | None:
    """The default version of `kind` whose stored body equals `body` (as stored), the newest
    such; None when none does. The content load never publishes a body that is stored already
    (Story 11.1), so an older file never supersedes a newer version."""
    kind = Kind(kind)
    async with get_sessionmaker()() as session:
        return await session.scalar(
            select(func.max(content_records.c.version)).where(
                content_records.c.kind == kind.value,
                content_records.c.class_session_id.is_(None),
                content_records.c.body == body,
            )
        )


async def question_set(version: int | None) -> tuple[int, QuestionSet]:
    """The question set at `version`, or the latest when None: (version, body) (Story 11.1)."""
    if version is None:
        version = await latest_version(Kind.QUESTION_SET)
    found: QuestionSet = await get(Kind.QUESTION_SET, version)
    return version, found


@dataclass(frozen=True)
class ScoringGuideRecord:
    """One stored Scoring guide version (Story 11.2): its id (what a pin, a copy and
    `is_checked` name), its number, the Class session it was made for (None for a default) and
    its body."""

    id: uuid.UUID
    version: int
    class_session_id: uuid.UUID | None
    guide: ScoringGuide


_GUIDE_COLUMNS = (
    content_records.c.id,
    content_records.c.version,
    content_records.c.class_session_id,
    content_records.c.body,
)


def _guide_record(row: Any) -> ScoringGuideRecord:
    return ScoringGuideRecord(
        id=row.id,
        version=row.version,
        class_session_id=row.class_session_id,
        guide=ScoringGuide.model_validate(row.body),
    )


async def scoring_guide_record(session: AsyncSession, record_id: uuid.UUID) -> ScoringGuideRecord:
    """The Scoring guide version with this id (Story 11.2); `ContentNotFound` when none."""
    row = (
        await session.execute(
            select(*_GUIDE_COLUMNS).where(
                content_records.c.id == record_id,
                content_records.c.kind == Kind.SCORING_GUIDE.value,
            )
        )
    ).first()
    if row is None:
        raise ContentNotFound(f"scoring_guide {record_id}")
    return _guide_record(row)


async def latest_scoring_guide(session: AsyncSession) -> ScoringGuideRecord:
    """The newest default Scoring guide (Story 11.2); `ContentNotFound` when none is stored."""
    version = await latest_version(Kind.SCORING_GUIDE, session)
    row = (
        await session.execute(
            select(*_GUIDE_COLUMNS).where(
                content_records.c.kind == Kind.SCORING_GUIDE.value,
                content_records.c.version == version,
            )
        )
    ).one()
    return _guide_record(row)


async def is_checked(
    scoring_guide_version_id: uuid.UUID, model_config_id: uuid.UUID | None
) -> bool:
    """Whether a Control test has checked this Scoring guide version with this model config
    (Story 11.2, FR-81, AD-27): the only place that answers it. The `checked` record is created
    and written by the Control test in Epic 12; until then no version is checked."""
    del scoring_guide_version_id, model_config_id
    return False


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
