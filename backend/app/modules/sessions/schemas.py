"""API shapes of `modules/sessions` (Stories 5.1 to 5.8)."""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictInt

from app.engine import GameSettings
from app.engine.settings import Role
from app.modules.games.service import Lifecycle, SeatMark, SeatState


class AiMode(StrEnum):
    """Who holds the AI Seats of the Class session's games (FR-15)."""

    llm = "llm"
    rule_based = "rule_based"


class DebriefMode(StrEnum):
    """How the Debrief is held (FR-16): the four of a Class game together, or each alone."""

    group = "group"
    personal = "personal"


LlmUnavailable = Literal["no_default_model"]
"""Why LLM players cannot be chosen now: no model config is pinned as the default (FR-15)."""


DateName = Literal["start_at", "play_deadline", "debrief_deadline", "test_deadline"]
"""The four dates of a Class session in their order: Startdato, Spillfrist, Debrieffrist and
Testfrist (FR-18)."""

DeadlineName = Literal["play_deadline", "debrief_deadline", "test_deadline"]
"""The three deadlines a Student is reminded of 24 hours ahead (Story 5.14)."""

AllocationMethod = Literal["random", "student_choice"]
"""How the Students get their Seats (Story 5.17, FR-20, FR-21): drawn at random by the Lecturer
(Stories 5.8 to 5.13), or taken by each Student before the Start date."""

DateKind = Literal["start", "play", "debrief", "test"]
"""A date by what it is, for «Neste frist»."""


class SettingProblem(BaseModel):
    """Why one Game setting is refused (Story 5.3, FR-12): the engine's stable code and the range
    that applies, its bounds as decimal strings («1», «100.00»), or None when the rule has none."""

    code: str
    minimum: str | None
    maximum: str | None
    decimal_places: int | None
    """For a cost rate: the most decimal places it takes."""


class SettingWarning(BaseModel):
    """A legal but unusual Game setting (FR-12): the engine's code, the setting it stands under,
    and the numbers behind it as decimal strings. It never blocks a save."""

    code: str
    field: str
    values: dict[str, str]


class SettingsCheckIn(BaseModel):
    """A draft of the Game settings to judge without saving: the editable settings, laid
    over the stored settings. Values are sent as typed, so the engine judges them all."""

    model_config = ConfigDict(extra="forbid")

    game_settings: dict[str, Any]


class SettingsCheckOut(BaseModel):
    """What the engine says of a draft (FR-12): the errors by setting, which block a save, and the
    warnings, which do not."""

    errors: dict[str, SettingProblem]
    warnings: list[SettingWarning]


class DemandSeriesOut(BaseModel):
    """The customer demand of Weeks 1 to the last, as the engine materialises it from the stored
    Demand pattern and seed (Story 5.4, FR-13): `demand[w - 1]` is the demand in Week w. For the
    Class's staff only; no Student-facing answer carries it (AD-3)."""

    demand: list[int]


class OfferedEffortLevelOut(BaseModel):
    """An Effort level the Class session may use (Story 5.5, FR-78), as the model config holds it
    and `ai.config.offered_effort_levels` offers it: nothing here is written by `sessions`."""

    name: str
    label: str | None
    """The config's Norwegian name for the level; None: show `name`."""
    effect: str | None
    """The config's one line on the effect on speed and cost; None for a config stored before."""
    default: bool
    time_per_order_median_s: str | None
    """The newest counting measurement's median seconds per Order, a decimal string; None when
    it has no figures (the seeded mock)."""
    cost_per_game_usd: str | None
    """The same measurement's cost per game in USD, a decimal string, or None."""


class AiDescriptionsOut(BaseModel):
    """The plain-language Norwegian description of each AI player type, from
    `players.service.describe` (FR-33): Markdown with a title line, paragraphs and `- ` lists."""

    llm: str
    rule_based: str


class LabHourIn(BaseModel):
    """A Lab hour as the Lecturer adds or changes it (Story 5.6, FR-19): its start and end as
    instants with their offset, and its place. The service judges the rules (`invalid_lab_hour`),
    so a blank or long place gets its reason rather than a schema error."""

    model_config = ConfigDict(extra="forbid")

    starts_at: AwareDatetime
    ends_at: AwareDatetime
    place: str = Field(max_length=1000)


class LabHourOut(BaseModel):
    """A Lab hour as the Class's staff read it, UTC; the web app shows it in Europe/Oslo."""

    id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    place: str
    ended: bool
    """It has ended by the server's clock; it no longer changes or goes."""


class EnrolledLabHourOut(BaseModel):
    """An upcoming Lab hour as a Student reads it (Story 5.6, FR-19), for Epic 6's Hjem."""

    id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    place: str


class CopiedFromOut(BaseModel):
    """The source of a copied Class session, as the Klasseøkt names it."""

    id: uuid.UUID
    class_name: str
    number: int


class ReplacedLevelOut(BaseModel):
    """An Effort level of the source the new model config does not offer: its name, and the
    source config's Norwegian label (None: show `name`)."""

    name: str
    label: str | None


class ClassSessionOut(BaseModel):
    """One Class session as its Class's staff read it."""

    id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    number: int
    """«Klasseøkt 2»: its place among its Class's sessions, oldest first, from 1."""
    game_settings: GameSettings
    """The engine's `GameSettings` the Class session holds, its demand seed included."""
    is_classic: bool
    """Whether the Game settings are the Classic preset (the demand seed aside): «Alt er fylt ut
    med standardene.» shows only then. The server decides; the web app compares nothing."""
    ai_mode: AiMode
    debrief_mode: DebriefMode
    inactivity_limit_hours: int
    """«Ventetid før KI tar over» in whole hours, never under 20 (Story 5.7, FR-36)."""
    obligatory: bool
    """The Lecturer marked it as stated in the course plan (Story 5.7, FR-17)."""
    required_share_percent: int
    """«Andel uker som kreves», a whole percent from 1 to 100 (Story 5.7). Stored whether or not
    the session is obligatory; nothing in this epic computes Completion with it."""
    llm_unavailable: LlmUnavailable | None
    """Set while LLM players cannot be chosen; the screen says why (FR-15, AD-17)."""
    effort_level: str | None
    """The Effort level in force (Story 5.5): a name among the config's levels; None for
    Rule-based players."""
    effort_levels: list[OfferedEffortLevelOut]
    """The levels offered by the session's model config, or by the active default while it has
    none, in the config's order; empty when there is no config to offer from."""
    ai_descriptions: AiDescriptionsOut
    provider_unavailable: bool
    """LLM players are chosen but the session's model config offers no level here: in
    production, its provider has no key. The Class session cannot open until it is set up
    (AD-17); the screen says so before the Start date."""
    saved_at: datetime | None
    """When «Lagre Klasseøkt» last saved it; None while it was never saved."""
    created_at: datetime
    can_manage: bool
    """Whether the User may change it: an owner of the Class, while the Class is not archived."""
    start_at: datetime | None
    play_deadline: datetime | None
    debrief_deadline: datetime | None
    test_deadline: datetime | None
    """The four dates in UTC, None until set (Story 5.2). The web app shows them in Europe/Oslo."""
    locked: bool
    """`service.is_locked`: the session is locked or its Start date has passed. Settings no
    longer change; deadlines that have not passed still move."""
    locked_at: datetime | None = None
    """When the lock froze the session (Story 5.11); None until then, also for a while after the
    Start date has passed (the sweep runs each minute, or the lock is refused)."""
    lock_refused: bool = False
    """Not locked, and the sweep has refused the lock for a missing provider key (GitHub issue
    109): LLM players and no key for the model's provider. The sweep tries again each minute."""
    passed_dates: list[DateName]
    """The dates that are set and have passed by the server's clock; they no longer move."""
    play_time_warning: bool
    """The time between the Start date and the Play deadline is shorter than the configured
    least playing time per Week times the Weeks. Never true while that value is unset (SM-11)."""
    settings_warnings: list[SettingWarning]
    """The engine's warnings on the stored Game settings, in its order (Story 5.3)."""
    calibrated_settings: GameSettings
    """The settings the product's content and Play guard were calibrated for: the Classic
    preset, so the web app holds no copy of it (FR-12)."""
    lab_hours: list[LabHourOut]
    """The Lab hours that were not removed, by start (Story 5.6); ended ones too."""
    capacity_enabled: bool
    """`FEATURE_CAPACITY` (Story 5.15, AD-17): the Klasseøkt offers a shipping capacity. Off, the
    screen shows nothing about capacity and the api refuses one (`feature_disabled`)."""
    info_visibility_enabled: bool
    """`FEATURE_INFO_VISIBILITY` (Story 5.16, AD-17): the Klasseøkt offers Information
    visibility. Off, the screen shows nothing about it and the api refuses a view switched on
    (`feature_disabled`)."""
    allocation_method: AllocationMethod = "random"
    """How the Students get their Seats (Story 5.17). `student_choice` is final once saved."""
    student_choice_enabled: bool = False
    """`FEATURE_STUDENT_CHOICE` (Story 5.17, AD-17): the Klasseøkt offers Student choice. Off, the
    screen shows no allocation-method choice and the api refuses Student choice
    (`feature_disabled`)."""
    copied_from: CopiedFromOut | None = None
    """The Class session this one was copied from (Story 5.18); None for one made with «Lag
    Klasseøkt», and when the source is gone or the User may no longer read it."""
    effort_level_replaced: ReplacedLevelOut | None = None
    """The source's Effort level when the new model config did not offer it, so the copy took
    that config's default (Story 5.18, FR-78)."""


class CopyIn(BaseModel):
    """«Lag kopi» (Story 5.18, FR-66): the Class session to copy, and whether to keep its demand
    seed (a fresh one is drawn otherwise)."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(max_length=64)
    """A Class session id; one that is not an id answers 403 `forbidden` like any other the User
    may not reach (FR-5)."""
    keep_seed: bool = False


class CopySourceOut(BaseModel):
    """A Class session the Lecturer may copy: one of a Class they are staff of."""

    id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    number: int
    start_at: datetime | None
    archived: bool
    """Its Class is archived (Story 4.10); it may still be copied."""


class CopySourceListOut(BaseModel):
    """The Class sessions a rerun may copy, newest first. No paging: a Lecturer has a handful."""

    items: list[CopySourceOut]


class ClassSessionListItem(BaseModel):
    id: uuid.UUID
    number: int
    """«Klasseøkt 2»: its place among its Class's sessions, oldest first, from 1."""
    created_at: datetime
    saved_at: datetime | None


class ClassSessionListOut(BaseModel):
    """The Class sessions of one Class, newest first. No paging: a Class has a handful."""

    items: list[ClassSessionListItem]
    rerun_enabled: bool = False
    """`FEATURE_RERUN` (Story 5.18, AD-17): the Klasse page offers «Lag fra en tidligere
    Klasseøkt». Off, the page shows no copy option and the copy routes answer
    `feature_disabled`."""


class DatesIn(BaseModel):
    """The four dates as the Lecturer set them, each an instant with its offset or None."""

    model_config = ConfigDict(extra="forbid")

    start_at: AwareDatetime | None
    play_deadline: AwareDatetime | None
    debrief_deadline: AwareDatetime | None
    test_deadline: AwareDatetime | None


class ClassSessionSaveIn(BaseModel):
    """«Lagre Klasseøkt». The screen sends the AI mode, Effort level and Debrief mode as chosen
    (Story 5.5), the four dates (Story 5.2) and the Game settings (Story 5.3) with the Demand
    pattern and its seed (Story 5.4), and the obligatory mark, its required share and the
    Inactivity limit (Story 5.7); a field left out keeps its value. `game_settings` is laid over
    the stored settings, so a setting left out keeps its value. With Rule-based players no Effort
    level is in force, and a sent one is ignored."""

    model_config = ConfigDict(extra="forbid")

    ai_mode: AiMode
    effort_level: str | None = Field(None, min_length=1, max_length=64)
    debrief_mode: DebriefMode | None = None
    dates: DatesIn | None = None
    game_settings: dict[str, Any] | None = None
    obligatory: bool | None = None
    required_share_percent: StrictInt | None = Field(None, ge=-1000, le=1000)
    """Whole percent, a JSON integer (no string, boolean or float); the service answers
    `out_of_range` outside 1 to 100. The bounds here only keep the value an integer the database
    holds."""
    inactivity_limit_hours: StrictInt | None = Field(None, ge=-100_000, le=8760)
    """Whole hours; the service answers `below_minimum` under 20. At most a year (a guard)."""
    allocation_method: AllocationMethod | None = None
    """Story 5.17: `student_choice` opens the Students' choice of a Class game and a Seat; left
    out, the method stays."""


class NextDeadline(BaseModel):
    kind: DateKind
    at: datetime


class SeatRef(BaseModel):
    """A Seat named by its Class game's number and its Role: «Grossist i Spill 17»."""

    game_number: int
    role: Role


TableHolder = Literal["student", "ai", "free"]


class TableSeatOut(BaseModel):
    """A Seat of the Student's Class game (Story 6.1, FR-22, FR-34): its Role and who holds it,
    a Student by name, any AI player as «KI-spiller» (`ai`, never which kind), or free."""

    role: Role
    holder: TableHolder
    name: str | None
    """The Student's name now; None for an AI player, a free Seat, or a Student no longer in the
    Class."""
    mine: bool
    ordered: bool | None
    """Story 6.14 (FR-25): whether the Seat has ordered in the open Week (in a Guided Week the
    Student's view counts); None when the game is not running."""
    wait_started_at: AwareDatetime | None
    """When the game began to wait for the Seat (the stored time; the web app counts the wait
    from `server_now`); None once ordered, before any Student ordered, or not running."""
    mark: SeatMark | None
    """`guard_switch`: an AI Seat the Play guard gave a rule-based KI-spiller; else None."""


class GameRulesOut(BaseModel):
    """The rules «Regler før første ordre» states (Story 6.2, FR-84), from the Class session's
    frozen settings: the delays, the number of Veiledede uker and the two cost rates. Never the
    number of Weeks, the demand, its seed or the largest Order (FR-14, AD-3)."""

    order_delay: int
    shipping_delay: int
    production_delay: int
    guided_weeks: int
    holding_cost: Decimal
    backorder_cost: Decimal


GamePlayStatus = Literal["not_ready", "ready", "running", "finished"]


class PlayTurnOut(BaseModel):
    """The Student's own turn in the open Week (Story 6.10): whether it is a Guided Week, the
    Seat's Order once placed (in a Guided Week the fixed Order, placed when the Week opened) and
    whether the Student has opened the Guided Week. Never how many Guided Weeks there are."""

    guided: bool
    order: int | None
    viewed: bool


class StudentGameOut(BaseModel):
    """The Student's Class game on Hjem (Story 6.1): «Spill 17 · Du er Grossist» and the four
    Seats, Fabrikk first (UX-DR73). Only from the Start date (`is_locked`)."""

    id: uuid.UUID
    number: int
    role: Role
    seats: list[TableSeatOut]
    briefing_first: bool
    """Story 6.2: the briefing comes first, until the Student has done the Starting task
    (`progress` `starting_task`). Nothing is stored for "briefing read"."""
    rules: GameRulesOut
    status: GamePlayStatus
    """Story 6.5: `not_ready` before the lock has given the Game its snapshot, `ready` to start,
    `running` (also while it plays out), or `finished`."""
    week: int | None
    """The open Week while `running`, else None. Never the number of Weeks (FR-14)."""
    server_now: AwareDatetime
    """The database clock when the game was read (Story 6.14): the Seats' waits count from it."""
    seat_state: SeatState | None
    """Story 6.17 (AD-3): what the Student's own Seat sees in the open Week while the game runs,
    from the same `games.views.seat_state` as the play envelope, so Hjem's Spillkort and the play
    screen never disagree; None unless `running`."""
    turn: PlayTurnOut | None
    """Story 6.17: the own turn in the open Week (the Order once placed), as in the play envelope;
    None unless `running`."""


class TableStatusOut(BaseModel):
    """Who sits in each Seat of the game, Fabrikk first (AD-3, UX-DR73): people, never numbers."""

    seats: list[TableSeatOut]


class OrderIn(BaseModel):
    """The Student's Order for the open Week (Story 6.12): one whole number; the command checks
    it lies from 0 to the Game settings maximum (`order_invalid`)."""

    model_config = ConfigDict(extra="forbid")

    order: StrictInt


class PlayOut(BaseModel):
    """The play screen's one envelope (Story 6.6, AD-3): what the Student's own Seat sees in the
    open Week (`seat_state`, numbers and Roles only), the own turn (`turn`, Story 6.10) and who
    sits where (`table_status`), with the server's clock. Never the number of Weeks, future
    demand, another Seat's numbers or a reference Order (FR-14, FR-23)."""

    seat_state: SeatState
    turn: PlayTurnOut
    table_status: TableStatusOut
    server_now: AwareDatetime
    """The database clock when the envelope was read, the clock every stored time is on (AD-20):
    durations are counted from it, never from the browser's clock."""
    next_change_at: AwareDatetime | None
    """The nearest time at which the envelope changes by time alone (Story 6.14): the earliest
    stored AI deadline of a Seat that has not ordered, while it lies after `server_now`; None
    while nothing is due. The web app reads the envelope again then."""


StegeneStep = Literal["class_game", "debrief", "quiz", "replay", "test", "report"]
StepState = Literal["done", "current", "locked"]


class StepOut(BaseModel):
    """A step of Stegene (Story 6.1, UX-DR29, AD-10, AD-16), its state computed here: the web app
    holds no rule for which step is open."""

    step: StegeneStep
    state: StepState


class EnrolledSessionOut(BaseModel):
    """A Class session as its Student reads it (Story 5.2, FR-18, AD-3): the dates and the next
    deadline that applies. Never the Game settings, the number of Weeks or the demand."""

    id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    number: int
    start_at: datetime | None
    play_deadline: datetime | None
    debrief_deadline: datetime | None
    """The Student's own Debrief deadline (`service.effective_debrief_deadline`)."""
    test_deadline: datetime | None
    """The Student's own Test deadline (`service.effective_test_deadline`)."""
    next_deadline: NextDeadline | None
    """The earliest of the Play, Debrief and Test deadline still ahead; None when none is."""
    obligatory: bool
    lab_hours: list[EnrolledLabHourOut]
    """The Lab hours that have not ended and were not removed, by start (Story 5.6)."""
    seat_choice_open: bool = False
    """Story 5.17: the Student may choose a Class game and a Seat now («Velg spill og sete»):
    `FEATURE_STUDENT_CHOICE` is on, the session uses Student choice and is not locked."""
    drawn_seat: SeatRef | None = None
    """Story 5.17: once locked, the Seat the draw gave this Student because they chose none
    («Du fikk et sete ved trekning: Grossist i Spill 17.»); None otherwise and with the flag off."""
    game: StudentGameOut | None = None
    """Story 6.1: the Student's Class game, from the Start date (`is_locked`) and once they hold
    or have held a Seat in it; None before, also after a confirmed allocation."""
    steps: list[StepOut] = []
    """Story 6.1: Stegene's six steps in order, Klassespill first. With no game every step not
    done is `locked`; with one, the first step not done is `current`."""


class EnrolledSessionListOut(BaseModel):
    items: list[EnrolledSessionOut]


WaitingReason = Literal["dates", "allocation"]


class SessionRef(BaseModel):
    id: uuid.UUID
    number: int
    lacks: list[WaitingReason]
    """What the Class session still waits for: a date (Story 5.2), a confirmed allocation before
    its lock (Story 5.9), or both, in that order."""


class WaitingClass(BaseModel):
    """A Class with Class sessions that still lack a date or a confirmed allocation."""

    class_id: uuid.UUID
    class_name: str
    sessions: list[SessionRef]


class NextDate(BaseModel):
    kind: DateKind
    at: datetime
    session_id: uuid.UUID
    number: int
    class_id: uuid.UUID
    class_name: str


class LecturerOverviewOut(BaseModel):
    """The Lærerhjem's «Venter» and «Neste frist» (Story 5.2, UX-DR56): over the User's Classes
    that are not archived."""

    waiting: list[WaitingClass]
    next_date: NextDate | None


class AllocationSeatOut(BaseModel):
    """One Seat of a Class game in the draft (Story 5.8). `user_id` None is an empty Seat (an AI
    player at the lock). `name` is resolved now through `classes.service.student_names`; None
    with a `user_id` means the Student is no longer in the Class."""

    role: Role
    user_id: uuid.UUID | None
    name: str | None


class AllocationStudentOut(BaseModel):
    """A registered Student without a Seat (Story 5.13)."""

    user_id: uuid.UUID
    name: str


class AllocationGameOut(BaseModel):
    """One Class game of the draft: its number and its four Seats, Fabrikk first."""

    number: int
    seats: list[AllocationSeatOut]
    lifecycle: Lifecycle | None = None
    """The Class game's lifecycle once the games are open (Story 5.12); None before."""


class AllocationDraftOut(BaseModel):
    """The stored draft (Story 5.8, FR-20): what the preview shows, never a recomputation.
    Story 5.9 confirms it by `id` and `revision`."""

    id: uuid.UUID
    revision: int
    drawn_at: datetime
    games: list[AllocationGameOut]


class AllocationOut(BaseModel):
    """The «Fordeling» block: the registered Students now, those of them not in the draft (they
    registered after it was drawn), and the draft, None until one is drawn."""

    registered_count: int
    missing_count: int
    draft: AllocationDraftOut | None
    confirmed: bool
    """The Lecturer confirmed the draft (Story 5.9): its Class games exist, and only move and
    swap remain (Story 5.10)."""
    confirmed_at: datetime | None
    """When the draft was confirmed, for «Fordelingen er bekreftet {dato}.» (Issue #107)."""
    opened: bool = False
    """Every Class game has its snapshot and AI players (Story 5.12): the games then list the
    Seats as the Class games hold them, each with its `lifecycle`."""
    method: AllocationMethod = "random"
    """Story 5.17: with `student_choice` the games are the Class games as their Seats hold them,
    from the save on, empty ones included; `missing_count` is the registered Students without a
    Seat. Nothing is drawn, confirmed or moved from the panel then."""
    without_seat: list[AllocationStudentOut] = []
    """Once the session is locked: the registered Students no Class game could seat (Story
    5.13), by name. Empty before the lock, when a late registrant is seated within a minute."""


class AllocationConfirmIn(BaseModel):
    """«Bekreft fordeling» (Story 5.9): the draft the Lecturer is looking at."""

    model_config = ConfigDict(extra="forbid")

    draft_id: uuid.UUID
    revision: StrictInt


class AllocationMoveIn(BaseModel):
    """Move or swap in the allocation (Story 5.10): the draft the Lecturer is looking at, the
    Seat of the Student who moves, and the Seat they move to. A Student in that Seat takes the
    first Seat (a swap)."""

    model_config = ConfigDict(extra="forbid")

    draft_id: uuid.UUID
    revision: StrictInt
    from_game: StrictInt
    from_role: Role
    to_game: StrictInt
    to_role: Role


# Student choice (Story 5.17, FR-21, UX-DR62).


class SeatChoiceIn(BaseModel):
    """«Ta setet …»: the Seat the Student takes. Anything that names no Seat of the Class
    session's games answers 422 `invalid_seat`."""

    model_config = ConfigDict(extra="forbid")

    game_number: StrictInt = Field(ge=-1_000_000, le=1_000_000)
    role: str = Field(max_length=32)


SeatHolder = Literal["free", "student", "ai"]


class SeatChoiceSeatOut(BaseModel):
    """One Seat as «Velg spill og sete» lists it: free, a Student (named now; None once removed
    from the Class) or, after the lock, an AI player. `mine` marks the reader's own Seat."""

    role: Role
    holder: SeatHolder
    name: str | None
    mine: bool


class SeatChoiceGameOut(BaseModel):
    number: int
    seats: list[SeatChoiceSeatOut]
    """Fabrikk first, Detaljist last, as every Seat list of the Klasseøkt."""


class SeatChoiceOut(BaseModel):
    """«Velg spill og sete» (Story 5.17): the Class session's Class games with their Seats, and
    the reader's own Seat. Never the Game settings, the number of Weeks or the demand."""

    class_session_id: uuid.UUID
    class_name: str
    number: int
    start_at: datetime | None
    open: bool
    """The Student may take or change a Seat: the session is not locked."""
    my_seat: SeatRef | None
    drawn: bool
    """The Student's Seat came from the draw at the lock, not from their own choice."""
    games: list[SeatChoiceGameOut]
