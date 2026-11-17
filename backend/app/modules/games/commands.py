"""The only write path for Games, Seats, occupancy, turns and Week states (AD-2).

Each command is one transaction: it locks the Game row (`SELECT … FOR UPDATE`), raises the
Game's `version` by one and emits `game:<id>` (AD-8) before it commits. A command that fails
raises `CommandError` and leaves nothing behind: no row, no version change, no event.
"""

import secrets
import uuid
from collections.abc import Mapping, Sequence

import structlog
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import (
    RULES_VERSION,
    DemandPattern,
    GameSettings,
    Role,
    SettingsError,
    WeekState,
    advance,
    demand_series,
    guided_order,
    initial_state,
    rule_based,
    seat_view,
    validate,
)
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
from app.modules.games.views import build_seat_state, stored_orders, stored_play
from app.platform import events
from app.platform.db import get_sessionmaker
from app.platform.parameter_sets import UnknownParameterSetError, read_parameter_set

__all__ = ["CommandError", "assign_seat", "create", "finish", "place_order", "start"]

log = structlog.get_logger(__name__)

ASSIGNABLE = frozenset({OccupantKind.RULE_BASED, OccupantKind.SCRIPTED})
"""Occupant kinds `assign_seat` takes; `llm` (Epic 2) and `student` (Epic 5) come later."""


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
    errors = validate(effective)
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
) -> str:
    """Store a `not_started` Game with one free Seat per Role and its frozen snapshot (AD-4).

    `demand_pattern` and `seed` replace the ones in `settings`; with no seed anywhere a new one
    is drawn. Returns the Game id.
    """
    _policy(purpose)
    effective = _effective_settings(settings, demand_pattern, seed)
    params = _rule_based_params(rule_based_params)
    runtime = SessionRuntime(
        ai_mode="rule_based",
        rule_based_params=params.id,
        rule_based_params_version=params.version,
    )
    game_id = uuid.uuid7()
    async with get_sessionmaker().begin() as session:
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
    return str(game_id)


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
            "a Rule-based occupant uses the Game's parameter set, not a policy id",
            422,
        )
    return occupant, policy_id


async def assign_seat(
    game_id: str, role: Role | str, occupant_kind: OccupantKind | str, policy_id: str | None = None
) -> str:
    """Give the free Seat of `role` its first occupant (`from_week` 1, reason `initial`).

    Returns the occupancy row id. An occupied Seat answers `seat_occupied`.
    """
    game_uuid = _game_uuid(game_id)
    async with get_sessionmaker().begin() as session:
        game = await repo.lock_game(session, game_uuid)
        if game is None:
            raise CommandError("game_not_found", f"no Game {game_id!r}", 404)
        occupant, policy_id = _occupant(str(occupant_kind), policy_id, _policy(game["purpose"]))
        if game["lifecycle"] != Lifecycle.NOT_STARTED:
            raise CommandError(
                "game_already_started", "Seats get their first occupant before the start", 409
            )
        seat = await repo.seat_by_role(session, game_uuid, str(role))
        if seat is None:
            raise CommandError("unknown_role", f"the Game has no Seat for {role!r}", 422)
        if await repo.has_occupant(session, seat["id"]):
            raise CommandError("seat_occupied", f"the {role} Seat already has an occupant", 409)
        occupancy_id = await _append_initial(session, seat["id"], occupant, policy_id)
        await _commit_change(session, game_uuid)
    log.info("seat_assigned", game_id=game_id, seat_id=str(seat["id"]))
    return str(occupancy_id)


async def _append_initial(
    session: AsyncSession, seat_id: uuid.UUID, occupant: OccupantKind, policy_id: str | None
) -> uuid.UUID:
    """Append a Seat's first occupancy row (`from_week` 1, reason `initial`)."""
    occupancy_id = uuid.uuid7()
    await repo.append_occupancy(
        session,
        {
            "id": occupancy_id,
            "seat_id": seat_id,
            "from_week": 1,
            "occupant_kind": occupant.value,
            "policy_id": policy_id,
            "reason": OccupancyReason.INITIAL.value,
        },
    )
    return occupancy_id


def _game_uuid(game_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(game_id)
    except ValueError, TypeError, AttributeError:
        raise CommandError("game_not_found", f"no Game {game_id!r}", 404) from None


def _snapshot(game: Mapping[str, object]) -> tuple[GameSettings, rule_based.RuleBasedParams]:
    """The Game's frozen settings and Rule-based parameters; refuses a snapshot this engine
    cannot reproduce (AD-4)."""
    if game["rules_version"] != RULES_VERSION:
        raise CommandError(
            "rules_version_unsupported",
            f"the Game needs rules version {game['rules_version']}, this engine has "
            f"{RULES_VERSION}",
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


async def _open_week(
    session: AsyncSession,
    game_id: uuid.UUID,
    settings: GameSettings,
    params: rule_based.RuleBasedParams,
    states: Sequence[WeekState],
    orders: Sequence[Mapping[str, int]],
    seat_ids: Mapping[str, uuid.UUID],
) -> None:
    """Store the newest of `states` and one turn per Seat with its Rule-based reference Order,
    computed here once from that Seat's own view (AD-5, AD-20, FR-67)."""
    state = states[-1]
    await repo.insert_week(session, game_id, state.week, state.model_dump(mode="json"))
    await repo.insert_turns(
        session,
        [
            {
                "id": uuid.uuid7(),
                "game_id": game_id,
                "seat_id": seat_ids[role.value],
                "week": state.week,
                "rule_based_reference_order": rule_based.order(
                    settings, seat_view(settings, states, orders, role), params
                ),
            }
            for role in settings.roles
        ],
    )


async def start(game_id: str) -> int:
    """Start a `not_started` Game: give every free Seat a Rule-based player, store the Week 1
    state and open one turn per Seat. Returns the opened Week (1)."""
    game_uuid = _game_uuid(game_id)
    async with get_sessionmaker().begin() as session:
        game = await repo.lock_game(session, game_uuid)
        if game is None:
            raise CommandError("game_not_found", f"no Game {game_id!r}", 404)
        if game["lifecycle"] != Lifecycle.NOT_STARTED:
            raise CommandError("game_already_started", "the Game has already started", 409)
        settings, params = _snapshot(game)
        seat_rows = await repo.seats_with_occupant(session, game_uuid)
        for seat in seat_rows:
            if seat["occupant_kind"] is None:
                await _append_initial(session, seat["id"], OccupantKind.RULE_BASED, None)
        state = initial_state(settings)
        seat_ids = {seat["role"]: seat["id"] for seat in seat_rows}
        await _open_week(session, game_uuid, settings, params, [state], [], seat_ids)
        await repo.set_lifecycle(session, game_uuid, Lifecycle.RUNNING.value)
        await _commit_change(session, game_uuid)
    log.info("game_started", game_id=game_id)
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


async def place_order(
    game_id: str, seat: Role | str, week: int, order: int, decided_by: DecidedBy | str
) -> OrderPlaced:
    """Place the Order of `seat` (a Role or a Seat id) for the open `week` and write its
    Decision log row with the state the Seat saw (AD-15, FR-67).

    When this Order completes the Week (`games.rules.week_complete`), the same transaction
    advances the engine one Week and opens the next turns, or finishes the Game after the last
    Week (AD-2, FR-26, FR-28). The version rises once either way."""
    game_uuid = _game_uuid(game_id)
    async with get_sessionmaker().begin() as session:
        game = await repo.lock_game(session, game_uuid)
        if game is None:
            raise CommandError("game_not_found", f"no Game {game_id!r}", 404)
        seat_rows = await repo.seats_with_occupant(session, game_uuid)
        row = next(
            (r for r in seat_rows if str(seat) in {r["role"], str(r["id"])}),
            None,
        )
        if row is None:
            raise CommandError("seat_not_found", f"the Game has no Seat {seat!r}", 404)
        if game["lifecycle"] == Lifecycle.NOT_STARTED:
            raise CommandError("game_not_started", "the Game has not started", 409)
        if game["lifecycle"] == Lifecycle.FINISHED:
            raise CommandError("game_finished", "the Game has finished", 409)
        decider = _decided_by(decided_by)
        settings, params = _snapshot(game)
        value = _check_order(settings, order)
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
                "fallback": Fallback.NONE.value,
                "occupant_kind": occupancy["occupant_kind"],
                "reason": occupancy["reason"],
                "opened_at": turn["opened_at"],
                "ordered_at": ordered_at,
                "rule_based_reference_order": turn["rule_based_reference_order"],
            },
        )
        lifecycle = Lifecycle(game["lifecycle"])
        open_week: int | None = week
        if rules.week_complete(await repo.week_turns(session, game_uuid, week)):
            week_orders = (await stored_orders(session, game_uuid))[week - 1]
            following = advance(settings, states[-1], week_orders)
            if following.finished:
                await finish(session, game_uuid, following)
                lifecycle, open_week = Lifecycle.FINISHED, None
            else:
                seat_ids = {r["role"]: r["id"] for r in seat_rows}
                await _open_week(
                    session,
                    game_uuid,
                    settings,
                    params,
                    [*states, following],
                    [*orders, week_orders],
                    seat_ids,
                )
                open_week = following.week
        await _commit_change(session, game_uuid)
    log.info("order_placed", game_id=str(game_uuid), seat_id=str(row["id"]), week=week)
    return OrderPlaced(
        seat_week_id=str(seat_week_id), week=week, open_week=open_week, lifecycle=lifecycle
    )


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
