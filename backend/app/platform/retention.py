"""When a Class session's Student data is deleted (Story 13.9, FR-77, AD-9, AD-14): the one rule.

The deletion date is the latest effective Test deadline of the Class session (its Test deadline,
or the latest per-Student extension of Story 11.13), read as a day on the Europe/Oslo calendar,
plus the retention period in whole calendar months; a day past the new month's end becomes its
last. `sessions.service` stores it on the Class session; Epic 15 (`ops.retention`) deletes on it
and reads the same rule. Pure (no clock, no database); in `platform` so that `sessions` and
`ops` share it.
"""

import calendar
from collections.abc import Sequence
from datetime import date, datetime
from zoneinfo import ZoneInfo

OSLO = ZoneInfo("Europe/Oslo")


def add_months(day: date, months: int) -> date:
    """`day` moved by whole calendar months; a day past the new month's end becomes its last."""
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def latest_test_deadline(
    test_deadline: datetime | None, extensions: Sequence[datetime] = ()
) -> datetime | None:
    """The latest effective Test deadline of a Class session: the later of its own and every
    Student's extension; None while the Class session has no Test deadline (an extension only
    ever extends a set one)."""
    if test_deadline is None:
        return None
    return max([test_deadline, *extensions])


def deletion_date(latest: datetime | None, months: int) -> date | None:
    """The day the Class session's Student data is deleted: `latest` (the latest effective Test
    deadline) on the Oslo calendar plus `months`; None while there is no Test deadline."""
    if latest is None:
        return None
    if latest.tzinfo is None:
        raise ValueError("a deadline carries a time zone")
    return add_months(latest.astimezone(OSLO).date(), months)
