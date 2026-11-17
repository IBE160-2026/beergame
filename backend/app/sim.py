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

The runner computes no game quantities: every printed number is an engine field or the Order
it was given.
"""

import argparse
import json
import re
import secrets
from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

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
from app.platform.parameter_sets import UnknownParameterSetError, read_parameter_set

DEMAND_PATTERN: TypeAdapter[DemandPattern] = TypeAdapter(DemandPattern)

type OrderPolicy = Callable[
    [GameSettings, Sequence[WeekState], Sequence[Mapping[str, int]]], Mapping[str, int]
]
"""Orders for the last opened Week of `states`, given the Order maps of the earlier Weeks."""

RULE_BASED = "rule_based"
DEFAULT_RULE_BASED_PARAMS = "placeholder-unverified"

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


def _format(values: Sequence[object]) -> str:
    cells = []
    for (name, width), value in zip(COLUMNS, values, strict=True):
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args, args.command_parser)


if __name__ == "__main__":
    raise SystemExit(main())
