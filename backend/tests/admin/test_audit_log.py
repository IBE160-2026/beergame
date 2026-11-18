"""Reading the audit log (Story 3.12, FR-3, FR-5, AD-12, AD-14, AD-15): newest first with names
read now, filters, and exactly one row for every Admin action of Epic 3. The api's clock is fixed
and moved by the test; the database clock is never read."""

import uuid
from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from app.modules.identity import service
from app.modules.identity.schemas import AccountRole
from app.platform import audit, auth
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker
from tests.conftest import TEST_DATABASE_URL, libpq_dsn
from tests.identity.helpers import CSRF, client, login

PASSWORD = "hemmelig-passord"
ADMIN = "kari.admin@example.com"
LECTURER = "ola@example.com"
NOW = datetime(2026, 11, 18, 12, 1, tzinfo=UTC)


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


@pytest.fixture
async def lecturer(admin):
    return await service.create_user(
        email=LECTURER, name="Ola Faglærer", password=PASSWORD, roles=[AccountRole.lecturer]
    )


async def as_user(c, email: str = ADMIN):
    assert (await login(c, email, PASSWORD)).status_code == 200


async def write(actor, action: str, target: dict, change: dict, at: datetime) -> uuid.UUID:
    async with get_sessionmaker().begin() as s:
        return await audit.record(s, actor, action, target, change, at)


async def listed(c, **query) -> dict:
    response = await c.get("/api/admin/audit", params=query)
    assert response.status_code == 200, response.text
    return response.json()


def actions(page: dict) -> list[str]:
    return [item["action"] for item in page["items"]]


async def test_rows_come_newest_first_with_names_read_now(admin, lecturer, clock):
    await write(admin, "role.granted", {"user_id": lecturer}, {"role": "lecturer"}, NOW)
    await write(None, "invitation.bootstrap", {"invitation_id": uuid.uuid7()}, {}, NOW)
    later = NOW + timedelta(minutes=1)
    await write(admin, "future.action", {"seat_id": uuid.uuid7(), "note": "x"}, {"k": 1}, later)
    async with client() as c:
        await as_user(c)
        page = await listed(c)
    assert actions(page) == ["future.action", "invitation.bootstrap", "role.granted"]
    future, system, granted = page["items"]
    assert (granted["actor_id"], granted["actor_name"]) == (str(admin), "Kari Admin")
    assert granted["targets"] == [{"key": "user_id", "id": str(lecturer), "label": "Ola Faglærer"}]
    assert granted["change"] == {"role": "lecturer"}
    assert datetime.fromisoformat(granted["occurred_at"]) == NOW
    assert (system["actor_id"], system["actor_name"]) == (None, None)
    # An unknown invitation id and a key no module registered still list, with no label.
    assert system["targets"][0]["label"] is None
    assert sorted((t["key"], t["label"]) for t in future["targets"]) == [
        ("note", None),
        ("seat_id", None),
    ]
    assert future["change"] == {"k": 1}


async def test_a_name_changed_since_shows_the_new_name(admin, clock):
    async with client() as c:
        await as_user(c)
        created = (
            await c.post("/api/admin/institutions", json={"name": "USN"}, headers=CSRF)
        ).json()
        await c.patch(
            f"/api/admin/institutions/{created['id']}", json={"name": "USN Bø"}, headers=CSRF
        )
        page = await listed(c)
    assert [item["targets"][0]["label"] for item in page["items"]] == ["USN Bø", "USN Bø"]
    assert page["items"][1]["change"] == {"name": "USN"}


async def test_pages_follow_the_cursor(admin, clock):
    for minute in range(3):
        await write(admin, f"a.{minute}", {}, {}, NOW + timedelta(minutes=minute))
    async with client() as c:
        await as_user(c)
        first = await listed(c, limit=2)
        second = await listed(c, limit=2, cursor=first["next_cursor"])
    assert actions(first) == ["a.2", "a.1"]
    assert actions(second) == ["a.0"]
    assert second["next_cursor"] is None


async def test_rows_at_the_same_time_page_by_id(admin, clock):
    for n in range(3):
        await write(admin, f"same.{n}", {}, {}, NOW)
    async with client() as c:
        await as_user(c)
        first = await listed(c, limit=2)
        second = await listed(c, limit=2, cursor=first["next_cursor"])
    assert actions(first) + actions(second) == ["same.2", "same.1", "same.0"]


@pytest.mark.parametrize(
    ("query", "field", "code"),
    [
        ({"cursor": "not-a-cursor"}, "cursor", "invalid_cursor"),
        ({"cursor": "MjAyNi0xMS0xOFQxMjowMXx4"}, "cursor", "invalid_cursor"),
        ({"actor": "nobody"}, "actor", "invalid_actor"),
        ({"since": "2026-11-18", "until": "2026-11-17"}, "until", "range_reversed"),
    ],
)
async def test_a_bad_filter_or_cursor_is_refused(admin, clock, query, field, code):
    async with client() as c:
        await as_user(c)
        response = await c.get("/api/admin/audit", params=query)
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == {field: code}


async def test_the_actor_filter_keeps_one_user_or_the_system(admin, lecturer, clock):
    await write(admin, "by.admin", {}, {}, NOW)
    await write(lecturer, "by.lecturer", {}, {}, NOW)
    await write(None, "by.system", {}, {}, NOW)
    async with client() as c:
        await as_user(c)
        assert actions(await listed(c, actor=str(lecturer))) == ["by.lecturer"]
        assert actions(await listed(c, actor="system")) == ["by.system"]
        assert actions(await listed(c, actor=str(uuid.uuid7()))) == []


async def test_an_invitation_is_named_by_its_address(admin, clock):
    async with client() as c:
        await as_user(c)
        invite = {"email": "ny@example.com", "role": "lecturer"}
        sent = await c.post("/api/admin/invitations", json=invite, headers=CSRF)
        page = await listed(c)
    [row] = page["items"]
    assert row["targets"] == [
        {"key": "invitation_id", "id": sent.json()["id"], "label": "ny@example.com"}
    ]


@pytest.mark.parametrize(
    "query",
    [
        {"actor": ""},
        {"since": "0001-01-01", "until": "9999-12-31"},
        {"since": "0001-01-01"},
        {"until": "9999-12-31"},
    ],
)
async def test_an_empty_actor_and_the_outermost_dates_filter_nothing(admin, clock, query):
    await write(admin, "kept", {}, {}, NOW)
    async with client() as c:
        await as_user(c)
        assert actions(await listed(c, **query)) == ["kept"]


async def test_the_action_filter_matches_exactly(admin, clock):
    await write(admin, "role.granted", {}, {}, NOW)
    await write(admin, "role.revoked", {}, {}, NOW)
    async with client() as c:
        await as_user(c)
        assert actions(await listed(c, action="role.granted")) == ["role.granted"]
        assert actions(await listed(c, action="role")) == []


async def test_the_date_range_is_whole_oslo_days(admin, clock):
    # 23:30 UTC on 17 Nov is 00:30 on 18 Nov in Oslo; 23:00 UTC on 18 Nov is 00:00 on the 19th.
    await write(admin, "before", {}, {}, datetime(2026, 11, 17, 22, 59, tzinfo=UTC))
    await write(admin, "first", {}, {}, datetime(2026, 11, 17, 23, 30, tzinfo=UTC))
    await write(admin, "last", {}, {}, datetime(2026, 11, 18, 22, 59, tzinfo=UTC))
    await write(admin, "after", {}, {}, datetime(2026, 11, 18, 23, 0, tzinfo=UTC))
    async with client() as c:
        await as_user(c)
        day = await listed(c, since="2026-11-18", until="2026-11-18")
        from_day = await listed(c, since="2026-11-18")
        to_day = await listed(c, until="2026-11-17")
    assert actions(day) == ["last", "first"]
    assert actions(from_day) == ["after", "last", "first"]
    assert actions(to_day) == ["before"]


async def test_the_actors_are_the_system_then_users_by_name(admin, lecturer, clock):
    await write(lecturer, "x", {}, {}, NOW)
    await write(admin, "x", {}, {}, NOW)
    await write(None, "x", {}, {}, NOW)
    async with client() as c:
        await as_user(c)
        response = await c.get("/api/admin/audit/actors")
    assert response.status_code == 200
    assert response.json()["items"] == [
        {"id": None, "name": None},
        {"id": str(admin), "name": "Kari Admin"},
        {"id": str(lecturer), "name": "Ola Faglærer"},
    ]


@pytest.mark.parametrize("path", ["/api/admin/audit", "/api/admin/audit/actors"])
async def test_only_an_admin_reads_the_log(lecturer, clock, path):
    async with client() as c:
        assert (await c.get(path)).status_code == 401
        await as_user(c, LECTURER)
        response = await c.get(path)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


@pytest.fixture
def db():
    """One connection for every check: a connection per query would cost more than the actions."""
    with psycopg.connect(libpq_dsn(TEST_DATABASE_URL), autocommit=True) as conn:
        yield conn


async def test_every_admin_action_of_the_epic_writes_exactly_one_row(
    admin, lecturer, clock, monkeypatch, db
):
    """FR-3: one row per action, with its own action name, and nothing else written."""

    def written() -> list[str]:
        return [row[0] for row in db.execute("SELECT action FROM audit_events ORDER BY id")]

    async def once(action: str, response, status: int | None = None):
        before = written()
        response = await response
        if status is not None:
            assert response.status_code == status, response.text
        assert written() == [*before, action]
        clock["now"] += timedelta(seconds=1)
        return response

    async with client() as c, client("203.0.113.8") as guest:
        await as_user(c)
        invite = {"email": "ny@example.com", "role": "lecturer"}
        sent = await once(
            "invitation.sent", c.post("/api/admin/invitations", json=invite, headers=CSRF), 201
        )
        resent = await once(
            "invitation.resent",
            c.post(f"/api/admin/invitations/{sent.json()['id']}/resend", headers=CSRF),
            201,
        )
        token = auth.link_token(service.INVITATION, uuid.UUID(resent.json()["id"]))
        body = {"token": token, "name": "Ny Faglærer", "password": PASSWORD}
        await once(
            "invitation.accepted",
            guest.post("/api/auth/invitation/accept", json=body, headers=CSRF),
            200,
        )

        to_existing = {"email": LECTURER, "role": "admin"}
        sent = await once(
            "invitation.sent", c.post("/api/admin/invitations", json=to_existing, headers=CSRF), 201
        )
        token = auth.link_token(service.INVITATION, uuid.UUID(sent.json()["id"]))
        body = {"token": token, "password": PASSWORD}
        await once(
            "invitation.accepted",
            guest.post("/api/auth/invitation/accept-login", json=body, headers=CSRF),
            200,
        )

        await once(
            "role.revoked", c.delete(f"/api/admin/users/{lecturer}/roles/admin", headers=CSRF), 200
        )
        grant = {"role": "admin"}
        await once(
            "role.granted",
            c.post(f"/api/admin/users/{lecturer}/roles", json=grant, headers=CSRF),
            200,
        )
        await once(
            "user.deactivated", c.post(f"/api/admin/users/{lecturer}/deactivate", headers=CSRF), 200
        )
        await once(
            "user.reactivated", c.post(f"/api/admin/users/{lecturer}/reactivate", headers=CSRF), 200
        )

        created = await once(
            "institution.created",
            c.post("/api/admin/institutions", json={"name": "USN"}, headers=CSRF),
            201,
        )
        renamed = {"name": "USN Bø"}
        institution = created.json()["id"]
        await once(
            "institution.renamed",
            c.patch(f"/api/admin/institutions/{institution}", json=renamed, headers=CSRF),
            200,
        )

    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "forste.admin@example.com")
    get_settings.cache_clear()
    await once("invitation.bootstrap", service.ensure_bootstrap_invitations(clock["now"]))
