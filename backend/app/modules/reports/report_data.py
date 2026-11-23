"""The Student report's content (Story 13.7, FR-58, AD-14, AD-16, AD-18).

`build_report_data(student, class_session, options)` is the only assembler of report content. It
runs in the `reports-single` job, after the api's policy allowed the request, and its output is
stored as a report snapshot that the print route `/print/report/<snapshot_id>` renders. Every part
is read through its owning module's `service.py`: the header through `sessions.report_heading` and
`classes.student_names`, the Completion status through `service.completion_status` (the one
assembler, AD-16).

The report is a header and an ordered list of sections. `SECTIONS` is the registry: each entry
names a section `kind` and its builder. A builder answers the section's model, or None to leave
it out. Story 13.8 adds `game`, Story 13.10 `debrief`, `replay` and `test`, Story 13.11 the AI
assessment (from `options`); each adds its model to `ReportSection`, a builder here, and a
renderer to the print route's registry (`frontend/src/app/print/report/sections.tsx`). The
report holds no other Student's name or free text, and no AI data unless an option asks for it.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.completion import CompletionStatus
from app.modules.classes import service as classes
from app.modules.reports import service
from app.modules.reports.schemas import CompletionStepName
from app.modules.sessions import service as sessions

__all__ = [
    "SECTIONS",
    "CompletionSectionOut",
    "ReportDataOut",
    "ReportOptions",
    "ReportSection",
    "build_report_data",
]

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ReportOptions:
    """What the person downloading chose. Story 13.11 adds the AI assessment section."""

    variant: Literal["standard"] = "standard"


class ReportStepOut(BaseModel):
    """One step of the requirement: whether it counts as done, and whether a Lecturer's correction
    decided it (never the reason)."""

    step: CompletionStepName
    done: bool
    corrected: bool


class CompletionSectionOut(BaseModel):
    """«Fullføring»: the Completion status per step and whether an obligatory requirement is met
    (FR-17, FR-58). The shares are whole percents; `required_share` the one that applies to the
    Student; `share_game` which game the shares come from when there is an Oppfølgingsspill."""

    kind: Literal["completion"] = "completion"
    obligatory: bool
    requirement_met: bool | None
    required_share: int
    ordered_share: int | None
    playout_share: int | None
    share_game: Literal["class", "makeup"] | None
    steps: list[ReportStepOut]


ReportSection = CompletionSectionOut
"""Every section model. Story 13.8 turns this into a union discriminated by `kind`
(`Annotated[CompletionSectionOut | GameSectionOut, Field(discriminator="kind")]`)."""


class ReportDatesOut(BaseModel):
    """The Class session's dates, with the Student's own Debrief and Test deadlines."""

    start_at: AwareDatetime | None
    play_deadline: AwareDatetime | None
    debrief_deadline: AwareDatetime | None
    test_deadline: AwareDatetime | None


class ReportDataOut(BaseModel):
    """A Student report's content, as the print route reads it from its snapshot (AD-18)."""

    schema_version: Literal[1] = SCHEMA_VERSION
    generated_at: AwareDatetime
    student_name: str
    class_name: str
    session_number: int
    dates: ReportDatesOut
    sections: list[ReportSection]


@dataclass(frozen=True)
class SectionContext:
    """What a section builder reads from: the Student, the Class session, the options, the
    Completion status, and the open read-only session."""

    s: AsyncSession
    user_id: uuid.UUID
    class_session_id: uuid.UUID
    options: ReportOptions
    completion: CompletionStatus


SectionBuilder = Callable[[SectionContext], Awaitable[ReportSection | None]]


async def _completion_section(ctx: SectionContext) -> CompletionSectionOut:
    found = ctx.completion
    return CompletionSectionOut(
        obligatory=found.obligatory,
        requirement_met=found.requirement_met,
        required_share=found.required_share,
        ordered_share=found.ordered_share,
        playout_share=found.playout_share,
        share_game=found.share_game,
        steps=[
            ReportStepOut(step=step.step, done=step.done, corrected=step.corrected)
            for step in found.steps
        ],
    )


SECTIONS: tuple[tuple[str, SectionBuilder], ...] = (("completion", _completion_section),)
"""The report's sections in reading order, by `kind` (see the module docstring)."""


class NotReportable(Exception):
    """The Student or the Class session is not (or no longer) one reports count: nothing built."""


async def build_report_data(
    s: AsyncSession,
    user_id: uuid.UUID,
    class_session_id: uuid.UUID,
    options: ReportOptions,
    *,
    now: datetime,
) -> ReportDataOut:
    """The Student report of `user_id` in the Class session, generated at `now`. Raises
    `NotReportable` when the Class session is gone, the Student is not in the Class now, or
    reports leave them out (`scope.reporting_students`)."""
    heading = await sessions.report_heading(s, class_session_id, user_id)
    if heading is None:
        raise NotReportable
    names = await classes.student_names(heading.class_id, [user_id], session=s)
    if user_id not in names:
        raise NotReportable
    completion = await service.completion_status(user_id, class_session_id, session=s)
    if completion is None:
        raise NotReportable
    ctx = SectionContext(
        s=s,
        user_id=user_id,
        class_session_id=class_session_id,
        options=options,
        completion=completion,
    )
    sections = [built for _, build in SECTIONS if (built := await build(ctx)) is not None]
    return ReportDataOut(
        generated_at=now,
        student_name=names[user_id],
        class_name=heading.class_name,
        session_number=heading.number,
        dates=ReportDatesOut(
            start_at=heading.start_at,
            play_deadline=heading.play_deadline,
            debrief_deadline=heading.debrief_deadline,
            test_deadline=heading.test_deadline,
        ),
        sections=sections,
    )
