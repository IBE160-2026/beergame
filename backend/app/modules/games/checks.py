"""The finished-game check (AD-9, FR-29, NFR-9): replay a finished Game and check its books.

`verify_finished(game_id)` is idempotent and takes only a Game id, so the simulation runner
calls it after a Game ends and a job can call it later. It writes one immutable `game_checks`
row and nothing else: it never changes the Game, its version or its rows, and emits no event.
"""

import uuid
from collections.abc import Mapping, Sequence

import structlog
from pydantic import ValidationError
from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import GameSettings, Role, Violation, WeekState, demand_series, rules
from app.engine.check import conservation
from app.engine.replay import replay
from app.modules.games import repo
from app.modules.games.schemas import GameCheck, Lifecycle, SeatState
from app.modules.games.views import ViewError, build_seat_state, stored_orders
from app.platform.db import get_sessionmaker

__all__ = [
    "as_game_check",
    "finished_game_ids",
    "rules_versions_without_package",
    "verify_finished",
]

log = structlog.get_logger(__name__)

_SHAPE_RULES = frozenset(
    {"states_shape", "week_sequence", "seat_shape", "orders_shape", "demand_series"}
)


def as_game_check(row: Mapping[str, object]) -> GameCheck:
    return GameCheck(
        id=str(row["id"]),
        game_id=str(row["game_id"]),
        rules_version=row["rules_version"],
        ok=row["ok"],
        checked_at=row["checked_at"],
        violations=row["violations"],
    )


async def verify_finished(game_id: str) -> GameCheck:
    """Replay the finished Game at its stored `rules_version`, run the conservation check and
    the Decision log check, and store the result once. A second call returns the stored row.

    Refuses (`ViewError`, nothing stored): `game_not_found` 404, `game_not_finished` 409,
    `rules_version_unsupported` 409 when the stored version has no rules package."""
    try:
        game_uuid = uuid.UUID(game_id)
    except ValueError, TypeError, AttributeError:
        raise ViewError("game_not_found", f"no Game {game_id!r}", 404) from None
    async with get_sessionmaker().begin() as session:
        stored = await repo.game_check(session, game_uuid)
        if stored is not None:
            return as_game_check(stored)
        game = await repo.get_game(session, game_uuid)
        if game is None:
            raise ViewError("game_not_found", f"no Game {game_id!r}", 404)
        if game["lifecycle"] != Lifecycle.FINISHED:
            raise ViewError("game_not_finished", "only a finished Game is checked", 409)
        version = game["rules_version"]
        if not rules.has_version(version):
            raise ViewError(
                "rules_version_unsupported", f"no rules package for rules version {version}", 409
            )
        violations = await _violations(session, game_uuid, game, version)
        check_id = uuid.uuid7()
        row = await repo.insert_game_check(
            session,
            {
                "id": check_id,
                "game_id": game_uuid,
                "rules_version": version,
                "ok": not violations,
                "violations": [violation.model_dump(mode="json") for violation in violations],
            },
        )
        if row is None:  # another call stored the check first
            row = await repo.game_check(session, game_uuid)
            return as_game_check(row)  # type: ignore[arg-type]
    if violations:
        log.error(
            "game_check_failed",
            game_id=game_id,
            check_id=str(check_id),
            violation_count=len(violations),
        )
    else:
        log.info("game_check_passed", game_id=game_id, check_id=str(check_id))
    return as_game_check(row)


async def _violations(
    session: AsyncSession, game_id: uuid.UUID, game: RowMapping, version: int
) -> list[Violation]:
    try:
        settings = GameSettings.model_validate(game["settings"])
        series = list(demand_series(settings))
    except ValidationError, ValueError:
        return [_snapshot("the stored settings are not valid Game settings")]
    found: list[Violation] = []
    if series != game["demand_series"]:
        found.append(_snapshot("the stored demand series does not match its settings"))
    states, bad = _states(await repo.week_rows(session, game_id))
    if bad:
        return found + bad
    orders = await stored_orders(session, game_id)
    found.extend(replay(settings, states, orders, version))
    books = conservation(settings, states, orders)
    found.extend(books)
    if not any(violation.rule in _SHAPE_RULES for violation in books):
        log_rows = await repo.decision_log(session, game_id)
        found.extend(_decision_log(settings, states, orders, log_rows))
    return found


def _snapshot(message: str) -> Violation:
    return Violation(rule="snapshot", week=None, role=None, message=message)


def _states(rows: Sequence[RowMapping]) -> tuple[list[WeekState], list[Violation]]:
    states: list[WeekState] = []
    bad: list[Violation] = []
    for row in rows:
        try:
            state = WeekState.model_validate(row["state"])
        except ValidationError:
            state = None
        if state is None or (state.week, state.finished) != (row["week"], row["finished"]):
            bad.append(
                Violation(
                    rule="stored_state",
                    week=row["week"],
                    role=None,
                    message="the stored Week state is not the engine state of its row",
                )
            )
        else:
            states.append(state)
    return states, bad


def _decision_log(
    settings: GameSettings,
    states: Sequence[WeekState],
    orders: Sequence[Mapping[str, int]],
    rows: Sequence[RowMapping],
) -> list[Violation]:
    """Each Decision log row's `state_seen` must be the `SeatState` its Seat saw."""
    opened = [state for state in states if not state.finished]
    found: list[Violation] = []
    for row in rows:
        week, role = row["week"], Role(row["role"])
        try:
            seen = SeatState.model_validate(row["state_seen"])
            # Neighbour numbers depend on the flag at play time (Story 6.21): a state recorded
            # with them or without them is checked as it was recorded.
            expected = build_seat_state(
                settings,
                opened[:week],
                orders[: week - 1],
                role,
                neighbours=bool(seen.neighbour_numbers),
            )
        except ValidationError, ValueError, KeyError, IndexError:
            differs = ["state_seen"]
        else:
            differs = [
                name
                for name in SeatState.model_fields
                if getattr(seen, name) != getattr(expected, name)
            ]
        if differs:
            found.append(
                Violation(
                    rule="decision_log",
                    week=week,
                    role=role,
                    message=f"the Decision log row differs from what the Seat saw in "
                    f"{', '.join(differs)}",
                )
            )
    return found


async def finished_game_ids() -> tuple[str, ...]:
    """The id of every finished Game, oldest first: what `sim check --all` checks."""
    async with get_sessionmaker()() as session:
        ids = await repo.finished_game_ids(session)
    return tuple(str(game_id) for game_id in ids)


async def rules_versions_without_package() -> tuple[int, ...]:
    """Every `rules_version` stored on a Game that has no rules package (AD-4)."""
    async with get_sessionmaker()() as session:
        stored = await repo.stored_rules_versions(session)
    return tuple(version for version in stored if not rules.has_version(version))
