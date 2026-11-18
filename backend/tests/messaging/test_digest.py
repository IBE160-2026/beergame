"""Story 3.5: digest notices are gathered into at most one mail per User per Europe/Oslo day,
never sent between 22:00 and 07:00 (AD-9). The clock is controlled: `now` is passed to the sweep,
and the dummy `test_digest` kind stands in for later reminders."""

from datetime import UTC, datetime, timedelta

from app.modules.messaging import delivery, service
from app.modules.ops import sweep
from tests.messaging.helpers import deliveries, drain, enqueue, mails, oslo, rows, user


async def sweep_at(now: datetime) -> None:
    await sweep.run(now)
    await drain(now)


async def test_three_notices_in_one_day_give_one_mail(mail_db):
    user_id = await user()
    for minute in (0, 10, 20):
        await enqueue(user_id, "test_digest", not_before=oslo(12, 9, minute))
    await drain()  # the claim jobs leave digest notices alone
    assert mails() == []
    await sweep_at(oslo(12, 9, 30))
    [mail] = mails()
    assert mail.subject == "Nytt fra ØL-spillet"
    assert mail.text.count("Dette er et testvarsel.") == 3
    assert deliveries() == [("digest", 3, True, None, 1)]
    await sweep_at(oslo(12, 9, 31))
    assert len(mails()) == 1


async def test_a_notice_due_at_2330_is_mailed_after_0700(mail_db):
    user_id = await user()
    await enqueue(user_id, "test_digest", not_before=oslo(12, 23, 30))
    for now in (oslo(12, 23, 31), oslo(13, 0, 0), oslo(13, 6, 59)):
        await sweep_at(now)
    assert mails() == []
    await sweep_at(oslo(13, 7, 0))
    assert len(mails()) == 1


async def test_a_notice_due_after_the_days_mail_is_mailed_the_next_day(mail_db):
    user_id = await user()
    await enqueue(user_id, "test_digest", not_before=oslo(12, 9))
    await sweep_at(oslo(12, 9, 30))
    await enqueue(user_id, "test_digest", not_before=oslo(12, 15))
    for now in (oslo(12, 15, 1), oslo(12, 21, 59), oslo(13, 6, 59)):
        await sweep_at(now)
    assert len(mails()) == 1
    await sweep_at(oslo(13, 7, 0))
    assert len(mails()) == 2
    assert [d[:3] for d in deliveries()] == [("digest", 1, True), ("digest", 1, True)]


async def test_each_user_gets_a_digest_of_their_own(mail_db):
    kari = await user()
    ola = await user("ola@example.no", "Ola")
    await enqueue(kari, "test_digest", not_before=oslo(12, 8))
    await enqueue(ola, "test_digest", not_before=oslo(12, 8))
    await sweep_at(oslo(12, 8, 1))
    assert sorted(m.to for m in mails()) == ["kari@example.no", "ola@example.no"]


async def test_an_immediate_mail_leaves_the_days_digest_alone(mail_db):
    user_id = await user()
    await enqueue(user_id, "test_immediate", "now")
    [(notice_id,)] = rows("SELECT id FROM notices WHERE dedupe_key = 'now'")
    assert await service.claim_notice(notice_id, oslo(12, 8)) is not None
    await enqueue(user_id, "test_digest", not_before=oslo(12, 8, 30))
    await sweep_at(oslo(12, 9))
    assert [m.subject for m in mails()] == ["Testmelding fra ØL-spillet", "Nytt fra ØL-spillet"]


async def test_a_late_digest_is_held_through_the_night_and_sent_from_0700(mail_db):
    user_id = await user()
    await enqueue(user_id, "test_digest", not_before=oslo(12, 21, 50))
    await sweep.run(oslo(12, 21, 59))  # claimed; its `mail` job runs late, at 22:05
    await drain(oslo(12, 22, 5))
    assert mails() == [] and deliveries() == [("digest", 1, False, None, 0)]
    await sweep_at(oslo(13, 6, 59))  # the retry waits for the allowed hours
    assert mails() == []
    await sweep_at(oslo(13, 7, 0))
    assert len(mails()) == 1


def test_quiet_hours_and_the_oslo_day_follow_local_time_across_utc():
    assert not delivery.digest_allowed(oslo(12, 6, 59))
    assert delivery.digest_allowed(oslo(12, 7, 0))
    assert delivery.digest_allowed(oslo(12, 21, 59))
    assert not delivery.digest_allowed(oslo(12, 22, 0))
    # 21:30 UTC on a summer day is 23:30 in Oslo.
    assert not delivery.digest_allowed(datetime(2027, 6, 1, 21, 30, tzinfo=UTC))
    start, end = delivery.oslo_day(datetime(2027, 1, 12, 23, 30, tzinfo=UTC))  # 00:30 on the 13th
    assert start == oslo(13, 0) and end == oslo(14, 0)
    # The spring-forward day has 23 hours; 07:00 local is 05:00 UTC there.
    start, end = delivery.oslo_day(datetime(2027, 3, 28, 12, tzinfo=UTC))
    assert end.astimezone(UTC) - start.astimezone(UTC) == timedelta(hours=23)
    assert delivery.digest_allowed(datetime(2027, 3, 28, 5, 0, tzinfo=UTC))
    assert not delivery.digest_allowed(datetime(2027, 3, 28, 4, 59, tzinfo=UTC))
