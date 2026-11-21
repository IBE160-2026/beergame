"""The facts set of one Seat of a finished Game (FR-44, AD-7, AD-15).

`facts(decision_log, seat, pattern_definitions)` reads the Game's Decision log (every Seat, every
Week) and returns ids, values and Roles only: the chain part, identical for every Seat of the
Game, and the Seat part with its Detected pattern occurrences and own moments. Every rule is
documented in `facts.md`; a change to a rule is a new `ANALYSIS_VERSION`.

Pure (AD-1): no I/O, no clock, no randomness; stdlib, pydantic and `app.engine` only."""

import statistics
from collections.abc import Sequence
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.analysis.patterns import Mechanism, PatternSet
from app.engine import Role

__all__ = [
    "ANALYSIS_VERSION",
    "LARGE_ORDER",
    "MIN_STUDENT_ORDERS",
    "MOMENTS",
    "ChainFacts",
    "DecisionLog",
    "FactSet",
    "LoggedOrder",
    "Moment",
    "PatternOccurrence",
    "RoleFacts",
    "SeatFacts",
    "Seen",
    "facts",
]

ANALYSIS_VERSION = 1
"""The version of these rules; stored with every facts set (AD-7)."""
LARGE_ORDER = 10
"""An Order of this many units or more is large (FR-44: the first such Week per Role)."""
MIN_STUDENT_ORDERS = 10
"""Fewer Orders with `decided_by = student` than this: no own moments, and the Student is left
out of SM-1 and SM-2 (FR-44, assumption: threshold of 10 Orders)."""
MOMENTS = 3
"""Own moments chosen for a Seat with enough Student Orders."""
assert MOMENTS <= MIN_STUDENT_ORDERS  # so a Seat with moments always has three

_PLACES = Decimal("0.001")
_FROZEN = ConfigDict(frozen=True, extra="forbid")

_Count = Annotated[int, Field(strict=True, ge=0)]
_Week = Annotated[int, Field(strict=True, ge=1)]
_Money = Annotated[Decimal, Field(allow_inf_nan=False)]
type DecidedBy = Literal["student", "llm", "rule_based", "scripted", "guided"]
type OccupantKind = Literal["student", "llm", "rule_based", "scripted"]


class LoggedOrder(BaseModel):
    """One Decision log row as the facts read it: the Seat's Order and what it saw (AD-15)."""

    model_config = _FROZEN

    week: _Week
    role: Role
    order: _Count
    decided_by: DecidedBy
    occupant_kind: OccupantKind
    incoming_order: _Count
    incoming_delivery: _Count
    shipped: _Count
    inventory: _Count
    backlog: _Count
    supply_line: _Count
    holding_cost: _Money
    backorder_cost: _Money
    week_cost: _Money

    @model_validator(mode="after")
    def _cost_parts_add_up(self) -> LoggedOrder:
        if self.holding_cost + self.backorder_cost != self.week_cost:
            raise ValueError(f"Week {self.week} {self.role}: the cost parts do not add up")
        return self


class DecisionLog(BaseModel):
    """A finished Game's Decision log: one row per Role per Week, Weeks 1..N, every Role."""

    model_config = _FROZEN

    roles: Annotated[tuple[Role, ...], Field(min_length=1)]
    """The chain, the Role that serves the customer first."""
    rows: tuple[LoggedOrder, ...]

    @model_validator(mode="after")
    def _complete(self) -> DecisionLog:
        if len(set(self.roles)) != len(self.roles):
            raise ValueError("a Role repeats in the chain")
        keys = [(row.week, row.role) for row in self.rows]
        if len(set(keys)) != len(keys):
            raise ValueError("a Role has two rows in one Week")
        weeks = max((row.week for row in self.rows), default=0)
        expected = {(week, role) for week in range(1, weeks + 1) for role in self.roles}
        if weeks == 0 or set(keys) != expected:
            raise ValueError("a finished Game's log has every Role in every Week from Week 1")
        return self


class Seen(BaseModel):
    """What one Seat saw in one Week, as numbers (`state_seen`, AD-3)."""

    model_config = _FROZEN

    role: Role
    incoming_order: _Count
    incoming_delivery: _Count
    shipped: _Count
    inventory: _Count
    backlog: _Count
    supply_line: _Count
    week_cost: _Money


class RoleFacts(BaseModel):
    model_config = _FROZEN

    role: Role
    orders_std: _Money
    """Population standard deviation of the Role's Orders over the whole Game."""
    amplification: _Money | None
    """`orders_std / demand_std`, None when customer demand never varied."""
    first_large_order_week: _Week | None
    """The first Week with an Order of `LARGE_ORDER` or more; None when there is none."""
    holding_cost: _Money
    backorder_cost: _Money
    total_cost: _Money


class ChainFacts(BaseModel):
    """The part every Seat of the Game shares, identical for all of them."""

    model_config = _FROZEN

    weeks: _Week
    roles: tuple[Role, ...]
    demand: tuple[_Count, ...]
    """Customer demand, Week by Week: the first Role's incoming order."""
    demand_std: _Money
    by_role: tuple[RoleFacts, ...]
    total_cost: _Money
    """The chain's Total cost."""
    ai_held_cost: _Money
    """The part of it incurred in Weeks a Seat was held by an AI player (`occupant_kind` other
    than `student`)."""
    ai_held_share: _Money | None
    """`ai_held_cost / total_cost`; None when the chain cost nothing."""


class PatternOccurrence(BaseModel):
    model_config = _FROZEN

    id: str
    """`<pattern>:<role>:<week>` (AD-7)."""
    pattern: str
    mechanism: Mechanism
    week: _Week
    order: _Count
    decided_by: DecidedBy
    state_seen: Seen
    later_cost: _Money
    """The Seat's cost over the following Weeks (`PatternSet.following_weeks`)."""
    later_weeks: _Count
    """How many following Weeks `later_cost` covers: fewer at the end of the Game."""
    others_seen: tuple[Seen, ...]
    """What the other Roles saw in the same Week, in chain order."""


class Moment(BaseModel):
    model_config = _FROZEN

    id: str
    """`moment:<role>:<week>`."""
    week: _Week
    order: _Count
    state_seen: Seen
    later_cost: _Money
    later_weeks: _Count
    others_seen: tuple[Seen, ...]
    patterns: tuple[str, ...]
    """The ids of the Seat's pattern occurrences in this Week; empty for a gap moment."""
    chosen_by: Literal["pattern", "order_gap"]


class SeatFacts(BaseModel):
    model_config = _FROZEN

    role: Role
    student_orders: _Count
    """The Seat's Orders with `decided_by = student`."""
    sm_excluded: bool
    """Fewer than `MIN_STUDENT_ORDERS` Student Orders: left out of SM-1 and SM-2 (FR-44)."""
    patterns: tuple[PatternOccurrence, ...]
    moments: tuple[Moment, ...]


class FactSet(BaseModel):
    model_config = _FROZEN

    analysis_version: int
    chain: ChainFacts
    seat: SeatFacts


def _std(values: Sequence[int]) -> Decimal:
    return statistics.pstdev([Decimal(value) for value in values])


def _places(value: Decimal) -> Decimal:
    return value.quantize(_PLACES, rounding=ROUND_HALF_EVEN)


def _seen(row: LoggedOrder) -> Seen:
    return Seen(
        role=row.role,
        incoming_order=row.incoming_order,
        incoming_delivery=row.incoming_delivery,
        shipped=row.shipped,
        inventory=row.inventory,
        backlog=row.backlog,
        supply_line=row.supply_line,
        week_cost=row.week_cost,
    )


def _chain(log: DecisionLog) -> ChainFacts:
    by_role = {role: [row for row in log.rows if row.role == role] for role in log.roles}
    for rows in by_role.values():
        rows.sort(key=lambda row: row.week)
    demand = tuple(row.incoming_order for row in by_role[log.roles[0]])
    demand_std = _std(demand)
    roles = []
    for role, rows in by_role.items():
        orders = [row.order for row in rows]
        orders_std = _std(orders)
        large = [row.week for row in rows if row.order >= LARGE_ORDER]
        roles.append(
            RoleFacts(
                role=role,
                orders_std=_places(orders_std),
                amplification=_places(orders_std / demand_std) if demand_std else None,
                first_large_order_week=large[0] if large else None,
                holding_cost=sum((row.holding_cost for row in rows), Decimal(0)),
                backorder_cost=sum((row.backorder_cost for row in rows), Decimal(0)),
                total_cost=sum((row.week_cost for row in rows), Decimal(0)),
            )
        )
    total = sum((row.week_cost for row in log.rows), Decimal(0))
    ai_held = sum((row.week_cost for row in log.rows if row.occupant_kind != "student"), Decimal(0))
    return ChainFacts(
        weeks=len(demand),
        roles=log.roles,
        demand=demand,
        demand_std=_places(demand_std),
        by_role=tuple(roles),
        total_cost=total,
        ai_held_cost=ai_held,
        ai_held_share=_places(ai_held / total) if total else None,
    )


class _SeatWeek(BaseModel):
    """The Seat's row of one Week with the numbers every occurrence and moment of it carries."""

    model_config = _FROZEN

    row: LoggedOrder
    later_cost: Decimal
    later_weeks: int
    others_seen: tuple[Seen, ...]


def _weeks(log: DecisionLog, role: Role, following: int) -> list[_SeatWeek]:
    rows = sorted((row for row in log.rows if row.role == role), key=lambda row: row.week)
    by_week = {(row.week, row.role): row for row in log.rows}
    weeks = []
    for index, row in enumerate(rows):
        later = rows[index + 1 : index + 1 + following]
        others = tuple(_seen(by_week[(row.week, other)]) for other in log.roles if other != role)
        weeks.append(
            _SeatWeek(
                row=row,
                later_cost=sum((each.week_cost for each in later), Decimal(0)),
                later_weeks=len(later),
                others_seen=others,
            )
        )
    return weeks


def _occurrences(weeks: Sequence[_SeatWeek], patterns: PatternSet) -> list[PatternOccurrence]:
    found = []
    backlogs: list[int] = []
    for week in weeks:
        row = week.row
        backlogs.append(row.backlog)
        if row.decided_by == "guided":
            continue  # a Guided Week's Order is the starting demand, not a decision
        for pattern in patterns.patterns:
            hit = pattern.matches(
                order=row.order,
                incoming=row.incoming_order,
                inventory=row.inventory,
                supply_line=row.supply_line,
                backlogs=backlogs,
            )
            if hit:
                found.append(
                    PatternOccurrence(
                        id=f"{pattern.id}:{row.role}:{row.week}",
                        pattern=pattern.id,
                        mechanism=pattern.mechanism,
                        week=row.week,
                        order=row.order,
                        decided_by=row.decided_by,
                        state_seen=_seen(row),
                        later_cost=week.later_cost,
                        later_weeks=week.later_weeks,
                        others_seen=week.others_seen,
                    )
                )
    return found


def _moments(weeks: Sequence[_SeatWeek], found: Sequence[PatternOccurrence]) -> list[Moment]:
    """`MOMENTS` own moments (the Seat has at least `MIN_STUDENT_ORDERS` ≥ `MOMENTS` Student
    Weeks), from Weeks with `decided_by = student` only: first the
    Weeks with a pattern, highest later cost first (then the earlier Week); then, to fill up,
    the other Weeks with the largest gap between the Order and the incoming order (then the
    higher later cost, then the earlier Week). Returned by Week."""
    own = [week for week in weeks if week.row.decided_by == "student"]
    hits: dict[int, list[str]] = {}
    for occurrence in found:
        hits.setdefault(occurrence.week, []).append(occurrence.id)
    with_pattern = sorted(
        (week for week in own if week.row.week in hits),
        key=lambda week: (-week.later_cost, week.row.week),
    )
    rest = sorted(
        (week for week in own if week.row.week not in hits),
        key=lambda week: (
            -abs(week.row.order - week.row.incoming_order),
            -week.later_cost,
            week.row.week,
        ),
    )
    chosen = [(week, "pattern") for week in with_pattern[:MOMENTS]]
    chosen += [(week, "order_gap") for week in rest[: MOMENTS - len(chosen)]]
    chosen.sort(key=lambda pair: pair[0].row.week)
    return [
        Moment(
            id=f"moment:{week.row.role}:{week.row.week}",
            week=week.row.week,
            order=week.row.order,
            state_seen=_seen(week.row),
            later_cost=week.later_cost,
            later_weeks=week.later_weeks,
            others_seen=week.others_seen,
            patterns=tuple(hits.get(week.row.week, ())),
            chosen_by=reason,
        )
        for week, reason in chosen
    ]


def facts(decision_log: DecisionLog, seat: Role | str, pattern_definitions: PatternSet) -> FactSet:
    """The facts set of the Seat of `seat` (its Role) from the Game's whole Decision log."""
    role = Role(seat)
    if role not in decision_log.roles:
        raise ValueError(f"{role} is not a Role in this Game")
    weeks = _weeks(decision_log, role, pattern_definitions.following_weeks)
    found = _occurrences(weeks, pattern_definitions)
    student_orders = sum(1 for week in weeks if week.row.decided_by == "student")
    excluded = student_orders < MIN_STUDENT_ORDERS
    return FactSet(
        analysis_version=ANALYSIS_VERSION,
        chain=_chain(decision_log),
        seat=SeatFacts(
            role=role,
            student_orders=student_orders,
            sm_excluded=excluded,
            patterns=tuple(found),
            moments=() if excluded else tuple(_moments(weeks, found)),
        ),
    )
