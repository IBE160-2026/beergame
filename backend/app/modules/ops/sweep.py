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

from app.modules.debrief import service as debrief
from app.modules.games import commands as games_commands
from app.modules.games import service as games
from app.modules.identity import service as identity
from app.modules.messaging import service as messaging
from app.modules.sessions import service as sessions
from app.modules.tests import selection as _question_set  # noqa: F401  (registers its pin)
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


async def _close_at_test_deadline(game_id: object, now: datetime) -> bool:
    """Close one unfinished Game at its Test deadline (Story 10.6): `games.commands.close`, which
    judges the deadline again at `now` under the Game row lock and does nothing to a Game already
    finished, so a repeat or a late item is harmless."""
    assert isinstance(game_id, str)
    return await games_commands.close(game_id, games.EndReason.TEST_DEADLINE, due=now)


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
    DueAction("games.verify_finished", _unchecked_finished_games, _verify_finished),
    # Story 10.6 (FR-18, AD-13): close each unfinished Replay once its Student's Test deadline has
    # passed (`effective_test_deadline`), never played out; one Game per transaction.
    DueAction(
        "games.close_at_test_deadline", games.due_test_deadline_closes, _close_at_test_deadline
    ),
    # Story 12.1 (AD-9, FR-61): the Test-deadline lock pins the «KI-vurdering» switch of each
    # Class session whose original Test deadline has passed, once; Epic 11 adds the Scoring guide
    # pin to it and closes the attempts after it.
    DueAction("sessions.lock_test", sessions.due_test_locks, sessions.lock_test_due),
    # Story 9.2: release the Debriefs of a held Class session once its last Class game has
    # finished (by the last Week or the playout), and tell each seated Student (AD-9).
    DueAction("debrief.release", debrief.due_releases, debrief.release_due),
    # Story 9.12 (FR-43): a joined Student two minutes without a heartbeat drops out of their
    # Group debrief, and a Group debrief still on its shared steps 48 hours after the game ended
    # falls back to a Personal debrief for each Student who has not finished.
    DueAction("debrief.dropouts", debrief.due_dropouts, debrief.drop_out_due),
    DueAction("debrief.fallback", debrief.due_fallbacks, debrief.fallback_due),
    # Story 9.14 (AD-9): defer the narration job of a Seat again when it was lost (no narration
    # stored ten minutes after its Class game finished).
    DueAction("debrief.narration", debrief.due_narrations, debrief.narrate_due),
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
