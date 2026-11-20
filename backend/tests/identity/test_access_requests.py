"""Requests for lecturer access from the Landing, and the Admin's invite and dismiss actions on
them (Story 3.13, FR-1, FR-3, AD-11, AD-15). The api's clock is fixed and moved by the test; the
database clock is never read."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.identity import service
from app.modules.identity.schemas import AccountRole
from app.platform import auth
from app.platform.config import get_settings
from tests.identity.helpers import CSRF, client, login
from tests.messaging.helpers import rows

PASSWORD = "hemmelig-passord"
ADMIN = "kari.admin@example.com"
LECTURER = "bard@example.com"
NOW = datetime(2026, 11, 18, 12, 1, tzinfo=UTC)
OLA = {"name": "  Ola   Nordmann ", "email": " OLA@usn.no ", "institution": " USN  Bø "}


@pytest.fixture
def clock(monkeypatch):
    times = {"now": NOW}
    monkeypatch.setattr(auth, "utcnow", lambda: times["now"])
    return times


@pytest.fixture
async def admin(identity_db, mail_db):
    return await service.create_user(
        email=ADMIN, name="Kari Admin", password=PASSWORD, roles=[AccountRole.admin]
    )


async def ask(c, body=None):
    return await c.post("/api/auth/access-request", json=body or OLA, headers=CSRF)


async def as_admin(c):
    assert (await login(c, ADMIN, PASSWORD)).status_code == 200


def stored() -> list[tuple]:
    return rows(
        "SELECT name, email, institution, requested_at, status, closed_by, invitation_id "
        "FROM access_requests ORDER BY id"
    )


def audit_rows() -> list[tuple]:
    return rows("SELECT actor_user_id, action, target_ids, change FROM audit_events ORDER BY id")


async def test_a_request_is_stored_normalised_and_creates_no_account_or_invitation(admin, clock):
    async with client() as c:
        response = await ask(c)
    assert response.status_code == 202
    assert response.content == b""
    assert stored() == [("Ola Nordmann", "ola@usn.no", "USN Bø", NOW, "open", None, None)]
    assert rows("SELECT count(*) FROM users WHERE email = 'ola@usn.no'") == [(0,)]
    assert rows("SELECT count(*) FROM invitations") == [(0,)]
    assert audit_rows() == []


async def test_an_address_with_an_account_gets_the_same_answer(admin, clock):
    async with client() as c:
        response = await ask(c, {**OLA, "email": ADMIN})
    assert response.status_code == 202
    assert [row[1] for row in stored()] == [ADMIN]


async def test_a_repeat_from_the_same_address_updates_the_one_open_request(admin, clock):
    async with client() as c:
        assert (await ask(c)).status_code == 202
        clock["now"] = NOW + timedelta(minutes=5)
        again = {"name": "Ola N.", "email": "ola@USN.no", "institution": "NTNU"}
        assert (await ask(c, again)).status_code == 202
    assert stored() == [
        ("Ola N.", "ola@usn.no", "NTNU", NOW + timedelta(minutes=5), "open", None, None)
    ]


@pytest.mark.parametrize(
    ("body", "fields"),
    [
        ({**OLA, "name": "   "}, {"name": "name_empty"}),
        ({**OLA, "name": "x" * 201}, {"name": "name_too_long"}),
        ({**OLA, "email": "x@"}, {"email": "invalid_email"}),
        ({**OLA, "institution": ""}, {"institution": "name_empty"}),
        ({**OLA, "institution": "a@b"}, {"institution": "name_invalid"}),
        ({**OLA, "institution": "x" * 201}, {"institution": "name_too_long"}),
        (
            {"name": "", "email": "nope", "institution": " "},
            {"name": "name_empty", "email": "invalid_email", "institution": "name_empty"},
        ),
    ],
)
async def test_a_bad_field_is_refused_with_its_code_and_nothing_is_stored(
    admin, clock, body, fields
):
    async with client() as c:
        response = await ask(c, body)
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == fields
    assert stored() == []


async def test_the_form_is_rate_limited_per_ip_address(admin, clock, monkeypatch):
    monkeypatch.setenv("ACCESS_REQUEST_RATE_LIMIT_PER_IP", "2")
    get_settings.cache_clear()
    async with client("198.51.100.1") as c:
        for n in range(2):
            assert (await ask(c, {**OLA, "email": f"ola{n}@usn.no"})).status_code == 202
        refused = await ask(c, {**OLA, "email": "ola9@usn.no"})
    assert refused.status_code == 429
    assert refused.json()["error"]["code"] == "rate_limited"
    assert 0 < int(refused.headers["Retry-After"]) <= 3600
    assert len(stored()) == 2
    # Another address is counted on its own.
    async with client("198.51.100.2") as c:
        assert (await ask(c, {**OLA, "email": "ola9@usn.no"})).status_code == 202


async def make_requests(c, clock, count: int) -> list[str]:
    for n in range(count):
        clock["now"] = NOW + timedelta(minutes=n)
        assert (
            await ask(c, {**OLA, "email": f"ola{n}@usn.no", "name": f"Ola {n}"})
        ).status_code == 202
    return [row[0] for row in rows("SELECT id FROM access_requests ORDER BY requested_at")]


async def test_the_admin_lists_open_requests_newest_first_one_page_at_a_time(admin, clock):
    async with client() as c:
        ids = await make_requests(c, clock, 4)
        await as_admin(c)
        assert (
            await c.post(f"/api/admin/access-requests/{ids[3]}/dismiss", headers=CSRF)
        ).status_code == 204
        first = (await c.get("/api/admin/access-requests", params={"limit": 2})).json()
        second = (
            await c.get(
                "/api/admin/access-requests", params={"limit": 2, "cursor": first["next_cursor"]}
            )
        ).json()
        bad = await c.get("/api/admin/access-requests", params={"cursor": "bogus"})
    assert [item["name"] for item in first["items"]] == ["Ola 2", "Ola 1"]
    assert first["items"][0] == {
        "id": str(ids[2]),
        "name": "Ola 2",
        "email": "ola2@usn.no",
        "institution": "USN Bø",
        "requested_at": (NOW + timedelta(minutes=2)).isoformat().replace("+00:00", "Z"),
    }
    assert [item["name"] for item in second["items"]] == ["Ola 0"]
    assert second["next_cursor"] is None
    assert bad.status_code == 422
    assert bad.json()["error"]["fields"] == {"cursor": "invalid_cursor"}


async def test_inviting_from_a_request_closes_it_with_one_audit_row(admin, clock):
    async with client() as c:
        [request_id] = await make_requests(c, clock, 1)
        await as_admin(c)
        response = await c.post(
            "/api/admin/invitations",
            json={"email": "ola0@usn.no", "role": "lecturer", "access_request_id": str(request_id)},
            headers=CSRF,
        )
        listed = (await c.get("/api/admin/access-requests")).json()
    assert response.status_code == 201
    invitation_id = response.json()["id"]
    [(*_, status, closed_by, closed_invitation)] = stored()
    assert (status, closed_by, str(closed_invitation)) == ("invited", admin, invitation_id)
    assert audit_rows() == [
        (
            admin,
            "access_request.invited",
            {"invitation_id": invitation_id, "access_request_id": str(request_id)},
            {"role": "lecturer"},
        )
    ]
    assert listed["items"] == []


@pytest.mark.parametrize("stale", ["dismissed", "unknown"])
async def test_inviting_with_a_request_that_is_not_open_sends_a_plain_invitation(
    admin, clock, stale
):
    async with client() as c:
        [request_id] = await make_requests(c, clock, 1)
        await as_admin(c)
        if stale == "dismissed":
            await c.post(f"/api/admin/access-requests/{request_id}/dismiss", headers=CSRF)
        else:
            request_id = uuid.uuid7()
        response = await c.post(
            "/api/admin/invitations",
            json={"email": "ola0@usn.no", "role": "lecturer", "access_request_id": str(request_id)},
            headers=CSRF,
        )
    assert response.status_code == 201
    assert audit_rows()[-1][1:3] == ("invitation.sent", {"invitation_id": response.json()["id"]})
    assert stored()[0][4] == ("dismissed" if stale == "dismissed" else "open")


@pytest.mark.parametrize(
    "body",
    [
        {"email": "someone.else@usn.no", "role": "lecturer"},
        {"email": "ola0@usn.no", "role": "admin"},
    ],
)
async def test_an_invitation_to_another_address_or_role_leaves_the_request_open(admin, clock, body):
    async with client() as c:
        [request_id] = await make_requests(c, clock, 1)
        await as_admin(c)
        response = await c.post(
            "/api/admin/invitations",
            json={**body, "access_request_id": str(request_id)},
            headers=CSRF,
        )
    assert response.status_code == 201
    assert audit_rows()[-1][1:3] == ("invitation.sent", {"invitation_id": response.json()["id"]})
    assert stored()[0][4:7] == ("open", None, None)


async def test_a_new_request_after_a_closed_one_opens_a_new_row(admin, clock):
    async with client() as c:
        [first] = await make_requests(c, clock, 1)
        await as_admin(c)
        await c.post(f"/api/admin/access-requests/{first}/dismiss", headers=CSRF)
        clock["now"] = NOW + timedelta(hours=1)
        assert (await ask(c, {**OLA, "email": "ola0@usn.no"})).status_code == 202
        listed = (await c.get("/api/admin/access-requests")).json()["items"]
    assert [row[4] for row in stored()] == ["dismissed", "open"]
    assert [item["email"] for item in listed] == ["ola0@usn.no"]
    assert listed[0]["id"] != str(first)


async def test_dismissing_closes_the_request_with_one_audit_row_and_only_once(admin, clock):
    async with client() as c:
        [request_id] = await make_requests(c, clock, 1)
        await as_admin(c)
        first = await c.post(f"/api/admin/access-requests/{request_id}/dismiss", headers=CSRF)
        again = await c.post(f"/api/admin/access-requests/{request_id}/dismiss", headers=CSRF)
        unknown = await c.post(f"/api/admin/access-requests/{uuid.uuid7()}/dismiss", headers=CSRF)
    assert first.status_code == 204
    assert (again.status_code, again.json()["error"]["code"]) == (404, "not_found")
    assert unknown.status_code == 404
    assert stored()[0][4:6] == ("dismissed", admin)
    assert audit_rows() == [
        (admin, "access_request.dismissed", {"access_request_id": str(request_id)}, {})
    ]


async def test_the_audit_page_names_the_request_by_its_sender(admin, clock):
    async with client() as c:
        [request_id] = await make_requests(c, clock, 1)
        await as_admin(c)
        await c.post(f"/api/admin/access-requests/{request_id}/dismiss", headers=CSRF)
        [event] = (await c.get("/api/admin/audit")).json()["items"]
    assert event["targets"] == [
        {"key": "access_request_id", "id": str(request_id), "label": "Ola 0"}
    ]


async def test_only_an_admin_reaches_the_request_list_and_actions(admin, clock):
    await service.create_user(
        email=LECTURER, name="Bård", password=PASSWORD, roles=[AccountRole.lecturer]
    )
    some_id = uuid.uuid7()
    async with client() as c:
        anonymous = [
            await c.get("/api/admin/access-requests"),
            await c.post(f"/api/admin/access-requests/{some_id}/dismiss", headers=CSRF),
        ]
        assert (await login(c, LECTURER, PASSWORD)).status_code == 200
        lecturer = [
            await c.get("/api/admin/access-requests"),
            await c.post(f"/api/admin/access-requests/{some_id}/dismiss", headers=CSRF),
        ]
    assert [r.status_code for r in anonymous] == [401, 401]
    assert [r.status_code for r in lecturer] == [403, 403]


async def test_the_upsert_works_on_a_warm_connection_where_postgres_plans_it_generically(admin):
    """psycopg prepares a statement on its sixth run on one connection, and Postgres then tries
    a generic plan, which could not match a bound `status` to the partial unique index: the
    eleventh request on one pooled connection failed. Twenty, on one connection."""
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.modules.identity import repo
    from app.platform.db import get_engine

    async with get_engine().connect() as conn, AsyncSession(conn) as session:
        for n in range(20):
            await repo.upsert_access_request(
                session,
                request_id=uuid.uuid4(),
                name="Ola",
                email=f"warm-{n % 4}@usn.no",
                institution="USN",
                now=NOW,
            )
        await session.commit()
    assert len(stored()) == 4
