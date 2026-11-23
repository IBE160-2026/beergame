"""The Klasserapport of a Class session (Story 14.1, FR-64, FR-68, FR-70, FR-79, AD-10, AD-13,
AD-15, AD-25): how the Class games went, for the Lecturers of the Class.

`class_report(user, class_session_id)` is the one assembler. It reads every other module through
its `service.py` and computes each figure here, never in the web app (AD-10):

- the scope: the Class games (`purpose = class`) of the Class session, none for a Control test
  Class session (AD-13, AD-27). Until Epic 13's `reports.scope` is on this branch, `_class_games`
  stands in for `scope.reporting_games(session, id, purposes={Purpose.CLASS})`; the merge
  replaces it with that call. Game figures are over the finished ones;
- the Trakt, as the Oversikt counts it (`progress.funnel` over the Class's registered Students);
- Kjedekost and Kostnad per Rolle from `game_summaries.chain_cost` and `games.cost_parts`;
- Forsterkning and «Mønstre» from the stored facts sets only (`games.fact_figures`): a finished
  game whose Seats have no stored set yet is not covered, and `facts_games` says how many are.
  The finish hook of `class_report_jobs` stores them, so this read never builds one (AD-7, AD-25);
- the AI play from the Decision log and the occupancy rows, each switch marked through the one
  AD-15 mapping (`games.seat_mark`);
- the plausibility ratings per AI mode, counts and median only (FR-70).

A fixed number of queries whatever the number of games (NFR-3), and no write.
"""

import uuid
from collections.abc import Iterable, Sequence
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.class_cost import FinishedGame, class_cost
from app.analysis.wall import quartiles
from app.engine.settings import ROLES, Role
from app.modules.classes import service as classes
from app.modules.content import service as content
from app.modules.games import service as games
from app.modules.games.service import ClassGameRow, OccupancyReason, OccupantKind
from app.modules.progress import service as progress
from app.modules.reports.class_report_schemas import (
    ClassReportOut,
    DistributionOut,
    GameAiOut,
    GameCostOut,
    PatternOut,
    RatingCountOut,
    RatingModeOut,
    ReportAiOut,
    ReportCostOut,
    RoleAmplificationOut,
    RoleCostDistributionOut,
    SwitchOut,
)
from app.modules.sessions import service as sessions
from app.modules.sessions.schemas import FunnelStageOut
from app.platform import authz
from app.platform.db import get_sessionmaker

__all__ = ["READ", "class_report", "distribution", "percent", "rating_median"]

READ = "class_report.read"
"""The Klasserapport's policy (FR-64, FR-5): the Lecturers who own the Class, never an Assistant
lecturer and never an Admin without a staff role in it."""

_CENT = Decimal("0.01")
_TENTH = Decimal("0.1")
_RATINGS = range(1, 6)


def distribution(values: Sequence[Decimal], places: Decimal = _CENT) -> DistributionOut | None:
    """The values with their median and quartiles rounded to `places` (half up); None for none."""
    spread = quartiles(values)
    if spread is None:
        return None
    lower, median, upper = (value.quantize(places, ROUND_HALF_UP) for value in spread)
    return DistributionOut(
        values=[value.quantize(places, ROUND_HALF_UP) for value in values],
        median=median,
        lower_quartile=lower,
        upper_quartile=upper,
    )


def percent(part: int, whole: int) -> Decimal | None:
    """`part` of `whole` in percent to one decimal (half up); None when `whole` is 0."""
    if whole <= 0:
        return None
    return (Decimal(part) * 100 / Decimal(whole)).quantize(_TENTH, ROUND_HALF_UP)


def rating_median(counts: dict[int, int]) -> Decimal | None:
    """The median of ratings given as counts per value (the midpoint of the two middle ones for an
    even number); None for none."""
    spread = quartiles(value for value, count in sorted(counts.items()) for _ in range(count))
    return None if spread is None else spread[1]


async def _class_games(s: AsyncSession, class_session_id: uuid.UUID, control_test: bool):
    """The Class games the report counts: `scope.reporting_games(..., purposes={class})` of Epic
    13 (AD-13), none for a Control test Class session (AD-27)."""
    return [] if control_test else await games.report_class_games(s, class_session_id)


def _cost_out(
    finished: list[ClassGameRow], parts: dict[uuid.UUID, dict[str, tuple[Decimal, Decimal]]]
) -> ReportCostOut | None:
    costed = [(game, game.chain_cost) for game in finished if game.chain_cost is not None]
    roles = [str(role) for role in ROLES]
    means = class_cost(
        [FinishedGame(chain_cost=cost, roles=parts.get(g.game_id, {})) for g, cost in costed],
        roles,
    )
    chain = distribution([cost for _, cost in costed])
    if means is None or chain is None:
        return None
    zero = (Decimal(0), Decimal(0))
    per_role = []
    for mean in means.roles:
        totals = [sum(parts.get(g.game_id, {}).get(mean.role, zero)) for g, _ in costed]
        spread = distribution(totals)
        assert spread is not None  # `costed` is not empty
        per_role.append(
            RoleCostDistributionOut(
                role=Role(mean.role),
                distribution=spread,
                holding_cost=mean.holding_cost,
                backorder_cost=mean.backorder_cost,
                total_cost=mean.total_cost,
            )
        )
    return ReportCostOut(
        chain=chain,
        holding_cost=means.holding_cost,
        backorder_cost=means.backorder_cost,
        roles=per_role,
        games=[
            GameCostOut(number=g.number, chain_cost=value)
            for (g, _), value in zip(costed, chain.values, strict=True)
        ],
    )


def _amplification_out(
    covered: list[ClassGameRow], figures: games.FactFigures
) -> list[RoleAmplificationOut]:
    found = []
    for role in ROLES:
        values = [
            value
            for game in covered
            if (value := figures.amplification.get(game.game_id, {}).get(str(role))) is not None
        ]
        found.append(
            RoleAmplificationOut(role=role, games=len(values), distribution=distribution(values))
        )
    return found


def _patterns_out(
    covered: list[ClassGameRow], figures: games.FactFigures, names: dict[str, str]
) -> list[PatternOut]:
    occurrences: dict[str, int] = {}
    in_games: dict[str, int] = {}
    for game in covered:
        for pattern, count in figures.patterns.get(game.game_id, {}).items():
            occurrences[pattern] = occurrences.get(pattern, 0) + count
            in_games[pattern] = in_games.get(pattern, 0) + 1
    order = list(names)
    return sorted(
        (
            PatternOut(
                pattern=pattern,
                name=names.get(pattern, pattern),
                occurrences=count,
                games=in_games[pattern],
            )
            for pattern, count in occurrences.items()
        ),
        key=lambda p: (
            -p.occurrences,
            -p.games,
            order.index(p.pattern) if p.pattern in order else len(order),
            p.pattern,
        ),
    )


def _ai_out(
    finished: list[ClassGameRow],
    seat_figures: Iterable[games.SeatFigure],
    occupancy: Iterable[games.OccupancyFigure],
    seat_counts: dict[uuid.UUID, int],
) -> ReportAiOut:
    numbers = {game.game_id: game.number for game in finished}
    position = {str(role): i for i, role in enumerate(ROLES)}
    by_game: dict[uuid.UUID, list[games.SeatFigure]] = {}
    for seat in seat_figures:
        by_game.setdefault(seat.game_id, []).append(seat)
    ai_seats = whole_game = 0
    per_game = []
    for game in finished:
        rows = by_game.get(game.game_id, [])
        ai_seats += sum(1 for seat in rows if seat.ai_weeks > 0)
        whole_game += sum(1 for seat in rows if seat.ai_weeks > 0 and seat.student_weeks == 0)
        ordered = sum(seat.ordered for seat in rows)
        llm = sum(seat.llm for seat in rows)
        per_game.append(
            GameAiOut(
                number=game.number,
                ordered=ordered,
                llm=llm,
                llm_percent=percent(llm, ordered),
                fallback=sum(seat.fallback for seat in rows),
            )
        )
    llm_seats: set[tuple[uuid.UUID, str]] = set()
    guard_switched: set[tuple[uuid.UUID, str]] = set()
    switches = []
    for row in occupancy:
        seat = (row.game_id, row.role)
        if row.occupant_kind == OccupantKind.LLM:
            llm_seats.add(seat)
        if row.reason not in (OccupancyReason.GUARD_SWITCH, OccupancyReason.COST_LIMIT):
            continue
        mark = games.seat_mark(None, None, row.occupant_kind, row.reason)
        if mark is None:  # a guard switch to anything but a Rule-based player marks nothing
            continue
        if row.reason == OccupancyReason.GUARD_SWITCH:
            guard_switched.add(seat)
        switches.append(
            SwitchOut(
                number=numbers[row.game_id], role=Role(row.role), week=row.from_week, mark=mark
            )
        )
    switches.sort(
        key=lambda s: (s.number is None, s.number or 0, s.week, position[str(s.role)], s.mark)
    )
    seats = sum(seat_counts.get(game.game_id, 0) for game in finished)
    # A Seat the guard switched held an LLM player first, whatever its rows say.
    llm_held = len(llm_seats | guard_switched)
    return ReportAiOut(
        seats=seats,
        ai_seats=ai_seats,
        whole_game=whole_game,
        ai_percent=percent(ai_seats, seats),
        games=per_game,
        switches=switches,
        llm_seats=llm_held,
        guard_switched=len(guard_switched),
        guard_percent=percent(len(guard_switched), llm_held),
    )


def _ratings_out(counts: dict[str, dict[int, int]]) -> list[RatingModeOut]:
    found = []
    for mode in ("llm", "rule_based"):
        values = counts.get(mode)
        if not values:
            continue
        median = rating_median(values)
        assert median is not None
        found.append(
            RatingModeOut(
                ai_mode=mode,
                count=sum(values.values()),
                median=median,
                values=[RatingCountOut(rating=r, count=values.get(r, 0)) for r in _RATINGS],
            )
        )
    return found


async def _pattern_names() -> dict[str, str]:
    """The latest Detected pattern definitions' names by id, in their order; the ids alone when
    none is stored (a database without content)."""
    try:
        _, defined = await content.detected_patterns(None)
    except content.ContentNotFound:
        return {}
    return {pattern.id: pattern.name for pattern in defined.patterns}


async def class_report(user: authz.Principal, class_session_id: uuid.UUID) -> ClassReportOut | None:
    """The Klasserapport, or None when the User may not read it or the Class session does not
    exist: one answer for both (FR-5, NFR-7)."""
    staffed = await sessions.staffed_session(user, class_session_id, READ)
    if staffed is None:
        return None
    async with get_sessionmaker()() as s:
        kind = await sessions.kind_of(class_session_id, session=s)
        control_test = kind == sessions.CONTROL_TEST
        class_games = await _class_games(s, class_session_id, control_test)
        registered = [] if control_test else await classes.registered_students(staffed.class_id)
        trakt = await progress.funnel(s, class_session_id, registered)
        finished = [game for game in class_games if game.finished]
        ids = [game.game_id for game in finished]
        parts = await games.cost_parts(s, ids) if ids else {}
        facts = await games.fact_figures(s, ids)
        seat_counts = await games.seat_counts(s, ids)
        seat_figures = await games.seat_figures(s, ids)
        occupancy = await games.occupancy_figures(s, ids)
        ratings = {} if control_test else await games.rating_counts(s, class_session_id)
    covered = [
        game
        for game in finished
        if seat_counts.get(game.game_id, 0) > 0
        and facts.seats.get(game.game_id, 0) >= seat_counts[game.game_id]
    ]
    names = await _pattern_names() if covered else {}
    return ClassReportOut(
        class_session_id=class_session_id,
        class_id=staffed.class_id,
        class_name=staffed.class_name,
        session_number=staffed.number,
        games=len(class_games),
        finished=len(finished),
        facts_games=len(covered),
        funnel=[FunnelStageOut(stage="registered", count=trakt.registered)]
        + [FunnelStageOut(stage=step.value, count=count) for step, count in trakt.steps],
        cost=_cost_out(finished, parts) if finished else None,
        amplification=_amplification_out(covered, facts),
        patterns=_patterns_out(covered, facts, names),
        ai=_ai_out(finished, seat_figures, occupancy, seat_counts),
        ratings=_ratings_out(ratings),
    )
