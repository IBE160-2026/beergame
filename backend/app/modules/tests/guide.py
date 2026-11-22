"""A Class session's Scoring guide: «Sensorveiledning» (Story 11.2, FR-81, FR-18, FR-66, AD-12,
AD-23, AD-27).

The Scoring guide is an immutable versioned record in `content` (kind `scoring_guide`): one fixed
five-step scale and, per long-answer question and Adapted item template, its descriptive guide
text and 5 to 8 coded criteria. A Class session reads the latest default until a Lecturer edits
it; a save («Lagre sensorveiledning») publishes a new version made for that Class session, with
only the descriptive texts changed (the criteria, the scale and the titles are read-only in v1),
through the same validation as the content load (`content.normalised`). The earlier version is
never changed. `test_scoring_guides` points the Class session at the version in force and keeps
the default it derives from (`base_id`): a question whose text differs from it is «Endret».

A save is for the Class's owners (`scoring_guide.change`) until the original Test deadline
(`sessions.lock_for_scoring_guide`, 409 `scoring_guide_locked`), in one transaction holding the
Class session's row lock, with an audit row (ids only) and `session:<id>`. At the Test deadline
`sessions.lock_test` runs `pin_guide` (registered with `sessions`), which pins the version in
force, once. Whether a version is checked by a Control test is asked of `content.is_checked` only.
`copy_guide`, registered with `sessions`, carries an edited version into a Class session made from
this one by its version id (FR-66).

`sessions` never imports this module: it registers itself there, and `ops.sweep` and the app
import it so every Test-deadline lock pins the guide."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import structlog
from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content import service as content
from app.modules.sessions import service as sessions
from app.modules.tests.models import test_scoring_guides
from app.modules.tests.schemas import (
    GuideCriterionOut,
    GuideQuestionOut,
    ScaleStepOut,
    ScoringGuideIn,
    ScoringGuideOut,
)
from app.platform import audit, authz, events
from app.platform.db import get_sessionmaker

__all__ = [
    "GUIDE_EDITED",
    "InForce",
    "UnknownQuestions",
    "copy_guide",
    "in_force",
    "pin_guide",
    "read_block",
    "save",
]

log = structlog.get_logger(__name__)

GUIDE_EDITED = "scoring_guide.edited"
"""The audit action of a saved Scoring guide edit (Story 11.2)."""

CHANGE = "scoring_guide.change"


class UnknownQuestions(Exception):
    """The save names a question the guide does not have, or a text the Scoring guide record
    refuses (422 `validation_error`); `fields` says which, by question id."""

    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__(fields)
        self.fields = fields


@dataclass(frozen=True)
class InForce:
    """The Scoring guide in force for a Class session: the version, the default it derives from,
    and when the Test-deadline lock pinned it (None before)."""

    record: content.ScoringGuideRecord
    base: content.ScoringGuideRecord
    pinned_at: datetime | None

    @property
    def edited(self) -> bool:
        return self.record.id != self.base.id


async def _row(
    s: AsyncSession, class_session_id: uuid.UUID, *, lock: bool = False
) -> Mapping[str, Any] | None:
    statement = select(test_scoring_guides).where(
        test_scoring_guides.c.class_session_id == class_session_id
    )
    if lock:
        statement = statement.with_for_update()
    return (await s.execute(statement)).mappings().one_or_none()


async def in_force(s: AsyncSession, class_session_id: uuid.UUID) -> InForce:
    """The Scoring guide in force: the session's row when it has one, else the latest default."""
    row = await _row(s, class_session_id)
    if row is None:
        latest = await content.latest_scoring_guide(s)
        return InForce(record=latest, base=latest, pinned_at=None)
    record = await content.scoring_guide_record(s, row["scoring_guide_id"])
    base = (
        record
        if row["base_id"] == record.id
        else await content.scoring_guide_record(s, row["base_id"])
    )
    return InForce(record=record, base=base, pinned_at=row["pinned_at"])


async def pin_guide(s: AsyncSession, class_session: Mapping[str, Any], at: datetime) -> bool:
    """`sessions.lock_test`'s pinner (Story 11.2, FR-18, AD-23): the Scoring guide in force at the
    original Test deadline, in the lock's transaction; a session that never edited it is pinned on
    the latest default. True when this call pinned it; a second call changes nothing."""
    class_session_id = class_session["id"]
    row = await _row(s, class_session_id, lock=True)
    if row is not None:
        if row["pinned_at"] is not None:
            return False
        await s.execute(
            update(test_scoring_guides)
            .where(test_scoring_guides.c.class_session_id == class_session_id)
            .values(pinned_at=at)
        )
        return True
    latest = await content.latest_scoring_guide(s)
    await s.execute(
        insert(test_scoring_guides).values(
            class_session_id=class_session_id,
            scoring_guide_id=latest.id,
            base_id=latest.id,
            pinned_at=at,
            updated_by=None,
            updated_at=at,
        )
    )
    return True


async def copy_guide(
    s: AsyncSession, source: Mapping[str, Any], target_id: uuid.UUID, now: datetime
) -> None:
    """`sessions.copy_from`'s copier (Story 11.2, FR-66): an edited Scoring guide is carried over
    by its version id with the default it derives from, so it stays «Endret» and keeps its checked
    status; never its pin. A source on a default copies nothing: the copy reads the latest
    default."""
    row = await _row(s, source["id"])
    if row is None or row["scoring_guide_id"] == row["base_id"]:
        return
    await s.execute(
        insert(test_scoring_guides).values(
            class_session_id=target_id,
            scoring_guide_id=row["scoring_guide_id"],
            base_id=row["base_id"],
            pinned_at=None,
            updated_by=None,
            updated_at=now,
        )
    )


async def _out(
    s: AsyncSession,
    found: InForce,
    *,
    model_config_id: uuid.UUID | None,
    open_: bool,
    can_change: bool,
) -> ScoringGuideOut:
    standard = {question.id: question.guide for question in found.base.guide.questions}
    latest = await content.latest_scoring_guide(s)
    return ScoringGuideOut(
        version_id=found.record.id,
        version=found.record.version,
        draft=found.record.guide.status == "draft",
        edited=found.edited,
        outdated=found.edited and found.pinned_at is None and found.base.id != latest.id,
        checked=await content.is_checked(found.record.id, model_config_id),
        pinned=found.pinned_at is not None,
        open=open_,
        can_change=can_change,
        scale=[ScaleStepOut(step=step.step, label=step.label) for step in found.record.guide.scale],
        questions=[
            GuideQuestionOut(
                id=question.id,
                kind=question.kind,
                title=question.title,
                guide=question.guide,
                standard_guide=standard.get(question.id, question.guide),
                changed=question.guide != standard.get(question.id),
                criteria=[
                    GuideCriterionOut(code=c.code, text=c.text, weight=c.weight)
                    for c in question.criteria
                ],
            )
            for question in found.record.guide.questions
        ],
    )


async def read_block(
    user: authz.Principal, class_session_id: uuid.UUID, now: datetime
) -> ScoringGuideOut | None:
    """The «Sensorveiledning» block for the Class's staff (`class_sessions.read`): the Scoring
    guide in force, the pinned one once the Test-deadline lock has run. None for every other
    caller."""
    found = await sessions.question_set_session(user, class_session_id, CHANGE)
    if found is None:
        return None
    async with get_sessionmaker()() as s:
        guide = await in_force(s, class_session_id)
        return await _out(
            s,
            guide,
            model_config_id=found.row["model_config_id"],
            open_=guide.pinned_at is None and not sessions.test_deadline_reached(found.row, now),
            can_change=found.can_change,
        )


def _edited_body(found: InForce, wanted: ScoringGuideIn) -> dict[str, Any] | None:
    """The body of the new version: the one in force with the wanted texts laid over; None when
    no text changes. Raises `UnknownQuestions` for a question the guide does not have."""
    body = found.record.guide.model_dump(mode="json")
    questions = {question["id"]: question for question in body["questions"]}
    unknown = {qid: "unknown_question" for qid in wanted.guides if qid not in questions}
    if unknown:
        raise UnknownQuestions(unknown)
    changed = False
    for qid, text in wanted.guides.items():
        if questions[qid]["guide"] != text:
            questions[qid]["guide"] = text
            changed = True
    return body if changed else None


def _fields_of(invalid: ValidationError, body: Mapping[str, Any]) -> dict[str, str]:
    """The question ids a refused body's errors point at (`questions.<i>…`), else `guides`."""
    ids = [question["id"] for question in body["questions"]]
    fields: dict[str, str] = {}
    for error in invalid.errors():
        loc = error["loc"]
        if len(loc) >= 2 and loc[0] == "questions" and isinstance(loc[1], int):
            fields[ids[loc[1]]] = "invalid"
    return fields or {"guides": "invalid"}


async def save(
    user: authz.Principal, class_session_id: uuid.UUID, wanted: ScoringGuideIn, now: datetime
) -> ScoringGuideOut | None:
    """«Lagre sensorveiledning» (Story 11.2, FR-81, AD-15, AD-23): a new Scoring guide version
    made for the Class session from the one in force with the changed texts, validated as the
    content load validates, in one transaction holding the Class session's row lock, with one
    audit row (ids only) and `session:<id>`. An unchanged text stores nothing. None (403) for
    anyone but an owner of the Class. Raises `sessions.ScoringGuideLocked` from the original
    Test deadline, `classes.ClassArchived`, `UnknownQuestions`; nothing is stored then."""
    found = await sessions.question_set_session(user, class_session_id, CHANGE)
    if found is None or not found.may_change:
        return None
    async with get_sessionmaker().begin() as s:
        try:
            await sessions.lock_for_scoring_guide(s, class_session_id, now=now)
        except LookupError:  # gone since it was read: as for one never there
            return None
        guide = await in_force(s, class_session_id)
        if guide.pinned_at is not None:
            raise sessions.ScoringGuideLocked({"scoring_guide": "locked"})
        body = _edited_body(guide, wanted)
        if body is not None:
            try:
                record_id, version = await content.publish_in(
                    s, content.Kind.SCORING_GUIDE, body, class_session_id=class_session_id
                )
            except content.ContentRejected as rejected:
                raise UnknownQuestions({"guides": rejected.code}) from None
            except ValidationError as invalid:
                raise UnknownQuestions(_fields_of(invalid, body)) from None
            values = {
                "scoring_guide_id": record_id,
                "base_id": guide.base.id,
                "updated_by": user.id,
                "updated_at": now,
            }
            await s.execute(
                insert(test_scoring_guides)
                .values(class_session_id=class_session_id, **values)
                .on_conflict_do_update(index_elements=["class_session_id"], set_=values)
            )
            await audit.record(
                s,
                user.id,
                GUIDE_EDITED,
                {"class_session_id": class_session_id},
                {"scoring_guide_id": str(record_id), "version": version},
                now,
            )
            await events.emit(s, "session", str(class_session_id))
            log.info(
                "scoring_guide_edited",
                class_session_id=str(class_session_id),
                version=version,
                questions=len(wanted.guides),
            )
    return await read_block(user, class_session_id, now)


# Every Test-deadline lock from now on pins the Scoring guide in force (AD-23), and «Lag kopi»
# carries an edited one over (FR-66).
sessions.register_test_pinner(pin_guide)
sessions.register_copier(copy_guide)
