"""The Student report's content (Story 13.7, FR-58, AD-14, AD-16, AD-18).

`build_report_data(student, class_session, options)` is the only assembler of report content. It
runs in the `reports-single` job, after the api's policy allowed the request, and its output is
stored as a report snapshot that the print route `/print/report/<snapshot_id>` renders. Every part
is read through its owning module's `service.py`: the header through `sessions.report_heading` and
`classes.student_names`, the Completion status through `service.completion_status` (the one
assembler, AD-16).

The report is a header and an ordered list of sections. `SECTIONS` is the registry: each entry
names a section `kind` and its builder. A builder answers the section's model, or None to leave
it out. `completion` (Story 13.7) and `game` (Story 13.8) are built; Story 13.10 adds `debrief`,
`replay` and `test`, Story 13.11 the AI assessment (from `options`); each adds its model to
`AnySection`, a builder here, and a renderer to the print route's registry
(`frontend/src/app/print/report/sections.tsx`). The
report holds no other Student's name or free text, and no AI data unless an option asks for it.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.completion import CompletionStatus
from app.engine.settings import Role
from app.modules.classes import service as classes
from app.modules.games import service as games
from app.modules.games.service import GameStatus, OccupantKind, SeatMark, SeatState
from app.modules.reports import service
from app.modules.reports.schemas import CompletionStepName
from app.modules.sessions import service as sessions

__all__ = [
    "SECTIONS",
    "CompletionSectionOut",
    "AnySection",
    "GameSectionOut",
    "ReportDemandWeekOut",
    "ReportGameOut",
    "ReportGameRoleOut",
    "ReportGameWeekOut",
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


class ReportGameWeekOut(BaseModel):
    """One Role in one opened Week of the chain (Spillinnsikt's read, Story 7.7): its placed
    Order (null for none), stored inventory and backlog, who held the Seat (`student`, `ai`, or
    `free`; never who) and the marks of the one AD-15 mapping (`games.service.seat_mark`)."""

    week: int
    order: int | None
    inventory: int
    backlog: int
    holder: Literal["student", "ai", "free"]
    marks: list[SeatMark]


class ReportGameRoleOut(BaseModel):
    """One Role of the chain, by Role only (never a name, AD-14), its Weeks in order."""

    role: Role
    weeks: list[ReportGameWeekOut]
    first_large_order_week: int | None


class ReportDemandWeekOut(BaseModel):
    week: int
    demand: int


class ReportGameOut(BaseModel):
    """The Student's game (`games.service.student_game`) as the report documents it (FR-58):
    `seat` is the Student's Seat in the game's last opened Week (its `history` the earlier
    Weeks), `last_order` that Week's Order; `roles` and `demand` the whole chain in chain order
    (the Role serving the customer first), as Spillinnsikt reads it (FR-34, AD-15)."""

    makeup: bool
    game_number: int | None
    role: Role
    weeks_played: int
    weeks_total: int | None
    finished: bool
    total_cost: Decimal
    seat: SeatState
    last_order: int | None
    demand: list[ReportDemandWeekOut]
    roles: list[ReportGameRoleOut]


class GameSectionOut(BaseModel):
    """«Klassespill» or «Oppfølgingsspill» (Story 13.8): `game` null when the Student has no
    game with an opened Week; the section then says so."""

    kind: Literal["game"] = "game"
    game: ReportGameOut | None


AnySection = CompletionSectionOut | GameSectionOut
ReportSection = Annotated[AnySection, Field(discriminator="kind")]
"""Every section model, discriminated by `kind`. Story 13.10 adds its own."""


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


SectionBuilder = Callable[[SectionContext], Awaitable[AnySection | None]]


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


_AI = frozenset({OccupantKind.LLM, OccupantKind.RULE_BASED, OccupantKind.SCRIPTED})


def _holder(kind: object) -> Literal["student", "ai", "free"]:
    if kind == OccupantKind.STUDENT:
        return "student"
    return "ai" if kind in _AI else "free"


async def _game_section(ctx: SectionContext) -> GameSectionOut:
    """The Student's game, read through `games.service`: `student_game` (a finished
    Oppfølgingsspill wins over the Class game, Story 13.5), the Seat's `seat_state` in its last
    opened Week, and the chain from `game_insight`, Spillinnsikt's read (Story 7.7). Ids and
    names never leave this function: other Seats are told apart by Role only (FR-58)."""
    found = await games.student_game(ctx.s, ctx.user_id, ctx.class_session_id)
    if found is None:
        return GameSectionOut(game=None)
    insight = await games.game_insight(ctx.s, found.game_id)
    own = (
        None
        if insight is None
        else next((role for role in insight.roles if role.role == found.role), None)
    )
    if insight is None or own is None or not own.weeks:
        return GameSectionOut(game=None)
    seat = await games.seat_state(str(found.game_id), found.role, session=ctx.s)
    last = own.weeks[-1]
    return GameSectionOut(
        game=ReportGameOut(
            makeup=found.makeup,
            game_number=found.number,
            role=Role(found.role),
            weeks_played=sum(1 for week in own.weeks if week.order is not None),
            weeks_total=insight.weeks_total,
            finished=insight.status == GameStatus.FINISHED and insight.end_reason is None,
            total_cost=seat.total_cost,
            seat=seat,
            last_order=last.order,
            demand=[
                ReportDemandWeekOut(week=week, demand=demand) for week, demand in insight.demand
            ],
            roles=[
                ReportGameRoleOut(
                    role=Role(role.role),
                    first_large_order_week=role.first_large_order_week,
                    weeks=[
                        ReportGameWeekOut(
                            week=week.week,
                            order=week.order,
                            inventory=week.inventory,
                            backlog=week.backlog,
                            holder=_holder(week.occupant_kind),
                            marks=list(week.marks),
                        )
                        for week in role.weeks
                    ],
                )
                for role in insight.roles
            ],
        )
    )


SECTIONS: tuple[tuple[str, SectionBuilder], ...] = (
    ("completion", _completion_section),
    ("game", _game_section),
)
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
