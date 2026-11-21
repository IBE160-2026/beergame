"""The Detected patterns (FR-44, AD-7, AD-23): their stored shape and their rules.

A closed list of three, stored together as one immutable versioned record of kind
`detected_patterns` in `modules/content`, which validates every version against `PatternSet`.
Each pattern has an exact definition worded as a pattern and never as a cause, its thresholds as
typed parameters, and one mechanism. The rules are documented in `facts.md`.

Pure (AD-1): stdlib and pydantic only."""

import re
from collections.abc import Sequence
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = [
    "MECHANISMS",
    "REVIEW",
    "LargeOrderFullSupplyLine",
    "LowAfterOvershoot",
    "Mechanism",
    "PatternSet",
    "SurgeAfterShortage",
]

_FROZEN = ConfigDict(frozen=True, extra="forbid")

REVIEW = "to be reviewed by two lecturers before pilot"
"""What the `review` field of a placeholder threshold set says (FR-44)."""

type Mechanism = Literal["delay", "supply_line", "demand_information_lost"]
MECHANISMS: tuple[str, ...] = ("delay", "supply_line", "demand_information_lost")
"""The mechanisms a pattern can match: delay, the Supply line, and demand information lost when
it travels only as orders (FR-44)."""

_CAUSE = re.compile(
    r"\b(fordi|derfor|grunnet|pga|på\s+grunn\s+av|som\s+følge\s+av|resultat\s+av|skyld\w*"
    r"|før\w*\s+til|medfør\w*|forårsak\w*|årsak\w*|because|caused?|due\s+to)\b",
    re.IGNORECASE,
)
"""Words that state a cause; a pattern describes what the Decision log shows, never why."""

_Text = Annotated[str, Field(min_length=1, max_length=500)]
_Ratio = Annotated[Decimal, Field(ge=0, le=100, max_digits=6, decimal_places=3)]
_Units = Annotated[int, Field(strict=True, ge=0, le=10_000)]
_Weeks = Annotated[int, Field(strict=True, ge=0, le=52)]


class _Pattern(BaseModel):
    model_config = _FROZEN

    name: _Text
    """A short label, Norwegian bokmål."""
    definition: _Text
    """The exact definition in words, Norwegian bokmål, worded as a pattern."""
    mechanism: Mechanism
    review: _Text
    """The thresholds' status: `REVIEW` while they are placeholders."""

    @model_validator(mode="after")
    def _a_pattern_not_a_cause(self) -> _Pattern:
        for text in (self.name, self.definition, self.review):
            if "!" in text or _CAUSE.search(text):
                raise ValueError(f"a pattern is worded as a pattern, not a cause: {text!r}")
        return self


def _well_above(order: int, incoming: int, min_ratio: Decimal, min_excess: int) -> bool:
    return order >= min_ratio * incoming and order - incoming >= min_excess


def _cover(units: int, incoming: int, weeks: Decimal) -> bool:
    """`units` hold at least `weeks` Weeks of the incoming order (at least 1 unit a Week)."""
    return units >= weeks * max(incoming, 1)


class SurgeAfterShortage(_Pattern):
    """An Order well above incoming orders after a shortage."""

    id: Literal["surge-after-shortage"]
    lookback_weeks: _Weeks
    """A shortage counts in the Week itself and in this many Weeks before it."""
    min_ratio: _Ratio
    min_excess: _Units

    @model_validator(mode="after")
    def _above_means_above(self) -> SurgeAfterShortage:
        if self.min_ratio < 1 or self.min_excess < 1:
            raise ValueError("an Order well above incoming orders needs min_ratio ≥ 1, excess ≥ 1")
        return self

    def matches(
        self,
        *,
        order: int,
        incoming: int,
        inventory: int,
        supply_line: int,
        backlogs: Sequence[int],
    ) -> bool:
        """`backlogs`: the Seat's backlog in the Weeks up to this one, oldest first. Every
        pattern takes the same arguments and reads the ones its rule names."""
        recent = backlogs[-(self.lookback_weeks + 1) :]
        shortage = any(backlog > 0 for backlog in recent)
        return shortage and _well_above(order, incoming, self.min_ratio, self.min_excess)


class LargeOrderFullSupplyLine(_Pattern):
    """A large Order while the Supply line already holds a lot."""

    id: Literal["large-order-full-supply-line"]
    min_ratio: _Ratio
    min_excess: _Units
    min_cover_weeks: _Ratio
    """The Supply line holds at least this many Weeks of the incoming order."""

    @model_validator(mode="after")
    def _large_means_large(self) -> LargeOrderFullSupplyLine:
        if self.min_ratio < 1 or self.min_excess < 1 or self.min_cover_weeks <= 0:
            raise ValueError("a large Order and a full Supply line need thresholds above zero")
        return self

    def matches(
        self,
        *,
        order: int,
        incoming: int,
        inventory: int,
        supply_line: int,
        backlogs: Sequence[int],
    ) -> bool:
        return _well_above(order, incoming, self.min_ratio, self.min_excess) and _cover(
            supply_line, incoming, self.min_cover_weeks
        )


class LowAfterOvershoot(_Pattern):
    """Very low Orders after an overshoot."""

    id: Literal["low-after-overshoot"]
    max_ratio: _Ratio
    min_shortfall: _Units
    min_cover_weeks: _Ratio
    """The overshoot: inventory holds at least this many Weeks of the incoming order."""

    @model_validator(mode="after")
    def _low_means_low(self) -> LowAfterOvershoot:
        if self.max_ratio > 1 or self.min_shortfall < 1 or self.min_cover_weeks <= 0:
            raise ValueError("a very low Order needs max_ratio ≤ 1, shortfall ≥ 1, cover > 0")
        return self

    def matches(
        self,
        *,
        order: int,
        incoming: int,
        inventory: int,
        supply_line: int,
        backlogs: Sequence[int],
    ) -> bool:
        low = order <= self.max_ratio * incoming and incoming - order >= self.min_shortfall
        return low and _cover(inventory, incoming, self.min_cover_weeks)


class PatternSet(BaseModel):
    """One version of the Detected pattern definitions: the closed list, in this order."""

    model_config = _FROZEN

    following_weeks: Annotated[int, Field(strict=True, ge=1, le=12)]
    """An occurrence's later cost sums the Seat's cost over this many following Weeks."""
    patterns: tuple[SurgeAfterShortage, LargeOrderFullSupplyLine, LowAfterOvershoot]
