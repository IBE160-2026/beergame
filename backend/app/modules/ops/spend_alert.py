"""The daily AI spend alert (Story 15.7, FR-69, AD-6, AD-9).

A due action of the sweep: once the AI spend of today (the Europe/Oslo calendar day) passes
`AI_DAILY_ALERT_USD`, the day's alert is recorded in `app/ai` and every active Admin gets one
`DAILY_SPEND_NOTICE` through `platform/notify.enqueue`, keyed by the day and the Admin, so each
Admin is told once a day however often the sweep runs. The sum comes from `ai.calls.day_spend`,
never from a sum here. With the amount not set, nothing is sent.

The kind is `immediate` in `messaging`'s delivery table (decided by this story: a runaway cost is
noticed the same day, also between 22:00 and 07:00); the mail names the day's dearest Class
sessions and links to «KI-kostnad» for that day.
"""

import uuid
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal

from app.ai import budget, calls
from app.modules.identity import service as identity
from app.modules.ops.ai_schemas import DailySpendOut, DaySessionSpendOut
from app.modules.sessions import service as sessions
from app.platform import notify
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

__all__ = [
    "DAILY_SPEND_NOTICE",
    "FutureDay",
    "alert_due",
    "daily_spend",
    "due_days",
    "notice_key",
]

DAILY_SPEND_NOTICE = "ai_daily_spend"
"""The notice kind of the daily spend alert, `immediate` (`messaging.delivery.KINDS`)."""


def notice_key(day: date, user_id: uuid.UUID) -> str:
    """One alert per Admin per day."""
    return f"{DAILY_SPEND_NOTICE}:{day.isoformat()}:{user_id}"


async def _untold(day: date) -> list[uuid.UUID]:
    async with get_sessionmaker()() as s:
        admins = await identity.active_admins(s)
        told = await notify.used_keys(s, [notice_key(day, admin) for admin in admins])
    return [admin for admin in admins if notice_key(day, admin) not in told]


async def due_days(now: datetime) -> Sequence[date]:
    """Today, when the alert amount is set, today's spend has passed it and an active Admin has
    not been told yet; else nothing."""
    amount = get_settings().ai_daily_alert_usd
    if amount is None:
        return []
    day = calls.oslo_date(now)
    spent = await calls.day_spend(day, top=0)
    if spent.total_usd <= amount or not await _untold(day):
        return []
    return [day]


async def alert_due(day: object, now: datetime) -> int:
    """Record `day`'s alert (the first record stands) and tell each active Admin not told yet,
    in one transaction. Returns how many notices were stored now."""
    assert isinstance(day, date)
    amount = get_settings().ai_daily_alert_usd
    if amount is None:
        return 0
    told = 0
    async with get_sessionmaker().begin() as s:
        spent = await calls.day_spend(day, top=0, session=s)
        if spent.total_usd <= amount:
            return 0
        alert = await budget.record_daily_alert(day, amount, spent.total_usd, now, session=s)
        for admin in sorted(await identity.active_admins(s)):
            key = notice_key(day, admin)
            if await notify.enqueue(s, admin, DAILY_SPEND_NOTICE, key, ref=alert.id):
                told += 1
    return told


DAY_SESSIONS = 10
"""The dearest Class sessions «KI-kostnad» lists for a day."""


class FutureDay(Exception):
    """A day after today in Europe/Oslo: nothing can have been spent yet."""


def _decimal(value: Decimal) -> str:
    """A USD amount as a decimal string with the column's eight places."""
    return format(value.quantize(Decimal("1e-8")), "f")


async def daily_spend(day: date | None, now: datetime) -> DailySpendOut:
    """The AI spend of `day` (today in Europe/Oslo when None) with its dearest Class sessions by
    name, the alert amount and whether the Admins were alerted, for «KI-kostnad». Read through
    `ai.calls.day_spend` and `ai.budget.daily_alert`; a day after today raises `FutureDay`."""
    today = calls.oslo_date(now)
    day = day or today
    if day > today:
        raise FutureDay(day)
    async with get_sessionmaker().begin() as s:
        spent = await calls.day_spend(day, top=DAY_SESSIONS, session=s)
        alert = await budget.daily_alert(day=day, session=s)
        ids = [line.class_session_id for line in spent.sessions]
        found = await sessions.evaluation_sessions(s, ids) if ids else []
    # An alerted day keeps the amount it was alerted at, also when the setting changed since.
    amount = alert.alert_usd if alert is not None else get_settings().ai_daily_alert_usd
    named = {item.id: item for item in found}
    lines = []
    for line in spent.sessions:
        item = named.get(line.class_session_id)
        lines.append(
            DaySessionSpendOut(
                class_session_id=line.class_session_id,
                label=(
                    f"{item.class_name} · Klasseøkt {item.number}"
                    if item
                    else str(line.class_session_id)
                ),
                institution_name=item.institution_name if item else None,
                usd=_decimal(line.usd),
                calls=line.calls,
            )
        )
    return DailySpendOut(
        day=day,
        today=today,
        total_usd=_decimal(spent.total_usd),
        calls=spent.calls,
        evaluation_usd=_decimal(spent.evaluation_usd),
        alert_usd=None if amount is None else _decimal(amount),
        passed=amount is not None and spent.total_usd > amount,
        alerted_at=None if alert is None else alert.alerted_at,
        sessions=lines,
        session_count=spent.session_count,
    )
