"""Headless simulation runner (`python -m app.sim`, AD-22).

Subcommands:
  trace   play one Game in the pure engine and print one row per Week and Role.

The runner computes no game quantities: every printed number is an engine field or the Order
it was given.
"""

import argparse
import re
from collections.abc import Callable, Mapping, Sequence

from app.engine import GameSettings, InvalidOrdersError, WeekState, advance, initial_state

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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args, args.command_parser)


if __name__ == "__main__":
    raise SystemExit(main())
