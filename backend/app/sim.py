"""Headless simulation runner (`python -m app.sim`, AD-22).

Subcommands:
  trace            play one Game in the pure engine and print one row per Week and Role.
                   `--orders rule_based` plays every Seat with the Rule-based player (Guided
                   Weeks order the starting demand) and warns when its parameter set is an
                   unverified placeholder.
  settings check   check a JSON file of GameSettings overrides; exit 0 when there
                   are only warnings, 1 on errors, 2 when the file is unreadable or not
                   a JSON object.
  demand           print the seed and the demand series of a Demand pattern (FR-13); a
                   seed is drawn from OS entropy when none is given, and the same seed
                   prints the same series. Exit 1 when the pattern or seed breaks a rule.
  create           store a simulation Game through `games.commands`, give every Seat its
                   occupant (`--seats rule_based`, `scripted:<id>`, or one per Role,
                   comma-separated) and print the Game id, seed and Seats read back from the
                   database. Exit 1 when a command refuses (its code is printed).
  start            start a stored Game through `games.commands.start` (free Seats get a
                   Rule-based player, Week 1 opens) and print its lifecycle, Week and Seats.
  show             print what one Seat sees in the open Week (`SeatState` as JSON), then the
                   open turn's `opened_at` and Rule-based reference Order.
  play             play a started Game to its end through `games.commands.place_order`: the
                   Guided Order in a Guided Week (`guided`), else the turn's stored Rule-based
                   reference Order (`rule_based`) or the Seat's scripted policy (`scripted`).
                   Prints the lifecycle and the number of Weeks played.
  log              print the Decision log: one row per Week and Seat with what the Seat saw,
                   its Order, the Week's cost, who decided and the Rule-based reference Order.

The runner computes no game quantities: every printed number is an engine field or the Order
it was given.
"""

import argparse
import asyncio
import json
import re
import secrets
import sys
from collections.abc import Callable, Coroutine, Mapping, Sequence
from decimal import Decimal
from pathlib import Path

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.exc import DBAPIError, OperationalError

from app.engine import (
    DEMAND_RANGES,
    RANGES,
    DemandPattern,
    GameSettings,
    InvalidOrdersError,
    SettingsError,
    SettingsWarning,
    WeekState,
    advance,
    guided_order,
    initial_state,
    rule_based,
    seat_view,
    validate,
    validate_demand,
    warnings,
)
from app.engine.demand import new_seed, series
from app.engine.scripted import REGISTRY
from app.modules.games import commands as game_commands
from app.modules.games import service as game_service
from app.platform import db
from app.platform.config import get_settings
from app.platform.logging import configure_logging
from app.platform.parameter_sets import UnknownParameterSetError, read_parameter_set

DEMAND_PATTERN: TypeAdapter[DemandPattern] = TypeAdapter(DemandPattern)

type OrderPolicy = Callable[
    [GameSettings, Sequence[WeekState], Sequence[Mapping[str, int]]], Mapping[str, int]
]
"""Orders for the last opened Week of `states`, given the Order maps of the earlier Weeks."""

RULE_BASED = "rule_based"
DEFAULT_RULE_BASED_PARAMS = rule_based.DEFAULT_SET_ID

SETTINGS: dict[str, Callable[[], GameSettings]] = {"classic": GameSettings}

COLUMNS = (
    ("week", 4),
    ("role", 11),
    ("incoming_order", 14),
    ("incoming_delivery", 17),
    ("shipped", 7),
    ("inventory", 9),
    ("backlog", 7),
    ("order", 5),
    ("cost", 8),
)


def _pass_through(
    settings: GameSettings, states: Sequence[WeekState], orders: Sequence[Mapping[str, int]]
) -> Mapping[str, int]:
    return {seat.role: seat.incoming_order for seat in states[-1].seats}


def _constant(order: int) -> OrderPolicy:
    def policy(
        settings: GameSettings, states: Sequence[WeekState], orders: Sequence[Mapping[str, int]]
    ) -> Mapping[str, int]:
        return {seat.role: order for seat in states[-1].seats}

    return policy


def rule_based_policy(params: rule_based.RuleBasedParams) -> OrderPolicy:
    """Every Seat played by the Rule-based player; Guided Weeks order the starting demand."""

    def policy(
        settings: GameSettings, states: Sequence[WeekState], orders: Sequence[Mapping[str, int]]
    ) -> Mapping[str, int]:
        if states[-1].week <= settings.guided_weeks:
            return {role: guided_order(settings) for role in settings.roles}
        return {
            role: rule_based.order(settings, seat_view(settings, states, orders, role), params)
            for role in settings.roles
        }

    return policy


def load_rule_based_params(set_id: str) -> rule_based.RuleBasedParams:
    """The Rule-based parameter set `set_id` from its configuration file."""
    return rule_based.parse_params(read_parameter_set(RULE_BASED, set_id), set_id)


def orders_spec(text: str) -> OrderPolicy | str:
    """`constant:N` (every Seat orders N every Week), `pass-through` (own incoming order) or
    `rule_based` (resolved with its parameter set once the options are parsed)."""
    if text == "pass-through":
        return _pass_through
    if text == RULE_BASED:
        return RULE_BASED
    match = re.fullmatch(r"constant:([0-9]+)", text)
    if match is None:
        raise argparse.ArgumentTypeError(
            f"unknown Orders spec {text!r}: use constant:N, pass-through or rule_based"
        )
    return _constant(int(match.group(1)))


def _format(values: Sequence[object], columns: Sequence[tuple[str, int]] = COLUMNS) -> str:
    cells = []
    for (name, width), value in zip(columns, values, strict=True):
        cell = str(value)
        cells.append(cell.ljust(width) if name == "role" else cell.rjust(width))
    return "  ".join(cells).rstrip()


def _trace(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    settings = SETTINGS[args.settings]()
    params: rule_based.RuleBasedParams | None = None
    if args.orders == RULE_BASED:
        try:
            params = load_rule_based_params(args.rule_based_params)
        except (UnknownParameterSetError, ValueError) as exc:
            parser.error(f"--rule-based-params: {exc}")
        policy: OrderPolicy = rule_based_policy(params)
    else:
        policy = args.orders
    state = initial_state(settings)
    states: list[WeekState] = []
    placed: list[Mapping[str, int]] = []
    print(_format([name for name, _ in COLUMNS]))
    while not state.finished:
        states.append(state)
        orders = policy(settings, states, placed)
        try:
            following = advance(settings, state, orders)
        except InvalidOrdersError as exc:
            parser.error(f"--orders: {exc}")
        placed.append(orders)
        for seat in state.seats:
            print(
                _format(
                    [
                        state.week,
                        seat.role.value,
                        seat.incoming_order,
                        seat.incoming_delivery,
                        seat.shipped,
                        seat.inventory,
                        seat.backlog,
                        orders[seat.role],
                        seat.cost,
                    ]
                )
            )
        state = following
    if params is not None and not params.verified:
        print(
            f"warning: Rule-based parameter set {params.id} v{params.version} is a placeholder "
            f"(unverified): {params.source}"
        )
    return 0


def _allowed(error: SettingsError) -> str:
    if error.minimum is None:
        return ""
    mark = " (placeholder)" if error.placeholder else ""
    return f" [allowed {error.minimum}..{error.maximum}{mark}]"


def _invalid(exc: ValidationError) -> list[SettingsError]:
    errors = []
    for error in exc.errors():
        loc = error["loc"]
        if loc[0] == "demand" and len(loc) > 2:
            # Drop the pattern kind pydantic puts in the path, and a fixed-series item index,
            # so the field matches what `validate` reports.
            loc = (loc[0], *loc[2:3])
        field = ".".join(str(part) for part in loc)
        demand_key = field.removeprefix("demand.") if field.startswith("demand") else None
        allowed = RANGES.get(field) or (DEMAND_RANGES.get(demand_key) if demand_key else None)
        errors.append(
            SettingsError(
                code="invalid",
                field=field,
                message=error["msg"],
                minimum=allowed.minimum if allowed else None,
                maximum=allowed.maximum if allowed else None,
                placeholder=allowed.placeholder if allowed else None,
            )
        )
    return errors


def _settings_check(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    try:
        text = Path(args.file).read_text(encoding="utf-8-sig")
    except OSError as exc:
        parser.error(f"cannot read {args.file}: {exc.strerror or exc}")
    except UnicodeDecodeError:
        parser.error(f"{args.file} is not UTF-8 text")
    try:
        overrides = json.loads(text, parse_float=Decimal)
    except ValueError as exc:
        parser.error(f"{args.file} is not JSON: {exc}")
    if not isinstance(overrides, dict):
        parser.error(f"{args.file} must hold a JSON object of GameSettings overrides")
    try:
        settings = GameSettings.model_validate(overrides)
    except ValidationError as exc:
        errors = _invalid(exc)
        found: tuple[SettingsWarning, ...] = ()
    else:
        errors = list(validate(settings))
        found = warnings(settings)
    for error in errors:
        print(f"error {error.code} {error.field}: {error.message}{_allowed(error)}")
    for warning in found:
        numbers = ", ".join(f"{key}={value}" for key, value in warning.values.items())
        print(f"warning {warning.code} {warning.field}: {warning.message} [{numbers}]")
    if not errors and not found:
        print("OK")
    return 1 if errors else 0


PATTERN_KINDS = ("fixed", "step", "random", "step+noise")


def _values_spec(text: str) -> list[int]:
    """Comma-separated whole numbers, e.g. `4,4,8`."""
    try:
        return [int(part) for part in text.split(",")]
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"{text!r} is not a comma-separated list of whole numbers"
        ) from None


def _pattern_data(args: argparse.Namespace) -> dict[str, object]:
    if args.pattern == "fixed":
        return {"kind": "fixed", "values": args.values}
    if args.pattern == "random":
        return {"kind": "random", "mean": args.mean, "spread": args.spread}
    data: dict[str, object] = {
        "kind": args.pattern,
        "start": args.start,
        "new_level": args.new_level,
        "change_week": args.change_week,
    }
    if args.pattern == "step+noise":
        data["spread"] = args.spread
    return data


def _demand(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.pattern == "fixed" and args.values is None:
        parser.error("--values is required for --pattern fixed")
    seed = args.seed if args.seed is not None else new_seed(secrets.token_bytes(16))
    try:
        pattern = DEMAND_PATTERN.validate_python(_pattern_data(args))
    except ValidationError as exc:
        details = "; ".join(f"{'.'.join(map(str, e['loc'][1:]))}: {e['msg']}" for e in exc.errors())
        parser.error(f"invalid Demand pattern: {details}")
    allowed = RANGES["weeks"]
    if not allowed.minimum <= args.weeks <= allowed.maximum:
        parser.error(f"--weeks must be from {allowed.minimum} to {allowed.maximum}")
    errors = validate_demand(pattern, args.weeks, seed)
    print(f"seed {seed}")
    if errors:
        for error in errors:
            print(f"error {error.code} {error.field}: {error.message}{_allowed(error)}")
        return 1
    print("series " + " ".join(str(value) for value in series(pattern, args.weeks, seed)))
    return 0


type Occupant = tuple[str, str | None]
"""An occupant kind and its policy id (scripted only)."""


def _seats_spec(text: str) -> list[Occupant]:
    """`rule_based` or `scripted:<id>`, once for every Seat or once per Role, comma-separated."""
    occupants: list[Occupant] = []
    for part in (piece.strip() for piece in text.split(",")):
        if part == RULE_BASED:
            occupants.append((RULE_BASED, None))
        elif part.startswith("scripted:") and part.removeprefix("scripted:") in REGISTRY:
            occupants.append(("scripted", part.removeprefix("scripted:")))
        else:
            raise argparse.ArgumentTypeError(
                f"unknown Seat spec {part!r}: use rule_based or scripted:<id> with id in "
                f"{', '.join(sorted(REGISTRY))}"
            )
    return occupants


def _run[T](coroutine: Coroutine[object, object, T]) -> T:
    # psycopg's async mode cannot run on Windows' default Proactor loop. A factory also keeps
    # asyncio.run from replacing the thread's current event loop.
    factory = asyncio.SelectorEventLoop if sys.platform == "win32" else asyncio.new_event_loop
    return asyncio.run(coroutine, loop_factory=factory)


def _report(exc: Exception) -> None:
    """Print a refused command or read, or a database failure, on stderr."""
    if isinstance(exc, (game_commands.CommandError, game_service.ViewError)):
        print(f"error {exc.code}: {exc.message}", file=sys.stderr)
        for field, code in getattr(exc, "fields", {}).items():
            print(f"error {code} {field}", file=sys.stderr)
    elif isinstance(exc, OperationalError):
        print("error db_unavailable: cannot reach the database", file=sys.stderr)
    else:
        print(f"error db_error: {type(getattr(exc, 'orig', exc)).__name__}", file=sys.stderr)


async def _create_game(
    settings: GameSettings, occupants: Sequence[Occupant], seed: int | None, params: str
) -> int:
    game_id: str | None = None
    try:
        game_id = await game_commands.create(
            "simulation", settings, seed=seed, rule_based_params=params
        )
        for role, (kind, policy_id) in zip(settings.roles, occupants, strict=True):
            await game_commands.assign_seat(game_id, role, kind, policy_id)
        game = await game_service.get_game(game_id)
        if game is None:
            raise game_commands.CommandError("game_not_found", f"no Game {game_id!r}", 404)
    except (game_commands.CommandError, DBAPIError) as exc:
        _report(exc)
        if game_id is not None:
            print(f"note: game {game_id} was stored with Seats still free", file=sys.stderr)
        return 1
    finally:
        await db.dispose()
    print(f"game {game.id}")
    print(f"seed {game.demand_seed}")
    print(f"lifecycle {game.lifecycle}")
    for seat in game.seats:
        print(" ".join(["seat", seat.role, str(seat.occupant_kind), seat.policy_id or ""]).rstrip())
    return 0


def _create(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    settings = SETTINGS[args.settings]()
    seats = args.seats
    if len(seats) == 1:
        seats = seats * len(settings.roles)
    elif len(seats) != len(settings.roles):
        parser.error(f"--seats needs one occupant or {len(settings.roles)}, not {len(seats)}")
    return _run(_create_game(settings, seats, args.seed, args.rule_based_params))


async def _start_game(game_id: str) -> int:
    try:
        week = await game_commands.start(game_id)
        game = await game_service.get_game(game_id)
        if game is None:
            raise game_commands.CommandError("game_not_found", f"no Game {game_id!r}", 404)
    except (game_commands.CommandError, DBAPIError) as exc:
        _report(exc)
        return 1
    finally:
        await db.dispose()
    print(f"game {game.id}")
    print(f"lifecycle {game.lifecycle}")
    print(f"week {week}")
    for seat in game.seats:
        print(" ".join(["seat", seat.role, str(seat.occupant_kind), seat.policy_id or ""]).rstrip())
    return 0


def _start(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    return _run(_start_game(args.game_id))


async def _show_seat(game_id: str, seat: str) -> int:
    try:
        state = await game_service.seat_state(game_id, seat)
        turn = await game_service.open_turn(game_id, seat, state.week)
    except (game_service.ViewError, DBAPIError) as exc:
        _report(exc)
        return 1
    finally:
        await db.dispose()
    print(state.model_dump_json(indent=2))
    print(f"opened_at {turn.opened_at.isoformat()}")
    print(f"reference_order {turn.rule_based_reference_order}")
    return 0


def _show(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    return _run(_show_seat(args.game_id, args.seat))


def _decide(
    game: game_service.GameOverview,
    seat: game_service.SeatOverview,
    state: game_service.SeatState,
    turn: game_service.TurnOverview,
) -> tuple[int, game_service.DecidedBy]:
    """The Order of one open turn and who decided it: the Guided Order in a Guided Week, else
    the stored Rule-based reference Order or the scripted policy on the Seat."""
    if turn.guided:
        return guided_order(game.settings), game_service.DecidedBy.GUIDED
    if seat.occupant_kind == game_service.OccupantKind.RULE_BASED:
        return turn.rule_based_reference_order, game_service.DecidedBy.RULE_BASED
    if seat.occupant_kind == game_service.OccupantKind.SCRIPTED and seat.policy_id in REGISTRY:
        return REGISTRY[seat.policy_id](state), game_service.DecidedBy.SCRIPTED
    raise game_commands.CommandError(
        "occupant_not_playable", f"the runner cannot play a {seat.occupant_kind} occupant", 422
    )


async def _play_game(game_id: str) -> int:
    try:
        game = await game_service.get_game(game_id)
        if game is None:
            raise game_commands.CommandError("game_not_found", f"no Game {game_id!r}", 404)
        if game.lifecycle == game_service.Lifecycle.FINISHED:
            raise game_commands.CommandError("game_finished", "the Game has finished", 409)
        week = 0
        while game.lifecycle != game_service.Lifecycle.FINISHED:
            for seat in game.seats:
                state = await game_service.seat_state(game_id, seat.id)
                turn = await game_service.open_turn(game_id, seat.id, state.week)
                week = state.week
                if turn.ordered_at is not None:
                    continue
                order, decided_by = _decide(game, seat, state, turn)
                await game_commands.place_order(game_id, seat.id, state.week, order, decided_by)
            # Read the Game again: its occupants and lifecycle may have changed meanwhile.
            game = await game_service.get_game(game_id)
            if game is None:
                raise game_commands.CommandError("game_not_found", f"no Game {game_id!r}", 404)
        lifecycle = game.lifecycle
    except (game_commands.CommandError, game_service.ViewError, DBAPIError) as exc:
        _report(exc)
        return 1
    finally:
        await db.dispose()
    print(f"game {game.id}")
    print(f"lifecycle {lifecycle}")
    print(f"weeks {week}")
    return 0


def _play(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    return _run(_play_game(args.game_id))


LOG_COLUMNS = (*COLUMNS, ("decided_by", 10), ("reference", 9))


async def _print_log(game_id: str) -> int:
    try:
        rows = await game_service.decision_log(game_id)
    except (game_service.ViewError, DBAPIError) as exc:
        _report(exc)
        return 1
    finally:
        await db.dispose()
    print(_format([name for name, _ in LOG_COLUMNS], LOG_COLUMNS))
    for row in rows:
        seen = row.state_seen
        print(
            _format(
                [
                    row.week,
                    row.role,
                    seen.incoming_order,
                    seen.incoming_delivery,
                    seen.shipped,
                    seen.inventory,
                    seen.backlog,
                    row.order,
                    seen.week_cost,
                    row.decided_by.value,
                    row.rule_based_reference_order,
                ],
                LOG_COLUMNS,
            )
        )
    return 0


def _log(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    return _run(_print_log(args.game_id))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.sim", description="Headless simulation runner."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    trace = commands.add_parser("trace", help="play one Game in the engine and print each Week")
    trace.add_argument("--settings", choices=sorted(SETTINGS), default="classic")
    trace.add_argument(
        "--orders",
        type=orders_spec,
        default="pass-through",
        metavar="SPEC",
        help="constant:N, pass-through (default) or rule_based",
    )
    trace.add_argument(
        "--rule-based-params",
        default=DEFAULT_RULE_BASED_PARAMS,
        metavar="ID",
        help=f"Rule-based parameter set id (default {DEFAULT_RULE_BASED_PARAMS})",
    )
    trace.set_defaults(handler=_trace, command_parser=trace)
    settings = commands.add_parser("settings", help="work with Game settings")
    settings_commands = settings.add_subparsers(dest="settings_command", required=True)
    check = settings_commands.add_parser(
        "check", help="check a JSON file of GameSettings overrides against ranges and warnings"
    )
    check.add_argument("file", help="JSON object of GameSettings overrides (missing = Classic)")
    check.set_defaults(handler=_settings_check, command_parser=check)
    demand = commands.add_parser(
        "demand", help="print the demand series of a Demand pattern and its seed"
    )
    demand.add_argument("--pattern", choices=PATTERN_KINDS, default="step")
    demand.add_argument("--weeks", type=int, default=36)
    demand.add_argument("--seed", type=int, help="seed to reuse (default: draw a new one)")
    demand.add_argument("--start", type=int, default=4, help="step: level before the change")
    demand.add_argument("--new-level", type=int, default=8, help="step: level from the change")
    demand.add_argument("--change-week", type=int, default=5, help="step: Week of the change")
    demand.add_argument("--mean", type=int, default=4, help="random: mean")
    demand.add_argument("--spread", type=int, default=2, help="random and step+noise: spread")
    demand.add_argument("--values", type=_values_spec, help="fixed: comma-separated series")
    demand.set_defaults(handler=_demand, command_parser=demand)
    create = commands.add_parser(
        "create", help="store a simulation Game with an occupant in every Seat"
    )
    create.add_argument("--settings", choices=sorted(SETTINGS), default="classic")
    create.add_argument(
        "--seats",
        type=_seats_spec,
        default=[(RULE_BASED, None)],
        metavar="SPEC",
        help="rule_based (default) or scripted:<id>, once or once per Role, comma-separated",
    )
    create.add_argument("--seed", type=int, help="demand seed (default: draw a new one)")
    create.add_argument(
        "--rule-based-params",
        default=DEFAULT_RULE_BASED_PARAMS,
        metavar="ID",
        help=f"Rule-based parameter set id (default {DEFAULT_RULE_BASED_PARAMS})",
    )
    create.set_defaults(handler=_create, command_parser=create)
    start = commands.add_parser("start", help="start a stored Game and open Week 1")
    start.add_argument("game_id")
    start.set_defaults(handler=_start, command_parser=start)
    show = commands.add_parser("show", help="print what one Seat sees in the open Week")
    show.add_argument("game_id")
    show.add_argument("--seat", required=True, metavar="SEAT", help="Role or Seat id")
    show.set_defaults(handler=_show, command_parser=show)
    play = commands.add_parser(
        "play", help="place every open turn's Order until the Game has finished"
    )
    play.add_argument("game_id")
    play.set_defaults(handler=_play, command_parser=play)
    log = commands.add_parser("log", help="print the Decision log, one row per Week and Seat")
    log.add_argument("game_id")
    log.set_defaults(handler=_log, command_parser=log)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args, args.command_parser)


if __name__ == "__main__":
    configure_logging(get_settings().log_level, stream=sys.stderr)  # stdout is the report
    raise SystemExit(main())
