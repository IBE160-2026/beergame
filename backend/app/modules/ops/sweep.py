"""The sweep's due actions (AD-9). Timers are data; this is the only thing that acts on them.

Each `DueAction` has a `find(now)` that reads what is due and an `act(item, now)` that the owning
module runs in one transaction per item, with ids only. A failing item is logged and the sweep
goes on; every action is idempotent, so the next minute's sweep repairs what this one missed.
Later epics append their due actions to `DUE_ACTIONS` (locks, Takeover, playout, reminders,
retention, …); there is no other cron.
"""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

import structlog

from app.modules.identity import service as identity
from app.modules.messaging import service as messaging
from app.modules.sessions import service as sessions
from app.platform import ratelimit
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

__all__ = ["DUE_ACTIONS", "DueAction", "run"]

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class DueAction:
    name: str
    find: Callable[[datetime], Awaitable[Sequence[object]]]
    act: Callable[[object, datetime], Awaitable[object]]


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
            except Exception as exc:
                log.error("sweep_item_failed", action=action.name, exc_type=type(exc).__name__)
    return done
