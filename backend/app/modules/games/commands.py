"""The only write path for Games, Seats, occupancy, turns and Week states (AD-2).

Each command is one transaction: it locks the Game row (`SELECT … FOR UPDATE`), raises the
Game's `version` by one and emits `game:<id>` (AD-8) before it commits. A command that fails
raises `CommandError` and leaves nothing behind: no row, no version change, no event.

When a Week opens, and right after a switch, the command calls `players.ensure_order` for its
Seats in its own transaction (AD-5); the Orders it places join that transaction. After its own
commit every command calls `advance` until it does nothing, so a Game whose open Week is
complete moves on one Week per transaction and none is left complete but open (AD-2, NFR-4).
"""

import secrets
import uuid
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime

import structlog
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import budget as ai_budget
from app.ai import config as ai_config
from app.engine import (
    RULES_VERSION,
    DemandPattern,
    GameSettings,
    Role,
    SettingsError,
    WeekState,
    demand_series,
    guided_order,
    initial_state,
    near_optimal,
    rule_based,
    seat_view,
    validate,
)
from app.engine import advance as engine_advance
from app.engine import rules as engine_rules
from app.engine.demand import new_seed
from app.engine.scripted import REGISTRY
from app.modules.games import repo, rules
from app.modules.games.policy import GamePolicy, PurposeNotSupportedError, policy
from app.modules.games.schemas import (
    DecidedBy,
    Fallback,
    Lifecycle,
    OccupancyReason,
    OccupantKind,
    OrderPlaced,
    Purpose,
    SessionRuntime,
)
from app.modules.games.service import scope_of
from app.modules.games.turns import OpenGame, play_of
from app.modules.games.views import build_seat_state, stored_orders, stored_play
from app.platform import events
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker
from app.platform.parameter_sets import UnknownParameterSetError, read_parameter_set

__all__ = [
    "CommandError",
    "advance",
    "assign_seat",
    "create",
    "finish",
    "place_order",
    "start",
    "switch_to_rule_based",
]

log = structlog.get_logger(__name__)

ASSIGNABLE = frozenset({OccupantKind.RULE_BASED, OccupantKind.SCRIPTED, OccupantKind.LLM})
"""Occupant kinds `assign_seat` takes; `student` comes with Epic 5."""


class CommandError(Exception):
    """A refused command, with a stable code for the API envelope (AD-19)."""

    def __init__(
        self,
        code: str,
        message: str,
        status: int,
        fields: Mapping[str, str] | None = None,
        errors: tuple[SettingsError, ...] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.fields = dict(fields or {})
        self.errors = errors
        """The engine's settings errors, for `invalid_settings`."""


def _policy(purpose: str) -> GamePolicy:
    try:
        return policy(purpose)
    except PurposeNotSupportedError:
        raise CommandError(
            "purpose_not_supported", f"Games of purpose {purpose!r} cannot be created yet", 422
        ) from None


def _effective_settings(
    settings: GameSettings, demand_pattern: DemandPattern | None, seed: int | None
) -> GameSettings:
    data = settings.model_dump()
    if demand_pattern is not None:
        data["demand"] = demand_pattern.model_dump()
    if seed is None:
        seed = settings.demand_seed
    data["demand_seed"] = seed if seed is not None else new_seed(secrets.token_bytes(16))
    try:
        effective = GameSettings.model_validate(data)
    except ValidationError as exc:
        fields = {".".join(str(part) for part in e["loc"]): "invalid" for e in exc.errors()}
        raise CommandError(
            "invalid_settings", "the Game settings are invalid", 422, fields
        ) from None
    errors = validate(effective, capacity_enabled=get_settings().feature_capacity)
    if errors:
        raise CommandError(
            "invalid_settings",
            "the Game settings break the engine's rules",
            422,
            {error.field: error.code for error in errors},
            errors,
        )
    return effective


def _rule_based_params(set_id: str) -> rule_based.RuleBasedParams:
    try:
        return rule_based.parse_params(read_parameter_set("rule_based", set_id), set_id)
    except UnknownParameterSetError:
        raise CommandError(
            "unknown_parameter_set", f"no Rule-based parameter set {set_id!r}", 422
        ) from None
    except ValueError:
        raise CommandError(
            "invalid_parameter_set", f"Rule-based parameter set {set_id!r} is invalid", 422
        ) from None


async def _commit_change(session: AsyncSession, game_id: uuid.UUID) -> int:
    """Lock the Game row, raise its version and announce it; the caller's transaction commits."""
    await repo.lock_game(session, game_id)
    version = await repo.bump_version(session, game_id)
    await events.emit(session, "game", str(game_id), version)
    return version


async def create(
    purpose: Purpose | str,
    settings: GameSettings,
    demand_pattern: DemandPattern | None = None,
    seed: int | None = None,
    *,
    rule_based_params: str = rule_based.DEFAULT_SET_ID,
    model_config_id: str | None = None,
    effort_level: str | None = None,
) -> str:
    """Store a `not_started` Game with one free Seat per Role and its frozen snapshot (AD-4).

    `demand_pattern` and `seed` replace the ones in `settings`; with no seed anywhere a new one
    is drawn. `model_config_id` and one of that config's Effort levels (default: its first) are
    frozen into the `SessionRuntime` for the Game's LLM players (AD-22, FR-78), and the config
    is marked referenced, so it can never change. Returns the Game id.
    """
    _policy(purpose)
    effective = _effective_settings(settings, demand_pattern, seed)
    params = _rule_based_params(rule_based_params)
    if effort_level is not None and model_config_id is None:
        raise CommandError("model_config_required", "an Effort level needs a model config", 422)
    game_id = uuid.uuid7()
    async with get_sessionmaker().begin() as session:
        level = None
        if model_config_id is not None:
            model_config_id, level = await _model_config(session, model_config_id, effort_level)
        runtime = SessionRuntime(
            ai_mode="rule_based" if model_config_id is None else "llm",
            rule_based_params=params.id,
            rule_based_params_version=params.version,
            model_config_id=model_config_id,
            effort_level=level,
        )
        await repo.insert_game(
            session,
            {
                "id": game_id,
                "purpose": Purpose(purpose).value,
                "lifecycle": Lifecycle.NOT_STARTED.value,
                "version": 0,
                "settings": effective.model_dump(mode="json"),
                "demand_series": list(demand_series(effective)),
                "demand_seed": effective.demand_seed,
                "rules_version": RULES_VERSION,
                "session_runtime": runtime.model_dump(mode="json"),
            },
        )
        await repo.insert_seats(session, game_id, [role.value for role in effective.roles])
        await _commit_change(session, game_id)
    log.info("game_created", game_id=str(game_id))
    await _settle(str(game_id))
    return str(game_id)


async def _model_config(
    session: AsyncSession, config_id: str, effort_level: str | None
) -> tuple[str, str]:
    """The stored config's id and the Effort level to freeze; marks the config referenced in
    the caller's transaction."""
    found = await ai_config.get(config_id, session=session)
    if found is None:
        raise CommandError("config_not_found", f"no model config {config_id!r}", 422)
    if effort_level is None:
        effort_level = found.spec.effort_levels[0].name
    elif found.effort_level(effort_level) is None:
        raise CommandError(
            "effort_level_unknown",
            f"model config {found.id} has no Effort level {effort_level!r}",
            422,
        )
    await ai_config.mark_referenced(found.id, session=session)
    return str(found.id), effort_level


def _occupant(
    kind: str, policy_id: str | None, game_policy: GamePolicy
) -> tuple[OccupantKind, str | None]:
    try:
        occupant = OccupantKind(kind)
    except ValueError:
        occupant = None
    if occupant not in ASSIGNABLE or (
        occupant is OccupantKind.SCRIPTED and not game_policy.scripted_occupants
    ):
        raise CommandError(
            "occupant_kind_not_allowed", f"a Seat of this Game cannot be given {kind!r}", 422
        )
    if occupant is OccupantKind.SCRIPTED:
        if policy_id is None:
            raise CommandError("policy_id_required", "a scripted occupant needs a policy id", 422)
        if policy_id not in REGISTRY:
            raise CommandError("unknown_policy", f"no scripted policy {policy_id!r}", 422)
    elif policy_id is not None:
        raise CommandError(
            "policy_id_not_allowed",
            "only a scripted occupant takes a policy id",
            422,
        )
    return occupant, policy_id


async def assign_seat(
    game_id: str, role: Role | str, occupant_kind: OccupantKind | str, policy_id: str | None = None
) -> str:
    """Give the free Seat of `role` its first occupant (`from_week` 1, reason `initial`):
    `rule_based`, `scripted` (with a policy id) or `llm`, which needs a Game whose
    `SessionRuntime` holds a model config (`model_config_required`).

    Returns the occupancy row id. An occupied Seat answers `seat_occupied`.
    """
    game_uuid = _game_uuid(game_id)
    async with get_sessionmaker().begin() as session:
        game = await repo.lock_game(session, game_uuid)
        if game is None:
            raise CommandError("game_not_found", f"no Game {game_id!r}", 404)
        occupant, policy_id = _occupant(str(occupant_kind), policy_id, _policy(game["purpose"]))
        runtime = SessionRuntime.model_validate(game["session_runtime"])
        if occupant is OccupantKind.LLM and runtime.model_config_id is None:
            raise CommandError(
                "model_config_required",
                "an LLM player needs a Game created with a model config",
                422,
            )
        if game["lifecycle"] != Lifecycle.NOT_STARTED:
            raise CommandError(
                "game_already_started", "Seats get their first occupant before the start", 409
            )
        seat = await repo.seat_by_role(session, game_uuid, str(role))
        if seat is None:
            raise CommandError("unknown_role", f"the Game has no Seat for {role!r}", 422)
        if await repo.has_occupant(session, seat["id"]):
            raise CommandError("seat_occupied", f"the {role} Seat already has an occupant", 409)
        reason = OccupancyReason.INITIAL
        if occupant is OccupantKind.LLM and await _cost_limited(session, game):
            # The scope reached the players' cost limit: no new LLM player (FR-69, AD-5).
            occupant, reason = OccupantKind.RULE_BASED, OccupancyReason.COST_LIMIT
        occupancy_id = await _append_initial(session, seat["id"], occupant, policy_id, reason)
        await _commit_change(session, game_uuid)
    log.info("seat_assigned", game_id=game_id, seat_id=str(seat["id"]))
    await _settle(game_id)
    return str(occupancy_id)


async def _append_initial(
    session: AsyncSession,
    seat_id: uuid.UUID,
    occupant: OccupantKind,
    policy_id: str | None,
    reason: OccupancyReason = OccupancyReason.INITIAL,
) -> uuid.UUID:
    """Append an occupancy row from Week 1 (reason `initial`, or `cost_limit` for an LLM
    player the cost limit turned into a Rule-based one before the Game started)."""
    occupancy_id = uuid.uuid7()
    await repo.append_occupancy(
        session,
        {
            "id": occupancy_id,
            "seat_id": seat_id,
            "from_week": 1,
            "occupant_kind": occupant.value,
            "policy_id": policy_id,
            "reason": reason.value,
        },
    )
    return occupancy_id


async def _cost_limited(session: AsyncSession, game: Mapping[str, object]) -> bool:
    """Whether the budget the Game charges has reached the players' cost limit
    (`players_exhausted_at`, FR-69): from then on no Seat of it gets an LLM player."""
    runtime = SessionRuntime.model_validate(game["session_runtime"])
    scope = scope_of(str(game["purpose"]), runtime)
    if scope is None:
        return False
    state = await ai_budget.state(scope, session=session)
    return state is not None and state.players_exhausted_at is not None


def _game_uuid(game_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(game_id)
    except ValueError, TypeError, AttributeError:
        raise CommandError("game_not_found", f"no Game {game_id!r}", 404) from None


def _snapshot(game: Mapping[str, object]) -> tuple[GameSettings, rule_based.RuleBasedParams]:
    """The Game's frozen settings and Rule-based parameters; refuses a snapshot this engine
    cannot reproduce (AD-4). Commands run the Game's stored `rules_version`."""
    if not engine_rules.has_version(game["rules_version"]):
        raise CommandError(
            "rules_version_unsupported",
            f"the Game needs rules version {game['rules_version']}, which has no rules package",
            409,
        )
    settings = GameSettings.model_validate(game["settings"])
    if list(demand_series(settings)) != game["demand_series"]:
        raise CommandError(
            "snapshot_mismatch", "the stored demand series does not match its settings", 409
        )
    runtime = SessionRuntime.model_validate(game["session_runtime"])
    params = _rule_based_params(runtime.rule_based_params)
    if params.version != runtime.rule_based_params_version:
        raise CommandError(
            "parameter_set_changed",
            f"Rule-based parameter set {params.id!r} is now version {params.version}, the Game "
            f"froze version {runtime.rule_based_params_version}",
            409,
        )
    return settings, params


async def _ensure_order(game: OpenGame, seat_id: uuid.UUID) -> None:
    """Hand the Seat to the one order source (AD-5). `players` imports `games.commands`, so the
    import is made here, when the first Week opens, not when this module loads."""
    from app.modules.players import service as players

    await players.ensure_order(game, str(seat_id))


async def _ai_order_budget(
    session: AsyncSession, game: Mapping[str, object], occupants: Iterable[str | None]
) -> float | None:
    """The per-Order time budget of the Effort level the Game froze, when an `llm` occupant
    needs it; None otherwise. The config is immutable once referenced, so it is read here."""
    if OccupantKind.LLM.value not in occupants:
        return None
    runtime = SessionRuntime.model_validate(game["session_runtime"])
    if runtime.model_config_id is None or runtime.effort_level is None:
        return None
    found = await ai_config.get(runtime.model_config_id, session=session)
    level = None if found is None else found.effort_level(runtime.effort_level)
    if level is None:  # the gateway refuses the call; the job places the fallback Order
        log.warning("effort_level_missing", game_id=str(game["id"]))
        return None
    return level.order_time_budget_s


async def _open_week(
    session: AsyncSession,
    game: Mapping[str, object],
    settings: GameSettings,
    params: rule_based.RuleBasedParams,
    states: Sequence[WeekState],
    orders: Sequence[Mapping[str, int]],
    seats: Sequence[Mapping[str, object]],
) -> None:
    """Store the newest of `states` and one turn per Seat with its two reference Orders,
    computed here once: the Rule-based one from that Seat's own view, the near-optimal one from
    the whole chain state and the Game's demand series (with its algorithm version); and its due
    times from `rules.turn_times` (AD-5, AD-20, FR-67, FR-79). Then every Seat, in chain
    order, goes to `players.ensure_order`, which places the Orders of its non-student occupants
    in this transaction. The Game must already be `running`.

    `seats` are the Game's Seats with their latest occupant (`repo.seats_with_occupant`; a free
    Seat has just been given a Rule-based player), which is the one in force in the new Week.
    `states` and `orders` are the Game's history as stored once this Week is written, so the
    order source gets them with the open Game instead of reading them again for every Seat."""
    game_id = game["id"]
    state = states[-1]
    stored = state.model_dump(mode="json")
    await repo.insert_week(session, game_id, state.week, stored)
    week = rules.TurnGame(
        guided_week=rules.guided_week(_policy(game["purpose"]), settings, state.week)
    )
    occupant = {
        seat["role"]: OccupantKind(seat["occupant_kind"] or OccupantKind.RULE_BASED)
        for seat in seats
    }
    budget = None if week.guided_week else await _ai_order_budget(session, game, occupant.values())
    inputs = rules.TurnInputs(ai_order_budget_s=budget)
    # The transaction's clock is read only when a deadline is computed from it; otherwise the
    # turns take it from the database as they are written (the same `now()`).
    opened_at = None if budget is None else await repo.now(session)

    def deadline(role: Role) -> datetime | None:
        if opened_at is None:
            return None
        seat = rules.TurnSeat(occupant[role.value], opened_at)
        return rules.turn_times(week, seat, inputs).ai_deadline_at

    seat_ids = {seat["role"]: seat["id"] for seat in seats}
    demand = tuple(game["demand_series"])  # equal to the settings' series (`_snapshot`)
    await repo.insert_turns(
        session,
        [
            {
                "id": uuid.uuid7(),
                "game_id": game_id,
                "seat_id": seat_ids[role.value],
                "week": state.week,
                "opened_at": func.now() if opened_at is None else opened_at,
                "ai_deadline_at": deadline(role),
                "rule_based_reference_order": rule_based.order(
                    settings, seat_view(settings, states, orders, role), params
                ),
                "near_optimal_reference_order": near_optimal.order(
                    settings, state, demand, state.week, role
                ),
                "near_optimal_algorithm_version": near_optimal.ALGORITHM_VERSION,
            }
            for role in settings.roles
        ],
    )
    # The newest state as a read of its stored row returns it, like the earlier ones.
    play = ([*states[:-1], WeekState.model_validate(stored)], list(orders))
    open_game = OpenGame(session=session, game_id=game_id, play=play)
    for role in settings.roles:
        await _ensure_order(open_game, seat_ids[role.value])


async def _settle(game_id: str) -> None:
    """Advance the Game one Week per transaction until an advance does nothing (AD-2, NFR-4).

    It runs after the caller's own commit, so the caller's result stands whatever happens here:
    a failed advance is logged and leaves the Game complete but open, for the next command or
    `advance` to move on."""
    try:
        while await _advance_once(game_id):
            pass
    except Exception:
        log.exception("settle_failed", game_id=game_id)


async def start(game_id: str) -> int:
    """Start a `not_started` Game: give every free Seat a Rule-based player, store the Week 1
    state, open one turn per Seat and let the order source place the Orders of the non-student
    Seats. Returns the opened Week (1); by then the Game may have advanced, or finished when no
    Student holds a Seat."""
    game_uuid = _game_uuid(game_id)
    async with get_sessionmaker().begin() as session:
        game = await repo.lock_game(session, game_uuid)
        if game is None:
            raise CommandError("game_not_found", f"no Game {game_id!r}", 404)
        if game["lifecycle"] != Lifecycle.NOT_STARTED:
            raise CommandError("game_already_started", "the Game has already started", 409)
        settings, params = _snapshot(game)
        seat_rows = await repo.seats_with_occupant(session, game_uuid)
        llm_seats = [s for s in seat_rows if s["occupant_kind"] == OccupantKind.LLM]
        limited = bool(llm_seats) and await _cost_limited(session, game)
        for seat in seat_rows:
            if seat["occupant_kind"] is None:
                await _append_initial(session, seat["id"], OccupantKind.RULE_BASED, None)
            elif limited and seat["occupant_kind"] == OccupantKind.LLM:
                # The cost limit was reached before the start (FR-69, AD-5).
                await _append_initial(
                    session, seat["id"], OccupantKind.RULE_BASED, None, OccupancyReason.COST_LIMIT
                )
        if limited:
            seat_rows = await repo.seats_with_occupant(session, game_uuid)
            log.info("seats_cost_limited", game_id=game_id, seats=len(llm_seats))
        state = initial_state(settings, game["rules_version"])
        await repo.set_lifecycle(session, game_uuid, Lifecycle.RUNNING.value)
        await _open_week(session, game, settings, params, [state], [], seat_rows)
        await _commit_change(session, game_uuid)
    log.info("game_started", game_id=game_id)
    await _settle(game_id)
    return state.week


def _decided_by(value: object) -> DecidedBy:
    try:
        return DecidedBy(value)
    except ValueError:
        raise CommandError(
            "decided_by_invalid", f"{value!r} is not who can decide an Order", 422
        ) from None


def _check_order(settings: GameSettings, order: object) -> int:
    if type(order) is not int or not 0 <= order <= settings.max_order:
        raise CommandError(
            "order_invalid",
            f"an Order is a whole number from 0 to {settings.max_order}",
            422,
            {"order": "invalid"},
        )
    return order


def _fallback(value: object) -> Fallback:
    try:
        return Fallback(value)
    except ValueError:
        raise CommandError("fallback_invalid", f"{value!r} is not a fallback type", 422) from None


def _call_ids(values: object) -> tuple[uuid.UUID, ...]:
    if isinstance(values, str | bytes) or not isinstance(values, Sequence):
        raise CommandError("llm_call_ids_invalid", "llm_call_ids is a list of ids", 422)
    try:
        return tuple(uuid.UUID(str(value)) for value in values)
    except ValueError:
        raise CommandError("llm_call_ids_invalid", "llm_call_ids is a list of ids", 422) from None


def _check_llm(
    decider: DecidedBy,
    fallback: Fallback,
    call_ids: Sequence[uuid.UUID],
    order: int,
    occupancy: Mapping[str, object],
    turn: Mapping[str, object],
) -> None:
    """An LLM Order and a fallback Order come only from an `llm` occupant; a fallback Order is
    the turn's Rule-based reference Order, decided by `rule_based` (FR-32, AD-15), and an LLM
    player's Rule-based Order is always such a marked fallback; call ids belong to one of those
    two, and an LLM Order carries at least one."""
    llm_seat = occupancy["occupant_kind"] == OccupantKind.LLM
    if decider is DecidedBy.LLM and not llm_seat:
        raise CommandError("decided_by_invalid", "only an LLM player decides by llm", 422)
    if decider is DecidedBy.LLM and not call_ids:
        raise CommandError("llm_call_ids_invalid", "an LLM Order carries its call ids", 422)
    if llm_seat and decider is DecidedBy.RULE_BASED and fallback is Fallback.NONE:
        raise CommandError(
            "fallback_invalid", "a Rule-based Order of an LLM player is a marked fallback", 422
        )
    if fallback is not Fallback.NONE and (
        not llm_seat
        or decider is not DecidedBy.RULE_BASED
        or order != turn["rule_based_reference_order"]
    ):
        raise CommandError(
            "fallback_invalid",
            "a fallback Order is the Rule-based reference Order of an LLM player's turn",
            422,
        )
    if call_ids and decider is not DecidedBy.LLM and fallback is Fallback.NONE:
        raise CommandError(
            "llm_call_ids_invalid", "only an LLM or a fallback Order carries call ids", 422
        )


def _seat_row(seat_rows: Sequence[Mapping[str, object]], seat: object) -> Mapping[str, object]:
    row = next((r for r in seat_rows if str(seat) in {r["role"], str(r["id"])}), None)
    if row is None:
        raise CommandError("seat_not_found", f"the Game has no Seat {seat!r}", 404)
    return row


async def _step(
    session: AsyncSession,
    game: Mapping[str, object],
    settings: GameSettings,
    params: rule_based.RuleBasedParams,
    states: Sequence[WeekState],
) -> tuple[Lifecycle, int | None]:
    """Run the complete open Week in the engine: open the next Week, or finish the Game after
    the last one. `states` are the opened Weeks as stored (`stored_play`), which completing
    the open Week does not change. Returns the lifecycle and the open Week after it."""
    game_uuid = game["id"]
    week = states[-1].week
    all_orders = await stored_orders(session, game_uuid)
    orders, week_orders = all_orders[: week - 1], all_orders[week - 1]
    following = engine_advance(settings, states[-1], week_orders, game["rules_version"])
    if following.finished:
        await finish(session, game_uuid, following)
        return Lifecycle.FINISHED, None
    seat_rows = await repo.seats_with_occupant(session, game_uuid)
    await _open_week(
        session, game, settings, params, [*states, following], [*orders, week_orders], seat_rows
    )
    return Lifecycle.RUNNING, following.week


async def _place(
    session: AsyncSession,
    game_uuid: uuid.UUID,
    seat: Role | str,
    week: int,
    order: int,
    decided_by: DecidedBy | str,
    *,
    advance_week: bool,
    open_game: OpenGame | None = None,
    fallback: Fallback | str = Fallback.NONE,
    llm_call_ids: Sequence[uuid.UUID | str] = (),
) -> OrderPlaced:
    """`place_order`'s checks and writes in `session`; with `advance_week` it also runs the Week
    this Order completes. `open_game` is the running command's Game, whose history it reuses."""
    game = await repo.lock_game(session, game_uuid)
    if game is None:
        raise CommandError("game_not_found", f"no Game {str(game_uuid)!r}", 404)
    seat_rows = await repo.seats_with_occupant(session, game_uuid)
    row = _seat_row(seat_rows, seat)
    if game["lifecycle"] == Lifecycle.NOT_STARTED:
        raise CommandError("game_not_started", "the Game has not started", 409)
    if game["lifecycle"] == Lifecycle.FINISHED:
        raise CommandError("game_finished", "the Game has finished", 409)
    decider = _decided_by(decided_by)
    marked = _fallback(fallback)
    call_ids = _call_ids(llm_call_ids)
    settings, params = _snapshot(game)
    value = _check_order(settings, order)
    if open_game is not None:
        states, orders = await play_of(open_game)
    else:
        states, orders = await stored_play(session, game_uuid)
    if type(week) is not int or week != states[-1].week:
        raise CommandError("week_not_open", f"Week {week!r} is not the open Week", 409)
    if await repo.has_seat_week(session, game_uuid, week, row["id"]):
        raise CommandError("order_exists", "the Seat has already ordered this Week", 409)
    guided = rules.guided_week(_policy(game["purpose"]), settings, week)
    if guided and (decider is not DecidedBy.GUIDED or value != guided_order(settings)):
        raise CommandError(
            "guided_order_required",
            f"Week {week} is a Guided Week: the Order is {guided_order(settings)}, "
            "decided by guided",
            422,
        )
    if not guided and decider is DecidedBy.GUIDED:
        raise CommandError("decided_by_invalid", f"Week {week} is not a Guided Week", 422)
    turn = await repo.turn(session, game_uuid, row["id"], week)
    occupancy = await repo.occupancy_in_force(session, row["id"], week)
    if turn is None or occupancy is None:  # `start` and every advance write both
        raise CommandError("week_not_open", f"the Seat has no turn in Week {week}", 409)
    _check_llm(decider, marked, call_ids, value, occupancy, turn)
    llm_occupant = occupancy["occupant_kind"] == OccupantKind.LLM
    ordered_at = await repo.set_ordered_at(session, turn["id"])
    seat_week_id = uuid.uuid7()
    state_seen = build_seat_state(settings, states, orders, row["role"])
    await repo.insert_seat_week(
        session,
        {
            "id": seat_week_id,
            "game_id": game_uuid,
            "seat_id": row["id"],
            "week": week,
            "state_seen": state_seen.model_dump(mode="json"),
            "order": value,
            "decided_by": decider.value,
            "fallback": marked.value,
            "occupant_kind": occupancy["occupant_kind"],
            "reason": occupancy["reason"],
            "opened_at": turn["opened_at"],
            "ordered_at": ordered_at,
            # Only an LLM player's Order was due at the AI deadline.
            "ai_deadline_at": turn["ai_deadline_at"] if llm_occupant else None,
            "rule_based_reference_order": turn["rule_based_reference_order"],
            # Copied from the turn, never recomputed (AD-5, AD-15).
            "near_optimal_reference_order": turn["near_optimal_reference_order"],
            "near_optimal_algorithm_version": turn["near_optimal_algorithm_version"],
            "llm_call_ids": list(call_ids),
        },
    )
    lifecycle, open_week = Lifecycle(game["lifecycle"]), week
    if advance_week and rules.week_complete(await repo.week_turns(session, game_uuid, week)):
        lifecycle, open_week = await _step(session, game, settings, params, states)
    log.info("order_placed", game_id=str(game_uuid), seat_id=str(row["id"]), week=week)
    return OrderPlaced(
        seat_week_id=str(seat_week_id), week=week, open_week=open_week, lifecycle=lifecycle
    )


async def place_order(
    game_id: str,
    seat: Role | str,
    week: int,
    order: int,
    decided_by: DecidedBy | str,
    *,
    within: OpenGame | None = None,
    fallback: Fallback | str = Fallback.NONE,
    llm_call_ids: Sequence[uuid.UUID | str] = (),
) -> OrderPlaced:
    """Place the Order of `seat` (a Role or a Seat id) for the open `week` and write its
    Decision log row with the state the Seat saw (AD-15, FR-67).

    When this Order completes the Week (`games.rules.week_complete`), the same transaction
    advances the engine one Week and opens the next turns, or finishes the Game after the last
    Week (AD-2, FR-26, FR-28). The version rises once either way.

    `within` is the running command's transaction, for the order source (`players`): the Order
    joins its lock, version increment and event, and never advances or finishes the Game.

    `fallback` and `llm_call_ids` are stored on the row as given (FR-32, FR-67): an LLM Order
    carries the ids of its attempts; a fallback Order (`decided_by = rule_based`, the turn's
    reference Order, an `llm` occupant) carries its failure type and the failed attempts."""
    if within is not None:
        if within.game_id != _game_uuid(game_id):
            raise ValueError("place_order within another Game's transaction")
        return await _place(
            within.session,
            within.game_id,
            seat,
            week,
            order,
            decided_by,
            advance_week=False,
            open_game=within,
            fallback=fallback,
            llm_call_ids=llm_call_ids,
        )
    game_uuid = _game_uuid(game_id)
    async with get_sessionmaker().begin() as session:
        placed = await _place(
            session,
            game_uuid,
            seat,
            week,
            order,
            decided_by,
            advance_week=True,
            fallback=fallback,
            llm_call_ids=llm_call_ids,
        )
        await _commit_change(session, game_uuid)
    await _settle(game_id)
    return placed


async def _complete_week(game_id: uuid.UUID) -> bool:
    """Whether the Game is running and its open Week is complete, read without a lock;
    refuses an unknown Game."""
    async with get_sessionmaker()() as session:
        game = await repo.get_game(session, game_id)
        if game is None:
            raise CommandError("game_not_found", f"no Game {str(game_id)!r}", 404)
        if game["lifecycle"] != Lifecycle.RUNNING:
            return False
        week = await repo.open_week(session, game_id)
        if week is None:
            return False
        return rules.week_complete(await repo.week_turns(session, game_id, week))


async def _advance_once(game_id: str) -> bool:
    """One `advance` transaction; False, with nothing written, when there is nothing to do."""
    game_uuid = _game_uuid(game_id)
    if not await _complete_week(game_uuid):
        return False
    async with get_sessionmaker().begin() as session:
        game = await repo.lock_game(session, game_uuid)
        if game is None or game["lifecycle"] != Lifecycle.RUNNING:
            return False
        states, _ = await stored_play(session, game_uuid)
        week = states[-1].week
        if not rules.week_complete(await repo.week_turns(session, game_uuid, week)):
            return False  # another command advanced it meanwhile
        settings, params = _snapshot(game)
        _, open_week = await _step(session, game, settings, params, states)
        await _commit_change(session, game_uuid)
    log.info("week_advanced", game_id=game_id, week=week, open_week=open_week)
    return True


async def advance(game_id: str) -> bool:
    """Advance the Game exactly one Week in its own transaction when its open Week is complete
    (`games.rules.week_complete`): open the next Week, whose non-student Seats get their Orders
    from `players.ensure_order`, or run the last Week in full and `finish` the Game. Does
    nothing otherwise (no version change, no event). Like every command it then keeps calling
    `advance` until one does nothing. Returns whether it advanced."""
    if not await _advance_once(game_id):
        return False
    await _settle(game_id)
    return True


def _switch_reason(reason: object) -> OccupancyReason:
    try:
        value = OccupancyReason(reason)
    except ValueError:
        value = None
    if value is None or value is OccupancyReason.INITIAL:
        raise CommandError("reason_invalid", f"{reason!r} is not a reason to switch a Seat", 422)
    return value


async def switch_to_rule_based(
    game_id: str, seat: Role | str, reason: OccupancyReason | str
) -> str:
    """Hand `seat` (a Role or a Seat id) to the Rule-based player for the rest of the Game.

    Appends an occupancy row with `occupant_kind = rule_based` and `reason`; it never edits an
    earlier row (AD-5). A Seat without an Order for the open Week switches from this Week and
    gets its Order from `players.ensure_order` in the same transaction; a Seat that has ordered
    switches from the next Week. Returns the occupancy row id."""
    switch_reason = _switch_reason(reason)
    game_uuid = _game_uuid(game_id)
    async with get_sessionmaker().begin() as session:
        game = await repo.lock_game(session, game_uuid)
        if game is None:
            raise CommandError("game_not_found", f"no Game {game_id!r}", 404)
        row = _seat_row(await repo.seats_with_occupant(session, game_uuid), seat)
        if game["lifecycle"] == Lifecycle.NOT_STARTED:
            raise CommandError("game_not_started", "the Game has not started", 409)
        if game["lifecycle"] == Lifecycle.FINISHED:
            raise CommandError("game_finished", "the Game has finished", 409)
        states, _ = await stored_play(session, game_uuid)
        week = states[-1].week
        ordered = await repo.has_seat_week(session, game_uuid, week, row["id"])
        occupancy_id = uuid.uuid7()
        await repo.append_occupancy(
            session,
            {
                "id": occupancy_id,
                "seat_id": row["id"],
                "from_week": week + 1 if ordered else week,
                "occupant_kind": OccupantKind.RULE_BASED.value,
                "policy_id": None,
                "reason": switch_reason.value,
            },
        )
        if not ordered:
            await _ensure_order(OpenGame(session=session, game_id=game_uuid), row["id"])
        await _commit_change(session, game_uuid)
    log.info("seat_switched", game_id=game_id, seat_id=str(row["id"]), reason=switch_reason)
    await _settle(game_id)
    return str(occupancy_id)


async def finish(session: AsyncSession, game_id: uuid.UUID, state: WeekState) -> None:
    """End the Game inside the caller's command transaction (`place_order`, later
    `games.commands.advance`): store the engine's finished state and set `lifecycle =
    finished`, so no further turn opens (FR-28). The caller has locked the Game row and raises
    its version once for the whole transaction."""
    if not state.finished:
        raise ValueError("finish needs the engine's finished state")
    await repo.insert_week(
        session, game_id, state.week, state.model_dump(mode="json"), finished=True
    )
    await repo.set_lifecycle(session, game_id, Lifecycle.FINISHED.value)
    log.info("game_finished", game_id=str(game_id))
