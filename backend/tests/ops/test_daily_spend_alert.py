"""The Admin is alerted when daily AI spend is high (Story 15.7, FR-69, AD-6, AD-9). The sweep's
due action sums today's spend (the Europe/Oslo day) through `ai.calls.day_spend`, records the day's
alert once it passes `AI_DAILY_ALERT_USD` and tells each active Admin once that day with an
immediate notice whose mail names the dearest Class sessions and links to «KI-kostnad» for the
day. Times are passed in; the database clock is never compared with them."""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.ai import budget, calls, config, seed
from app.modules.identity.schemas import AccountRole
from app.modules.messaging import delivery
from app.modules.ops import spend_alert, sweep
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker
from tests.classes.test_classes import LECTURER, as_user, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.identity.helpers import CSRF, client
from tests.messaging.helpers import drain, mails, rows
from tests.sessions.test_dates import new_session

__all__ = ["clock", "klass"]

ADMIN = "admin157@example.com"
OTHER_ADMIN = "admin157b@example.com"
DAY = date(2026, 11, 19)
"""The day of the roster tests' clock (09:00 UTC, 10:00 in Oslo, winter time UTC+1)."""
NOW = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)
MIDNIGHT = datetime(2026, 11, 18, 23, 0, tzinfo=UTC)
"""00:00 on 19 November in Oslo."""
TICK = timedelta(microseconds=1)


@pytest.fixture(autouse=True)
def _empty(ai_db, mail_db, games_db):
    """No model config, call or alert unless a test adds one, and no notices."""


@pytest.fixture
def alert_at(monkeypatch):
    def set_amount(value: str) -> None:
        monkeypatch.setenv("AI_DAILY_ALERT_USD", value)
        get_settings.cache_clear()

    set_amount("1.00")
    return set_amount


@pytest.fixture
async def admin(klass) -> uuid.UUID:
    return await make(ADMIN, roles=(AccountRole.admin,))


@pytest.fixture
async def model() -> uuid.UUID:
    row = await config.add(config.parse({**seed.MOCK_SPEC, "name": "kostnad"}))
    return row.id


def spend(
    model: uuid.UUID, scope_id: str | uuid.UUID, usd: str, at: datetime, kind="class_session"
):
    """One `llm_call` attempt of `usd` started at `at`."""
    execute(
        "INSERT INTO llm_call (id, purpose, scope_kind, scope_id, caller_ref, model_config_id, "
        "provider, endpoint, model_version, quantisation, effort_level, prompt_version, attempt, "
        "input_tokens, output_tokens, reasoning_tokens, cost_usd, latency_ms, outcome, request, "
        "started_at) VALUES (%s, 'player_order', %s, %s, '{}', %s, 'mock', 'mock', 'mock-v1', "
        "'none', 'fast', 1, 1, 10, 5, 0, %s, 100, 'ok', '{}', %s)",
        uuid.uuid7(),
        kind,
        str(scope_id),
        model,
        usd,
        at,
    )


def notices() -> list[tuple]:
    return rows("SELECT user_id, kind, dedupe_key, ref FROM notices ORDER BY dedupe_key")


async def get_day(day: str | None = None, who: str = ADMIN):
    async with client() as c:
        await as_user(c, who)
        query = "" if day is None else f"?day={day}"
        return await c.get(f"/api/admin/ai/daily-spend{query}", headers=CSRF)


async def test_the_daily_spend_counts_each_call_in_its_own_oslo_day(klass, model):
    first, second = await new_session(klass), await new_session(klass)
    spend(model, first, "1.00000000", MIDNIGHT - TICK)  # 23:59:59.999999 on the 18th
    spend(model, first, "2.00000000", MIDNIGHT)  # 00:00 on the 19th
    spend(model, second, "3.12345678", MIDNIGHT + timedelta(hours=23) - TICK)  # last instant
    spend(model, first, "4.00000000", MIDNIGHT + timedelta(hours=24))  # 00:00 on the 20th
    spend(model, model, "0.25000000", NOW, kind="evaluation")

    found = await calls.day_spend(DAY)
    assert found.total_usd == Decimal("5.37345678")  # unrounded, every scope
    assert found.calls == 3
    assert found.evaluation_usd == Decimal("0.25")
    assert [(line.class_session_id, line.usd) for line in found.sessions] == [
        (uuid.UUID(second), Decimal("3.12345678")),
        (uuid.UUID(first), Decimal("2.00000000")),
    ]
    assert found.session_count == 2
    assert (await calls.day_spend(DAY - timedelta(days=1))).total_usd == Decimal("1")
    assert (await calls.day_spend(DAY + timedelta(days=1))).total_usd == Decimal("4")
    assert (await calls.day_spend(DAY, top=1)).sessions[0].usd == Decimal("3.12345678")


async def test_each_admin_is_alerted_once_a_day_with_the_dearest_class_sessions(
    klass, admin, model, alert_at
):
    other = await make(OTHER_ADMIN, roles=(AccountRole.admin,))
    session_id = await new_session(klass)
    spend(model, session_id, "1.50000000", NOW - timedelta(hours=1))
    spend(model, model, "0.40000000", NOW, kind="evaluation")

    done = await sweep.run(NOW)
    assert done["ops.daily_spend_alert"] == 1
    [alert] = rows("SELECT id, day, alert_usd, spent_usd, alerted_at FROM ai_spend_alerts")
    assert alert[1:] == (DAY, Decimal("1.00000000"), Decimal("1.90000000"), NOW)
    assert notices() == sorted(
        (user, "ai_daily_spend", f"ai_daily_spend:2026-11-19:{user}", alert[0])
        for user in (admin, other)
    )
    # A second sweep the same day sends nothing.
    assert (await sweep.run(NOW + timedelta(minutes=1)))["ops.daily_spend_alert"] == 0
    assert len(notices()) == 2

    await drain(NOW)
    sent = mails()
    assert sorted(mail.to for mail in sent) == sorted([ADMIN, OTHER_ADMIN])
    mail = sent[0]
    assert mail.subject == "KI-kostnaden har passert varselgrensen"
    assert "KI-kostnaden 19. november 2026 er 1,90 USD" in mail.text
    assert "1,00 USD" in mail.text
    assert "class-of-1994 · Klasseøkt 1: 1,50 USD" in mail.text
    assert "/admin/ki-kostnad?dag=2026-11-19" in mail.text
    assert "/admin/ki-kostnad?dag=2026-11-19" in mail.html
    assert LECTURER not in mail.text and "Lecturer" not in mail.text  # no other User's data

    # An Admin added later that day is told once; the alert row stands as first recorded.
    late = await make("admin157c@example.com", roles=(AccountRole.admin,))
    spend(model, session_id, "1.00000000", NOW + timedelta(minutes=2))
    assert await spend_alert.alert_due(DAY, NOW + timedelta(minutes=3)) == 1
    assert [n[0] for n in notices()].count(late) == 1
    assert rows("SELECT spent_usd FROM ai_spend_alerts") == [(Decimal("1.90000000"),)]

    # The next day starts again: a new alert and a new notice per Admin.
    tomorrow = NOW + timedelta(days=1)
    assert await spend_alert.due_days(tomorrow) == []
    spend(model, session_id, "1.10000000", tomorrow)
    assert await spend_alert.due_days(tomorrow) == [DAY + timedelta(days=1)]
    assert await spend_alert.alert_due(DAY + timedelta(days=1), tomorrow) == 3
    assert len(rows("SELECT day FROM ai_spend_alerts")) == 2


async def test_no_alert_at_or_below_the_amount_or_without_one(klass, admin, model, alert_at):
    session_id = await new_session(klass)
    spend(model, session_id, "1.00000000", NOW)
    assert await spend_alert.due_days(NOW) == []  # equal is not passed
    assert await spend_alert.alert_due(DAY, NOW) == 0
    spend(model, session_id, "5.00000000", NOW)
    alert_at("")  # not set
    assert get_settings().ai_daily_alert_usd is None
    assert await spend_alert.due_days(NOW) == []
    assert await spend_alert.alert_due(DAY, NOW) == 0
    assert notices() == [] and rows("SELECT id FROM ai_spend_alerts") == []
    body = (await get_day()).json()
    assert (body["alert_usd"], body["passed"], body["alerted_at"]) == (None, False, None)


async def test_the_page_reads_the_day_its_alert_and_its_class_sessions(
    klass, admin, model, alert_at
):
    session_id = await new_session(klass)
    spend(model, session_id, "1.25000000", NOW)
    spend(model, model, "0.50000000", NOW, kind="evaluation")
    spend(model, session_id, "9.00000000", NOW - timedelta(days=1))

    response = await get_day()
    assert response.status_code == 200
    body = response.json()
    assert body["day"] == body["today"] == "2026-11-19"
    assert (body["total_usd"], body["calls"], body["evaluation_usd"]) == (
        "1.75000000",
        2,
        "0.50000000",
    )
    assert (body["alert_usd"], body["passed"], body["alerted_at"]) == ("1.00000000", True, None)
    assert body["sessions"] == [
        {
            "class_session_id": session_id,
            "label": "class-of-1994 · Klasseøkt 1",
            "institution_name": "USN Bø",
            "usd": "1.25000000",
            "calls": 1,
        }
    ]
    assert body["session_count"] == 1

    await spend_alert.alert_due(DAY, NOW)
    assert (await get_day()).json()["alerted_at"] is not None
    # An alerted day keeps the amount it was alerted at, also once the setting changed.
    alert_at("")
    alerted = (await get_day()).json()
    assert (alerted["alert_usd"], alerted["passed"]) == ("1.00000000", True)
    yesterday = (await get_day("2026-11-18")).json()
    assert (yesterday["total_usd"], yesterday["alerted_at"]) == ("9.00000000", None)
    future = await get_day("2026-11-20")
    assert future.status_code == 422
    assert future.json()["error"]["code"] == "day_in_future"
    assert (await get_day("0001-01-01")).status_code == 422  # before the product
    assert (await get_day(who=LECTURER)).status_code == 403


async def test_the_alert_is_an_immediate_kind_and_skips_a_user_who_is_no_admin(klass, admin, model):
    assert delivery.DAILY_SPEND_KIND == spend_alert.DAILY_SPEND_NOTICE
    assert delivery.table()[spend_alert.DAILY_SPEND_NOTICE].mode == delivery.IMMEDIATE
    assert delivery.usd_text(Decimal("1234.505")) == "1 234,51 USD"
    spend(model, await new_session(klass), "2.00000000", NOW)
    async with get_sessionmaker().begin() as s:
        alert = await budget.record_daily_alert(DAY, Decimal(1), Decimal(2), NOW, session=s)
        # A User who is no longer an Admin gets no mail.
        assert (
            await delivery.KINDS[delivery.DAILY_SPEND_KIND].context(s, uuid.uuid7(), alert.id, NOW)
            is None
        )
        context = await delivery.KINDS[delivery.DAILY_SPEND_KIND].context(s, admin, alert.id, NOW)
    assert context is not None and context["day_path"] == "/admin/ki-kostnad?dag=2026-11-19"
    assert context["sessions"] == [{"name": "class-of-1994 · Klasseøkt 1", "spent": "2,00 USD"}]
