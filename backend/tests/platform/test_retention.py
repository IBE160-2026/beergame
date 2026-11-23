"""The deletion date rule (Story 13.9, FR-77): the latest effective Test deadline on the Oslo
calendar plus the retention months, a month's end clamped."""

from datetime import UTC, date, datetime

import pytest

from app.platform.retention import add_months, deletion_date, latest_test_deadline


def test_six_months_after_the_test_deadline():
    assert deletion_date(datetime(2026, 12, 18, 10, tzinfo=UTC), 6) == date(2027, 6, 18)


def test_the_day_is_read_on_the_oslo_calendar():
    # 23:30 UTC on New Year's Eve is 00:30 on 1 January in Oslo.
    assert deletion_date(datetime(2026, 12, 31, 23, 30, tzinfo=UTC), 6) == date(2027, 7, 1)
    # Summer time: 22:30 UTC on 30 June is 00:30 on 1 July in Oslo.
    assert deletion_date(datetime(2026, 6, 30, 22, 30, tzinfo=UTC), 6) == date(2027, 1, 1)


def test_a_day_past_the_months_end_becomes_its_last():
    assert add_months(date(2026, 8, 31), 6) == date(2027, 2, 28)
    assert add_months(date(2027, 8, 31), 6) == date(2028, 2, 29)
    assert add_months(date(2026, 11, 30), 14) == date(2028, 1, 30)


def test_no_test_deadline_has_no_date():
    assert deletion_date(None, 6) is None
    assert latest_test_deadline(None, [datetime(2027, 1, 1, tzinfo=UTC)]) is None


def test_the_latest_extension_counts():
    own = datetime(2027, 1, 20, tzinfo=UTC)
    assert latest_test_deadline(datetime(2027, 1, 10, tzinfo=UTC), [own]) == own
    # A Class deadline moved past every extension is the latest one.
    later = datetime(2027, 2, 1, tzinfo=UTC)
    assert latest_test_deadline(later, [own]) == later


def test_a_naive_deadline_is_refused():
    with pytest.raises(ValueError):
        deletion_date(datetime(2027, 1, 1), 6)
