"""Sending Invitations to a Class's Roster through the api (Story 4.4, FR-7, FR-8, AD-9, AD-12,
AD-14): the one transaction, the validity range, idempotency, addresses already on the Roster,
the Student mail and the Roster counts. The api's clock is fixed (2026-11-19 09:00 UTC, 10:00 in
Oslo); the database clock is never read, and nothing is ordered by a timestamp."""

import asyncio
import re
import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import structlog.testing

from app.modules.identity.schemas import AccountRole
from app.platform import auth
from tests.classes.test_classes import OTHER, as_user, make
from tests.classes.test_roster_upload import NOW, clock, klass, paste
from tests.identity.helpers import CSRF, client
from tests.messaging.helpers import deliveries, drain, mails, rows

LINK = re.compile(r"http://127\.0\.0\.1:8080/invitasjon#([A-Za-z0-9_-]+)")
EXPIRES = datetime(2026, 12, 3, 23, 0, tzinfo=UTC)
"""Midnight in Oslo (UTC+1 in winter) after the 14th day from 2026-11-19."""


__all__ = ["clock", "klass"]  # fixtures from `test_roster_upload`: its clock and the Class


@pytest.fixture(autouse=True)
def _empty_mail(mail_db):
    """The mail tables and the mock outbox empty, before `klass` makes its Users."""


def send_path(class_id: str) -> str:
    return f"/api/classes/{class_id}/invitations"


async def staged_id(c, class_id: str, text: str) -> str:
    response = await paste(c, class_id, text)
    assert response.status_code == 201
    return response.json()["id"]


async def send(c, class_id: str, upload_id: str, valid_days: object = 14):
    return await c.post(
        send_path(class_id), json={"upload_id": upload_id, "valid_days": valid_days}, headers=CSRF
    )


def entries() -> list[tuple]:
    return sorted(rows("SELECT email, registration, user_id, removed_at FROM roster_entries"))


def student_invitations() -> list[tuple]:
    return sorted(
        rows(
            "SELECT i.email, i.role, i.class_id, i.expires_at, e.email "
            "FROM invitations i JOIN roster_entries e ON e.id = i.roster_entry_id "
            "WHERE i.kind = 'student'"
        )
    )


def staging_count() -> int:
    return rows("SELECT count(*) FROM roster_uploads")[0][0]


async def test_sending_writes_the_roster_deletes_the_staging_and_enqueues_one_invitation_each(
    klass,
):
    async with client() as c:
        await as_user(c)
        upload_id = await staged_id(c, klass, "a@x.no, B@X.no; c@x.no\nugyldig")
        response = await send(c, klass, upload_id)
        listed = (await c.get("/api/classes")).json()["items"]
        one = (await c.get(f"/api/classes/{klass}")).json()
    assert response.status_code == 201
    assert response.json() == {
        "sent": 3,
        "valid_days": 14,
        "last_valid_day": "2026-12-03",
        "expires_at": "2026-12-03T23:00:00Z",
    }
    addresses = ["a@x.no", "b@x.no", "c@x.no"]
    assert entries() == [(a, "invited", None, None) for a in addresses]
    klass_id = uuid.UUID(klass)
    assert student_invitations() == [(a, None, klass_id, EXPIRES, a) for a in addresses]
    notices = rows("SELECT user_id, kind, ref FROM notices")
    ids = {row[0] for row in rows("SELECT id FROM invitations")}
    assert len(notices) == 3
    assert {(n[0], n[1]) for n in notices} == {(None, "invitation")}
    assert {n[2] for n in notices} == ids
    assert staging_count() == 0
    assert [item["roster_count"] for item in listed] == [3]
    assert one["roster_count"] == 3


@pytest.mark.parametrize("days", [0, 61, 1.5, "fjorten", "14", True])
async def test_a_validity_outside_one_to_sixty_whole_days_is_refused_and_nothing_changes(
    klass, days
):
    async with client() as c:
        await as_user(c)
        upload_id = await staged_id(c, klass, "a@x.no")
        response = await send(c, klass, upload_id, days)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert "valid_days" in response.json()["error"]["fields"]
    assert entries() == [] and rows("SELECT count(*) FROM notices") == [(0,)]
    assert staging_count() == 1


@pytest.mark.parametrize(("days", "last"), [(1, "2026-11-20"), (60, "2027-01-18")])
async def test_the_ends_of_the_range_are_accepted(klass, days, last):
    async with client() as c:
        await as_user(c)
        response = await send(c, klass, await staged_id(c, klass, "a@x.no"), days)
    assert response.status_code == 201
    assert response.json()["last_valid_day"] == last


async def test_sending_twice_gives_no_second_invitation_or_mail(klass):
    async with client() as c:
        await as_user(c)
        upload_id = await staged_id(c, klass, "a@x.no b@x.no")
        first, second = await asyncio.gather(send(c, klass, upload_id), send(c, klass, upload_id))
        third = await send(c, klass, upload_id)
    assert sorted([first.status_code, second.status_code]) == [201, 404]
    assert third.status_code == 404
    assert third.json()["error"]["code"] == "not_found"
    assert len(entries()) == 2
    assert rows("SELECT count(*) FROM invitations") == [(2,)]
    assert rows("SELECT count(*) FROM notices") == [(2,)]
    await drain(NOW)
    assert len(mails()) == 2


async def test_a_replaced_staging_is_not_sent(klass):
    async with client() as c:
        await as_user(c)
        old = await staged_id(c, klass, "a@x.no")
        await staged_id(c, klass, "b@x.no")
        stale = await send(c, klass, old)
        unknown = await send(c, klass, str(uuid.uuid4()))
    assert (stale.status_code, unknown.status_code) == (404, 404)
    assert entries() == [] and staging_count() == 1


async def test_an_address_already_on_the_roster_is_listed_and_not_invited_again(klass):
    async with client() as c:
        await as_user(c)
        await send(c, klass, await staged_id(c, klass, "ola@x.no"))
        # A registered Student of the Class (Story 4.5 writes these; here by hand).
        rows(
            "INSERT INTO roster_entries (id, class_id, email, registration, added_at) "
            "VALUES (gen_random_uuid(), %s, 'kari@x.no', 'registered', %s) RETURNING id",
            klass,
            NOW,
        )
        staged = await paste(c, klass, " Ola@X.no , kari@x.no, ny@x.no")
        body = staged.json()
        response = await send(c, klass, body["id"])
    assert body["valid_count"] == 1
    assert [(r["row_number"], r["value"], r["reason"]) for r in body["invalid_rows"]] == [
        (1, "Ola@X.no", "on_roster"),
        (2, "kari@x.no", "on_roster"),
    ]
    assert response.json()["sent"] == 1
    assert [e[:2] for e in entries()] == [
        ("kari@x.no", "registered"),
        ("ny@x.no", "invited"),
        ("ola@x.no", "invited"),
    ]
    assert [i[0] for i in student_invitations()] == ["ny@x.no", "ola@x.no"]


async def test_a_file_upload_also_marks_roster_addresses(klass):
    from tests.classes.test_roster_upload import upload

    async with client() as c:
        await as_user(c)
        await send(c, klass, await staged_id(c, klass, "s1@stud.example.no"))
        staged = await upload(c, klass, "liste.csv", b"E-post\ns1@stud.example.no\ns2@x.no\n")
        again = await c.get(f"/api/classes/{klass}/roster-upload")
    assert staged.json()["valid_count"] == 1
    assert [r["reason"] for r in staged.json()["invalid_rows"]] == ["on_roster"]
    assert again.json()["upload"]["invalid_rows"] == staged.json()["invalid_rows"]


async def test_a_staging_with_no_valid_row_is_refused_and_kept(klass):
    async with client() as c:
        await as_user(c)
        response = await send(c, klass, await staged_id(c, klass, "ugyldig"))
        empty = await send(c, klass, await staged_id(c, klass, ""))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "nothing_to_send"
    assert empty.json()["error"]["code"] == "nothing_to_send"
    assert staging_count() == 1 and entries() == []


async def test_only_a_lecturer_who_owns_the_class_may_send(klass):
    async with client() as c:
        await as_user(c)
        upload_id = await staged_id(c, klass, "a@x.no")
    await make("admin@x.no", roles=(AccountRole.admin,))
    for who in (OTHER, "admin@x.no"):
        async with client() as c:
            await as_user(c, who)
            other = await send(c, klass, upload_id)
            unknown = await c.post(
                send_path(str(uuid.uuid4())),
                json={"upload_id": upload_id, "valid_days": 14},
                headers=CSRF,
            )
        assert (other.status_code, unknown.status_code) == (403, 403)
    async with client() as c:
        anonymous = await send(c, klass, upload_id)
    assert anonymous.status_code == 401
    assert entries() == [] and staging_count() == 1


async def test_the_mail_names_the_class_and_the_last_valid_day(klass):
    async with client() as c:
        await as_user(c)
        await send(c, klass, await staged_id(c, klass, "ola@x.no"))
    await drain(NOW)
    [mail] = mails()
    assert mail.to == "ola@x.no"
    assert mail.subject == "Invitasjon til ØL-spillet"
    assert mail.text.startswith("ØL-spillet")
    assert "Klassen class-of-1994" in mail.text
    assert "gyldig til og med 3. desember 2026" in mail.text
    assert "til og med 3. desember 2026" in mail.html
    token = LINK.search(mail.text).group(1)
    [(token_hash,)] = rows("SELECT token_hash FROM invitations")
    assert auth.token_hash(token) == token_hash
    assert deliveries() == [("immediate", 1, True, None, 1)]

    # «Du er invitert» takes the mailed link (Story 4.5).
    async with client() as c:
        checked = await c.post("/api/auth/invitation/check", json={"token": token}, headers=CSRF)
    assert checked.status_code == 200 and checked.json()["kind"] == "student"


async def test_an_invitation_past_its_last_day_is_not_mailed(klass):
    async with client() as c:
        await as_user(c)
        await send(c, klass, await staged_id(c, klass, "ola@x.no"), 1)
    await drain(datetime(2026, 11, 20, 23, 0, tzinfo=UTC))  # midnight in Oslo after the 20th
    assert mails() == []
    assert deliveries() == [("immediate", 1, False, "no_recipient", 0)]


async def test_student_invitations_stay_out_of_the_admin_invitation_list(klass):
    await make("admin@x.no", roles=(AccountRole.admin,))
    async with client() as c:
        await as_user(c)
        await send(c, klass, await staged_id(c, klass, "ola@x.no"))
    [(student_id,)] = rows("SELECT id FROM invitations")
    async with client() as c:
        await as_user(c, "admin@x.no")
        listed = await c.get("/api/admin/invitations")
        resent = await c.post(f"/api/admin/invitations/{student_id}/resend", headers=CSRF)
    assert listed.json()["items"] == []
    assert resent.status_code == 404


async def test_four_hundred_addresses_commit_in_one_request_with_ids_only_in_the_logs(
    klass, monkeypatch
):
    from app.modules.identity import repo
    from app.platform import notify

    # Batches of 150, so every batched INSERT runs more than once (the real size is 1000).
    monkeypatch.setattr(repo, "ROSTER_BATCH", 150)
    monkeypatch.setattr(notify, "BY_REF_BATCH", 150)
    text = "\n".join(f"s{i}@stud.example.no" for i in range(400))
    async with client() as c:
        await as_user(c)
        upload_id = await staged_id(c, klass, text)
        with structlog.testing.capture_logs() as logs:
            started = time.perf_counter()
            response = await send(c, klass, upload_id)
            took = time.perf_counter() - started
    assert response.status_code == 201 and response.json()["sent"] == 400
    assert rows("SELECT count(*) FROM notices") == [(400,)]
    assert rows("SELECT count(*) FROM roster_entries") == [(400,)]
    assert rows("SELECT count(*), count(DISTINCT roster_entry_id) FROM invitations") == [(400, 400)]
    assert rows(
        "SELECT count(*), count(DISTINCT queueing_lock) FROM procrastinate_jobs "
        "WHERE task_name = 'messaging.claim_notice' AND queue_name = 'mail'"
    ) == [(400, 400)]
    assert took < 10  # the request returns once the rows commit; mails leave later
    assert not any("@" in str(value) for line in logs for value in line.values())
    assert any(line["event"] == "roster_invitations_sent" for line in logs)


def test_the_expiry_is_the_oslo_midnight_after_the_last_day_also_in_summer_time():
    from app.modules.identity import service

    summer = datetime(2027, 6, 1, 21, 30, tzinfo=UTC)  # 23:30 on 1 June in Oslo
    assert service.student_invitation_expiry(summer, 14) == datetime(2027, 6, 15, 22, 0, tzinfo=UTC)
    assert service.last_valid_day(datetime(2027, 6, 15, 22, 0, tzinfo=UTC)).isoformat() == (
        "2027-06-15"
    )
    late = datetime(2026, 11, 19, 23, 30, tzinfo=UTC)  # already the 20th in Oslo
    assert (
        service.last_valid_day(service.student_invitation_expiry(late, 1))
        == (late + timedelta(days=2)).date()
    )
