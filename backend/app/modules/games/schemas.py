"""Value types of the games module."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.engine import (
    CostLine,
    GameSettings,
    OrderPreview,
    Role,
    SeatView,
    SupplyLineSlot,
    Violation,
    WeekValues,
)


class Purpose(StrEnum):
    """Why a Game exists (AD-13). `games.policy` says what each one means."""

    CLASS = "class"
    REPLAY = "replay"
    MAKEUP = "makeup"
    LECTURER_TEST = "lecturer_test"
    SIMULATION = "simulation"


class Lifecycle(StrEnum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PLAYING_OUT = "playing_out"
    FINISHED = "finished"


class GameStatus(StrEnum):
    """A Game's status as staff see it (FR-39), from `games.rules.game_status` only (AD-2);
    `paused` from Story 8.6 (FR-89)."""

    NOT_STARTED = "not_started"
    RUNNING = "running"
    WAITING = "waiting"
    PAUSED = "paused"
    FINISHED = "finished"


class OccupantKind(StrEnum):
    """Who holds a Seat from a Week on (AD-5)."""

    STUDENT = "student"
    LLM = "llm"
    RULE_BASED = "rule_based"
    SCRIPTED = "scripted"


class OccupancyReason(StrEnum):
    INITIAL = "initial"
    TAKEOVER_INACTIVITY = "takeover_inactivity"
    TAKEOVER_STAFF = "takeover_staff"
    TAKEOVER_PEER = "takeover_peer"
    RECLAIM = "reclaim"
    GUARD_SWITCH = "guard_switch"
    COST_LIMIT = "cost_limit"
    PLAYOUT = "playout"
    MOVED = "moved"
    """The Seat was freed before the start: its Student moved to another Seat (Story 5.10). The
    row has no occupant kind; it is the only reason such a row has."""


class SeatMark(StrEnum):
    """What a Seat's row says beyond its holder (AD-15, Story 6.14), from the one mapping
    `games.service.seat_mark`. Story 7.7 adds a mark for every other occupancy `reason` and every
    `fallback` (FR-34, FR-62)."""

    GUARD_SWITCH = "guard_switch"
    """The Play guard switched the Seat's LLM player to a Rule-based player (FR-79)."""
    COST_LIMIT = "cost_limit"
    """The cost limit switched the Seat's LLM player to a Rule-based player."""
    TAKEOVER_INACTIVITY = "takeover_inactivity"
    """An AI player took the Seat over after the Inactivity limit (FR-37)."""
    TAKEOVER_STAFF = "takeover_staff"
    """A Lecturer or Assistant lecturer put an AI player in the Seat (Epic 8)."""
    TAKEOVER_PEER = "takeover_peer"
    """The other Students of the game put an AI player in the Seat (Epic 8)."""
    RECLAIM = "reclaim"
    """The Student took the Seat back from an AI player."""
    PLAYOUT = "playout"
    """An AI player played the game out to its end."""
    FALLBACK_TIMEOUT = "fallback_timeout"
    """The Order is the Rule-based reference: the LLM call timed out (FR-32)."""
    FALLBACK_INVALID_OUTPUT = "fallback_invalid_output"
    """The Order is the Rule-based reference: the LLM answer was not a valid Order."""
    FALLBACK_BUDGET_EXHAUSTED = "fallback_budget_exhausted"
    """The Order is the Rule-based reference: the AI budget was used up."""
    FALLBACK_PROVIDER_ERROR = "fallback_provider_error"
    """The Order is the Rule-based reference: the model provider failed."""


class DecidedBy(StrEnum):
    """Who decided an Order in the Decision log (AD-15)."""

    STUDENT = "student"
    LLM = "llm"
    RULE_BASED = "rule_based"
    SCRIPTED = "scripted"
    GUIDED = "guided"


class Fallback(StrEnum):
    """Why an Order is not the occupant's own decision (FR-32, AD-15): `none`, or the typed
    failure of the LLM call whose Week got the Rule-based reference Order instead. Kept apart
    from `decided_by`, which then says `rule_based`."""

    NONE = "none"
    TIMEOUT = "timeout"
    INVALID_OUTPUT = "invalid_output"
    BUDGET_EXHAUSTED = "budget_exhausted"
    PROVIDER_ERROR = "provider_error"


_FROZEN = ConfigDict(frozen=True, extra="forbid")


class SessionRuntime(BaseModel):
    """The runtime part of a Game's snapshot (AD-4). Later epics add fields here (Inactivity
    limit, prompt and content versions)."""

    model_config = _FROZEN

    schema_version: Literal[1] = 1
    ai_mode: Literal["llm", "rule_based"]
    rule_based_params: str
    """Id of the Rule-based parameter set every Rule-based player of the Game uses."""
    rule_based_params_version: int
    model_config_id: str | None = None
    """The model config every LLM player of the Game uses (AD-22, FR-78); None: no LLM player
    may hold a Seat."""
    effort_level: str | None = None
    """The config's Effort level the Game froze, set together with `model_config_id`."""
    play_guard_params: str | None = None
    """Id of the Play guard parameter set the Game froze (FR-79); None only on Games created
    before Story 2.10, for which the guard does not run."""
    play_guard_params_version: int | None = None
    inactivity_limit_hours: int | None = None
    """The Class session's Inactivity limit the lock froze (Story 5.11); None on other Games."""
    prompt_versions: dict[str, int] | None = None
    """The prompt version per purpose of `model_config_id`, frozen with it (Story 5.11)."""
    pins: dict[str, Any] | None = None
    """The open map of pinned content versions and further runtime fields that the Class
    session's lock fills from its registered pin providers (Story 5.11, AD-23)."""

    @model_validator(mode="after")
    def _config_and_level(self) -> SessionRuntime:
        if (self.model_config_id is None) != (self.effort_level is None):
            raise ValueError("model_config_id and effort_level are set together")
        if (self.play_guard_params is None) != (self.play_guard_params_version is None):
            raise ValueError("play_guard_params and its version are set together")
        return self


class SeatOverview(BaseModel):
    model_config = _FROZEN

    id: str
    role: str
    occupant_kind: OccupantKind | None
    """The current occupant; None while the Seat is free."""
    policy_id: str | None
    user_id: str | None = None
    """The Student of a `student` occupant (Story 5.9); None for every other occupant."""


class GameOverview(BaseModel):
    """A stored Game as read back from the database."""

    model_config = _FROZEN

    id: str
    purpose: Purpose
    lifecycle: Lifecycle
    version: int
    demand_seed: int | None
    rules_version: int | None
    settings: GameSettings | None
    """The Game's frozen settings (AD-4); None, like the rest of the snapshot, on a Game whose
    policy takes it at the lock and that has not got it yet."""
    session_runtime: SessionRuntime | None
    class_session_id: str | None = None
    """The Class session of a Class game (Story 5.9), with its `game_number` in it."""
    game_number: int | None = None
    seats: tuple[SeatOverview, ...]


_Count = Annotated[int, Field(strict=True, ge=0)]
_Week = Annotated[int, Field(strict=True, ge=1)]
_Money = Annotated[Decimal, Field(allow_inf_nan=False)]


def _rates(cost_lines: Any) -> tuple[Decimal, Decimal] | None:
    """The holding and backorder rates in a stored state's `cost_lines`, or None if they are not
    both there as decimals."""
    if not isinstance(cost_lines, (list, tuple)):
        return None
    by_kind: dict[str, Decimal] = {}
    for line in cost_lines:
        if isinstance(line, dict) and isinstance(line.get("rate"), (str, Decimal)):
            try:
                rate = Decimal(line["rate"])
            except ArithmeticError:
                return None
            if not rate.is_finite():
                return None  # the cost split then stays missing, and the field checks refuse it
            by_kind[line.get("kind")] = rate
    if "holding" not in by_kind or "backorder" not in by_kind:
        return None
    return by_kind["holding"], by_kind["backorder"]


class SeatState(SeatView):
    """What one Seat sees in one opened Week: the single information boundary (AD-3, FR-23).

    The play screen, the LLM player's prompt and the Decision log (`state_seen`) all read this
    model, and a field is added here, never beside it. It holds numbers and Roles only: no
    names, no number of Weeks, no future demand and no other Seat's state beyond the
    `neighbour_numbers` that Information visibility allows: the direct neighbours' inventory and
    backlog in the open Week, filled by `games.views.build_seat_state` while
    `FEATURE_INFO_VISIBILITY` is on (Story 6.21).
    Every number comes from `engine.seat_view` and `engine.seat_detail`; engine functions that
    take a `SeatView` accept this model as it is.

    Version 2 (Story 6.6) adds `net_inventory` to the Week and to each `history` row, for the
    play screen's Netto lager. Version 3 (Story 6.7) adds `holding_cost` and `backorder_cost` to
    each `history` row, for the graph's Kost per uke bars. Version 4 (Story 6.16) adds the running
    sums for «Kostnad så langt»: `total_holding_cost` and `total_backorder_cost` on the Week, and
    `total_cost`, `total_holding_cost` and `total_backorder_cost` on each `history` row. A stored
    version 1, 2 or 3 state reads as version 4."""

    schema_version: Literal[4] = 4
    week: _Week
    incoming_order: _Count
    """This Week's incoming order; customer demand for the Retailer."""
    incoming_delivery: _Count
    shipped: _Count
    supply_line_slots: tuple[SupplyLineSlot, ...]
    """Units ordered and not received, arrives soonest first, with their arrival Weeks."""
    overdue: _Count
    """Units the upstream Seat received an Order for but has not shipped yet."""
    net_inventory: int
    """Netto lager: inventory minus backlog."""
    position: int
    """Posisjon: inventory minus backlog plus the supply line."""
    cost_lines: tuple[CostLine, ...]
    week_cost: _Money
    total_cost: _Money
    """Running Total cost: the earlier Weeks plus this Week's."""
    total_holding_cost: _Money
    """The part of `total_cost` charged on inventory (Story 6.16)."""
    total_backorder_cost: _Money
    """The part of `total_cost` charged on backlog (Story 6.16)."""
    history: tuple[WeekValues, ...]
    """The Seat's own earlier Weeks with their Orders, oldest first."""
    min_order: _Count
    max_order: _Count
    preview: OrderPreview

    @model_validator(mode="before")
    @classmethod
    def _upgrade_stored_versions(cls, data: Any) -> Any:
        """A state stored as version 1, 2 or 3 (a Decision log row's `state_seen` written before
        Story 6.6, 6.7 or 6.16) reads as version 4 with the same numbers.

        Version 1 → 2: `net_inventory`, on the Week and on each `history` row, is the inventory
        minus the backlog it already holds; a version-1 object that holds it is refused.
        Version 2 → 3: each `history` row's `holding_cost` and `backorder_cost` are its inventory
        and backlog times the rates in the state's own `cost_lines` (a Game's rates never change);
        an older object that holds them is refused.
        Version 3 → 4: the running sums are the `history` rows' costs added up in order, and on
        the Week those plus its `cost_lines` amounts; an older object that holds them is refused."""
        if not isinstance(data, dict) or data.get("schema_version") not in (1, 2, 3):
            return data
        version = data["schema_version"]
        if type(version) is not int:
            raise ValueError("schema_version must be a whole number")
        rates = _rates(data.get("cost_lines"))
        for name in _RUNNING:
            if name in data:
                raise ValueError(f"schema_version {version} has no {name}")

        def upgraded(values: Any, *, row: bool) -> Any:
            if not isinstance(values, dict):
                return values
            found = dict(values)
            inventory, backlog = values.get("inventory"), values.get("backlog")
            whole = type(inventory) is int and type(backlog) is int
            if version == 1:
                if "net_inventory" in values:
                    raise ValueError("schema_version 1 has no net_inventory")
                if whole:
                    found["net_inventory"] = inventory - backlog
            if row:
                if version < 3 and ("holding_cost" in values or "backorder_cost" in values):
                    raise ValueError(f"schema_version {version} has no cost split")
                if version < 3 and whole and rates is not None:
                    found["holding_cost"] = rates[0] * inventory
                    found["backorder_cost"] = rates[1] * backlog
                if any(name in values for name in ("total_cost", *_RUNNING)):
                    raise ValueError(f"schema_version {version} has no running sums")
            # Incomplete or malformed values stay as they are: the field checks name what is wrong.
            return found

        found = {**upgraded(data, row=False), "schema_version": 4}
        if isinstance(data.get("history"), (list, tuple)):
            rows = [upgraded(row, row=True) for row in data["history"]]
            sums = _running(rows)
            if sums is not None:
                for row, (cost, held, owed) in zip(rows, sums[0], strict=True):
                    row.update(total_cost=cost, total_holding_cost=held, total_backorder_cost=owed)
                now = _amounts(data.get("cost_lines"))
                if now is not None:
                    found["total_holding_cost"] = sums[1][0] + now[0]
                    found["total_backorder_cost"] = sums[1][1] + now[1]
            found["history"] = rows
        return found


_RUNNING = ("total_holding_cost", "total_backorder_cost")


def _decimal(value: Any) -> Decimal | None:
    if not isinstance(value, (str, Decimal, int)) or isinstance(value, bool):
        return None
    try:
        found = Decimal(value)
    except ArithmeticError:
        return None
    return found if found.is_finite() else None


def _running(
    rows: list[Any],
) -> tuple[list[tuple[Decimal, Decimal, Decimal]], tuple[Decimal, Decimal]] | None:
    """The running (total, holding, backorder) of each upgraded `history` row, and the holding
    and backorder sums after the last; None when a row lacks a readable cost, so the field
    checks refuse the state."""
    cost = held = owed = Decimal(0)
    found: list[tuple[Decimal, Decimal, Decimal]] = []
    for row in rows:
        if not isinstance(row, dict):
            return None
        week, holding, backorder = (
            _decimal(row.get(name)) for name in ("cost", "holding_cost", "backorder_cost")
        )
        if week is None or holding is None or backorder is None:
            return None
        cost, held, owed = cost + week, held + holding, owed + backorder
        found.append((cost, held, owed))
    return found, (held, owed)


def _amounts(cost_lines: Any) -> tuple[Decimal, Decimal] | None:
    """This Week's holding and backorder amounts in a stored state's `cost_lines`."""
    if not isinstance(cost_lines, (list, tuple)):
        return None
    by_kind: dict[Any, Decimal] = {}
    for line in cost_lines:
        if isinstance(line, dict):
            amount = _decimal(line.get("amount"))
            if amount is None:
                return None
            by_kind[line.get("kind")] = amount
    if "holding" not in by_kind or "backorder" not in by_kind:
        return None
    return by_kind["holding"], by_kind["backorder"]


class TurnOverview(BaseModel):
    """One Seat's turn in one opened Week (AD-20)."""

    model_config = _FROZEN

    week: int
    guided: bool
    """A Guided Week: the Order is `engine.guided_order`, placed with `decided_by = guided`."""
    opened_at: datetime
    ordered_at: datetime | None
    viewed_at: datetime | None = None
    """When the Student holding the Seat opened this Guided Week (`view_week`, Story 6.10)."""
    order: int | None = None
    """The Seat's Order in this Week, None before it has ordered."""
    rule_based_reference_order: int
    near_optimal_reference_order: int | None = None
    """Computed from the whole chain when the Week opened (FR-79); None only on turns opened
    before Story 2.9."""
    near_optimal_algorithm_version: str | None = None
    """The algorithm that computed it (`engine.near_optimal.ALGORITHM_VERSION`)."""


class PendingTurn(BaseModel):
    """A Seat's turn in the open Week as the order source sees it inside the running command's
    transaction (AD-5): who holds the Seat in that Week and what it may order from."""

    model_config = _FROZEN

    game_id: str
    seat_id: str
    role: str
    week: int
    guided: bool
    """A Guided Week: every occupant, a Student too (Story 6.10), orders `guided_order`."""
    guided_order: int
    occupant_kind: OccupantKind
    """The occupant in force in `week` (`from_week <= week`, newest)."""
    policy_id: str | None
    rule_based_reference_order: int
    """Stored on the turn when the Week opened; never recomputed."""
    ordered: bool
    """The Seat already has an Order for `week`."""
    ai_deadline_at: datetime | None = None
    """When the LLM player's Order is due (`games.rules.turn_times`); None: no deadline."""
    read_at: datetime | None = None
    """The database clock when the turn was read (`llm_turn`): the clock `ai_deadline_at` is
    on, so `ai_deadline_at - read_at` is the time left on any other clock."""
    seat_state: SeatState


class OrderPlaced(BaseModel):
    """What `place_order` did: the Decision log row and the Week that is open after it."""

    model_config = _FROZEN

    seat_week_id: str
    week: int
    """The Week the Order was placed in."""
    open_week: int | None
    """The Week open after the command: `week`, or the next one if it advanced; None once the
    Game has finished."""
    lifecycle: Lifecycle
    pause_ended: bool = False
    """Whether this Student's Order ended the Game's Pause (Story 8.6, FR-89)."""


class DecisionLogRow(BaseModel):
    """One `seat_weeks` row as read back (AD-15)."""

    model_config = _FROZEN

    week: int
    role: str
    seat_id: str
    order: int
    decided_by: DecidedBy
    fallback: Fallback
    occupant_kind: OccupantKind
    reason: OccupancyReason
    opened_at: datetime
    ordered_at: datetime
    ai_deadline_at: datetime | None = None
    """When an LLM player's Order was due (AD-20); None for every other Order."""
    rule_based_reference_order: int
    near_optimal_reference_order: int | None = None
    """Copied from the turn (FR-67, FR-79); None only on rows written before Story 2.9."""
    near_optimal_algorithm_version: str | None = None
    """The algorithm that computed it, copied from the turn."""
    llm_call_ids: tuple[str, ...] = ()
    """The LLM call rows behind the Order: every attempt of an LLM Order or of the failed call
    behind a fallback Order (FR-67)."""
    effort_level: str | None = None
    """The Effort level the Game froze, on rows an `llm` occupant ordered (FR-78); None on every
    other row and on rows written before Story 2.11."""
    state_seen: SeatState


class OccupancyRow(BaseModel):
    """One row of a Seat's append-only occupancy history (AD-5): who holds the Seat from
    `from_week` on, and why. A Play guard switch is a `guard_switch` row whose `from_week` is
    the Week after the Order that caused it (FR-79, FR-67)."""

    model_config = _FROZEN

    role: str
    seat_id: str
    from_week: int
    occupant_kind: OccupantKind | None
    """None: the Seat is free from `from_week` on (reason `moved`, Story 5.10)."""
    policy_id: str | None
    reason: OccupancyReason


class SimulationBatch(BaseModel):
    """One `simulation_batches` row with its Games (Story 2.11, AD-22)."""

    model_config = _FROZEN

    id: str
    batch_file: dict[str, Any]
    """The batch file as it was played (`model_config` filled in)."""
    pass_lines: dict[str, Any]
    """The pass lines from the batch file; empty when it has none."""
    mock: bool
    """The batch's LLM Seats were answered by the mock provider."""
    started_at: datetime
    game_ids: tuple[str, ...]
    """The batch's Games in the order they were created."""


class GameCheck(BaseModel):
    """One `game_checks` row: the result of replaying and checking a finished Game (AD-9)."""

    model_config = _FROZEN

    id: str
    game_id: str
    rules_version: int
    """The stored `rules_version` the Game was replayed at."""
    ok: bool
    checked_at: datetime
    violations: tuple[Violation, ...]
    """Every broken rule with its Week and Role; empty when `ok`."""


class GameSummary(BaseModel):
    """A finished Game in numbers, read from `game_weeks`, the Decision log and `game_checks`
    (AD-22)."""

    model_config = _FROZEN

    game_id: str
    demand_seed: int
    weeks: int
    """The last Week, which ran in full."""
    total_cost: tuple[tuple[str, Decimal], ...]
    """Each Role's Total cost in chain order, from the finished Week state."""
    chain_cost: Decimal
    orders: tuple[tuple[DecidedBy, int], ...]
    """Decision log rows per `decided_by`, in `DecidedBy` order; zero counts left out."""
    check: GameCheck | None
    """The finished-game check, or None when it has not run."""


class CostSum(BaseModel):
    """Holding and backlog cost and their sum, in kroner (Story 6.18)."""

    model_config = _FROZEN

    holding_cost: _Money
    backorder_cost: _Money
    total_cost: _Money


class RoleCost(CostSum):
    """One Role's cost over the whole Game: a row of Kjedens regning, per Role, never per name."""

    role: Role


class ChainWeekCost(CostSum):
    """The chain's cost from Uke 1 through `week`, summed over its Roles."""

    week: int


class GameResult(BaseModel):
    """A finished Game's cost (Story 6.18, FR-28): each Role's, the chain's, and the chain's
    running cost per Uke. Numbers and Roles only: no names, no demand, no settings."""

    model_config = _FROZEN

    roles: tuple[RoleCost, ...]
    """Detaljist to Fabrikk, the chain order of the Game's settings."""
    chain: CostSum
    weeks: tuple[ChainWeekCost, ...]
    """Uke 1 to the last Uke, oldest first."""


TableHolder = Literal["student", "ai", "free"]


class TableSeat(BaseModel):
    """One Seat of a Game as its players see who sits there (Story 6.1, AD-3): a Student's name,
    an AI player («KI-spiller», never which kind) or free. People only, never numbers."""

    model_config = _FROZEN

    role: str
    holder: TableHolder
    name: str | None
    """The Student's name, read at request time; None for an AI player, a free Seat, or a Student
    who is no longer in the Class."""
    mine: bool
    """Whether this is the viewer's own Seat (held now, or last held)."""
    ordered: bool | None = None
    """Whether the Seat has ordered in the open Week (`rules.has_ordered`: in a Guided Week a
    Student's view counts); None when the Game is not running (Story 6.14)."""
    wait_started_at: datetime | None = None
    """When the game began to wait for the Seat in the open Week, the stored
    `seat_turns.wait_started_at`; None once it has ordered, before any Student has ordered, or
    when the Game is not running."""
    mark: SeatMark | None = None
    """The Seat's mark (`games.service.seat_mark`), e.g. a Play guard switch; None for most."""
    taken_over: bool = False
    """An AI player holds the Seat after a Takeover of its Student (Story 8.2, FR-37): the mark
    is one of the Takeover marks. «KI-spiller  bestiller for Jonas»."""
    ordering_for: str | None = None
    """For a Seat `taken_over`: the name, read now, of the Student whose Seat it was; None when
    that Student is no longer in the Class, and for every other Seat."""
    guard_switched: bool = False
    """An AI player that is Rule-based because the Play guard switched the Seat once, also when
    that switch came before a later Takeover or Reclaim (Story 8.2, FR-79)."""
    reclaim_queued: bool = False
    """The viewer's own Seat, taken over, with their «Ta tilbake setet» queued: it is theirs
    again when the next Week opens (Story 8.4, FR-37). False on every other Seat."""
    insert_at: datetime | None = None
    """Story 8.8 (FR-89, UX-DR27): the stored insert time of another Student's Seat that has not
    ordered, while it lies ahead and the game is paused or the time is agreed: «Etter on. 10:00
    kan dere sette inn en KI-spiller.»; None otherwise, and always for a viewer who holds no
    other Seat. Never why one Seat's time is later."""
    insert_agreed: bool = False
    """Story 8.8: `insert_at` is the Lecturer's agreed time, not the Seat's own limit («Avtalt tid
    to. 19:00. Etter det kan dere sette inn en KI-spiller.»)."""
    can_insert: bool = False
    """Story 8.8: the viewer may press «Sett inn KI-spiller for …» on this Seat now:
    `rules.can_take_over` with the `peer` actor, for a viewer who holds another Seat."""
    inserted_by: str | None = None
    """Story 8.8: for a Seat a Student of the game put an AI player in (`takeover_peer`), that
    Student's name, read now; None for every other Seat."""


class TablePause(BaseModel):
    """The game's Pause line as a Student sees it (Story 8.6, FR-89, UX-DR62): `paused` while a
    Pause is in force, named by who set it; `ended` from the Order that ended it until the next
    Week opens, named by who ordered. Never a Week count (FR-14)."""

    model_config = _FROZEN

    state: Literal["paused", "ended"]
    name: str | None
    """The Student's name, read now; None for someone no longer in the Class."""
    mine: bool
    """Whether the viewer set (or ended) it: «satt av deg», «Du har bestilt»."""
    staff: bool = False
    """Story 8.7: a staff member, not a Student of the Game, set (or ended) it: «satt av
    faglæreren», «Faglæreren har avsluttet den». The name is then never shown to Students."""
    resume_at: datetime | None = None
    """Story 8.7: the Lecturer's agreed time while paused («Pause til to. 19:00, satt av
    faglæreren.»); None without one, and always on `ended`."""


class TableStatus(BaseModel):
    """The people side of a Game for one viewer (AD-3), Fabrikk first (UX-DR73). Built at read
    time by `views.table_status`; never stored and never passed to an LLM."""

    model_config = _FROZEN

    seats: tuple[TableSeat, ...]
    due_times: tuple[datetime, ...] = ()
    """The stored AI deadlines of the Seats that have not ordered in the open Week, earliest
    first: when an AI player's Order is due (the only due times before Epic 8)."""
    can_pause: bool = False
    """Whether the viewer may press «Ta pause» (Story 8.6, FR-89): a Game whose policy has Pause,
    running and not paused, and a Seat the viewer holds now as a Student."""
    pause: TablePause | None = None
    """The Pause line (Story 8.6); None when there is none to show."""
