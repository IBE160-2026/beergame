"""Headless simulation runner (`python -m app.sim`, AD-22).

Subcommands:
  trace            play one Game in the pure engine and print one row per Week and Role.
  settings check   check a JSON file of GameSettings overrides; exit 0 when there
                   are only warnings, 1 on errors, 2 when the file is unreadable or not
                   a JSON object.

The runner computes no game quantities: every printed number is an engine field or the Order
it was given.
"""

import argparse
import json
import re
from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from app.engine import (
    RANGES,
    GameSettings,
    InvalidOrdersError,
    SettingsError,
    SettingsWarning,
    WeekState,
    advance,
    initial_state,
    validate,
    warnings,
)

type OrderPolicy = Callable[[WeekState], Mapping[str, int]]

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


def _pass_through(state: WeekState) -> Mapping[str, int]:
    return {seat.role: seat.incoming_order for seat in state.seats}


def _constant(order: int) -> OrderPolicy:
    def policy(state: WeekState) -> Mapping[str, int]:
        return {seat.role: order for seat in state.seats}

    return policy


def orders_spec(text: str) -> OrderPolicy:
    """`constant:N` (every Seat orders N every Week) or `pass-through` (own incoming order)."""
    if text == "pass-through":
        return _pass_through
    match = re.fullmatch(r"constant:([0-9]+)", text)
    if match is None:
        raise argparse.ArgumentTypeError(
            f"unknown Orders spec {text!r}: use constant:N or pass-through"
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
    policy: OrderPolicy = args.orders
    state = initial_state(settings)
    print(_format([name for name, _ in COLUMNS]))
    while not state.finished:
        orders = policy(state)
        try:
            following = advance(settings, state, orders)
        except InvalidOrdersError as exc:
            parser.error(f"--orders: {exc}")
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
    return 0


def _allowed(error: SettingsError) -> str:
    if error.minimum is None:
        return ""
    mark = " (placeholder)" if error.placeholder else ""
    return f" [allowed {error.minimum}..{error.maximum}{mark}]"


def _invalid(exc: ValidationError) -> list[SettingsError]:
    errors = []
    for error in exc.errors():
        field = ".".join(str(part) for part in error["loc"])
        allowed = RANGES.get(field)
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
        help="constant:N or pass-through (default)",
    )
    trace.set_defaults(handler=_trace, command_parser=trace)
    settings = commands.add_parser("settings", help="work with Game settings")
    settings_commands = settings.add_subparsers(dest="settings_command", required=True)
    check = settings_commands.add_parser(
        "check", help="check a JSON file of GameSettings overrides against ranges and warnings"
    )
    check.add_argument("file", help="JSON object of GameSettings overrides (missing = Classic)")
    check.set_defaults(handler=_settings_check, command_parser=check)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args, args.command_parser)


if __name__ == "__main__":
    raise SystemExit(main())
