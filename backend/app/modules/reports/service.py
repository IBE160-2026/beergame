"""The one Completion assembler and the funnel caller (Story 13.1, FR-17, AD-16, AD-25).

Every reader of a Student's Completion status (Hjem now; the Studentside, the Completion export
and the Student report later) calls `completion_status`, which gathers the inputs through the
`progress`, `sessions`, `games`, `debrief` and `tests` services and calls the pure
`analysis.completion`. The Oversikt's Trakt comes through `funnel`, which passes the reporting
Students to `progress.funnel`. Both read through `reports.scope`. `sessions` reaches them through
the providers registered at the end of this module, since `reports` imports `sessions`.
"""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.completion import (
    CompletionSettings,
    CompletionStatus,
    Correction,
    DecisionLogSummary,
    LoggedWeek,
    StepInputs,
    completion,
)
from app.modules.debrief import service as debrief
from app.modules.games import service as games
from app.modules.games.service import Purpose
from app.modules.identity import service as identity
from app.modules.progress import service as progress
from app.modules.reports import repo, scope
from app.modules.sessions import service as sessions
from app.modules.tests import service as tests
from app.platform import storage
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

__all__ = ["completion_status", "completion_statuses", "funnel", "requirement_not_met"]


@asynccontextmanager
async def _reading(within: AsyncSession | None) -> AsyncIterator[AsyncSession]:
    if within is not None:
        yield within
        return
    async with get_sessionmaker()() as session:
        yield session


def _required_parts() -> tuple[str, ...]:
    raw = get_settings().completion_test_required_parts
    return tuple(part.strip() for part in raw.split(",") if part.strip())


async def completion_status(
    user_id: uuid.UUID, class_session_id: uuid.UUID, *, session: AsyncSession | None = None
) -> CompletionStatus | None:
    """The Student's Completion status in the Class session (FR-17); None for an unknown Class
    session or a User reports do not count there (`reports.scope.reporting_students`). A
    Lecturer's corrections (Story 13.3) are passed oldest first, so the latest of a step applies.
    The reads owned by `progress`, `sessions` and `games` run in `session` when given (Story 13.3:
    the status before a correction, in its transaction)."""
    async with _reading(session) as s:
        terms = await sessions.completion_terms(s, class_session_id)
        if terms is None or user_id not in await scope.reporting_students(s, class_session_id):
            return None
        return await _status(s, user_id, class_session_id, terms)


async def _status(
    s: AsyncSession,
    user_id: uuid.UUID,
    class_session_id: uuid.UUID,
    terms: sessions.CompletionTerms,
) -> CompletionStatus:
    """`completion_status` for a Student the caller found in the reporting scope."""
    events = await progress.step_events(s, user_id, class_session_id)
    corrected = await progress.corrections(s, user_id, class_session_id)
    adjustment = await sessions.get_adjustment(s, class_session_id, user_id)
    log = None
    # The Class game itself: a finished Oppfølgingsspill is the Student's game (Story 13.5),
    # but Completion takes its log once, below.
    game = await games.class_game_of(s, user_id, class_session_id)
    if game is not None:
        counted = await scope.reporting_games(s, class_session_id, [Purpose.CLASS])
        if any(each.game_id == game.game_id for each in counted):
            log = await _log_of(s, game.game_id, game.role)
    # Story 13.4: the Oppfølgingsspill's Decision log beside the Class game's, finished or
    # partly played; a Week it never played counts as not ordered.
    makeup_log = None
    makeup = await repo.makeup_of(s, user_id, class_session_id)
    if makeup is not None:
        counted = await scope.reporting_games(s, class_session_id, [Purpose.MAKEUP])
        own = await games.own_game(s, user_id, makeup.game_id)
        # Not before it has started: a share of 0 % in a game not yet played says nothing.
        started = (await games.play_status(s, makeup.game_id)).status in ("running", "finished")
        if own is not None and started and any(each.game_id == makeup.game_id for each in counted):
            makeup_log = await _log_of(s, makeup.game_id, own.role)
    test_status = await tests.attempt_status(user_id, class_session_id)
    config = get_settings()
    return completion(
        StepInputs(
            events={step.value: at for step, at in events.items()},
            explanation_length=await debrief.explanation_length(user_id, class_session_id),
            test_status=test_status,
            test_parts=(
                await tests.parts_with_content(user_id, class_session_id)
                if test_status == "auto_submitted"
                else None
            ),
        ),
        log,
        tuple(Correction(step=each.step, done=each.done, at=each.at) for each in corrected),
        CompletionSettings(
            obligatory=terms.obligatory,
            required_share=terms.required_share,
            adjusted_share=None if adjustment is None else adjustment.share_percent,
            explanation_min_length=config.completion_explanation_min_length,
            test_required_parts=_required_parts(),
        ),
        makeup_log,
    )


async def requirement_not_met(
    class_session_id: uuid.UUID, *, session: AsyncSession | None = None
) -> list[tuple[uuid.UUID, CompletionStatus]]:
    """The reporting Students of an Obligatory class session who have not met the requirement now,
    each with their Completion status, by id (Story 13.6, FR-17): `completion_status` over
    `scope.reporting_students`, so the Oversikt's count, the Meldingsskjema's table and the
    Message's recipients judge it alike. Empty at once for a Class session that is not obligatory
    or does not exist."""
    async with _reading(session) as s:
        terms = await sessions.completion_terms(s, class_session_id)
        if terms is None or not terms.obligatory:
            return []
        found = []
        # The scope is read once, not again per Student as `completion_status` reads it.
        for user_id in await scope.reporting_students(s, class_session_id):
            status = await _status(s, user_id, class_session_id, terms)
            if status.requirement_met is False:
                found.append((user_id, status))
        return found


async def completion_statuses(
    class_session_id: uuid.UUID, *, session: AsyncSession | None = None
) -> dict[uuid.UUID, CompletionStatus]:
    """The Completion status of every reporting Student of the Class session, by id (Story 13.14,
    the Completion export, FR-60, AD-16): `completion_status` over `scope.reporting_students`,
    read once, so the file agrees with the Studentside, Hjem and the funnel. Empty for a Class
    session that does not exist."""
    async with _reading(session) as s:
        terms = await sessions.completion_terms(s, class_session_id)
        if terms is None:
            return {}
        return {
            user_id: await _status(s, user_id, class_session_id, terms)
            for user_id in await scope.reporting_students(s, class_session_id)
        }


async def _log_of(s: AsyncSession, game_id: uuid.UUID, role: str) -> DecisionLogSummary | None:
    seat = await games.seat_log(s, game_id, role)
    if seat is None:
        return None
    return DecisionLogSummary(
        weeks=seat.weeks,
        guided_weeks=seat.guided_weeks,
        rows=tuple(LoggedWeek(*row) for row in seat.rows),
    )


async def funnel(
    class_session_id: uuid.UUID, *, session: AsyncSession | None = None
) -> progress.Funnel:
    """The Trakt of the Class session (Story 7.6) over `scope.reporting_students`: it counts step
    events, never the requirement; how many Students met it is `completion_status`'s to say."""
    async with _reading(session) as s:
        students = await scope.reporting_students(s, class_session_id)
        return await progress.funnel(s, class_session_id, students)


async def _funnel_in(session: AsyncSession, class_session_id: uuid.UUID) -> progress.Funnel:
    return await funnel(class_session_id, session=session)


sessions.register_completion(completion_status, _funnel_in)
# Story 12.5's list of AI assessments counts the Students reports count.
sessions.register_reporting_students(scope.reporting_students)
# Story 13.4: Hjem and the `makeup_given` mail find the Student's Oppfølgingsspill here.
sessions.register_makeup_game(repo.makeup_game_of)


async def _erase_reports(user_id: uuid.UUID, now: datetime) -> None:
    """The erasure of a Student (Story 15.2, FR-76, AD-14), before the erasure's transaction while
    the Roster still names their Classes: delete the PDFs of every report about them and then
    the rows (their snapshots go with them); delete every stored ZIP of their Class sessions,
    which holds their report, and clear its path. Objects go before rows, so a storage failure
    leaves the rows for a repeat; every part is idempotent."""
    del now
    files = storage.get_storage()
    async with get_sessionmaker().begin() as s:
        reports = await repo.report_paths_of(s, user_id)
        zips = await repo.zip_paths_of(s, user_id)
    for path in reports + zips:
        await files.delete(storage.REPORTS, path)
    async with get_sessionmaker().begin() as s:
        await repo.delete_report_requests_of(s, user_id)
        await repo.clear_zip_paths(s, zips)


identity.register_erasure_preparation(
    "reports", {"report_requests", "report_snapshots"}, _erase_reports
)
identity.register_erasure_step(
    "completion", {"completion_corrections"}, progress.delete_corrections_of
)
