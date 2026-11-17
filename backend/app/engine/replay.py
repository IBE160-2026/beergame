"""Replay a stored Game through the engine and compare (AD-4, FR-29): pure, never raises.

`replay(settings, states, orders, rules_version)` rebuilds the Game from `initial_state` with
the stored Orders at `rules_version` and compares each rebuilt state with the stored state at
the same place. Stored states are only compared, never fed back in, so a changed Week state
shows at its own Week and Role and a changed Order shows from the Week it reaches.

Rules (stable codes): `rules_version` (no package for the version) and `replay` (a stored
state differs from the rebuilt one, a state is missing or extra, Orders follow the finish, or
the engine refused the stored Orders).

"Never raises" rests on the rules-package contract (RULES_VERSIONS.md): a package refuses bad
input only with a `ValueError` (`InvalidOrdersError`, `GameFinishedError`), which becomes a
violation; anything else is a bug in that package and propagates.
"""

from collections.abc import Mapping, Sequence

from app.engine import rules, week
from app.engine.check import Violation
from app.engine.errors import UnknownRulesVersionError
from app.engine.settings import GameSettings, Role
from app.engine.state import SeatState, WeekState

_SEAT_FIELDS = tuple(name for name in SeatState.model_fields if name != "role")


def replay(
    settings: GameSettings,
    states: Sequence[WeekState],
    orders: Sequence[Mapping[str, object]],
    rules_version: int,
) -> tuple[Violation, ...]:
    """Every difference between `states` and the replay of `orders` at `rules_version`; `()`
    when they are equal."""
    try:
        rules.package(rules_version)
    except UnknownRulesVersionError:
        return (
            Violation(
                rule="rules_version",
                week=None,
                role=None,
                actual=repr(rules_version),
                message=f"no rules package for rules version {rules_version!r}",
            ),
        )
    found: list[Violation] = []
    rebuilt = _rebuild(settings, orders, rules_version, found)
    for index in range(max(len(states), len(rebuilt))):
        if index >= len(states):
            found.append(
                Violation(
                    rule="replay",
                    week=rebuilt[index].week,
                    role=None,
                    message=f"the replay reaches state {index}, which the Game did not store",
                )
            )
        elif index >= len(rebuilt):
            found.append(
                Violation(
                    rule="replay",
                    week=states[index].week,
                    role=None,
                    message=f"the Game stored state {index}, which the replay does not reach",
                )
            )
        else:
            found.extend(_compare(rebuilt[index], states[index]))
    return tuple(found)


def _rebuild(
    settings: GameSettings,
    orders: Sequence[Mapping[str, object]],
    rules_version: int,
    found: list[Violation],
) -> list[WeekState]:
    """The replayed states; stops at the first refusal, which it records in `found`."""
    rebuilt: list[WeekState] = []
    try:
        rebuilt.append(week.initial_state(settings, rules_version))
        for placed in orders:
            if rebuilt[-1].finished:
                found.append(
                    Violation(
                        rule="replay",
                        week=rebuilt[-1].week,
                        role=None,
                        message="the Game stored Orders after it finished",
                    )
                )
                break
            rebuilt.append(week.advance(settings, rebuilt[-1], placed, rules_version))
    except ValueError as error:
        found.append(
            Violation(
                rule="replay",
                week=len(rebuilt) or None,
                role=_role(getattr(error, "role", None)),
                message=f"the engine refused the stored Game: {error}",
            )
        )
    return rebuilt


def _role(value: object) -> Role | None:
    try:
        return Role(value)
    except ValueError:
        return None


def _compare(expected: WeekState, actual: WeekState) -> list[Violation]:
    if (expected.week, expected.finished) != (actual.week, actual.finished):
        return [
            Violation(
                rule="replay",
                week=actual.week,
                role=None,
                expected=f"week {expected.week} finished {expected.finished}",
                actual=f"week {actual.week} finished {actual.finished}",
                message="the stored state is not the Week the replay reaches here",
            )
        ]
    if len(expected.seats) != len(actual.seats):
        return [
            Violation(
                rule="replay",
                week=actual.week,
                role=None,
                expected=str(len(expected.seats)),
                actual=str(len(actual.seats)),
                message="the stored state has another number of Seats",
            )
        ]
    found = []
    for want, have in zip(expected.seats, actual.seats, strict=True):
        names = [name for name in _SEAT_FIELDS if getattr(want, name) != getattr(have, name)]
        if want.role != have.role:
            names.insert(0, "role")
        if names:
            found.append(
                Violation(
                    rule="replay",
                    week=actual.week,
                    role=want.role,
                    expected=", ".join(f"{name}={getattr(want, name)}" for name in names),
                    actual=", ".join(f"{name}={getattr(have, name)}" for name in names),
                    message=f"the stored state differs from the replay in {', '.join(names)}",
                )
            )
    return found
