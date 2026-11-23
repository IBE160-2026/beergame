"""The Klasserapport's response (Story 14.1, FR-64, FR-68, FR-70, FR-79, AD-10, AD-14).

Every number is the api's: medians, quartiles, means, shares and percents are computed in
`class_report.py` and sent as decimal strings, so the web app only formats them (AD-10). Game
numbers, Roles, Weeks and counts only: never a name, a `user_id` or a single rating (AD-14)."""

import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.engine.settings import Role
from app.modules.games.schemas import SeatMark
from app.modules.sessions.schemas import FunnelStageOut

__all__ = [
    "ClassReportOut",
    "DistributionOut",
    "GameAiOut",
    "GameCostOut",
    "PatternOut",
    "RatingCountOut",
    "RatingModeOut",
    "ReportAiOut",
    "ReportCostOut",
    "RoleAmplificationOut",
    "RoleCostDistributionOut",
    "SwitchOut",
]


class DistributionOut(BaseModel):
    """The values of a distribution (one per finished Class game, by game number, for the
    Kostnadsfordeling's ticks) with their median and quartiles (the inclusive method of
    `analysis.wall.quartiles`)."""

    values: list[Decimal]
    median: Decimal
    lower_quartile: Decimal
    upper_quartile: Decimal


class GameCostOut(BaseModel):
    """A finished Class game's chain Total cost, for «Vis som tabell»."""

    number: int | None
    chain_cost: Decimal


class RoleCostDistributionOut(BaseModel):
    """One Role's Total cost over the finished Class games: its distribution and its mean Lager
    and Restordre per game (`total_cost` is their sum), in kroner rounded to the øre."""

    role: Role
    distribution: DistributionOut
    holding_cost: Decimal
    backorder_cost: Decimal
    total_cost: Decimal


class ReportCostOut(BaseModel):
    """Kjedekost and Kostnad per Rolle (FR-64, UX-DR72): the chain cost's distribution with the
    chain's mean Lager and Restordre per game, and each Role in chain order (Detaljist first)."""

    chain: DistributionOut
    holding_cost: Decimal
    backorder_cost: Decimal
    roles: list[RoleCostDistributionOut]
    games: list[GameCostOut]


class RoleAmplificationOut(BaseModel):
    """One Role's Order amplification (`orders_std / demand_std`, the facts sets' chain part)
    over the covered games where demand varied; None without one."""

    role: Role
    games: int
    distribution: DistributionOut | None


class PatternOut(BaseModel):
    """A Detected pattern across the covered Class games: the occurrences in Weeks a Student
    decided, and in how many games at least one."""

    pattern: str
    name: str
    occurrences: int
    games: int


class GameAiOut(BaseModel):
    """One finished Class game's AI play (FR-68): its Orders outside Guided Weeks, those an LLM
    player decided and their share in percent (None with no Order), and those the fallback
    replaced (AD-15)."""

    number: int | None
    ordered: int
    llm: int
    llm_percent: Decimal | None
    fallback: int


class SwitchOut(BaseModel):
    """A switch by the cost limit or the Play guard: the game, the Seat's Role, the Week it took
    effect and its mark from the one AD-15 mapping."""

    number: int | None
    role: Role
    week: int
    mark: SeatMark


class ReportAiOut(BaseModel):
    """The share of Seats played by AI players (FR-64), the Share of LLM Orders per game and the
    switches (FR-68), and the share of LLM-held Seats the Play guard switched (FR-79)."""

    seats: int
    ai_seats: int
    whole_game: int
    ai_percent: Decimal | None
    games: list[GameAiOut]
    switches: list[SwitchOut]
    llm_seats: int
    guard_switched: int
    guard_percent: Decimal | None


class RatingCountOut(BaseModel):
    rating: int
    count: int


class RatingModeOut(BaseModel):
    """The plausibility ratings of one AI mode (FR-70): the count of each value 1–5, their
    number and median. Never a single rating or who gave it."""

    ai_mode: Literal["llm", "rule_based"]
    count: int
    median: Decimal
    values: list[RatingCountOut]


class ClassReportOut(BaseModel):
    """The Klasserapport of a Class session (Story 14.1). `games` counts its Class games,
    `finished` those finished, which every game figure is over, and `facts_games` those of them
    whose every Seat has its stored facts set, which Forsterkning and Mønstre are over. `cost` is
    None while no game has finished."""

    class_session_id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    session_number: int
    games: int
    finished: int
    facts_games: int
    funnel: list[FunnelStageOut]
    cost: ReportCostOut | None
    amplification: list[RoleAmplificationOut]
    patterns: list[PatternOut]
    ai: ReportAiOut
    ratings: list[RatingModeOut]
