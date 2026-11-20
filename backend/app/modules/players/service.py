"""The one order source for every Seat that no Student holds (AD-5, FR-30), and for every Seat
in a Guided Week (Story 6.10).

`games.commands` calls `ensure_order` when a Week opens and right after a switch, inside its own
transaction. Guided, Rule-based and scripted Orders are placed there and then, through
`games.commands.place_order(..., within=game)`, so they share that command's lock, version
increment and event. An `llm` occupant's Order outside a Guided Week comes from one `ai-orders`
job (`players.jobs`), deferred on the same transaction. `players` reaches game state only
through `games.service` and `games.commands`.

This module loads no LLM library: it defers the job by its task name.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import structlog

from app.engine.scripted import REGISTRY
from app.modules.games import commands as games_commands
from app.modules.games import service as games_service
from app.platform import jobs

__all__ = [
    "DESCRIBED_KINDS",
    "PLACE_LLM_ORDER",
    "Description",
    "apply_cost_limit",
    "describe",
    "ensure_order",
    "llm_order_key",
]

PLACE_LLM_ORDER = "players.place_llm_order"
"""The `ai-orders` task that places an LLM player's Order (`players.jobs`)."""


def llm_order_key(game_id: str, week: int, seat_id: str) -> str:
    """The natural key of one LLM Order's job: `(game, week, seat)` (AD-5)."""
    return f"{jobs.AI_ORDERS}:{game_id}:{week}:{seat_id}"


log = structlog.get_logger(__name__)


def _order(turn: games_service.PendingTurn) -> tuple[int, games_service.DecidedBy] | None:
    """The Order of the turn and who decided it, or None when this source places none."""
    kind = turn.occupant_kind
    if turn.guided:
        # Every Seat, a Student's too, orders the Guided Order when the Week opens (Story 6.10).
        return turn.guided_order, games_service.DecidedBy.GUIDED
    if kind is games_service.OccupantKind.STUDENT:
        return None
    if kind is games_service.OccupantKind.RULE_BASED:
        return turn.rule_based_reference_order, games_service.DecidedBy.RULE_BASED
    if kind is games_service.OccupantKind.SCRIPTED:
        policy = REGISTRY.get(turn.policy_id or "")
        if policy is None:
            raise games_commands.CommandError(
                "occupant_not_playable", f"no scripted policy {turn.policy_id!r}", 422
            )
        return policy(turn.seat_state), games_service.DecidedBy.SCRIPTED
    return None  # `llm`: an `ai-orders` job (`ensure_order`)


async def ensure_order(game: games_service.OpenGame, seat: str) -> None:
    """Make sure the Seat with id `seat` gets its Order for the open Week.

    In a Guided Week every occupant, a Student too (Story 6.10), orders the Guided Order, so no
    model is asked (FR-31); a Student's Week then waits for their view (`view_week`). Outside it
    a `rule_based` occupant orders the reference Order stored on its turn (never recomputed), a
    `scripted` occupant the Order of the policy on its occupancy row, and an `llm` occupant gets
    one `ai-orders` job keyed `(game, week, seat)`, deferred on the command's connection so it
    commits with the Week or not at all (AD-5, AD-9). Does nothing for a Student outside a
    Guided Week, when the Game is not running, or when the Seat has already ordered, so it is
    safe to call again."""
    turn = await games_service.pending_turn(game, seat)
    if turn is None or turn.ordered:
        return
    decided = _order(turn)
    if decided is None:
        if turn.occupant_kind is games_service.OccupantKind.LLM:
            deferred = await jobs.defer(
                game.session,
                PLACE_LLM_ORDER,
                queue=jobs.AI_ORDERS,
                queueing_lock=llm_order_key(turn.game_id, turn.week, turn.seat_id),
                game_id=turn.game_id,
                seat_id=turn.seat_id,
                week=turn.week,
            )
            if deferred:
                log.debug("llm_order_deferred", game_id=turn.game_id, seat_id=turn.seat_id)
        return
    order, decided_by = decided
    await games_commands.place_order(
        turn.game_id, turn.seat_id, turn.week, order, decided_by, within=game
    )
    log.debug("order_ensured", game_id=turn.game_id, seat_id=turn.seat_id, week=turn.week)


SWITCH_ENDED = frozenset({"game_finished", "game_not_started", "game_not_found"})
"""Refusals of a switch that mean the Game no longer has a Seat to switch."""


async def apply_cost_limit(game_id: str) -> int:
    """Hand every `llm` Seat of every running Game charged to the same budget as `game_id` to
    the Rule-based player (`games.commands.switch_to_rule_based`, reason `cost_limit`), for the
    rest of each Game (FR-69, AD-5). Called once the budget's players' cost limit is reached;
    safe to call again: a Seat already switched has no `llm` occupant. Games that have not
    started get Rule-based players at `start`. Returns the number of Seats switched."""
    scope = await games_service.budget_scope(game_id)
    if scope is None:
        return 0
    switched = 0
    for charged in await games_service.games_charged_to(scope):
        game = await games_service.get_game(charged)
        if game is None:
            continue
        for seat in game.seats:
            if seat.occupant_kind != games_service.OccupantKind.LLM:
                continue
            try:
                await games_commands.switch_to_rule_based(
                    charged, seat.id, games_service.OccupancyReason.COST_LIMIT
                )
            except games_commands.CommandError as exc:
                if exc.code not in SWITCH_ENDED:
                    raise
                break
            switched += 1
    log.info("cost_limit_applied", game_id=game_id, scope_id=str(scope.id), seats_switched=switched)
    return switched


DESCRIPTIONS_DIR = Path(__file__).parent / "descriptions"
"""Plain-language Norwegian descriptions of the AI player types, at `v<N>/<kind>.md` (FR-33)."""

DESCRIBED_KINDS = (games_service.OccupantKind.RULE_BASED, games_service.OccupantKind.LLM)
"""The AI player types a Lecturer chooses between, in the order they are shown."""


@dataclass(frozen=True)
class Description:
    """One AI player type's description and the version of the text."""

    kind: games_service.OccupantKind
    version: int
    text: str


def _versions(kind: str) -> list[int]:
    if not DESCRIPTIONS_DIR.is_dir():
        return []
    return sorted(
        int(match.group(1))
        for folder in DESCRIPTIONS_DIR.iterdir()
        if (match := re.fullmatch(r"v([1-9][0-9]*)", folder.name))
        and (folder / f"{kind}.md").is_file()
    )


def describe(kind: str, version: int | None = None) -> Description:
    """The Norwegian bokmål description of how an AI player type decides (FR-33, FR-72).

    `kind` is `rule_based` or `llm` (an `OccupantKind` or its value); `version` defaults to the
    newest one with a file for the kind. Raises `ValueError` for any other kind or a version
    with no file. Texts are never changed once shipped: a new text is a new version."""
    try:
        occupant = games_service.OccupantKind(kind)
    except ValueError:
        raise ValueError(f"no description for occupant kind {kind!r}") from None
    if occupant not in DESCRIBED_KINDS:
        raise ValueError(f"no description for occupant kind {kind!r}")
    versions = _versions(occupant.value)
    if not versions:
        raise ValueError(f"no description file for {occupant.value}")
    chosen = versions[-1] if version is None else version
    if type(chosen) is not int or chosen not in versions:
        raise ValueError(f"no description version {version!r} for {occupant.value}")
    path = DESCRIPTIONS_DIR / f"v{chosen}" / f"{occupant.value}.md"
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return Description(kind=occupant, version=chosen, text=text)
