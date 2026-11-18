"""The report of a simulation batch (`python -m app.sim report`, Story 2.11, AD-22).

Pure: no I/O and no clock. `measure` turns what `app.sim` read back for each Game of a batch
(its summary, Decision log, occupancy history and LLM call attempts) into figures, and
`report_lines` prints them. Every figure is a stored value or a statistic over stored values:
Orders, fallbacks and the Effort level from the Decision log, cost, tokens and times from the
LLM call rows, switches and the cost limit from the occupancy history, chain cost from the
finished Week state. With the one AD-15 mapping:

- **LLM-path Orders** are Decision log rows with `occupant_kind = llm` and `decided_by ≠ guided`:
  the Orders an LLM player was asked for, its fallbacks included.
- **Time per Order** is the span from an LLM-path Order's first attempt's `started_at` to the end
  (`started_at + latency_ms`) of its last attempt: retries and back-off included, the wait in
  the job queue not.
- **Retries per Order** is the number of call ids on an LLM-path Order minus one, over the
  Orders with calls.
- **llm Seats** are Seats whose first occupancy row is `llm`; a Seat counts as **switched** when
  it has a `guard_switch` row (FR-79).
- The **Share of LLM Orders** is `decided_by = llm` over the rows with `occupant_kind ≠ student`
  and `decided_by ≠ guided` (FR-68).
- The **coefficient of variation** of chain Total cost is the sample standard deviation over the
  mean, across the batch's Games (SM-3b).
- Median and p95 are nearest-rank values.

Pass lines come only from the batch file (C-3): the batch's mean AI cost per Game, its p95 time
per Order in seconds and its switched share, each at most its line. A batch the cost limit
cut short misses every line it carries: its later Games ran on Rule-based players, so its
figures do not measure the model.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol

from app.modules.games.service import (
    DecidedBy,
    DecisionLogRow,
    Fallback,
    GameSummary,
    OccupancyReason,
    OccupancyRow,
    OccupantKind,
)

PASS_LINES = ("cost_per_game_usd", "time_per_order_p95_s", "switched_share")
"""The pass lines a batch file may carry, in report order; none has a default (C-3)."""

MOCK_WARNING = (
    "MOCK PROVIDER: the mock answered every LLM call of this batch; these numbers are not "
    "measurements"
)


class Attempt(Protocol):
    """What the report reads from one LLM call row (`ai.calls.GameAttempt`)."""

    @property
    def id(self) -> Any: ...
    @property
    def started_at(self) -> datetime: ...
    @property
    def latency_ms(self) -> int: ...
    @property
    def input_tokens(self) -> int: ...
    @property
    def output_tokens(self) -> int: ...
    @property
    def reasoning_tokens(self) -> int: ...
    @property
    def cost_usd(self) -> Decimal: ...


@dataclass(frozen=True)
class GameInput:
    """What `app.sim` read back for one Game of the batch."""

    summary: GameSummary
    log: Sequence[DecisionLogRow]
    occupancy: Sequence[OccupancyRow]
    attempts: Sequence[Attempt]
    effort_level: str | None
    """The Effort level the Game froze (`SessionRuntime`)."""


@dataclass(frozen=True)
class Spread:
    median: int | None
    p95: int | None


@dataclass(frozen=True)
class Figures:
    """The figures of one Game or of the whole batch."""

    ai_cost_usd: Decimal
    calls: int
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    latency_ms: Spread
    """Per attempt."""
    order_time_ms: Spread
    """Per LLM-path Order with calls."""
    llm_orders: int
    """LLM-path Orders."""
    retries_mean: Decimal | None
    retries_max: int | None
    fallbacks: tuple[tuple[Fallback, int], ...]
    """LLM-path Orders per fallback type, in `Fallback` order."""
    llm_seats: int
    switched_seats: int
    llm_decided: int
    llm_share_base: int
    """The Orders the Share of LLM Orders is taken over."""
    chain_cost: Decimal


@dataclass(frozen=True)
class GameFigures:
    summary: GameSummary
    figures: Figures


@dataclass(frozen=True)
class PassLine:
    name: str
    line: Decimal | None
    """None: the batch file has no such line."""
    measured: Decimal | None
    """None: nothing to measure (no LLM Seat, no LLM-path Order with calls)."""
    cut_short: bool = False
    """The cost limit cut the batch short: a line it carries is missed."""

    @property
    def verdict(self) -> str:
        if self.line is None:
            return "no line"
        if self.cut_short:
            return "miss (cut short)"
        if self.measured is None:
            return "n/a"
        return "pass" if self.measured <= self.line else "miss"


@dataclass(frozen=True)
class CutShort:
    game_id: str
    week: int
    """The first Week of that Game played on Rule-based players after the cost limit."""


@dataclass(frozen=True)
class BatchFigures:
    batch_id: str
    started_at: datetime
    mock: bool
    model_config_id: str | None
    effort_levels: tuple[str, ...]
    games: tuple[GameFigures, ...]
    total: Figures
    cost_per_game_usd: Decimal | None
    """The batch's mean AI cost per Game; None without an llm Seat."""
    chain_cost_cv: Decimal | None
    cut_short: CutShort | None
    pass_lines: tuple[PassLine, ...]


def nearest_rank(values: Sequence[int], share: Decimal) -> int | None:
    """The nearest-rank `share` quantile of `values`; None when there are none."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(share * len(ordered)))
    return ordered[rank - 1]


def _spread(values: Sequence[int]) -> Spread:
    return Spread(nearest_rank(values, Decimal("0.5")), nearest_rank(values, Decimal("0.95")))


def _ms(delta: timedelta) -> int:
    return round(delta / timedelta(milliseconds=1))


def _llm_path(row: DecisionLogRow) -> bool:
    return row.occupant_kind is OccupantKind.LLM and row.decided_by is not DecidedBy.GUIDED


def _figures(
    log: Sequence[DecisionLogRow],
    occupancy: Sequence[OccupancyRow],
    attempts: Sequence[Attempt],
    chain_cost: Decimal,
) -> Figures:
    by_id = {str(attempt.id): attempt for attempt in attempts}
    path = [row for row in log if _llm_path(row)]
    times: list[int] = []
    retries: list[int] = []
    for row in path:
        found = [by_id[call_id] for call_id in row.llm_call_ids if call_id in by_id]
        if row.llm_call_ids:
            retries.append(len(row.llm_call_ids) - 1)
        if found:
            start = min(attempt.started_at for attempt in found)
            end = max(
                attempt.started_at + timedelta(milliseconds=attempt.latency_ms) for attempt in found
            )
            times.append(_ms(end - start))
    first: dict[str, OccupancyRow] = {}
    switched: set[str] = set()
    for row in occupancy:
        first.setdefault(row.seat_id, row)
        if row.reason is OccupancyReason.GUARD_SWITCH:
            switched.add(row.seat_id)
    llm_seats = {seat for seat, row in first.items() if row.occupant_kind is OccupantKind.LLM}
    base = [
        row
        for row in log
        if row.occupant_kind is not OccupantKind.STUDENT and row.decided_by is not DecidedBy.GUIDED
    ]
    return Figures(
        ai_cost_usd=sum((attempt.cost_usd for attempt in attempts), Decimal(0)),
        calls=len(attempts),
        input_tokens=sum(attempt.input_tokens for attempt in attempts),
        output_tokens=sum(attempt.output_tokens for attempt in attempts),
        reasoning_tokens=sum(attempt.reasoning_tokens for attempt in attempts),
        latency_ms=_spread([attempt.latency_ms for attempt in attempts]),
        order_time_ms=_spread(times),
        llm_orders=len(path),
        retries_mean=Decimal(sum(retries)) / len(retries) if retries else None,
        retries_max=max(retries) if retries else None,
        fallbacks=tuple(
            (kind, count)
            for kind in Fallback
            if (count := sum(1 for row in path if row.fallback is kind))
        ),
        llm_seats=len(llm_seats),
        switched_seats=len(llm_seats & switched),
        llm_decided=sum(1 for row in base if row.decided_by is DecidedBy.LLM),
        llm_share_base=len(base),
        chain_cost=chain_cost,
    )


def coefficient_of_variation(values: Sequence[Decimal]) -> Decimal | None:
    """Sample standard deviation over the mean; None for fewer than two values or a mean of 0."""
    if len(values) < 2:
        return None
    mean = sum(values, Decimal(0)) / len(values)
    if mean == 0:
        return None
    variance = sum(((value - mean) ** 2 for value in values), Decimal(0)) / (len(values) - 1)
    return variance.sqrt() / mean


def _cut_short(games: Sequence[GameInput]) -> CutShort | None:
    for game in games:
        weeks = [
            row.from_week for row in game.occupancy if row.reason is OccupancyReason.COST_LIMIT
        ]
        if weeks:
            return CutShort(game.summary.game_id, min(weeks))
    return None


def _line(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def measure(
    batch_id: str,
    started_at: datetime,
    *,
    mock: bool,
    model_config_id: str | None,
    pass_lines: Mapping[str, Any],
    games: Sequence[GameInput],
) -> BatchFigures:
    """The figures of each Game and of the batch, and the pass or miss against each line."""
    per_game = tuple(
        GameFigures(
            game.summary,
            _figures(game.log, game.occupancy, game.attempts, game.summary.chain_cost),
        )
        for game in games
    )
    total = _figures(
        [row for game in games for row in game.log],
        [row for game in games for row in game.occupancy],
        [attempt for game in games for attempt in game.attempts],
        sum((game.summary.chain_cost for game in games), Decimal(0)),
    )
    has_llm = total.llm_seats > 0
    cost_per_game = total.ai_cost_usd / len(games) if has_llm and games else None
    p95 = total.order_time_ms.p95
    measured = {
        "cost_per_game_usd": cost_per_game,
        "time_per_order_p95_s": None if p95 is None else Decimal(p95) / 1000,
        "switched_share": (Decimal(total.switched_seats) / total.llm_seats if has_llm else None),
    }
    cut_short = _cut_short(games)
    levels = {game.effort_level for game in games if game.effort_level is not None}
    return BatchFigures(
        batch_id=batch_id,
        started_at=started_at,
        mock=mock,
        model_config_id=model_config_id,
        effort_levels=tuple(sorted(levels)),
        games=per_game,
        total=total,
        cost_per_game_usd=cost_per_game,
        chain_cost_cv=coefficient_of_variation([game.summary.chain_cost for game in games]),
        cut_short=cut_short,
        pass_lines=tuple(
            PassLine(name, _line(pass_lines.get(name)), measured[name], cut_short is not None)
            for name in PASS_LINES
        ),
    )


def _share(part: int, whole: int) -> str:
    return "n/a" if whole == 0 else f"{Decimal(part) / whole:.4f}"


def _value(value: object) -> str:
    return "n/a" if value is None else str(value)


def _usd(value: Decimal | None) -> str:
    return "n/a" if value is None else f"{value:.8f}"


PLACES = {"cost_per_game_usd": 8, "time_per_order_p95_s": 3, "switched_share": 4}
"""Decimal places a measured pass-line value is printed with (it is compared unrounded)."""


def _measured(name: str, value: Decimal | None) -> str:
    return "n/a" if value is None else f"{value:.{PLACES[name]}f}"


def _figure_lines(figures: Figures) -> list[str]:
    fallback = " ".join(
        f"{kind.value}={_share(count, figures.llm_orders)}" for kind, count in figures.fallbacks
    )
    retries_mean = None if figures.retries_mean is None else f"{figures.retries_mean:.2f}"
    return [
        f"  ai_cost usd={_usd(figures.ai_cost_usd)} calls={figures.calls}",
        f"  tokens input={figures.input_tokens} output={figures.output_tokens} "
        f"reasoning={figures.reasoning_tokens}",
        f"  latency_per_attempt_ms median={_value(figures.latency_ms.median)} "
        f"p95={_value(figures.latency_ms.p95)}",
        f"  time_per_order_ms median={_value(figures.order_time_ms.median)} "
        f"p95={_value(figures.order_time_ms.p95)}",
        f"  retries_per_order mean={_value(retries_mean)} max={_value(figures.retries_max)}",
        f"  fallback llm_orders={figures.llm_orders}" + (f" {fallback}" if fallback else ""),
        f"  guard_switched seats={figures.switched_seats}/{figures.llm_seats} "
        f"share={_share(figures.switched_seats, figures.llm_seats)}",
        f"  llm_share orders={figures.llm_decided}/{figures.llm_share_base} "
        f"share={_share(figures.llm_decided, figures.llm_share_base)}",
        f"  chain_cost {figures.chain_cost}",
    ]


def _check(summary: GameSummary) -> str:
    if summary.check is None:
        return "check missing"
    return "check ok" if summary.check.ok else f"check failed {len(summary.check.violations)}"


def report_lines(figures: BatchFigures) -> list[str]:
    """The printed report: the provider line first, so mock numbers are never read as
    measurements, then the batch head, each Game, the batch, cut short and the pass lines."""
    if figures.mock:
        lines = [MOCK_WARNING]
    elif figures.total.llm_seats:
        lines = ["provider real"]
    else:
        lines = ["provider none (no llm Seats)"]
    lines.append(
        f"batch {figures.batch_id} started {figures.started_at.isoformat()} "
        f"games {len(figures.games)} model_config {figures.model_config_id or '-'} "
        f"effort_level {','.join(figures.effort_levels) or '-'}"
    )
    for game in figures.games:
        summary = game.summary
        lines.append(
            f"game {summary.game_id} seed {summary.demand_seed} weeks {summary.weeks} "
            + _check(summary)
        )
        lines += _figure_lines(game.figures)
    lines.append(f"batch games {len(figures.games)}")
    lines += _figure_lines(figures.total)
    lines.append(f"  ai_cost_per_game usd={_usd(figures.cost_per_game_usd)}")
    cv = None if figures.chain_cost_cv is None else f"{figures.chain_cost_cv:.4f}"
    lines.append(f"  chain_cost_cv {_value(cv)}")
    if figures.cut_short is None:
        lines.append("cut_short no")
    else:
        lines.append(
            f"cut_short game {figures.cut_short.game_id} week {figures.cut_short.week} "
            "(evaluation budget's cost limit; Rule-based players from then on)"
        )
    for line in figures.pass_lines:
        if line.line is None:
            lines.append(f"pass_line {line.name} no line")
        else:
            lines.append(
                f"pass_line {line.name} line={line.line} "
                f"measured={_measured(line.name, line.measured)} {line.verdict}"
            )
    return lines
