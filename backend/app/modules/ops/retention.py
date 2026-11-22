"""When a Class session's Student data is deleted (FR-77, AD-14): the seam Story 15.3 fills.

Story 15.3 computes the retention date from the latest effective Test deadline plus a period set
per Institution, and deletes on that date. Until it lands, `deletion_date` gives the placeholder
default: the Class session's Test deadline plus six calendar months, read on the Europe/Oslo
calendar. The evaluation export (Story 15.4) shows it, because exported data must be deleted by
then too.
"""

import calendar
from datetime import date, datetime
from zoneinfo import ZoneInfo

OSLO = ZoneInfo("Europe/Oslo")
RETENTION_MONTHS = 6
"""Placeholder (FR-77 `[ASSUMPTION]`): course end plus six months; per Institution in 15.3."""


def add_months(day: date, months: int) -> date:
    """`day` moved by whole calendar months; a day past the new month's end becomes its last."""
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def deletion_date(test_deadline: datetime | None) -> date | None:
    """The day the Class session's Student data is deleted, or None while it has no Test
    deadline."""
    if test_deadline is None:
        return None
    return add_months(test_deadline.astimezone(OSLO).date(), RETENTION_MONTHS)
