"""Demand patterns and the customer demand series (FR-13, AD-1).

A pattern gives each Week a level; `random` and `step+noise` add discrete uniform noise of
`spread` around it. The draw for Week w is `SHA-256(f"{seed}:{w}")` read as one big-endian
integer modulo `2 * spread + 1`, so the series depends only on the pattern, the seed and the
Week, and is the same on every platform and Python version. A drawn value below 0 becomes 0.
The engine never gathers entropy: a caller passes it to `new_seed`.
"""

import hashlib
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

FROZEN = ConfigDict(frozen=True, extra="forbid")

Level = Annotated[int, Field(strict=True, ge=0)]
WeekNumber = Annotated[int, Field(strict=True, ge=1)]
Spread = Annotated[int, Field(strict=True)]
"""Signed on purpose: a negative spread is reported by `validate` with its allowed range."""

SEED_MAX = 999_999_999
"""Seeds are whole numbers from 0 to this: short enough to show, store and type again."""

MIN_ENTROPY_BYTES = 8


class DemandFixed(BaseModel):
    """A fixed series: `values[w - 1]` is the demand in Week w."""

    model_config = FROZEN

    kind: Literal["fixed"]
    values: Annotated[tuple[Level, ...], Field(min_length=1)]

    @property
    def spread(self) -> int:
        return 0

    def level_for(self, week: int) -> int:
        return self.values[week - 1]

    @property
    def starting_level(self) -> int:
        return self.values[0]

    @property
    def first_change_week(self) -> int | None:
        """The first Week whose demand differs from Week 1, or None when demand is flat."""
        for week, value in enumerate(self.values, start=1):
            if value != self.values[0]:
                return week
        return None

    @property
    def peak(self) -> int:
        return max(self.values)


class _Stepped(BaseModel):
    """`start` until `change_week`, then `new_level` from that Week on."""

    model_config = FROZEN

    start: Level
    new_level: Level
    change_week: WeekNumber

    def level_for(self, week: int) -> int:
        return self.new_level if week >= self.change_week else self.start

    @property
    def starting_level(self) -> int:
        return self.start

    @property
    def first_change_week(self) -> int | None:
        """The first Week whose level differs from `start`, or None when the levels match."""
        return self.change_week if self.new_level != self.start else None


class DemandStep(_Stepped):
    """Customer demand `start` until `change_week`, then `new_level` from that Week on."""

    kind: Literal["step"]

    @property
    def spread(self) -> int:
        return 0

    @property
    def peak(self) -> int:
        return max(self.start, self.new_level)


class DemandStepNoise(_Stepped):
    """A step in the mean with discrete uniform noise of `spread` around it."""

    kind: Literal["step+noise"]
    spread: Spread

    @property
    def peak(self) -> int:
        return max(self.start, self.new_level) + self.spread


class DemandRandom(BaseModel):
    """Discrete uniform demand over `mean - spread` to `mean + spread`, never below 0."""

    model_config = FROZEN

    kind: Literal["random"]
    mean: Level
    spread: Spread

    def level_for(self, week: int) -> int:
        return self.mean

    @property
    def starting_level(self) -> int:
        return self.mean

    @property
    def first_change_week(self) -> int | None:
        return None

    @property
    def peak(self) -> int:
        return self.mean + self.spread


DemandPattern = Annotated[
    DemandFixed | DemandStep | DemandRandom | DemandStepNoise, Field(discriminator="kind")
]

SEEDED_KINDS = frozenset({"random", "step+noise"})
"""Pattern kinds whose series needs a seed."""


def _noise(seed: int, week: int, spread: int) -> int:
    digest = hashlib.sha256(f"{seed}:{week}".encode("ascii")).digest()
    return int.from_bytes(digest, "big") % (2 * spread + 1) - spread


def week_noise(seed: int, week: int, spread: int) -> int:
    """The variation `seed` draws for `week`: from `-spread` to `spread`, the same draw a seeded
    pattern adds to its level (the Replay scenario's fixed series uses it, Story 10.1)."""
    return _noise(seed, week, spread)


def series(pattern: DemandPattern, weeks: int, seed: int | None = None) -> tuple[int, ...]:
    """The customer demand of Weeks 1 to `weeks`, one whole number per Week.

    Raises ValueError when the inputs break what `validate` checks: a fixed series of another
    length, a negative spread, or a missing or out-of-range seed for a seeded pattern.
    """
    if type(weeks) is not int or weeks < 1:
        raise ValueError(f"a series needs a whole number of Weeks from 1, not {weeks!r}")
    if isinstance(pattern, DemandFixed) and len(pattern.values) != weeks:
        raise ValueError(f"the fixed series has {len(pattern.values)} Weeks, not {weeks}")
    if pattern.spread < 0:
        raise ValueError(f"spread cannot be negative ({pattern.spread})")
    if pattern.kind not in SEEDED_KINDS:
        return _materialise(pattern, weeks, None)
    if type(seed) is not int or not 0 <= seed <= SEED_MAX:
        raise ValueError(f"a {pattern.kind} pattern needs a seed from 0 to {SEED_MAX}")
    return _materialise(pattern, weeks, seed)


@lru_cache(maxsize=256)
def _materialise(pattern: DemandPattern, weeks: int, seed: int | None) -> tuple[int, ...]:
    """Bounded cache: the Week sequence looks the series up once per Week."""
    if seed is None:
        return tuple(pattern.level_for(week) for week in range(1, weeks + 1))
    return tuple(
        max(0, pattern.level_for(week) + _noise(seed, week, pattern.spread))
        for week in range(1, weeks + 1)
    )


def new_seed(entropy: bytes) -> int:
    """A fresh seed from entropy the caller gathered (e.g. `secrets.token_bytes(16)`)."""
    if not isinstance(entropy, bytes):
        raise TypeError(f"entropy must be bytes, not {type(entropy).__name__}")
    if len(entropy) < MIN_ENTROPY_BYTES:
        raise ValueError(f"entropy needs at least {MIN_ENTROPY_BYTES} bytes, not {len(entropy)}")
    return int.from_bytes(hashlib.sha256(entropy).digest(), "big") % (SEED_MAX + 1)
