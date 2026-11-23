"""The stored aggregates of Cross-class statistics (Story 14.3, FR-65, AD-9, AD-10, AD-13, AD-14).

`write_aggregate(class_session_id)` stores one anonymised aggregate per Class session in
`class_aggregates` (a header: when it was written, its group sizes and the keys a comparison must
hold equal) and `class_aggregate_measures` (one scalar figure per measure code). The figures are
the Klasserapport's own (`class_report.report_parts`, `class_report_learning.learning_of`), so
the comparison and the live report agree; scores are Core-only, never the total and never a
letter. A measure whose group holds fewer than `MIN_GROUP` Students is stored as withheld, with
no value. Nothing stored names a Student, a Seat or a Game.

When it runs:

- the sweep's due action `reports.write_aggregate` finds each course Class session whose latest
  effective Test deadline (Story 13.9's value) has passed, with no attempt still open, whose
  deletion date has not come, and whose aggregate is missing or older than its latest AI
  assessment, finished game, stored facts set or plausibility rating
  (`games.latest_report_changes`), unless its job failed `MAX_FAILURES` times; it defers
  `reports.write_aggregate` on `reports-bulk`, one job per Class session by its queueing lock,
  ids only. The job replaces that Class session's rows;
- retention (Story 15.3) runs `ensure_aggregate` first through `identity`'s gate: it writes one
  only when none exists, so a retention run interrupted half-way never rewrites the aggregate
  over half-erased data.

A Control test Class session gets none (AD-13, AD-27), and a Class session whose Student data
retention deleted is never written again. The previous Class session's stored median chain Total
cost is the Kostnadsfordeling's «Fjoråret» (UX-DR51), read through `previous_median`.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import structlog
from sqlalchemy import delete, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assessment import service as assessment
from app.modules.classes import service as classes
from app.modules.content import service as content
from app.modules.games import service as games
from app.modules.identity import service as identity
from app.modules.reports import class_report, class_report_learning, scope
from app.modules.reports.class_report_learning_schemas import ClassLearningOut
from app.modules.reports.models import class_aggregate_measures, class_aggregates
from app.modules.sessions import service as sessions
from app.modules.tests import service as tests
from app.platform import auth, jobs
from app.platform import retention as retention_rule
from app.platform.db import get_sessionmaker

__all__ = [
    "CHAIN_MEDIAN",
    "MAX_FAILURES",
    "MIN_GROUP",
    "WRITE_TASK",
    "Measure",
    "aggregate_key",
    "defer_due",
    "due_sessions",
    "ensure_aggregate",
    "measures",
    "previous_median",
    "write_aggregate",
]

log = structlog.get_logger(__name__)

MAX_FAILURES = 3
"""A Class session whose aggregate job failed this many times is not deferred again (each failure
is logged), so a job that always fails is not deferred every minute."""
MIN_GROUP = 10
"""The anonymisation threshold (FR-65, AD-14): a measure over fewer Students is withheld."""

WRITE_TASK = "reports.write_aggregate"
CHAIN_MEDIAN = "chain.median"
"""The measure «Fjoråret» marks: the median chain Total cost of the finished Class games."""


def aggregate_key(class_session_id: object) -> str:
    return f"class-aggregate:{class_session_id}"


@dataclass(frozen=True)
class Measure:
    """One figure of an aggregate: its code, how many Students it is over and its value."""

    measure: str
    group_size: int
    value: Decimal


def _add(found: list[Measure], code: str, group: int, value: Decimal | int | None) -> None:
    if value is not None:
        found.append(Measure(code, group, Decimal(value)))


def measures(
    report: class_report.ReportParts,
    learning: ClassLearningOut | None,
    *,
    game_students: int,
    rating_students: dict[str, int] | None = None,
) -> list[Measure]:
    """The measures of a Class session from the Klasserapport's figures (pure): the game measures
    over `game_students` (who held a Seat in the finished Class games), the Trakt and the share
    handed in over the registered Students, each question over the Students whose test held it,
    the Starting task over those who did both, the Core-only subscore over the ready assessments,
    and each AI mode's plausibility ratings over the Students who rated. A figure with no value
    (no game, the AI assessment off) is left out."""
    found: list[Measure] = []
    g = game_students
    cost = report.cost
    if cost is not None:
        _add(found, CHAIN_MEDIAN, g, cost.chain.median)
        _add(found, "chain.lower_quartile", g, cost.chain.lower_quartile)
        _add(found, "chain.upper_quartile", g, cost.chain.upper_quartile)
        _add(found, "chain.holding", g, cost.holding_cost)
        _add(found, "chain.backorder", g, cost.backorder_cost)
        for role in cost.roles:
            _add(found, f"cost.{role.role}.median", g, role.distribution.median)
            _add(found, f"cost.{role.role}.holding", g, role.holding_cost)
            _add(found, f"cost.{role.role}.backorder", g, role.backorder_cost)
    for row in report.amplification:
        if row.distribution is not None:
            _add(found, f"amplification.{row.role}.median", g, row.distribution.median)
    for pattern in report.patterns:
        _add(found, f"pattern.{pattern.pattern}.occurrences", g, pattern.occurrences)
        _add(found, f"pattern.{pattern.pattern}.games", g, pattern.games)
    if report.finished > 0:
        ai = report.ai
        _add(found, "ai.seats_percent", g, ai.ai_percent)
        ordered = sum(game.ordered for game in ai.games)
        _add(
            found,
            "ai.llm_percent",
            g,
            class_report.percent(sum(game.llm for game in ai.games), ordered),
        )
        _add(found, "ai.guard_percent", g, ai.guard_percent)
    registered = next((stage.count for stage in report.funnel if stage.stage == "registered"), 0)
    for stage in report.funnel:
        _add(found, f"funnel.{stage.stage}", registered, stage.count)
    if learning is not None:
        _add(
            found,
            "learning.submitted_percent",
            learning.students,
            class_report.percent(learning.submitted, learning.students),
        )
        for question in learning.questions:
            if question.scoring == "computed":
                _add(found, f"question.{question.id}.percent", question.students, question.percent)
        for item in learning.starting_task.items:
            _add(found, f"starting.{item.number}.start_percent", item.students, item.start_percent)
            _add(found, f"starting.{item.number}.test_percent", item.students, item.test_percent)
        core = learning.ai.core
        if core is not None:
            ready = learning.ai.ready
            _add(found, "core.median", ready, core.median)
            _add(found, "core.lower_quartile", ready, core.lower_quartile)
            _add(found, "core.upper_quartile", ready, core.upper_quartile)
    for mode in report.ratings:
        # Over the Students who rated, not the ratings: one Student may rate a Class game and a
        # Replay.
        raters = (rating_students or {}).get(mode.ai_mode, 0)
        _add(found, f"rating.{mode.ai_mode}.median", raters, mode.median)
        _add(found, f"rating.{mode.ai_mode}.count", raters, mode.count)
    return found


async def _keys(class_session_id: uuid.UUID) -> dict[str, object]:
    """The comparability keys (FR-65): `sessions`' settings and AI keys, `tests`' question set,
    Item weights and Scoring guide (left out where no content is stored)."""
    async with get_sessionmaker()() as s:
        found: dict[str, object] = dict(
            await sessions.comparability_source(s, class_session_id) or {}
        )
        try:
            found.update(await tests.comparability_keys(s, class_session_id))
        except content.ContentNotFound:
            pass
    return found


async def _rating_students(class_session_id: uuid.UUID) -> dict[str, int]:
    async with get_sessionmaker()() as s:
        return await games.rating_students(s, class_session_id)


async def _learning(class_session_id: uuid.UUID, now: datetime) -> ClassLearningOut | None:
    try:
        return await class_report_learning.learning_of(class_session_id, now)
    except content.ContentNotFound:  # a database with no question set: no learning measures
        return None


async def write_aggregate(
    class_session_id: uuid.UUID, *, now: datetime | None = None, for_retention: bool = False
) -> bool:
    """Write (or replace) the Class session's aggregate (the module doc); False when none is
    written: a Control test, an unknown Class session, one whose Student data is deleted, or (but
    for retention's own gate, `for_retention`) one whose deletion date has come, since retention
    may be erasing its Students. Both are checked again under the Class session's row lock in the
    writing transaction, so a job queued earlier never writes over half-erased data."""
    now = now or auth.utcnow()
    async with get_sessionmaker()() as s:
        # Database time, read before the figures: the finder compares it with when a game, a facts
        # set, a rating or an assessment last changed (also database time, Issue #63), so a change
        # after this read makes the aggregate due again.
        started = await s.scalar(select(func.now()))
        target = await sessions.retention_target(s, class_session_id)
        reporting = target is not None and await scope.is_reporting_session(s, class_session_id)
    if target is None or not reporting or target.data_deleted_at is not None:
        return False
    report = await class_report.report_parts(class_session_id)
    learning = await _learning(class_session_id, now)
    keys = await _keys(class_session_id)
    async with get_sessionmaker()() as s:
        game_students = await games.student_count(s, report.game_ids)
    rating_students = await _rating_students(class_session_id)
    found = measures(report, learning, game_students=game_students, rating_students=rating_students)
    registered = next((stage.count for stage in report.funnel if stage.stage == "registered"), 0)
    async with get_sessionmaker().begin() as s:
        locked = await sessions.retention_target(s, class_session_id, lock=True)
        if locked is None or locked.data_deleted_at is not None:
            return False
        today = now.astimezone(retention_rule.OSLO).date()
        if not for_retention and locked.deletion_date is not None and locked.deletion_date <= today:
            return False
        facts = (await classes.class_facts(s, [locked.class_id])).get(locked.class_id)
        if facts is None:  # pragma: no cover - a Class session always has its Class
            return False
        header = {
            "written_at": started,
            # Story 14.7: the Institution the figures speak for, as it is when they are written.
            "institution_id": facts.institution_id,
            "students": registered,
            "game_students": game_students,
            "games_finished": report.finished,
            "keys": keys,
        }
        # The header row first: a second writer waits on it, then replaces what the first wrote.
        await s.execute(
            pg_insert(class_aggregates)
            .values(class_session_id=class_session_id, **header)
            .on_conflict_do_update(index_elements=["class_session_id"], set_=header)
        )
        await s.execute(
            delete(class_aggregate_measures).where(
                class_aggregate_measures.c.class_session_id == class_session_id
            )
        )
        if found:
            await s.execute(
                insert(class_aggregate_measures),
                [
                    {
                        "class_session_id": class_session_id,
                        "measure": m.measure,
                        "group_size": m.group_size,
                        "withheld": m.group_size < MIN_GROUP,
                        "value": None if m.group_size < MIN_GROUP else m.value,
                    }
                    for m in found
                ],
            )
    log.info(
        "class_aggregate_written",
        class_session_id=str(class_session_id),
        measures=len(found),
        withheld=sum(1 for m in found if m.group_size < MIN_GROUP),
    )
    return True


async def ensure_aggregate(class_session_id: uuid.UUID) -> None:
    """Retention's gate (Story 15.3, through `identity.register_session_aggregate_writer`): write
    the aggregate when none is stored yet; one that exists is kept. Raises what writing raises,
    and retention then deletes nothing."""
    async with get_sessionmaker()() as s:
        stored = await s.scalar(
            select(class_aggregates.c.class_session_id).where(
                class_aggregates.c.class_session_id == class_session_id
            )
        )
    if stored is None and not await write_aggregate(class_session_id, for_retention=True):
        # A Control test, or a Class session gone or deleted meanwhile: nothing to write.
        log.info("class_aggregate_skipped", class_session_id=str(class_session_id))


async def due_sessions(now: datetime) -> Sequence[uuid.UUID]:
    """The sweep's finder (the module doc), in a fixed number of reads."""
    candidates = await sessions.aggregate_candidates(now)
    if not candidates:
        return []
    async with get_sessionmaker()() as s:
        written = {
            row.class_session_id: row.written_at
            for row in await s.execute(
                select(class_aggregates.c.class_session_id, class_aggregates.c.written_at).where(
                    class_aggregates.c.class_session_id.in_(candidates)
                )
            )
        }
        latest = await assessment.latest_updates(s, candidates)
        played = await games.latest_report_changes(s, candidates)
        open_ = await tests.sessions_with_open_attempts(s, candidates)
        keys = [aggregate_key(c) for c in candidates]
        live = await jobs.live_locks(s, keys)
        failed = await jobs.failed_counts(s, keys)
    due = []
    for class_session_id in candidates:
        key = aggregate_key(class_session_id)
        if class_session_id in open_ or key in live or failed.get(key, 0) >= MAX_FAILURES:
            continue
        at = written.get(class_session_id)
        changed = max(
            (t for t in (latest.get(class_session_id), played.get(class_session_id)) if t),
            default=None,
        )
        if at is None or (changed is not None and changed > at):
            due.append(class_session_id)
    return due


async def defer_due(class_session_id: object, now: datetime) -> bool:
    """The sweep's act: defer the Class session's job on `reports-bulk`, ids only."""
    assert isinstance(class_session_id, uuid.UUID)
    async with get_sessionmaker().begin() as s:
        return await jobs.defer(
            s,
            WRITE_TASK,
            queue=jobs.REPORTS_BULK,
            queueing_lock=aggregate_key(class_session_id),
            class_session_id=str(class_session_id),
        )


@jobs.app.task(name=WRITE_TASK, queue=jobs.REPORTS_BULK)
async def write_class_aggregate(class_session_id: str) -> None:
    try:
        await write_aggregate(uuid.UUID(class_session_id))
    except Exception as exc:  # the type only: an exception's text may hold personal data
        log.error(
            "class_aggregate_failed", class_session_id=class_session_id, exc_type=type(exc).__name__
        )
        raise


async def previous_median(s: AsyncSession, class_session_id: uuid.UUID) -> Decimal | None:
    """«Fjoråret» (UX-DR51): the median chain Total cost stored for the previous Class session of
    the same Class; None without one, without its aggregate or when it was withheld."""
    previous = await sessions.previous_session_id(s, class_session_id)
    if previous is None:
        return None
    return await s.scalar(
        select(class_aggregate_measures.c.value).where(
            class_aggregate_measures.c.class_session_id == previous,
            class_aggregate_measures.c.measure == CHAIN_MEDIAN,
            class_aggregate_measures.c.withheld.is_(False),
        )
    )


identity.register_session_aggregate_writer("reports.class_aggregate", ensure_aggregate)
sessions.register_previous_cost(previous_median)
