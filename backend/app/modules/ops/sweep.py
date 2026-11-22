"""The sweep's due actions (AD-9). Timers are data; this is the only thing that acts on them.

Each `DueAction` has a `find(now)` that reads what is due and an `act(item, now)` that the owning
module runs in one transaction per item, with ids only. A failing item is logged and the sweep
goes on; every action is idempotent, so the next minute's sweep repairs what this one missed.
Later epics append their due actions to `DUE_ACTIONS` (locks, Takeover, playout, reminders,
retention, …); there is no other cron.
"""

import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

import structlog

from app.modules.games import commands as games_commands
from app.modules.games import service as games
from app.modules.identity import service as identity
from app.modules.messaging import service as messaging
from app.modules.sessions import service as sessions
from app.platform import ratelimit
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

__all__ = ["DUE_ACTIONS", "Backoff", "DueAction", "run"]

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class DueAction:
    name: str
    find: Callable[[datetime], Awaitable[Sequence[object]]]
    act: Callable[[object, datetime], Awaitable[object]]


class Backoff(Exception):
    """An item that failed, was logged by its action and waits before it is tried again: the
    sweep neither counts nor logs it again."""


RATE_LIMIT_KEEP = timedelta(days=1)
"""Rate-limit windows older than this (and older than the login window) are purged."""


async def _stale_rate_limit_windows(now: datetime) -> Sequence[datetime]:
    window = timedelta(minutes=get_settings().login_rate_limit_window_minutes)
    return [now - max(RATE_LIMIT_KEEP, 2 * window)]


async def _purge_rate_limit_windows(cutoff: object, now: datetime) -> int:
    assert isinstance(cutoff, datetime)
    async with get_sessionmaker().begin() as session:
        return await ratelimit.purge_before(session, cutoff)


async def _roster_purge_due(now: datetime) -> Sequence[datetime]:
    return [now]


async def _purge_roster_uploads(at: object, now: datetime) -> int:
    assert isinstance(at, datetime)
    return await identity.purge_expired_roster_uploads(at)


FINISHED_CHECKS_PER_SWEEP = 20
"""The most finished Games one sweep verifies; the next minute's sweep takes the rest."""
FINISHED_CHECK_BACKOFF_MAX = timedelta(hours=1)
"""The longest wait before a failing finished-game check is tried again (2, 4, 8, … minutes)."""


@dataclass(frozen=True)
class _Failing:
    failures: int
    retry_at: datetime


_failing_checks: dict[str, _Failing] = {}
"""Finished Games whose check raised, in this process: they wait before the next try, so one
failing Game neither floods the log every minute nor takes a place from the others."""


async def _unchecked_finished_games(now: datetime) -> Sequence[str]:
    waiting = [uuid.UUID(g) for g, failing in _failing_checks.items() if failing.retry_at > now]
    async with get_sessionmaker()() as session:
        found = await games.unchecked_finished_game_ids(
            session, FINISHED_CHECKS_PER_SWEEP, exclude=waiting
        )
    return [str(game_id) for game_id in found]


async def _verify_finished(game_id: object, now: datetime) -> object:
    """Verify one finished Game. A check that raises is logged once, at warning level, the first
    time; it is then tried again after 2, 4, 8, … minutes, at most `FINISHED_CHECK_BACKOFF_MAX`
    (follow-up review of Story 6.18)."""
    assert isinstance(game_id, str)
    try:
        checked = await games.verify_finished(game_id)
    except Exception as exc:
        failing = _failing_checks.get(game_id)
        failures = 1 if failing is None else failing.failures + 1
        wait = min(FINISHED_CHECK_BACKOFF_MAX, timedelta(minutes=2 ** min(failures, 6)))
        _failing_checks[game_id] = _Failing(failures, now + wait)
        if failing is None:
            log.warning("finished_check_failing", game_id=game_id, exc_type=type(exc).__name__)
        raise Backoff from exc
    if _failing_checks.pop(game_id, None) is not None:
        log.info("finished_check_recovered", game_id=game_id)
    return checked


async def _due_takeovers(now: datetime) -> Sequence[tuple[str, str]]:
    return await games.due_takeovers(now)


TAKEOVER_RACES = frozenset(
    {
        "seat_not_student_held",
        "order_exists",
        "takeover_not_due",
        "game_not_running",
        "takeover_not_allowed",
        # A staff member put an AI player in first (Story 8.5).
        "takeover_exists",
        # A Student paused the game after the finder's read (Story 8.6).
        "game_paused",
        # The Play deadline playout took the Game over after the finder's read (Story 8.14).
        "play_deadline_passed",
    }
)
"""`rules.can_take_over`'s refusals: what changed between the finder's read and the lock."""


async def _take_over(item: object, now: datetime) -> bool:
    """Story 8.2 (FR-36, AD-9): hand one due Seat to an AI player in its own transaction. A
    refusal under the lock is the race the command settles (the Student ordered first, another
    sweep took it, the Week moved on): nothing to do and nothing to log as a failure, but the due
    time has passed, so the Game's events are emitted and open pages read it again (Story 8.3,
    AD-8). Any other refusal (a snapshot the engine cannot run, say) is raised, so the sweep logs
    it."""
    assert isinstance(item, tuple)
    game_id, seat_id = item
    try:
        await games_commands.takeover(game_id, seat_id, actor="system", now=now)
    except games_commands.CommandError as refused:
        if refused.code not in TAKEOVER_RACES:
            raise
        log.info("takeover_skipped", game_id=game_id, seat_id=seat_id, code=refused.code)
        await games.announce(game_id)
        return False
    return True


async def _due_agreed_times(now: datetime) -> Sequence[str]:
    return await games.due_agreed_times(now)


async def _reach_agreed_time(item: object, now: datetime) -> bool:
    """Story 8.7 (FR-89, AD-8, AD-9): the agreed time of one paused Game has passed. The Pause
    goes on and nothing is taken over; the command marks the Game once and emits its events, so
    every view reads it again. A Game whose Pause ended or whose time changed meanwhile is
    skipped by the command itself."""
    assert isinstance(item, str)
    return await games_commands.reach_agreed_time(item, now=now)


async def _due_in_room_ends(now: datetime) -> Sequence[str]:
    return await games.due_in_room_ends(now)


async def _end_in_room(item: object, now: datetime) -> bool:
    """Story 8.11 (FR-36, AD-9): the Lab hour of one Game marked «I rommet» has ended. The command
    clears the mark and puts the due times back on the Inactivity limit; a mark ended or moved
    meanwhile is skipped by the command itself."""
    assert isinstance(item, str)
    return await games_commands.end_in_room(item, actor=None, now=now)


async def _due_insert_times(now: datetime) -> Sequence[tuple[str, str]]:
    return await games.due_insert_times(now)


async def _announce_insert_time(item: object, now: datetime) -> bool:
    """Story 8.8 (FR-89, AD-8, AD-9): one Seat's insert time has passed. The command marks the
    turn once and, while the Seat still waits, emits the Game's events, so «Sett inn KI-spiller
    for …» shows on every open view without a reload. It never takes the Seat."""
    assert isinstance(item, tuple)
    game_id, seat_id = item
    return await games_commands.announce_insert_time(game_id, seat_id, now=now)


async def _due_turn_reminders(now: datetime) -> Sequence[tuple[str, str]]:
    return await games.due_turn_reminders(now)


async def _queue_turn_reminder(item: object, now: datetime) -> bool:
    """Story 8.13 (FR-27, AD-9): one Seat's reminder time has passed. While the game still waits
    for it, the command queues one `turn_reminder` digest notice for its Student; the next
    minute's digest claim gathers it. A paused Game is not found; a Seat no longer waited for is
    marked quietly by the command itself."""
    assert isinstance(item, tuple)
    game_id, seat_id = item
    return await games_commands.queue_turn_reminder(game_id, seat_id, now=now)


async def _stalled_playout_turns(now: object) -> Sequence[tuple[str, str]]:
    return await games.stalled_playout_turns()


async def _ensure_playout_order(item: object, now: datetime) -> bool:
    """Story 8.14 (AD-5, AD-9): a turn of a Game playing out has no Order and no live job: its
    LLM job was lost, so the Seat gets its Order again on `llm-batch`."""
    assert isinstance(item, tuple)
    game_id, seat_id = item
    return await games_commands.ensure_playout_order(game_id, seat_id)


_overdue_logged: set[str] = set()
"""Games logged as playing out past the allowed time in this process: each is logged once."""


async def _overdue_playouts(now: datetime) -> Sequence[str]:
    allowed = timedelta(minutes=get_settings().playout_allowed_minutes)
    return [g for g in await games.overdue_playouts(now - allowed) if g not in _overdue_logged]


async def _log_overdue_playout(item: object, now: datetime) -> bool:
    """Story 8.14 (FR-38, NFR-3): a Game still playing out after `playout_allowed_minutes` (a
    placeholder, set after the prototype) is logged as an error with its id, once."""
    assert isinstance(item, str)
    _overdue_logged.add(item)
    log.error("playout_overdue", game_id=item)
    return True


DUE_ACTIONS: tuple[DueAction, ...] = (
    # The first due action (Story 3.5): claim due notices into mails and defer their `mail` jobs.
    DueAction("messaging.mail", messaging.due_items, messaging.claim),  # type: ignore[arg-type]
    DueAction("ratelimit.purge", _stale_rate_limit_windows, _purge_rate_limit_windows),
    # Story 5.11: lock each Class session whose Start date has passed (AD-4), and purge the
    # expired Roster staging rows on time rather than only when the next upload looks (AD-14).
    DueAction("sessions.lock", sessions.due_locks, sessions.lock_due),
    DueAction("identity.purge_expired_roster_uploads", _roster_purge_due, _purge_roster_uploads),
    # Story 5.13: give an AI player the Seat of a removed Student in a Class game that has not
    # started, and seat each Student who registered after the allocation was confirmed (FR-7,
    # FR-20). After `sessions.lock`, so games opened this minute count, and the removal first, so
    # a late registrant can take the Seat it frees in the same minute.
    DueAction(
        "sessions.replace_removed_student",
        sessions.removed_students,
        sessions.replace_removed_student_due,
    ),
    DueAction(
        "sessions.seat_late_registrant",
        sessions.late_registrants,
        sessions.seat_late_registrant_due,
    ),
    # Story 5.17: tell each Student who registered after Student choice was saved that they may
    # choose, with more empty Class games when the Seats run short (FR-21).
    DueAction(
        "sessions.offer_student_choice",
        sessions.student_choice_offers,
        sessions.offer_student_choice_due,
    ),
    # Story 6.18: the finished-game check (FR-29, NFR-9, AD-4): replay each finished Game that
    # has no `game_checks` row yet, one Game per transaction, so the end screen never waits.
    # Story 8.2: an AI player takes the Seat of a Student who has not ordered by the stored
    # `takeover_due_at` (FR-36, NFR-4), one Seat per transaction; within a minute of the due time,
    # so before the finished-game checks, whose replays may take a while.
    DueAction("games.takeover", _due_takeovers, _take_over),
    # Story 8.11: end each «I rommet» mark whose Lab hour has ended (FR-36); the due times go back
    # to the Inactivity limit. After the Takeover, so a Seat due under the in-room limit this
    # minute is still taken.
    DueAction("games.end_in_room", _due_in_room_ends, _end_in_room),
    # Story 8.7: announce once that a Lecturer's agreed Pause time has passed (FR-89).
    DueAction("games.reach_agreed_time", _due_agreed_times, _reach_agreed_time),
    # Story 8.8: announce once that a Seat's insert time has passed (FR-89); after the Takeover,
    # so a Seat taken over this minute is not announced as waiting.
    DueAction("games.announce_insert_time", _due_insert_times, _announce_insert_time),
    # Story 8.13: queue a turn reminder for each Seat the game has waited for since its reminder
    # time (FR-27); after the Takeover, so a Seat taken over this minute is not reminded.
    DueAction("games.queue_turn_reminder", _due_turn_reminders, _queue_turn_reminder),
    # Story 8.14: at the Play deadline every unfinished Class game (never started and paused ones
    # too) is played out by AI players, one Game per transaction (FR-38). After the Takeover and
    # the reminders, which then find nothing more in it, and before the finished-game checks, so a
    # Game played out by Rule-based players is checked in the same minute. A lost LLM job of a
    # Game playing out is deferred again, and one playing out too long is logged.
    DueAction("sessions.playout", sessions.due_playouts, sessions.playout_due),
    DueAction("games.playout_orders", _stalled_playout_turns, _ensure_playout_order),
    DueAction("games.playout_overdue", _overdue_playouts, _log_overdue_playout),
    DueAction("games.verify_finished", _unchecked_finished_games, _verify_finished),
    # Story 5.14: remind every Student of a Play, Debrief or Test deadline 24 hours ahead, once
    # per deadline time (FR-18). The reminders join the next minute's digest claim.
    DueAction(
        "sessions.send_deadline_reminder",
        sessions.due_deadline_reminders,
        sessions.send_deadline_reminder_due,
    ),
)


async def run(now: datetime) -> dict[str, int]:
    """One sweep at `now`; returns the number of items each action acted on."""
    done: dict[str, int] = {}
    for action in DUE_ACTIONS:
        done[action.name] = 0
        try:
            items = await action.find(now)
        except Exception as exc:  # the type only: an exception's text may hold personal data
            log.error("sweep_find_failed", action=action.name, exc_type=type(exc).__name__)
            continue
        for item in items:
            try:
                await action.act(item, now)
                done[action.name] += 1
            except Backoff:
                continue
            except Exception as exc:
                log.error("sweep_item_failed", action=action.name, exc_type=type(exc).__name__)
    return done
