"""The only write path for Games, Seats, occupancy, turns and Week states (AD-2).

Each command is one transaction: it locks the Game row (`SELECT … FOR UPDATE`), raises the
Game's `version` by one and emits `game:<id>` (AD-8) before it commits. A command that fails
raises `CommandError` and leaves nothing behind: no row, no version change, no event.

When a Week opens, and right after a switch, the command calls `players.ensure_order` for its
Seats in its own transaction (AD-5); the Orders it places join that transaction. After its own
commit every command calls `advance` until it does nothing, so a Game whose open Week is
complete moves on one Week per transaction and none is left complete but open (AD-2, NFR-4).

The scheduling aid's `propose_time` and `accept_time` (Story 6.19) join the AD-2 list: they write
the Game's proposal of a time to play, never a turn, so no Week moves and no wait changes (AD-20).
"""

import secrets
import uuid
from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
    Collection,
    Iterable,
    Mapping,
    Sequence,
)
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any

import structlog
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import budget as ai_budget
from app.ai import config as ai_config
from app.analysis import play_guard
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
from app.engine.settings import ROLES
from app.modules.games import overview, repo, rules
from app.modules.games.models import SNAPSHOT_COLUMNS
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
from app.modules.games.service import scope_of, seated_students, student_game
from app.modules.games.turns import OpenGame, play_of
from app.modules.games.views import build_seat_state, stored_orders, stored_play
from app.modules.progress import service as progress
from app.platform import audit, events, notify
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker
from app.platform.parameter_sets import UnknownParameterSetError, read_parameter_set

__all__ = [
    "TAKEOVER_NOTICE",
    "TIME_PROPOSED_NOTICE",
    "CommandError",
    "accept_time",
    "advance",
    "announce_insert_time",
    "assign_seat",
    "create",
    "default_runtime",
    "finish",
    "move_seat",
    "pause",
    "place_order",
    "propose_time",
    "reach_agreed_time",
    "request_reclaim",
    "resume",
    "set_agreed_time",
    "set_snapshot",
    "start",
    "switch_to_rule_based",
    "takeover",
    "view_week",
]

log = structlog.get_logger(__name__)

ASSIGNABLE = frozenset(
    {OccupantKind.RULE_BASED, OccupantKind.SCRIPTED, OccupantKind.LLM, OccupantKind.STUDENT}
)
"""Occupant kinds `assign_seat` takes; `student` where the purpose's policy allows it (5.9)."""

DEFAULT_PLAY_GUARD_SET = "placeholder-0"
"""The Play guard parameter set a new Game freezes when the caller names none (FR-79). A new
set, or a new settings profile in one, is a configuration file, not a change in `analysis`."""


class CommandError(Exception):
    """A refused command, with a stable code for the API envelope (AD-19)."""

    def __init__(
        self,
        code: str,
        message: str,
        status: int,
        fields: Mapping[str, Any] | None = None,
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
    flags = get_settings()
    errors = validate(
        effective,
        capacity_enabled=flags.feature_capacity,
        info_visibility_enabled=flags.feature_info_visibility,
    )
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


def _play_guard_params(set_id: str) -> play_guard.PlayGuardParams:
    try:
        return play_guard.parse_params(read_parameter_set("play_guard", set_id), set_id)
    except UnknownParameterSetError:
        raise CommandError(
            "unknown_parameter_set", f"no Play guard parameter set {set_id!r}", 422
        ) from None
    except ValueError:
        raise CommandError(
            "invalid_parameter_set", f"Play guard parameter set {set_id!r} is invalid", 422
        ) from None


def default_runtime(
    *,
    model_config_id: str | None,
    effort_level: str | None,
    inactivity_limit_hours: int | None = None,
    prompt_versions: Mapping[str, int] | None = None,
    pins: Mapping[str, Any] | None = None,
) -> SessionRuntime:
    """The `SessionRuntime` a Game freezes with today's Rule-based and Play guard parameter sets:
    LLM players with `model_config_id`, Rule-based ones without. The Class session's lock builds
    its snapshot with this (Story 5.11), so a Class game and a Game that takes its snapshot at
    creation have the same shape (AD-4)."""
    params = _rule_based_params(rule_based.DEFAULT_SET_ID)
    guard = _play_guard_params(DEFAULT_PLAY_GUARD_SET)
    return SessionRuntime(
        ai_mode="rule_based" if model_config_id is None else "llm",
        rule_based_params=params.id,
        rule_based_params_version=params.version,
        model_config_id=model_config_id,
        effort_level=effort_level,
        play_guard_params=guard.id,
        play_guard_params_version=guard.version,
        inactivity_limit_hours=inactivity_limit_hours,
        prompt_versions=dict(prompt_versions) if prompt_versions is not None else None,
        pins=dict(pins) if pins is not None else None,
    )


def _frozen_play_guard(runtime: SessionRuntime) -> play_guard.PlayGuardParams | None:
    """The Play guard set the Game froze, or None for a Game created before Story 2.10;
    refuses a set whose version has changed since (AD-4)."""
    if runtime.play_guard_params is None:
        return None
    guard = _play_guard_params(runtime.play_guard_params)
    if guard.version != runtime.play_guard_params_version:
        raise CommandError(
            "parameter_set_changed",
            f"Play guard parameter set {guard.id!r} is now version {guard.version}, the Game "
            f"froze version {runtime.play_guard_params_version}",
            409,
        )
    return guard


async def _commit_change(session: AsyncSession, game_id: uuid.UUID) -> int:
    """Lock the Game row, raise its version, rewrite its `game_summaries` row and announce it;
    the caller's transaction commits. Every command calls it after its own writes, so the
    summary is the Game as this transaction leaves it (Story 7.1, AD-25). A Game the Lecturer
    overview lists also announces its Class session (AD-8, AD-13)."""
    game = await repo.lock_game(session, game_id)
    version = await repo.bump_version(session, game_id)
    if game is not None:
        await overview.refresh(session, game, version)
    await events.emit(session, "game", str(game_id), version)
    if (
        game is not None
        and game["class_session_id"] is not None
        and _policy(game["purpose"]).lecturer_overview
    ):
        await events.emit(session, "session", str(game["class_session_id"]))
    return version


@asynccontextmanager
async def _transaction(within: AsyncSession | None) -> AsyncIterator[AsyncSession]:
    """The command's own transaction, or the caller's (`within`), which commits it."""
    if within is not None:
        yield within
        return
    async with get_sessionmaker().begin() as session:
        yield session


def _class_session(
    game_policy: GamePolicy, class_session_id: uuid.UUID | str | None, game_number: int | None
) -> uuid.UUID | None:
    """The Class session of a new Game: given with its game number exactly when the purpose's
    Games belong to one."""
    if not game_policy.class_session_game:
        if class_session_id is not None or game_number is not None:
            raise CommandError(
                "class_session_not_allowed", "a Game of this purpose has no Class session", 422
            )
        return None
    if class_session_id is None:
        raise CommandError(
            "class_session_required", "a Game of this purpose needs its Class session", 422
        )
    if not game_policy.game_number:
        # A test Game (Story 6.20): the session's, never one of its numbered Class games.
        if game_number is not None:
            raise CommandError(
                "game_number_not_allowed", "a Game of this purpose takes no game number", 422
            )
    elif type(game_number) is not int or game_number < 1:
        raise CommandError(
            "class_session_required",
            "a Game of this purpose needs its Class session and a game number from 1",
            422,
        )
    try:
        return uuid.UUID(str(class_session_id))
    except ValueError:
        raise CommandError(
            "class_session_required", "the Class session id is not an id", 422
        ) from None


async def create(
    purpose: Purpose | str,
    settings: GameSettings | None = None,
    demand_pattern: DemandPattern | None = None,
    seed: int | None = None,
    *,
    rule_based_params: str | None = None,
    model_config_id: str | None = None,
    effort_level: str | None = None,
    play_guard_params: str | None = None,
    batch_id: str | None = None,
    class_session_id: uuid.UUID | str | None = None,
    game_number: int | None = None,
    snapshot: Mapping[str, Any] | None = None,
    within: AsyncSession | None = None,
) -> str:
    """Store a `not_started` Game with one free Seat per Role.

    A purpose whose policy takes the snapshot at creation needs `settings`
    (`settings_required`) and freezes them now (AD-4): `demand_pattern` and `seed` replace the
    ones in `settings`; with no seed anywhere a new one is drawn. `model_config_id` and one of
    that config's Effort levels (default: its first) are frozen into the `SessionRuntime` for the
    Game's LLM players (AD-22, FR-78), and the config is marked referenced, so it can never
    change. The Rule-based and Play guard parameter sets (default: today's) are frozen too
    (FR-79). A purpose that takes it at the lock (Class games, Story 5.9) takes none of these
    (`settings_not_allowed`), stores no snapshot and gets the Classic Roles' Seats.

    `snapshot` is a ready snapshot (Story 6.20), the five `SNAPSHOT_COLUMNS` as
    `sessions.build_snapshot` made them from a Class session: a purpose that takes its snapshot at
    creation stores it as given, checked like `set_snapshot`'s (`invalid_snapshot`), and then takes
    none of the other snapshot arguments (`settings_not_allowed`).

    A purpose whose Games belong to a Class session needs `class_session_id` and `game_number`
    (unique together); others refuse them. `batch_id` puts the Game in a stored simulation batch
    (Story 2.11); an unknown one is refused (`batch_not_found`). `within` is the caller's
    transaction, which commits the Game with its own work (`sessions.confirm_allocation`).
    Returns the Game id.
    """
    game_policy = _policy(purpose)
    class_session = _class_session(game_policy, class_session_id, game_number)
    batch_uuid = _batch_uuid(batch_id)
    snapshot_given = (
        settings,
        demand_pattern,
        seed,
        model_config_id,
        effort_level,
        rule_based_params,
        play_guard_params,
        batch_id,  # a simulation batch freezes its Games' snapshot at creation
    )
    ready: dict[str, Any] | None = None
    if snapshot is not None:
        if game_policy.snapshot != "at_creation" or any(
            value is not None for value in snapshot_given
        ):
            raise CommandError(
                "settings_not_allowed",
                "a ready snapshot comes alone, for a purpose that takes it at creation",
                422,
            )
        ready = _checked_snapshot(snapshot)
    if game_policy.snapshot == "at_lock":
        if any(value is not None for value in snapshot_given):
            raise CommandError(
                "settings_not_allowed",
                "a Game of this purpose takes its snapshot at its Class session's lock",
                422,
            )
        values: dict[str, object] = dict.fromkeys(SNAPSHOT_COLUMNS)
        roles = [role.value for role in ROLES]
    elif ready is not None:
        values = dict(ready)
        roles = [role.value for role in GameSettings.model_validate(ready["settings"]).roles]
    else:
        if settings is None:
            raise CommandError("settings_required", "a Game of this purpose needs settings", 422)
        effective = _effective_settings(settings, demand_pattern, seed)
        params = _rule_based_params(
            rule_based.DEFAULT_SET_ID if rule_based_params is None else rule_based_params
        )
        guard = _play_guard_params(
            DEFAULT_PLAY_GUARD_SET if play_guard_params is None else play_guard_params
        )
        if effort_level is not None and model_config_id is None:
            raise CommandError("model_config_required", "an Effort level needs a model config", 422)
        roles = [role.value for role in effective.roles]
    game_id = uuid.uuid7()
    async with _transaction(within) as session:
        if batch_uuid is not None and await repo.get_batch(session, batch_uuid) is None:
            raise CommandError("batch_not_found", f"no simulation batch {batch_id!r}", 422)
        if ready is not None:
            # The model config of the frozen runtime can never change from now on (FR-78).
            config_id = SessionRuntime.model_validate(ready["session_runtime"]).model_config_id
            if config_id is not None:
                await ai_config.mark_referenced(config_id, session=session)
        elif game_policy.snapshot == "at_creation":
            level = None
            if model_config_id is not None:
                model_config_id, level = await _model_config(session, model_config_id, effort_level)
            runtime = SessionRuntime(
                ai_mode="rule_based" if model_config_id is None else "llm",
                rule_based_params=params.id,
                rule_based_params_version=params.version,
                model_config_id=model_config_id,
                effort_level=level,
                play_guard_params=guard.id,
                play_guard_params_version=guard.version,
            )
            values = {
                "settings": effective.model_dump(mode="json"),
                "demand_series": list(demand_series(effective)),
                "demand_seed": effective.demand_seed,
                "rules_version": RULES_VERSION,
                "session_runtime": runtime.model_dump(mode="json"),
            }
        await repo.insert_game(
            session,
            {
                "id": game_id,
                "purpose": Purpose(purpose).value,
                "lifecycle": Lifecycle.NOT_STARTED.value,
                "version": 0,
                **values,
                "batch_id": batch_uuid,
                "class_session_id": class_session,
                "game_number": game_number if class_session is not None else None,
            },
        )
        await repo.insert_seats(session, game_id, roles)
        await _commit_change(session, game_id)
    log.info("game_created", game_id=str(game_id))
    if within is None:
        await _settle(str(game_id))
    return str(game_id)


def _batch_uuid(batch_id: str | None) -> uuid.UUID | None:
    if batch_id is None:
        return None
    try:
        return uuid.UUID(str(batch_id))
    except ValueError:
        raise CommandError("batch_not_found", f"no simulation batch {batch_id!r}", 422) from None


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
    if (
        occupant not in ASSIGNABLE
        or (occupant is OccupantKind.SCRIPTED and not game_policy.scripted_occupants)
        or (occupant is OccupantKind.STUDENT and not game_policy.student_occupants)
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


def _student(occupant: OccupantKind, user_id: uuid.UUID | str | None) -> uuid.UUID | None:
    """The Student's id: given exactly for a `student` occupant."""
    if occupant is not OccupantKind.STUDENT:
        if user_id is not None:
            raise CommandError(
                "user_id_not_allowed", "only a student occupant takes a user id", 422
            )
        return None
    if user_id is not None:
        try:
            return uuid.UUID(str(user_id))
        except ValueError:
            pass
    raise CommandError("user_id_required", "a student occupant needs the Student's id", 422)


async def assign_seat(
    game_id: str,
    role: Role | str,
    occupant_kind: OccupantKind | str,
    policy_id: str | None = None,
    *,
    user_id: uuid.UUID | str | None = None,
    replace: bool = False,
    within: AsyncSession | None = None,
) -> str:
    """Give the free Seat of `role` its first occupant (`from_week` 1, reason `initial`):
    `rule_based`, `scripted` (with a policy id), `llm`, which needs a Game whose
    `SessionRuntime` holds a model config (`model_config_required`; `game_not_ready` before its
    snapshot), or `student` with the Student's `user_id` (Story 5.9), where the purpose's policy
    allows Students. A Student holds at most one Seat per Class session
    (`student_already_seated`); the caller that seats a Class session's Students holds that
    session's lock, so two of them never race.

    Returns the occupancy row id. An occupied Seat answers `seat_occupied`, unless `replace` is
    given (Story 5.12): then the new occupant is appended after the Seat's current one, whose row
    stays in the history (AD-5). Either way only a `not_started` Game takes it. `within` is the
    caller's transaction, which commits the Seat with its own work.
    """
    game_uuid = _game_uuid(game_id)
    async with _transaction(within) as session:
        game = await repo.lock_game(session, game_uuid)
        if game is None:
            raise CommandError("game_not_found", f"no Game {game_id!r}", 404)
        occupant, policy_id = _occupant(str(occupant_kind), policy_id, _policy(game["purpose"]))
        student = _student(occupant, user_id)
        seat_id, occupancy_id = await _assign(
            session, game, role, occupant, policy_id, student, replace=replace
        )
        await _commit_change(session, game_uuid)
    log.info("seat_assigned", game_id=game_id, seat_id=str(seat_id), replace=replace)
    if within is None:
        await _settle(game_id)
    return str(occupancy_id)


async def _assign(
    session: AsyncSession,
    game: Mapping[str, Any],
    role: Role | str,
    occupant: OccupantKind,
    policy_id: str | None,
    student: uuid.UUID | None,
    *,
    replace: bool,
) -> tuple[uuid.UUID, uuid.UUID]:
    """`assign_seat`'s checks and its one appended row, in the caller's locked transaction; also
    how `set_snapshot` gives a Seat its AI player. Returns the Seat id and the occupancy row id."""
    if occupant is OccupantKind.LLM:
        if game["session_runtime"] is None:
            raise CommandError(
                "game_not_ready", "the Game gets its AI players with its snapshot", 409
            )
        runtime = SessionRuntime.model_validate(game["session_runtime"])
        if runtime.model_config_id is None:
            raise CommandError(
                "model_config_required",
                "an LLM player needs a Game created with a model config",
                422,
            )
    if game["lifecycle"] != Lifecycle.NOT_STARTED:
        raise CommandError(
            "game_already_started", "Seats get their first occupant before the start", 409
        )
    seat = await repo.seat_by_role(session, game["id"], str(role))
    if seat is None:
        raise CommandError("unknown_role", f"the Game has no Seat for {role!r}", 422)
    if not replace and await repo.has_occupant(session, seat["id"]):
        raise CommandError("seat_occupied", f"the {role} Seat already has an occupant", 409)
    if (
        student is not None
        and game["class_session_id"] is not None
        and await repo.student_seated(session, game["class_session_id"], student)
    ):
        raise CommandError(
            "student_already_seated",
            "the Student already holds a Seat in this Class session",
            409,
        )
    reason = OccupancyReason.INITIAL
    if occupant is OccupantKind.LLM and await _cost_limited(session, game):
        # The scope reached the players' cost limit: no new LLM player (FR-69, AD-5).
        occupant, reason = OccupantKind.RULE_BASED, OccupancyReason.COST_LIMIT
    occupancy_id = await _append_initial(
        session, seat["id"], occupant, policy_id, reason, user_id=student
    )
    return seat["id"], occupancy_id


async def set_snapshot(
    game_id: str,
    snapshot: Mapping[str, Any],
    *,
    keep_students: Collection[uuid.UUID],
) -> bool:
    """Give a Game that takes its snapshot at the lock (a Class game) its Class session's frozen
    snapshot (Story 5.12, AD-4): the five `SNAPSHOT_COLUMNS` as `sessions.build_snapshot` made
    them. In the same transaction, under the Game row lock, every free Seat, and every Seat whose
    Student is not in `keep_students` (removed from the Roster since the allocation), gets the AI
    player the snapshot's AI mode gives, `llm` with a model config and `rule_based` without,
    reason `initial`, through `assign_seat`'s own code with `replace` (FR-30, FR-7, AD-5). So
    `start` never fills a Seat with a Rule-based player against the AI mode. That code keeps its
    one exception: once the budget reached the players' cost limit, an LLM player is Rule-based
    with reason `cost_limit` (FR-69).

    The version rises once with `game:<id>` (and `session:<id>`), and every Student who held a
    Seat gets `user:<id>`. A Game that has its snapshot already is left as it is: False, nothing
    written. Refuses `game_not_found`, `snapshot_not_allowed` (a purpose that freezes at
    creation) and `invalid_snapshot`. Returns True when it stored the snapshot."""
    game_uuid = _game_uuid(game_id)
    values = _checked_snapshot(snapshot)
    ai = (
        OccupantKind.LLM
        if SessionRuntime.model_validate(values["session_runtime"]).model_config_id is not None
        else OccupantKind.RULE_BASED
    )
    async with get_sessionmaker().begin() as session:
        game = await repo.lock_game(session, game_uuid)
        if game is None:
            raise CommandError("game_not_found", f"no Game {game_id!r}", 404)
        game_policy = _policy(game["purpose"])
        if game_policy.snapshot != "at_lock":
            raise CommandError(
                "snapshot_not_allowed", "a Game of this purpose froze its snapshot at creation", 422
            )
        if game["settings"] is not None:
            return False
        await repo.set_snapshot(session, game_uuid, values)
        game = {**game, **values}
        kept = {uuid.UUID(str(student)) for student in keep_students}
        seated: list[uuid.UUID] = []
        replaced = 0
        for seat in await repo.seats_with_occupant(session, game_uuid):
            holder = seat["user_id"]
            if seat["occupant_kind"] == OccupantKind.STUDENT:
                seated.append(holder)
                if holder in kept:
                    continue
                replaced += 1
            elif seat["occupant_kind"] is not None:
                continue
            await _assign(session, game, seat["role"], ai, None, None, replace=True)
        await _commit_change(session, game_uuid)
        for student in seated:
            await events.emit(session, "user", str(student))
    log.info(
        "game_snapshot_set",
        game_id=game_id,
        ai_player=ai.value,
        students=len(seated) - replaced,
        removed_students=replaced,
    )
    return True


def _checked_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """The snapshot's five columns, refused (`invalid_snapshot`) unless they reproduce: the
    settings validate, the demand series is theirs, and the runtime is a `SessionRuntime`."""
    if set(snapshot) != set(SNAPSHOT_COLUMNS):
        raise CommandError("invalid_snapshot", "a snapshot has exactly the snapshot columns", 422)
    try:
        settings = GameSettings.model_validate(snapshot["settings"])
        SessionRuntime.model_validate(snapshot["session_runtime"])
    except ValidationError:
        raise CommandError("invalid_snapshot", "the snapshot does not validate", 422) from None
    if (
        list(demand_series(settings)) != list(snapshot["demand_series"])
        or snapshot["demand_seed"] != settings.demand_seed
        or not engine_rules.has_version(snapshot["rules_version"])
    ):
        raise CommandError("invalid_snapshot", "the snapshot does not reproduce", 422)
    return {column: snapshot[column] for column in SNAPSHOT_COLUMNS}


async def move_seat(
    game_id: str,
    role: Role | str,
    to_game_id: str,
    to_role: Role | str,
    *,
    within: AsyncSession | None = None,
) -> None:
    """Move the Student of one Seat to another Seat of the same Class session before the start
    (Story 5.10, FR-20): to a free Seat, which leaves the first Seat free, or to a Seat another
    Student holds, who takes the first Seat (a swap). Both Games are locked in id order, so two
    moves over the same Games never deadlock.

    The Seats get rows from Week 1 (`student`, reason `initial`); a Seat left free gets a row
    with no occupant kind and reason `moved`, since occupancy is append-only (AD-5). Each Game's
    version rises with `game:<id>` (and `session:<id>`), and each moved Student gets
    `user:<id>`. A Student holds one Seat per Class session afterwards
    (`student_already_seated` otherwise, nothing kept).

    Refuses `game_not_found`, `game_already_started`, `class_session_mismatch` (the two Games are
    not of one Class session), `occupant_kind_not_allowed` (no Students in this purpose),
    `unknown_role`, `same_seat`, `seat_not_student` (no Student to move) and `seat_occupied` (the
    target holds an AI player). `within` is the caller's transaction (`sessions`).
    """
    source_id, target_id = _game_uuid(game_id), _game_uuid(to_game_id)
    async with _transaction(within) as session:
        locked: dict[uuid.UUID, Mapping[str, object]] = {}
        for each in sorted({source_id, target_id}):
            game = await repo.lock_game(session, each)
            if game is None:
                raise CommandError("game_not_found", f"no Game {str(each)!r}", 404)
            locked[each] = game
        source, target = locked[source_id], locked[target_id]
        if source["class_session_id"] is None or (
            source["class_session_id"] != target["class_session_id"]
        ):
            raise CommandError(
                "class_session_mismatch", "a Student moves between Games of one Class session", 422
            )
        if not _policy(str(source["purpose"])).student_occupants:
            raise CommandError(
                "occupant_kind_not_allowed", "a Seat of this Game cannot be given a Student", 422
            )
        if any(game["lifecycle"] != Lifecycle.NOT_STARTED for game in locked.values()):
            raise CommandError(
                "game_already_started", "Students move only before the Game starts", 409
            )
        from_seat = await repo.seat_by_role(session, source_id, str(role))
        to_seat = await repo.seat_by_role(session, target_id, str(to_role))
        if from_seat is None or to_seat is None:
            raise CommandError("unknown_role", "the Game has no Seat for that Role", 422)
        if from_seat["id"] == to_seat["id"]:
            raise CommandError("same_seat", "a Student moves to another Seat", 422)
        moving = _holder(await repo.seats_with_occupant(session, source_id), from_seat["id"])
        staying = _holder(await repo.seats_with_occupant(session, target_id), to_seat["id"])
        if moving is None or moving["occupant_kind"] != OccupantKind.STUDENT:
            raise CommandError("seat_not_student", f"no Student holds the {role} Seat", 409)
        if staying is not None and staying["occupant_kind"] not in (None, OccupantKind.STUDENT):
            raise CommandError(
                "seat_occupied", f"the {to_role} Seat holds a player who does not move", 409
            )
        swapped = staying["user_id"] if staying is not None else None
        await _append_initial(
            session, to_seat["id"], OccupantKind.STUDENT, None, user_id=moving["user_id"]
        )
        if swapped is not None:
            await _append_initial(
                session, from_seat["id"], OccupantKind.STUDENT, None, user_id=swapped
            )
        else:
            await repo.append_occupancy(
                session,
                {
                    "id": uuid.uuid7(),
                    "seat_id": from_seat["id"],
                    "from_week": 1,
                    "occupant_kind": None,
                    "policy_id": None,
                    "reason": OccupancyReason.MOVED.value,
                    "user_id": None,
                },
            )
        students = [moving["user_id"], *([swapped] if swapped is not None else [])]
        class_session = source["class_session_id"]
        for student in students:
            if await repo.student_seat_count(session, class_session, student) != 1:
                raise CommandError(
                    "student_already_seated",
                    "the Student already holds a Seat in this Class session",
                    409,
                )
        for each in sorted(locked):
            await _commit_change(session, each)
        for student in students:
            await events.emit(session, "user", str(student))
    log.info(
        "seat_moved",
        game_id=str(source_id),
        to_game_id=str(target_id),
        swapped=swapped is not None,
    )


def _holder(
    rows: Sequence[Mapping[str, object]], seat_id: uuid.UUID
) -> Mapping[str, object] | None:
    """The Seat's row from `repo.seats_with_occupant`: its latest occupant kind and Student."""
    return next((row for row in rows if row["id"] == seat_id), None)


async def _append_initial(
    session: AsyncSession,
    seat_id: uuid.UUID,
    occupant: OccupantKind,
    policy_id: str | None,
    reason: OccupancyReason = OccupancyReason.INITIAL,
    *,
    user_id: uuid.UUID | None = None,
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
            "user_id": user_id,
        },
    )
    return occupancy_id


async def _cost_limited(session: AsyncSession, game: Mapping[str, object]) -> bool:
    """Whether the budget the Game charges has reached the players' cost limit
    (`players_exhausted_at`, FR-69): from then on no Seat of it gets an LLM player."""
    if game["session_runtime"] is None:
        return False
    runtime = SessionRuntime.model_validate(game["session_runtime"])
    scope = scope_of(str(game["purpose"]), runtime, game["class_session_id"])
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
    _frozen_play_guard(runtime)
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
    Student holds a Seat. Emits `game:<id>`, `session:<id>` where the Lecturer overview lists
    the Game, and `user:<id>` for each Student holding a Seat (Story 6.5)."""
    game_uuid = _game_uuid(game_id)
    async with get_sessionmaker().begin() as session:
        game = await repo.lock_game(session, game_uuid)
        if game is None:
            raise CommandError("game_not_found", f"no Game {game_id!r}", 404)
        if game["lifecycle"] != Lifecycle.NOT_STARTED:
            raise CommandError("game_already_started", "the Game has already started", 409)
        if game["settings"] is None:
            raise CommandError(
                "game_not_ready",
                "the Game has no settings snapshot yet (it comes at the lock)",
                409,
            )
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
        # Story 6.5: each Student in the Game sees it started, on Hjem too (AD-8).
        for student in sorted(
            {
                str(seat["user_id"])
                for seat in seat_rows
                if seat["occupant_kind"] == OccupantKind.STUDENT and seat["user_id"] is not None
            }
        ):
            await events.emit(session, "user", student)
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
        # A Reclaim queued in the last Week has no Week to take effect in (Story 8.4).
        await repo.delete_reclaims(session, game_uuid)
        await finish(session, game_uuid, following)
        return Lifecycle.FINISHED, None
    await _apply_reclaims(session, game_uuid, following.week)
    seat_rows = await repo.seats_with_occupant(session, game_uuid)
    await _open_week(
        session, game, settings, params, [*states, following], [*orders, week_orders], seat_rows
    )
    return Lifecycle.RUNNING, following.week


async def _apply_reclaims(session: AsyncSession, game_id: uuid.UUID, week: int) -> None:
    """Hand each queued Reclaim's Seat back to its Student from the Week about to open (Story 8.4,
    FR-37, AD-5): one appended occupancy row, occupant `student`, reason `reclaim`, the Student as
    `actor_user_id`, in the transaction that opens the Week; the request is deleted either way. A
    Seat a Student holds already (none today) is left as it is. Its new turn starts with no clock
    running: the wait starts only when another Student orders (`_start_waits`)."""
    queued = await repo.queued_reclaims(session, game_id)
    if not queued:
        return
    holders = {row["id"]: row for row in await repo.seats_with_occupant(session, game_id)}
    for seat_id, user_id in sorted(queued.items(), key=lambda item: str(item[0])):
        holder = holders.get(seat_id)
        if holder is not None and holder["occupant_kind"] not in (None, OccupantKind.STUDENT):
            await repo.append_occupancy(
                session,
                {
                    "id": uuid.uuid7(),
                    "seat_id": seat_id,
                    "from_week": week,
                    "occupant_kind": OccupantKind.STUDENT.value,
                    "policy_id": None,
                    "reason": OccupancyReason.RECLAIM.value,
                    "user_id": user_id,
                    "actor_user_id": user_id,
                },
            )
            log.info("seat_reclaimed", game_id=str(game_id), seat_id=str(seat_id), week=week)
        await repo.delete_reclaim(session, seat_id)


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
    actor: uuid.UUID | None = None,
) -> OrderPlaced:
    """`place_order`'s checks and writes in `session`; with `advance_week` it also runs the Week
    this Order completes. `open_game` is the running command's Game, whose history it reuses.
    With an `actor`, the Seat's occupant in force must be that Student (Story 6.12)."""
    game = await repo.lock_game(session, game_uuid)
    if game is None:
        raise CommandError("game_not_found", f"no Game {str(game_uuid)!r}", 404)
    seat_rows = await repo.seats_with_occupant(session, game_uuid)
    row = _seat_row(seat_rows, seat)
    if game["lifecycle"] == Lifecycle.NOT_STARTED:
        raise CommandError("game_not_started", "the Game has not started", 409)
    decider = _decided_by(decided_by)
    marked = _fallback(fallback)
    call_ids = _call_ids(llm_call_ids)
    settings, params = _snapshot(game)
    value = _check_order(settings, order)
    # The Seat's stored Order for `week` answers `order_exists` before the Week or the Game is
    # found closed: a retry of an Order that completed the Week, or the last Week, is told its
    # Order stands (Story 6.13).
    stored = (
        type(week) is int
        and week >= 1
        and await repo.has_seat_week(session, game_uuid, week, row["id"])
    )
    if stored:
        await _check_actor(session, row, week, actor)
        raise CommandError("order_exists", "the Seat has already ordered this Week", 409)
    if game["lifecycle"] == Lifecycle.FINISHED:
        raise CommandError("game_finished", "the Game has finished", 409)
    if open_game is not None:
        states, orders = await play_of(open_game)
    else:
        states, orders = await stored_play(session, game_uuid)
    if type(week) is not int or week != states[-1].week:
        raise CommandError("week_not_open", f"Week {week!r} is not the open Week", 409)
    await _check_actor(session, row, week, actor)
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
            # The turn's wait start and FR-36 due times as they stand now (Story 8.1, AD-15).
            "wait_started_at": turn["wait_started_at"],
            "takeover_due_at": turn["takeover_due_at"],
            "insert_allowed_at": turn["insert_allowed_at"],
            # The Effort level the Game froze, on every Order of an LLM player (FR-78).
            "effort_level": (
                SessionRuntime.model_validate(game["session_runtime"]).effort_level
                if llm_occupant
                else None
            ),
        },
    )
    if decider is DecidedBy.LLM:
        await _run_play_guard(session, game, settings, row, week)
    pause_ended = False
    if decider is DecidedBy.STUDENT:
        await _start_waits(session, game, week)
        # Story 8.6 (FR-89): any Student's Order ends the Pause, whoever set it. The due times
        # kept running, so a Seat already past its due time is taken at the next sweep.
        student = occupancy["user_id"]
        if rules.is_paused(game) and student is not None:
            await repo.end_pause(session, game_uuid, student)
            pause_ended = True
    lifecycle, open_week = Lifecycle(game["lifecycle"]), week
    if advance_week and await _week_complete(session, game, week):
        lifecycle, open_week = await _step(session, game, settings, params, states)
    log.info("order_placed", game_id=str(game_uuid), seat_id=str(row["id"]), week=week)
    return OrderPlaced(
        seat_week_id=str(seat_week_id),
        week=week,
        open_week=open_week,
        lifecycle=lifecycle,
        pause_ended=pause_ended,
    )


async def _check_actor(
    session: AsyncSession, row: Mapping[str, object], week: int, actor: uuid.UUID | None
) -> None:
    """With an `actor`, the Seat's occupant in Week `week` must be that Student, before anything
    about the Seat's Order is told: only its Student may know (FR-5)."""
    if actor is None:
        return
    holder = await repo.occupancy_in_force(session, row["id"], week)
    if (
        holder is None
        or holder["occupant_kind"] != OccupantKind.STUDENT
        or holder["user_id"] != actor
    ):
        raise CommandError("seat_not_yours", "the Seat is not the actor's", 409)


async def _run_play_guard(
    session: AsyncSession,
    game: Mapping[str, object],
    settings: GameSettings,
    seat: Mapping[str, object],
    week: int,
) -> None:
    """Run the Play guard over the Seat's stored Decision log rows, the new LLM Order included,
    in the caller's transaction (FR-79, AD-5). On `switch` the Seat gets a Rule-based player
    from the next Week for the rest of the Game: one appended occupancy row, reason
    `guard_switch`. Games created before Story 2.10 froze no set and are not guarded."""
    guard = _frozen_play_guard(SessionRuntime.model_validate(game["session_runtime"]))
    if guard is None:
        return
    rows = await repo.seat_guard_rows(session, game["id"], seat["id"])
    result = play_guard.evaluate(
        [play_guard.GuardRow.model_validate(dict(row)) for row in rows],
        guard,
        calibrated=play_guard.is_calibrated(settings, guard),
    )
    if result.decision is not play_guard.GuardDecision.SWITCH:
        return
    await repo.append_occupancy(
        session,
        {
            "id": uuid.uuid7(),
            "seat_id": seat["id"],
            "from_week": week + 1,
            "occupant_kind": OccupantKind.RULE_BASED.value,
            "policy_id": None,
            "reason": OccupancyReason.GUARD_SWITCH.value,
        },
    )
    log.info(
        "play_guard_switched",
        game_id=str(game["id"]),
        seat_id=str(seat["id"]),
        week=week,
        statistic=result.statistic,
        value=str(result.value),
        parameter_set=guard.id,
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
    actor: uuid.UUID | str | None = None,
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
    reference Order, an `llm` occupant) carries its failure type and the failed attempts.

    An Order with `decided_by = llm` runs the Play guard in the same transaction; on `switch`
    the Seat is Rule-based from the next Week, reason `guard_switch` (FR-79, AD-5).

    `actor` is the User who pressed «Bekreft ordre» (Story 6.12, AD-2): the Seat's occupant in
    force must be that Student, or the command refuses `seat_not_yours` and writes nothing. Calls
    without a person (guided Orders, `players` jobs, the rescue loop) pass none and skip the
    check. Emits `game:<id>`, `session:<id>` where the Lecturer overview lists the Game, and
    `user:<id>` for the actor and, when the Order completed the Week or ended the Pause, for every
    Student holding a Seat (AD-8).

    A Student's Order (`decided_by = student`) on a paused Game ends the Pause in the same
    transaction, whoever set it (Story 8.6, FR-89): the Pause columns are cleared and who ended it,
    and when, is kept for «Pausen er over.»."""
    actor_id: uuid.UUID | None = None
    if actor is not None:
        actor_id = _actor(actor)
        if actor_id is None:
            raise CommandError("seat_not_yours", "the Seat is not the actor's", 409)
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
            actor=actor_id,
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
            actor=actor_id,
        )
        await _commit_change(session, game_uuid)
        told: set[uuid.UUID] = {actor_id} if actor_id is not None else set()
        if (
            placed.open_week != placed.week
            or placed.lifecycle == Lifecycle.FINISHED
            or placed.pause_ended
        ):
            # The Week is done: every Student of the Game waits on a new one, or on nothing; or
            # the Order ended the Pause, which every Student of the Game reads (Story 8.6).
            told |= {
                row["user_id"]
                for row in await repo.seats_with_occupant(session, game_uuid)
                if row["occupant_kind"] == OccupantKind.STUDENT and row["user_id"] is not None
            }
        for student in sorted(str(each) for each in told):
            await events.emit(session, "user", student)
    await _settle(game_id)
    return placed


def _actor(actor: object) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(actor))
    except ValueError, TypeError, AttributeError:
        return None


async def view_week(game_id: str, seat: Role | str, week: int, *, actor: uuid.UUID | str) -> bool:
    """The Student `actor` has the Guided Week `week` on screen (Story 6.10, FR-24, AD-2): set
    `viewed_at` on their Seat's turn, once. In a Guided Week viewing counts as ordering (founder
    decision 2026-11-12): the Seat's fixed Order was placed when the Week opened, and the view
    that leaves no Student Seat unviewed completes the Week (`games.rules.week_complete`), which
    then advances exactly one Week in this transaction.

    One transaction with the Game row lock and a version bump, emitting `game:<id>`,
    `session:<id>` where the Lecturer overview lists the Game, and `user:<id>` for the viewer and,
    when the Week advances, for every Student holding a Seat (AD-8). A Week already viewed changes
    nothing: no write, no version, no event; returns False then, True when it recorded the view.

    Refuses `game_not_found`, `seat_not_found`, `game_not_started`, `game_finished`,
    `week_not_open` (not the open Week), `week_not_guided`, `seat_not_student` (no Student holds
    the Seat in that Week) and `seat_not_yours` (another Student does)."""
    game_uuid = _game_uuid(game_id)
    actor_id = _actor(actor)
    async with get_sessionmaker().begin() as session:
        game = await repo.lock_game(session, game_uuid)
        if game is None:
            raise CommandError("game_not_found", f"no Game {game_id!r}", 404)
        seat_rows = await repo.seats_with_occupant(session, game_uuid)
        row = _seat_row(seat_rows, seat)
        if game["lifecycle"] == Lifecycle.NOT_STARTED:
            raise CommandError("game_not_started", "the Game has not started", 409)
        if game["lifecycle"] == Lifecycle.FINISHED:
            raise CommandError("game_finished", "the Game has finished", 409)
        settings, params = _snapshot(game)
        states, _ = await stored_play(session, game_uuid)
        if type(week) is not int or week != states[-1].week:
            raise CommandError("week_not_open", f"Week {week!r} is not the open Week", 409)
        if not rules.guided_week(_policy(game["purpose"]), settings, week):
            raise CommandError("week_not_guided", f"Week {week} is not a Guided Week", 409)
        turn = await repo.turn(session, game_uuid, row["id"], week)
        occupancy = await repo.occupancy_in_force(session, row["id"], week)
        if turn is None or occupancy is None:  # `start` and every advance write both
            raise CommandError("week_not_open", f"the Seat has no turn in Week {week}", 409)
        if occupancy["occupant_kind"] != OccupantKind.STUDENT:
            raise CommandError("seat_not_student", "no Student holds the Seat this Week", 409)
        if actor_id is None or occupancy["user_id"] != actor_id:
            raise CommandError("seat_not_yours", "another Student holds the Seat", 409)
        if turn["viewed_at"] is not None:
            return False
        if turn["ordered_at"] is None:
            # A Week opened before the Student's Guided Order was placed at opening (a Game
            # started before Story 6.10): place it now, so the view can complete the Week.
            await _ensure_order(OpenGame(session=session, game_id=game_uuid), row["id"])
        await repo.set_viewed_at(session, turn["id"])
        await _start_waits(session, game, week)
        advanced = await _week_complete(session, game, week)
        if advanced:
            await _step(session, game, settings, params, states)
        await _commit_change(session, game_uuid)
        told = {actor_id}
        if advanced:  # a new Week opens for every Student of the Game, one back by a Reclaim too
            told |= seated_students(await repo.seats_with_occupant(session, game_uuid))
        for student in sorted(str(each) for each in told):
            await events.emit(session, "user", student)
    log.info("week_viewed", game_id=game_id, seat_id=str(row["id"]), week=week, advanced=advanced)
    await _settle(game_id)
    return True


async def _start_waits(session: AsyncSession, game: Mapping[str, Any], week: int) -> None:
    """A Student has ordered in `week`, or viewed it as a Guided Week: from now the game waits
    for every Seat that has not ordered (`rules.has_ordered`). Each such turn without a wait
    start gets one, from `rules.turn_times` with this transaction's clock as the clock start
    (Story 6.14, FR-25, AD-20); one already set stays, so the first Student's moment counts.
    A Student-held one also gets its FR-36 due times from the Inactivity limit in the Game's
    `SessionRuntime`, when the Game's policy has inactivity Takeover (Story 8.1, AD-13). An insert
    time a Lecturer's agreed Pause time gave the turn before any clock ran is its agreed time, so
    it stays the insert time for this Week after the Order (Story 8.7, open-assumptions)."""
    guided = rules.guided_week(
        _policy(game["purpose"]), GameSettings.model_validate(game["settings"]), week
    )
    turns = await repo.week_turns_with_occupant(session, game["id"], week)
    waiting = [
        turn
        for turn in turns
        if turn["wait_started_at"] is None and not rules.has_ordered(turn, guided=guided)
    ]
    if not waiting:
        return
    clock_start = await repo.now(session)
    limit = _inactivity_limit(game)
    for turn in waiting:
        kind = OccupantKind(turn["occupant_kind"] or OccupantKind.RULE_BASED)
        seat = rules.TurnSeat(occupant_kind=kind, opened_at=turn["opened_at"])
        inputs = rules.TurnInputs(
            clock_start=clock_start,
            inactivity_limit=limit,
            agreed_time=turn["insert_allowed_at"],
        )
        times = rules.turn_times(rules.TurnGame(guided_week=guided), seat, inputs)
        await repo.set_wait_times(
            session,
            turn["id"],
            wait_started_at=times.wait_started_at,
            takeover_due_at=times.takeover_due_at,
            insert_allowed_at=times.insert_allowed_at,
        )


def _inactivity_limit(game: Mapping[str, Any]) -> timedelta | None:
    """The Inactivity limit the Game froze (Story 5.11), or None when its policy has no
    inactivity Takeover (a Replay, a Lecturer's test Game, a simulation, AD-13) or it froze none."""
    if not _policy(game["purpose"]).inactivity_takeover or game["session_runtime"] is None:
        return None
    hours = SessionRuntime.model_validate(game["session_runtime"]).inactivity_limit_hours
    return None if hours is None else timedelta(hours=hours)


async def _unviewed_guided_student(
    session: AsyncSession, game: Mapping[str, Any], seat_id: uuid.UUID, week: int
) -> bool:
    """Whether `week` is a Guided Week whose turn of `seat_id` a Student holds and has not
    viewed: that Seat has not ordered yet (Story 6.10)."""
    settings = GameSettings.model_validate(game["settings"])
    if not rules.guided_week(_policy(game["purpose"]), settings, week):
        return False
    occupancy = await repo.occupancy_in_force(session, seat_id, week)
    turn = await repo.turn(session, game["id"], seat_id, week)
    return (
        occupancy is not None
        and occupancy["occupant_kind"] == OccupantKind.STUDENT
        and turn is not None
        and turn["viewed_at"] is None
    )


async def _week_complete(session: AsyncSession, game: Mapping[str, Any], week: int) -> bool:
    """`games.rules.week_complete` for the Game's `week`, with the occupants in force in it and
    whether it is a Guided Week (Story 6.10)."""
    guided = rules.guided_week(
        _policy(game["purpose"]), GameSettings.model_validate(game["settings"]), week
    )
    turns = await repo.week_turns_with_occupant(session, game["id"], week)
    return rules.week_complete(turns, guided=guided)


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
        return await _week_complete(session, game, week)


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
        if not await _week_complete(session, game, week):
            return False  # another command advanced it meanwhile
        settings, params = _snapshot(game)
        _, open_week = await _step(session, game, settings, params, states)
        await _commit_change(session, game_uuid)
        # Every Student of the Game waits on a new Week, or on nothing: their Hjem reads again,
        # as after the Order that completes a Week (follow-up review of Story 6.13).
        for student in sorted(seated_students(await repo.seats_with_occupant(session, game_uuid))):
            await events.emit(session, "user", str(student))
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
    switches from the next Week. In a Guided Week a Student Seat that has not viewed the Week
    has not ordered (Story 6.10), so it switches from this Week. Returns the occupancy row id."""
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
        if ordered and await _unviewed_guided_student(session, game, row["id"], week):
            # Viewing counts as ordering in a Guided Week (Story 6.10): a Student who has not
            # opened it has not ordered, so the new occupant takes this Week.
            ordered = False
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


TAKEOVER_NOTICE = "takeover_notice"
"""The notice kind each Student of a Class game gets when an AI player takes a Seat over,
`immediate` (Story 8.2, AD-9). Its `ref` is the occupancy row; the mail reads it at send time."""


async def takeover(
    game_id: str,
    seat: Role | str,
    *,
    actor: rules.TakeoverActor,
    actor_user_id: uuid.UUID | str | None = None,
    now: datetime | None = None,
) -> str:
    """Hand the Student-held `seat` (a Role or a Seat id) to an AI player (Stories 8.2 and 8.5,
    FR-36, FR-37, AD-2, AD-5). `actor` `system` is the sweep's automatic Takeover after the
    Inactivity limit; `staff` is a Lecturer or Assistant lecturer, `actor_user_id`, pressing
    «Sett inn KI-spiller» in Spillstyring; `peer` is a Student of the game, `actor_user_id`, who
    holds another Seat of it and presses «Sett inn KI-spiller for Jonas» once the Seat's insert
    time has passed (Story 8.8, FR-89): reason `takeover_peer` with the Student as actor and an
    audit row, refused `seat_not_yours` without another Seat and `insert_not_allowed_yet` before
    the insert time. `now` is the clock a `system` Takeover judges the due time on (the sweep's),
    the database clock when none is given.

    One transaction under the Game row lock: `rules.can_take_over` decides (refusals below), one
    occupancy row is appended with reason `takeover_inactivity` and no `actor_user_id`,
    `takeover_staff` with the staff member, or `takeover_peer` with the Student (each person's
    with an audit row, FR-3, AD-15). A Seat that has not
    ordered (`has_ordered`) is taken from the open Week and `players.ensure_order` gives it its
    Order in the same transaction; a Seat that has ordered (only a `staff` Takeover may) is taken
    from the next Week and its Order stands. The new occupant is `llm` when the Game froze a
    model config, else `rule_based`; and `rule_based` when the Play guard has switched the Seat
    before or the budget reached the players' cost limit (FR-30, FR-69, FR-79). An `llm` occupant
    taken this Week gets its turn's AI deadline from `rules.turn_times`, counted from now. In a
    Guided Week the Seat keeps the fixed Order placed at opening; when no other Student Seat is
    still unviewed the Week is then complete, and `_settle` advances it after the commit (FR-24).

    The version rises once with `game:<id>` and `session:<id>`; every Student who holds a Seat
    and the Student whose Seat it was get `user:<id>`, and each of them one `takeover_notice`
    (dedupe key per occupancy row) (AD-8, AD-9). A staff Takeover of a Seat that has ordered the
    Game's last Week is refused `order_exists`: no Week is left for it. Refuses `game_not_found`,
    `seat_not_found`, and 409 `game_not_running`, `takeover_not_allowed`, `game_paused` (a `system`
    Takeover of a paused Game, Story 8.6), `seat_not_student_held`, `order_exists`,
    `takeover_not_due`, and `takeover_exists` with `fields.acted_by` (`kind`
    `staff`, `student` or `system`, and `user_id`) and `fields.acted_at`: who acted first, by id
    only (Story 8.5). Returns the occupancy row id."""
    game_uuid = _game_uuid(game_id)
    person = _actor(actor_user_id) if actor in ("staff", "peer") else None
    if actor in ("staff", "peer") and person is None:
        raise ValueError("a staff or peer Takeover names the person who pressed")
    async with get_sessionmaker().begin() as session:
        game = await repo.lock_game(session, game_uuid)
        if game is None:
            raise CommandError("game_not_found", f"no Game {game_id!r}", 404)
        seat_rows = await repo.seats_with_occupant(session, game_uuid)
        row = _seat_row(seat_rows, seat)
        # Story 8.8: a Student puts an AI player in only from another Seat of the same Game that
        # they hold now.
        peer_seated = actor == "peer" and any(
            other["id"] != row["id"]
            and other["occupant_kind"] == OccupantKind.STUDENT
            and other["user_id"] == person
            for other in seat_rows
        )
        week = await repo.open_week(session, game_uuid) if game["settings"] is not None else None
        turn = None
        guided = False
        if week is not None:
            turns = await repo.week_turns_with_occupant(session, game_uuid, week)
            turn = next((t for t in turns if t["seat_id"] == row["id"]), None)
            guided = rules.guided_week(
                _policy(game["purpose"]), GameSettings.model_validate(game["settings"]), week
            )
        at = now if now is not None else await repo.clock_now(session)
        refused = rules.can_take_over(
            game, turn, actor, at, guided=guided, seat=row, peer_seated=peer_seated
        )
        if refused == "takeover_exists":
            raise CommandError(
                refused, "an AI player has taken the Seat over already", 409, _acted(row)
            )
        if refused is not None:
            raise CommandError(refused, "the Seat cannot be taken over now", 409)
        assert turn is not None and week is not None  # `can_take_over` refuses otherwise
        student = turn["user_id"]
        ordered = rules.has_ordered(turn, guided=guided)
        if ordered and week >= GameSettings.model_validate(game["settings"]).weeks:
            # The Seat has ordered the last Week: no Week is left for an AI player to take.
            raise CommandError("order_exists", "the Seat has ordered the last Week", 409)
        from_week = week + 1 if ordered else week
        occupant = await _takeover_occupant(session, game, row["id"])
        occupancy_id = uuid.uuid7()
        reason = {
            "staff": OccupancyReason.TAKEOVER_STAFF,
            "peer": OccupancyReason.TAKEOVER_PEER,
        }.get(actor, OccupancyReason.TAKEOVER_INACTIVITY)
        await repo.append_occupancy(
            session,
            {
                "id": occupancy_id,
                "seat_id": row["id"],
                "from_week": from_week,
                "occupant_kind": occupant.value,
                "policy_id": None,
                "reason": reason.value,
                "actor_user_id": person,
            },
        )
        if not ordered:
            if occupant is OccupantKind.LLM and not guided:
                await _takeover_deadline(session, game, turn)
            await _ensure_order(OpenGame(session=session, game_id=game_uuid), row["id"])
        if person is not None:
            await audit.record(
                session,
                person,
                SEAT_TAKEN_OVER,
                # `user_id`: whose Seat it was, named on the audit page by its labeler.
                {
                    "game_id": game_uuid,
                    "seat_id": row["id"],
                    "occupancy_id": occupancy_id,
                    "user_id": student,
                },
                {"reason": reason.value, "from_week": from_week, "occupant_kind": occupant.value},
                at,
            )
        await _commit_change(session, game_uuid)
        told = set(seated_students(await repo.seats_with_occupant(session, game_uuid)))
        if student is not None:
            told.add(student)
        for each in sorted(told, key=str):
            await events.emit(session, "user", str(each))
            await notify.enqueue(
                session,
                each,
                TAKEOVER_NOTICE,
                f"{TAKEOVER_NOTICE}:{occupancy_id}:{each}",
                ref=occupancy_id,
            )
    log.info(
        "seat_taken_over",
        game_id=game_id,
        seat_id=str(row["id"]),
        week=week,
        from_week=from_week,
        occupant_kind=occupant.value,
        actor=actor,
    )
    await _settle(game_id)
    return str(occupancy_id)


SEAT_TAKEN_OVER = "seat.taken_over"
"""The audit action of a Takeover a person triggered (Story 8.5, FR-3, AD-15)."""

_ACTED_BY_KIND = {
    OccupancyReason.TAKEOVER_STAFF: "staff",
    OccupancyReason.TAKEOVER_PEER: "student",
    OccupancyReason.TAKEOVER_INACTIVITY: "system",
}


def _acted(row: Mapping[str, Any]) -> dict[str, Any]:
    """`fields` of a `takeover_exists` refusal (Story 8.5, the deferred decision on conflict
    errors): who put the AI player in, as a kind and a User id (None for the system), and when.
    Ids only: the web app reads the name from the view it reads again (AD-14)."""
    kind = _ACTED_BY_KIND.get(OccupancyReason(row["reason"]), "system")
    actor = row["actor_user_id"]
    created = row["created_at"]
    return {
        "acted_by": {"kind": kind, "user_id": None if actor is None else str(actor)},
        "acted_at": None if created is None else created.isoformat(),
    }


async def request_reclaim(game_id: str, seat: Role | str, *, actor: uuid.UUID | str) -> bool:
    """«Ta tilbake setet» (Story 8.4, FR-37, AD-2): the Student `actor` asks for the Seat an AI
    player took over from them. The request is queued and changes no occupancy; the command that
    opens the next Week hands the Seat back (`_apply_reclaims`). Returns True when it queued the
    request; False, writing nothing, when one is queued already or a Reclaim gave the Seat back.

    One transaction under the Game row lock with a version bump: `game:<id>`, `session:<id>` and
    `user:<actor>` (AD-8). Refuses `game_not_found`, `seat_not_found` (404) and 409
    `game_finished`, `game_not_running` (not started) and `seat_not_yours`: anyone but the Student
    of the Seat's latest Student row, or a Seat no Takeover holds since that row."""
    game_uuid = _game_uuid(game_id)
    actor_id = _actor(actor)
    async with get_sessionmaker().begin() as session:
        game = await repo.lock_game(session, game_uuid)
        if game is None:
            raise CommandError("game_not_found", f"no Game {game_id!r}", 404)
        row = _seat_row(await repo.seats_with_occupant(session, game_uuid), seat)
        if game["lifecycle"] == Lifecycle.FINISHED:
            raise CommandError("game_finished", "the Game has finished", 409)
        if game["lifecycle"] != Lifecycle.RUNNING:
            raise CommandError("game_not_running", "the Game is not running", 409)
        history = (await repo.seat_histories(session, game_uuid)).get(row["id"])
        if actor_id is None or history is None or history["last_student"] != actor_id:
            raise CommandError("seat_not_yours", "the Seat was never the actor's", 409)
        if (
            row["occupant_kind"] == OccupantKind.STUDENT
            and row["reason"] == OccupancyReason.RECLAIM
        ):
            return False  # theirs again: a repeat after the Reclaim took effect
        if row["occupant_kind"] == OccupantKind.STUDENT or not history["taken_over"]:
            raise CommandError("seat_not_yours", "no Takeover holds the Seat", 409)
        if not await repo.queue_reclaim(session, game_uuid, row["id"], actor_id):
            return False
        await _commit_change(session, game_uuid)
        await events.emit(session, "user", str(actor_id))
    log.info("reclaim_requested", game_id=game_id, seat_id=str(row["id"]))
    return True


GAME_PAUSED = "game.paused"
"""The audit action of a Pause a person set (Story 8.6, FR-89, AD-15)."""
GAME_PAUSE_TIME_SET = "game.pause_time_set"
"""The audit action of a Lecturer's change of the agreed Pause time (Story 8.7, AD-15)."""
GAME_RESUMED = "game.resumed"
"""The audit action of a Lecturer's «Avslutt pausen» (Story 8.7, AD-15)."""


async def pause(
    game_id: str,
    *,
    actor: uuid.UUID | str,
    staff: bool = False,
    resume_at: datetime | None = None,
    latest: Latest = None,
) -> str:
    """«Ta pause» (Story 8.6, FR-89, AD-2): the Student `actor` pauses the Class game their group
    plays; with `staff` (Story 8.7) the Lecturer `actor` of its Class pauses it, the route having
    checked the Lecturer through `platform/authz`, optionally with the agreed time `resume_at`.
    While it is paused no automatic Takeover runs (`rules.can_take_over`), and the stored due times
    keep running unmoved; any Student's Order ends it (`place_order`). A Student never gives a time.

    One transaction under the Game row lock: `paused_at` (the transaction's clock), `paused_by`
    and `resume_at` are written, and `lifecycle` is unchanged; an audit row `game.paused`. The
    open Week's insert times are recomputed with an agreed time (`_recompute_insert_times`). The
    version rises once with `game:<id>` and `session:<id>`, and every Student holding a Seat gets
    `user:<id>` (AD-8). Refuses `game_not_found` (404) and 409 `pause_not_allowed` (the Game's
    policy has no Pause), `game_not_running` (not started), `game_finished`, `seat_not_yours` (a
    Student actor holds no Seat of the Game now as a Student), 422 `time_out_of_range` (an agreed
    time not after now or after the Play deadline `latest`, `PROPOSAL_HORIZON` ahead without one)
    and 409 `already_paused` with `fields.acted_by` (`kind` `student` or `staff`, and `user_id`)
    and `fields.acted_at`: who paused first, by id only (Story 8.5's shape). Returns `paused_at`
    in ISO form."""
    game_uuid = _game_uuid(game_id)
    actor_id = _actor(actor)
    if not staff and resume_at is not None:
        raise ValueError("a Student never sets an agreed time")
    _check_aware(resume_at)
    async with get_sessionmaker().begin() as session:
        deadline = await latest(session) if callable(latest) else latest
        game = await _pausable_game(session, game_uuid, game_id)
        seated = seated_students(await repo.seats_with_occupant(session, game_uuid))
        if actor_id is None or (not staff and actor_id not in seated):
            raise CommandError("seat_not_yours", "the actor holds no Seat of the Game", 409)
        if rules.is_paused(game):
            raise CommandError(
                "already_paused", "the Game is paused already", 409, _paused_by(game, seated)
            )
        if resume_at is not None:
            await _check_agreed_time(session, resume_at, deadline)
        paused_at = await repo.set_pause(session, game_uuid, actor_id, resume_at)
        # Only an agreed time changes an insert time: a Pause without one leaves them as they are,
        # so an agreed time kept after an earlier Pause ended stays for this Week.
        if resume_at is not None:
            await _recompute_insert_times(session, game, resume_at)
        await audit.record(
            session,
            actor_id,
            GAME_PAUSED,
            {"game_id": game_uuid},
            {
                "paused_at": paused_at.isoformat(),
                "resume_at": None if resume_at is None else resume_at.isoformat(),
            },
            paused_at,
        )
        await _commit_change(session, game_uuid)
        for student in sorted(seated, key=str):
            await events.emit(session, "user", str(student))
    log.info("game_paused", game_id=game_id, staff=staff, agreed_time=resume_at is not None)
    return str(paused_at.isoformat())


async def set_agreed_time(
    game_id: str, resume_at: datetime | None, *, actor: uuid.UUID | str, latest: Latest = None
) -> bool:
    """«Endre avtalt tid» (Story 8.7, FR-89, AD-2): the Lecturer `actor` sets, changes or (None)
    clears the agreed time of the Pause in force, also of one a Student set; `paused_by` stays.
    The route has checked the Lecturer through `platform/authz`.

    One transaction under the Game row lock: `resume_at` is written, the sweep's mark that it has
    passed is cleared, the open Week's insert times are recomputed (`_recompute_insert_times`),
    and an audit row `game.pause_time_set`. The version rises once with `game:<id>`,
    `session:<id>` and `user:<id>` for every seated Student (AD-8). Refuses `game_not_found` (404)
    and 409 `pause_not_allowed`, `game_not_running`, `game_finished`, `not_paused`, and 422
    `time_out_of_range` as `pause`. Returns False, writing nothing, when the time is the one in
    force."""
    game_uuid = _game_uuid(game_id)
    actor_id = _actor(actor)
    if actor_id is None:
        raise ValueError("an agreed time names its Lecturer")
    _check_aware(resume_at)
    async with get_sessionmaker().begin() as session:
        deadline = await latest(session) if callable(latest) else latest
        game = await _pausable_game(session, game_uuid, game_id)
        if not rules.is_paused(game):
            raise CommandError("not_paused", "the Game is not paused", 409)
        if resume_at == game["resume_at"]:
            return False
        if resume_at is not None:
            await _check_agreed_time(session, resume_at, deadline)
        await repo.set_agreed_time(session, game_uuid, resume_at)
        await _recompute_insert_times(session, game, resume_at)
        at = await repo.clock_now(session)
        await audit.record(
            session,
            actor_id,
            GAME_PAUSE_TIME_SET,
            {"game_id": game_uuid},
            {
                "resume_at": None if resume_at is None else resume_at.isoformat(),
                "was": None if game["resume_at"] is None else game["resume_at"].isoformat(),
            },
            at,
        )
        await _commit_change(session, game_uuid)
        seated = seated_students(await repo.seats_with_occupant(session, game_uuid))
        for student in sorted(seated, key=str):
            await events.emit(session, "user", str(student))
    log.info("pause_time_set", game_id=game_id, agreed_time=resume_at is not None)
    return True


async def resume(game_id: str, *, actor: uuid.UUID | str) -> bool:
    """«Avslutt pausen» (Story 8.7, FR-89, AD-2): the Lecturer `actor` ends the Pause in force,
    whoever set it. The route has checked the Lecturer through `platform/authz`.

    One transaction under the Game row lock: the Pause columns and the agreed time are cleared,
    and `pause_ended_at`/`pause_ended_by` name the Lecturer, so every Student reads that the
    Pause is over until the next Week opens. The open Week's insert times are recomputed without
    the agreed time, but an insert time already passed stays: the right to put in an AI player
    survives the end (EXPERIENCE.md → Pausevalg → End). Due times were never moved, so a Seat past
    its due time is taken at the next sweep. An audit row `game.resumed`; the version rises once
    with `game:<id>`, `session:<id>` and `user:<id>` for every seated Student (AD-8). Refuses
    `game_not_found` (404) and 409 `pause_not_allowed`, `game_not_running`, `game_finished` and
    `not_paused`. Returns True."""
    game_uuid = _game_uuid(game_id)
    actor_id = _actor(actor)
    if actor_id is None:
        raise ValueError("an end of a Pause names its Lecturer")
    async with get_sessionmaker().begin() as session:
        game = await _pausable_game(session, game_uuid, game_id)
        if not rules.is_paused(game):
            raise CommandError("not_paused", "the Game is not paused", 409)
        await repo.end_pause(session, game_uuid, actor_id)
        await _recompute_insert_times(session, game, None, keep_passed=True)
        at = await repo.clock_now(session)
        await audit.record(
            session,
            actor_id,
            GAME_RESUMED,
            {"game_id": game_uuid},
            {
                "paused_at": game["paused_at"].isoformat(),
                "resume_at": None if game["resume_at"] is None else game["resume_at"].isoformat(),
            },
            at,
        )
        await _commit_change(session, game_uuid)
        seated = seated_students(await repo.seats_with_occupant(session, game_uuid))
        for student in sorted(seated, key=str):
            await events.emit(session, "user", str(student))
    log.info("game_resumed", game_id=game_id)
    return True


async def reach_agreed_time(game_id: str, *, now: datetime) -> bool:
    """The sweep crossed the agreed time of a paused Game (Story 8.7, FR-89, AD-8, AD-9): the Pause
    goes on and no AI player takes a Seat, but the right to put one in may now show, so the Game
    is marked once (`agreed_time_reached_at`) and its version rises with `game:<id>`,
    `session:<id>` and `user:<id>` for every seated Student; every open view reads it again.
    `now` is the sweep's clock. One transaction under the Game row lock; idempotent: False,
    writing nothing, when the Game no longer runs or is not paused, has no agreed time, has not
    reached it at `now` or was marked already. Refuses `game_not_found` (404)."""
    game_uuid = _game_uuid(game_id)
    async with get_sessionmaker().begin() as session:
        game = await repo.lock_game(session, game_uuid)
        if game is None:
            raise CommandError("game_not_found", f"no Game {game_id!r}", 404)
        if (
            game["lifecycle"] != Lifecycle.RUNNING
            or not rules.is_paused(game)
            or game["resume_at"] is None
            or game["resume_at"] > now
            or game["agreed_time_reached_at"] is not None
        ):
            return False
        await repo.mark_agreed_time_reached(session, game_uuid, now)
        await _commit_change(session, game_uuid)
        seated = seated_students(await repo.seats_with_occupant(session, game_uuid))
        for student in sorted(seated, key=str):
            await events.emit(session, "user", str(student))
    log.info("agreed_time_reached", game_id=game_id)
    return True


async def announce_insert_time(game_id: str, seat_id: str, *, now: datetime) -> bool:
    """The sweep crossed a Seat's insert time in the open Week (Story 8.8, FR-89, AD-8, AD-9): the
    other Students may now put an AI player in, so «Sett inn KI-spiller for …» must show without
    a reload. The turn is marked once (`insert_announced_at`); while the Game runs and a Student
    still holds the Seat without having ordered, the version rises with `game:<id>`,
    `session:<id>` and `user:<id>` for every seated Student. `now` is the sweep's clock. One
    transaction under the Game row lock; idempotent: False, writing nothing, when the turn is no
    longer in the open Week, has no insert time, has not reached it at `now` or was marked
    already; False with only the mark written when the Seat no longer waits. Refuses
    `game_not_found` (404)."""
    game_uuid = _game_uuid(game_id)
    seat_uuid = uuid.UUID(str(seat_id))
    async with get_sessionmaker().begin() as session:
        game = await repo.lock_game(session, game_uuid)
        if game is None:
            raise CommandError("game_not_found", f"no Game {game_id!r}", 404)
        week = await repo.open_week(session, game_uuid) if game["settings"] is not None else None
        if week is None:
            return False
        turns = await repo.week_turns_with_occupant(session, game_uuid, week)
        turn = next((t for t in turns if t["seat_id"] == seat_uuid), None)
        if (
            turn is None
            or turn["insert_allowed_at"] is None
            or turn["insert_allowed_at"] > now
            or turn["insert_announced_at"] is not None
        ):
            return False
        await repo.mark_insert_announced(session, turn["id"], now)
        guided = rules.guided_week(
            _policy(game["purpose"]), GameSettings.model_validate(game["settings"]), week
        )
        if (
            game["lifecycle"] != Lifecycle.RUNNING
            or turn["occupant_kind"] != OccupantKind.STUDENT
            or rules.has_ordered(turn, guided=guided)
        ):
            return False
        await _commit_change(session, game_uuid)
        seated = seated_students(await repo.seats_with_occupant(session, game_uuid))
        for student in sorted(seated, key=str):
            await events.emit(session, "user", str(student))
    log.info("insert_time_reached", game_id=game_id, seat_id=str(seat_uuid))
    return True


async def _pausable_game(
    session: AsyncSession, game_uuid: uuid.UUID, game_id: str
) -> Mapping[str, Any]:
    """The Game row under its lock, refused unless a Pause applies to it now: `game_not_found`
    (404), 409 `pause_not_allowed`, `game_finished` and `game_not_running`."""
    game = await repo.lock_game(session, game_uuid)
    if game is None:
        raise CommandError("game_not_found", f"no Game {game_id!r}", 404)
    if not _policy(game["purpose"]).pause:
        raise CommandError("pause_not_allowed", "Games of this purpose have no Pause", 409)
    if game["lifecycle"] == Lifecycle.FINISHED:
        raise CommandError("game_finished", "the Game has finished", 409)
    if game["lifecycle"] != Lifecycle.RUNNING:
        raise CommandError("game_not_running", "the Game is not running", 409)
    return game


def _check_aware(resume_at: datetime | None) -> None:
    if resume_at is not None and (not isinstance(resume_at, datetime) or resume_at.tzinfo is None):
        raise CommandError("time_out_of_range", "the time carries no time zone", 422)


async def _check_agreed_time(
    session: AsyncSession, resume_at: datetime, deadline: datetime | None
) -> None:
    """FR-89 (AD-10, AD-19): an agreed time lies after now on the database clock and not after
    the Play deadline; with none, not more than `PROPOSAL_HORIZON` ahead, as a proposed time."""
    now = await repo.clock_now(session)
    if deadline is None:
        deadline = now + PROPOSAL_HORIZON
    if not (now < resume_at <= deadline):
        raise CommandError(
            "time_out_of_range", "the time is not between now and the Play deadline", 422
        )


async def _recompute_insert_times(
    session: AsyncSession,
    game: Mapping[str, Any],
    agreed: datetime | None,
    *,
    keep_passed: bool = False,
) -> None:
    """Story 8.7 (FR-89, AD-20): the insert time of every turn of the open Week that a Student
    holds and that has not ordered, from `rules.turn_times` with its stored wait start as the
    clock start, the Inactivity limit the Game froze and the agreed time `agreed`. The Takeover
    due time is never moved. With `keep_passed` (the end of a Pause) an insert time at or before
    now stays: a right to put in an AI player that has arisen survives the end."""
    if game["settings"] is None:
        return
    week = await repo.open_week(session, game["id"])
    if week is None:
        return
    guided = rules.guided_week(
        _policy(game["purpose"]), GameSettings.model_validate(game["settings"]), week
    )
    now = await repo.clock_now(session)
    limit = _inactivity_limit(game)
    for turn in await repo.week_turns_with_occupant(session, game["id"], week):
        if turn["occupant_kind"] != OccupantKind.STUDENT or rules.has_ordered(turn, guided=guided):
            continue
        stored = turn["insert_allowed_at"]
        if keep_passed and stored is not None and stored <= now:
            continue
        times = rules.turn_times(
            rules.TurnGame(guided_week=guided),
            rules.TurnSeat(occupant_kind=OccupantKind.STUDENT, opened_at=turn["opened_at"]),
            rules.TurnInputs(
                clock_start=turn["wait_started_at"], inactivity_limit=limit, agreed_time=agreed
            ),
        )
        if times.insert_allowed_at != stored:
            await repo.set_insert_allowed(session, turn["id"], times.insert_allowed_at)


def _paused_by(game: Mapping[str, Any], seated: Collection[uuid.UUID]) -> dict[str, Any]:
    """`fields` of an `already_paused` refusal (Story 8.6, Story 8.5's shape): who set the Pause
    in force, a Student of the Game or (from Story 8.7) a staff member, by id, and when."""
    by = game["paused_by"]
    return {
        "acted_by": {
            "kind": "student" if by in seated else "staff",
            "user_id": None if by is None else str(by),
        },
        "acted_at": game["paused_at"].isoformat(),
    }


async def _takeover_occupant(
    session: AsyncSession, game: Mapping[str, Any], seat_id: uuid.UUID
) -> OccupantKind:
    """The AI player a Takeover puts in (FR-30, FR-69, FR-79): the Class session's AI mode, but
    Rule-based once the Play guard has switched the Seat or the budget is cost-limited."""
    runtime = SessionRuntime.model_validate(game["session_runtime"])
    if runtime.model_config_id is None:
        return OccupantKind.RULE_BASED
    if await repo.guard_switched(session, seat_id) or await _cost_limited(session, game):
        return OccupantKind.RULE_BASED
    return OccupantKind.LLM


async def _takeover_deadline(
    session: AsyncSession, game: Mapping[str, Any], turn: Mapping[str, Any]
) -> None:
    """An LLM player that took the Seat mid-Week is due its per-Order budget after now, so the
    rescue loop places the fallback Order if its job never does (AD-5, Issue #141)."""
    budget = await _ai_order_budget(session, game, [OccupantKind.LLM.value])
    if budget is None:
        return
    times = rules.turn_times(
        rules.TurnGame(guided_week=False),
        # The database clock at this statement, after the Game row lock was granted.
        rules.TurnSeat(
            OccupantKind.LLM, turn["opened_at"], occupied_since=await repo.clock_now(session)
        ),
        rules.TurnInputs(ai_order_budget_s=budget),
    )
    await repo.set_ai_deadline(session, turn["id"], times.ai_deadline_at)


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
    await _record_class_game_step(session, game_id)
    log.info("game_finished", game_id=str(game_id))


async def _record_class_game_step(session: AsyncSession, game_id: uuid.UUID) -> None:
    """Record `progress` `class_game` for every Student the Game ever seated, read from the
    occupancy history, so one whose Seat an AI player took over counts too (Story 6.18, AD-16),
    where `games.policy` says the purpose records it. Whether the step counts toward Completion
    is `analysis.completion`'s to decide. Each new step emits `user:<id>` and `session:<id>` in
    this transaction."""
    game = await repo.get_game(session, game_id)
    if game is None or game["class_session_id"] is None:
        return
    if not _policy(game["purpose"]).records_class_game_step:
        return
    named = {
        row["user_id"]
        for row in await repo.occupancy_history(session, game_id)
        if row["occupant_kind"] == OccupantKind.STUDENT and row["user_id"] is not None
    }
    # A Student moved to another Game of the Class session before the start was named here once;
    # their Class game is the one `student_game` gives, so only this Game's own Students count.
    students = []
    for user_id in sorted(named, key=str):
        own = await student_game(session, user_id, game["class_session_id"])
        if own is not None and own.game_id == game_id:
            students.append(user_id)
    at = await repo.now(session)
    for student in students:
        await progress.record_step(
            student, game["class_session_id"], progress.Step.CLASS_GAME, at, within=session
        )


TIME_PROPOSED_NOTICE = "time_proposed"

PROPOSAL_HORIZON = timedelta(days=90)
"""How far ahead a proposed time to play may lie when the Class session has no Play deadline
(follow-up review of Epic 6): about one teaching term."""

Latest = datetime | Callable[[AsyncSession], Awaitable[datetime | None]] | None
"""The Play deadline a proposal may not pass: a time, none, or a read of it in the command's
transaction, before the Game row lock (the caller's lock order: Class session, then Game)."""
"""The notice kind each other Student of a Class game gets when a time to play is proposed,
`digest` (Story 6.19, AD-9). Its `ref` is the proposal; the mail reads it at send time."""


async def _scheduling_game(
    session: AsyncSession, game_uuid: uuid.UUID, game_id: str, actor_id: uuid.UUID | None
) -> set[uuid.UUID]:
    """Lock a Game for the scheduling aid and return its seated Students. Refuses
    `game_not_found`, `game_finished`, and `seat_not_yours` for an actor who holds no Seat."""
    game = await repo.lock_game(session, game_uuid)
    if game is None:
        raise CommandError("game_not_found", f"no Game {game_id!r}", 404)
    if game["lifecycle"] == Lifecycle.FINISHED:
        raise CommandError("game_finished", "the Game has finished", 409)
    students = set(seated_students(await repo.seats_with_occupant(session, game_uuid)))
    if actor_id is None or actor_id not in students:
        raise CommandError("seat_not_yours", "the actor holds no Seat in the Game", 409)
    return students


async def propose_time(
    game_id: str, at: datetime, *, actor: uuid.UUID | str, latest: Latest
) -> str:
    """A Student proposes a time to play (Story 6.19, FR-22, AD-2): a date and a time, never
    text. The time must lie after now on the database clock and, when the caller gives the Play
    deadline as `latest`, not after it; with no Play deadline, not more than `PROPOSAL_HORIZON`
    ahead (`time_out_of_range`). A callable `latest` is read in the transaction, so the deadline
    holds while the proposal is stored. The Game keeps one open proposal: this
    one replaces the earlier proposal and its acceptances.

    One transaction with the Game row lock and a version bump, emitting `game:<id>`,
    `session:<id>` where the Lecturer overview lists the Game, and, through one `time_proposed`
    notice per other seated Student (dedupe key per proposal), `user:<id>` for each (AD-8, AD-9).
    The proposal is no input of `rules.turn_times` (AD-20). Refuses `game_not_found`,
    `game_finished`, `seat_not_yours` and `time_out_of_range`. Returns the proposal's id."""
    game_uuid = _game_uuid(game_id)
    actor_id = _actor(actor)
    if not isinstance(at, datetime) or at.tzinfo is None:
        raise CommandError("time_out_of_range", "the time carries no time zone", 422)
    async with get_sessionmaker().begin() as session:
        deadline = await latest(session) if callable(latest) else latest
        students = await _scheduling_game(session, game_uuid, game_id, actor_id)
        assert actor_id is not None  # `_scheduling_game` refuses a missing actor
        now = await repo.clock_now(session)
        if deadline is None:
            deadline = now + PROPOSAL_HORIZON
        if not (now < at <= deadline):
            raise CommandError(
                "time_out_of_range", "the time is not between now and the Play deadline", 422
            )
        proposal_id = uuid.uuid7()
        await repo.replace_time_proposal(session, game_uuid, proposal_id, actor_id, at)
        await _commit_change(session, game_uuid)
        # The proposer's own other pages read it too; the others hear of it through the notice.
        await events.emit(session, "user", str(actor_id))
        for other in sorted(students - {actor_id}, key=str):
            await notify.enqueue(
                session,
                other,
                TIME_PROPOSED_NOTICE,
                f"{TIME_PROPOSED_NOTICE}:{proposal_id}:{other}",
                ref=proposal_id,
            )
    log.info("time_proposed", game_id=game_id, proposal_id=str(proposal_id))
    return str(proposal_id)


async def accept_time(game_id: str, proposal_id: str, *, actor: uuid.UUID | str) -> bool:
    """A Student accepts the Game's open proposal of a time to play with one press (Story 6.19,
    FR-22, AD-2). One transaction with the Game row lock and a version bump, emitting
    `game:<id>`, `session:<id>` where the Lecturer overview lists the Game, and `user:<id>` for
    every seated Student, so all see who accepted (AD-8). An acceptance already stored changes
    nothing (no write, no version, no event) and returns False; True when it was stored.

    Refuses `game_not_found`, `game_finished`, `seat_not_yours`, `proposal_gone` (not the open
    proposal, which another replaced, or its time has passed) and `own_proposal`."""
    game_uuid = _game_uuid(game_id)
    actor_id = _actor(actor)
    proposal_uuid = _actor(proposal_id)
    async with get_sessionmaker().begin() as session:
        students = await _scheduling_game(session, game_uuid, game_id, actor_id)
        assert actor_id is not None
        proposal = await repo.time_proposal(session, game_uuid)
        if (
            proposal is None
            or proposal["id"] != proposal_uuid
            or proposal["at"] <= await repo.clock_now(session)
        ):
            raise CommandError("proposal_gone", "the proposal is not open any more", 409)
        if proposal["proposed_by"] == actor_id:
            raise CommandError("own_proposal", "the Student proposed this time", 409)
        if not await repo.accept_time_proposal(session, proposal["id"], actor_id):
            return False
        await _commit_change(session, game_uuid)
        for student in sorted(str(each) for each in students):
            await events.emit(session, "user", student)
    log.info("time_accepted", game_id=game_id, proposal_id=proposal_id)
    return True
