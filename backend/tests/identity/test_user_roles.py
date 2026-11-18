"""«Brukere og roller»: the User list, and granting and revoking account roles through the api
(Story 3.9, FR-2, FR-3, AD-8, AD-12, AD-14, AD-15). The api's clock is fixed; the database clock is
never read."""

import asyncio
import json
import uuid
from datetime import UTC, datetime

import psycopg
import pytest
from structlog.testing import capture_logs

from app.modules.identity import service
from app.modules.identity.schemas import AccountRole
from app.platform import auth, events
from app.platform.events.registry import COMMAND_TOPICS
from tests.conftest import libpq_dsn
from tests.identity.helpers import CSRF, client, login
from tests.messaging.helpers import rows

PASSWORD = "hemmelig-passord"
ADMIN = "kari.admin@example.com"


@pytest.fixture
def clock(monkeypatch):
    now = datetime(2026, 11, 18, 12, 1, tzinfo=UTC)
    monkeypatch.setattr(auth, "utcnow", lambda: now)
    return now


async def make(email: str, name: str, roles=(), is_active: bool = True) -> uuid.UUID:
    return await service.create_user(
        email=email, name=name, password=PASSWORD, roles=list(roles), is_active=is_active
    )


@pytest.fixture
async def admin(identity_db):
    return await make(ADMIN, "Kari Admin", [AccountRole.admin])


async def as_user(c, email: str = ADMIN):
    assert (await login(c, email, PASSWORD)).status_code == 200


async def grant(c, user_id, role: str = "lecturer"):
    return await c.post(f"/api/admin/users/{user_id}/roles", json={"role": role}, headers=CSRF)


async def revoke(c, user_id, role: str = "lecturer"):
    return await c.delete(f"/api/admin/users/{user_id}/roles/{role}", headers=CSRF)


def audit_rows() -> list[tuple]:
    return rows("SELECT actor_user_id, action, target_ids, change, occurred_at FROM audit_events")


def roles_in_db(user_id) -> list[str]:
    return [
        r for (r,) in rows("SELECT role FROM user_roles WHERE user_id = %s ORDER BY role", user_id)
    ]


async def test_the_list_shows_users_by_name_with_roles_and_status(admin):
    bard = await make("bard@example.com", "bård Hansen", [AccountRole.lecturer, AccountRole.admin])
    anne = await make("anne@example.com", "Anne Uten", is_active=False)
    async with client() as c:
        await as_user(c)
        response = await c.get("/api/admin/users")
    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": str(anne),
                "name": "Anne Uten",
                "email": "anne@example.com",
                "roles": [],
                "is_active": False,
            },
            {
                "id": str(bard),
                "name": "bård Hansen",
                "email": "bard@example.com",
                "roles": ["admin", "lecturer"],
                "is_active": True,
            },
            {
                "id": str(admin),
                "name": "Kari Admin",
                "email": ADMIN,
                "roles": ["admin"],
                "is_active": True,
            },
        ],
        "next_cursor": None,
    }


async def test_the_list_pages_by_cursor_without_repeats(admin):
    # "Bo" and "bo" tie on the sort name: the id breaks the tie at a page boundary.
    for i, name in enumerate(["Eva", "Dag", "bo", "Bo"]):
        await make(f"u{i}@example.com", name)
    seen: list[str] = []
    pages = []
    cursor = None
    async with client() as c:
        await as_user(c)
        while True:
            params = {"limit": 2} | ({"cursor": cursor} if cursor else {})
            body = (await c.get("/api/admin/users", params=params)).json()
            pages.append(len(body["items"]))
            seen += [item["name"] for item in body["items"]]
            cursor = body["next_cursor"]
            if cursor is None:
                break
    assert pages == [2, 2, 1]
    assert sorted(seen[:2]) == ["Bo", "bo"]
    assert seen[2:] == ["Dag", "Eva", "Kari Admin"]


# The last one decodes to an id, but of no User.
@pytest.mark.parametrize("cursor", ["!!!", "abc", "x" * 64, "AAAAAAAAAAAAAAAAAAAAAA"])
async def test_a_cursor_the_api_did_not_hand_out_is_refused(admin, cursor):
    async with client() as c:
        await as_user(c)
        response = await c.get("/api/admin/users", params={"cursor": cursor})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


@pytest.mark.parametrize(
    ("q", "names"),
    [
        (" KARI ", ["Kari Admin"]),
        ("example.com", ["Bård Hansen", "Kari Admin"]),
        ("ård", ["Bård Hansen"]),
        ("%", ["Pro%sent"]),
        ("_", ["a_b"]),
        ("\\", ["c\\d"]),
        ("ingen-slik", []),
    ],
)
async def test_the_search_matches_part_of_the_email_or_the_name(admin, q, names):
    await make("bard@example.com", "Bård Hansen", [AccountRole.lecturer])
    await make("p@example.org", "Pro%sent")
    await make("q@example.org", "a_b")
    await make("r@example.org", "c\\d")
    async with client() as c:
        await as_user(c)
        response = await c.get("/api/admin/users", params={"q": q})
    assert response.status_code == 200
    assert [item["name"] for item in response.json()["items"]] == names


async def test_the_search_text_is_never_logged(admin):
    async with client() as c:
        await as_user(c)
        with capture_logs() as logs:
            response = await c.get("/api/admin/users", params={"q": "hemmelig-søk"})
    assert response.status_code == 200
    assert logs, "the request is logged"
    assert "hemmelig" not in json.dumps(logs, default=str)


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"q": "x" * 201}])
async def test_a_page_size_or_search_out_of_range_is_refused_without_echo(admin, params):
    async with client() as c:
        await as_user(c)
        with capture_logs() as logs:
            response = await c.get("/api/admin/users", params=params)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert "x" * 50 not in response.text
    assert "x" * 50 not in json.dumps(logs, default=str)


async def test_the_default_page_holds_fifty_users(admin):
    for i in range(50):
        await service.create_user(email=f"n{i:02}@example.com", name=f"N{i:02}", password=PASSWORD)
    async with client() as c:
        await as_user(c)
        body = (await c.get("/api/admin/users")).json()
    assert len(body["items"]) == 50
    assert body["next_cursor"] is not None


async def test_only_an_admin_reaches_the_list_and_the_roles(admin):
    lecturer = await make("bard@example.com", "Bård", [AccountRole.lecturer])
    async with client() as c:
        assert (await c.get("/api/admin/users")).status_code == 401
        await as_user(c, "bard@example.com")
        assert (await c.get("/api/admin/users")).status_code == 403
        assert (await grant(c, lecturer, "admin")).status_code == 403
        assert (await revoke(c, admin, "admin")).status_code == 403
    assert roles_in_db(lecturer) == ["lecturer"]
    assert audit_rows() == []


async def test_a_grant_is_stored_audited_emitted_and_held_at_the_next_request(
    admin, clock, identity_db
):
    bard = await make("bard@example.com", "Bård", [AccountRole.admin])
    async with client() as admin_c, client() as bard_c:
        await as_user(admin_c)
        await as_user(bard_c, "bard@example.com")
        assert (await bard_c.get("/api/auth/me")).json()["user"]["roles"] == ["admin"]
        with psycopg.connect(libpq_dsn(identity_db), autocommit=True) as listen:
            listen.execute(f"LISTEN {events.CHANNEL}")
            response = await grant(admin_c, bard)
            received = [json.loads(n.payload) for n in listen.notifies(timeout=2, stop_after=1)]
        me = (await bard_c.get("/api/auth/me")).json()["user"]
    assert response.status_code == 200
    assert response.json() == {
        "id": str(bard),
        "name": "Bård",
        "email": "bard@example.com",
        "roles": ["admin", "lecturer"],
        "is_active": True,
    }
    assert received == [{"topic": "user", "id": str(bard), "version": None}]
    assert {item["topic"] for item in received} == COMMAND_TOPICS["identity.grant_role"]
    assert me["roles"] == ["admin", "lecturer"]
    assert audit_rows() == [
        (admin, "role.granted", {"user_id": str(bard)}, {"role": "lecturer"}, clock)
    ]


async def test_granting_a_held_role_changes_and_writes_nothing(admin):
    bard = await make("bard@example.com", "Bård", [AccountRole.lecturer])
    async with client() as c:
        await as_user(c)
        response = await grant(c, bard)
    assert response.status_code == 200
    assert response.json()["roles"] == ["lecturer"]
    assert audit_rows() == []


async def test_a_revoke_is_audited_emitted_and_ends_access_at_the_next_request(
    admin, clock, identity_db
):
    bard = await make("bard@example.com", "Bård", [AccountRole.admin, AccountRole.lecturer])
    async with client() as admin_c, client() as bard_c:
        await as_user(admin_c)
        await as_user(bard_c, "bard@example.com")
        assert (await bard_c.get("/api/admin/users")).status_code == 200
        with psycopg.connect(libpq_dsn(identity_db), autocommit=True) as listen:
            listen.execute(f"LISTEN {events.CHANNEL}")
            response = await revoke(admin_c, bard, "admin")
            received = [json.loads(n.payload) for n in listen.notifies(timeout=2, stop_after=1)]
        assert (await bard_c.get("/api/admin/users")).status_code == 403
        assert (await bard_c.get("/api/auth/me")).json()["user"]["roles"] == ["lecturer"]
    assert response.status_code == 200
    assert response.json()["roles"] == ["lecturer"]
    assert received == [{"topic": "user", "id": str(bard), "version": None}]
    assert {item["topic"] for item in received} == COMMAND_TOPICS["identity.revoke_role"]
    assert audit_rows() == [
        (admin, "role.revoked", {"user_id": str(bard)}, {"role": "admin"}, clock)
    ]


async def test_revoking_a_role_not_held_changes_and_writes_nothing(admin):
    bard = await make("bard@example.com", "Bård")
    async with client() as c:
        await as_user(c)
        response = await revoke(c, bard)
    assert response.status_code == 200
    assert response.json()["roles"] == []
    assert audit_rows() == []


async def test_the_last_active_admin_cannot_revoke_their_own_admin_role(admin):
    # A deactivated Admin does not count as another Admin.
    await make("gammel@example.com", "Gammel Admin", [AccountRole.admin], is_active=False)
    async with client() as c:
        await as_user(c)
        response = await revoke(c, admin, "admin")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "last_admin"
    assert roles_in_db(admin) == ["admin"]
    assert audit_rows() == []


async def test_an_admin_may_revoke_their_own_admin_role_while_another_is_active(admin):
    await make("bard@example.com", "Bård", [AccountRole.admin])
    async with client() as c:
        await as_user(c)
        response = await revoke(c, admin, "admin")
        assert response.status_code == 200
        # The next request is held to the change.
        assert (await c.get("/api/admin/users")).status_code == 403
    assert roles_in_db(admin) == []


async def test_a_deactivated_admin_loses_the_role_even_with_no_other_active_holder(admin):
    gammel = await make("gammel@example.com", "Gammel", [AccountRole.admin], is_active=False)
    async with client() as c:
        await as_user(c)
        response = await revoke(c, gammel, "admin")
    assert response.status_code == 200
    assert roles_in_db(gammel) == []


async def test_two_admins_revoking_each_other_at_once_leave_one_admin(admin, monkeypatch):
    bard = await make("bard@example.com", "Bård", [AccountRole.admin])
    # A blocker that holds each revoke, after its count, until the other has counted too (or a
    # short wait ends). Without the role lock both counts see one other Admin and both revokes
    # go through; with it the second count waits for the first commit.
    inside: list[uuid.UUID] = []
    both_inside = asyncio.Event()

    async def hold(session, user_id):
        inside.append(user_id)
        if len(inside) == 2:
            both_inside.set()
        try:
            await asyncio.wait_for(both_inside.wait(), timeout=0.3)
        except TimeoutError:
            pass
        return 0

    monkeypatch.setattr(service, "_REVOKE_BLOCKERS", {})
    service.register_revoke_blocker(AccountRole.admin, hold)
    async with client() as kari_c, client() as bard_c:
        await as_user(kari_c)
        await as_user(bard_c, "bard@example.com")
        answers = await asyncio.gather(
            revoke(kari_c, bard, "admin"), revoke(bard_c, admin, "admin")
        )
    assert sorted(a.status_code for a in answers) == [200, 409]
    assert rows("SELECT count(*) FROM user_roles WHERE role = 'admin'") == [(1,)]
    assert len(audit_rows()) == 1


async def test_a_revoke_blocker_keeps_the_lecturer_role_and_names_the_count(admin, monkeypatch):
    bard = await make("bard@example.com", "Bård", [AccountRole.lecturer, AccountRole.admin])
    asked: list[uuid.UUID] = []

    async def owns_two(session, user_id):
        asked.append(user_id)
        return 2

    monkeypatch.setattr(service, "_REVOKE_BLOCKERS", {})
    service.register_revoke_blocker(AccountRole.lecturer, owns_two)
    async with client() as c:
        await as_user(c)
        blocked = await revoke(c, bard)
        other_role = await revoke(c, bard, "admin")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "role_revoke_blocked"
    assert blocked.json()["error"]["fields"] == {"classes": 2}
    assert asked == [bard]  # the Admin revoke asks no Lecturer blocker
    assert other_role.status_code == 200
    assert roles_in_db(bard) == ["lecturer"]
    assert [row[1] for row in audit_rows()] == ["role.revoked"]


async def test_a_blocker_reporting_nothing_lets_the_revoke_through(admin, monkeypatch):
    bard = await make("bard@example.com", "Bård", [AccountRole.lecturer])

    async def owns_none(session, user_id):
        return 0

    async def owns_negative(session, user_id):
        return -3

    monkeypatch.setattr(service, "_REVOKE_BLOCKERS", {})
    service.register_revoke_blocker(AccountRole.lecturer, owns_none)
    service.register_revoke_blocker(AccountRole.lecturer, owns_negative)
    async with client() as c:
        await as_user(c)
        assert (await revoke(c, bard)).status_code == 200
    assert roles_in_db(bard) == []


async def test_a_negative_count_cannot_cancel_another_blocker(admin, monkeypatch):
    bard = await make("bard@example.com", "Bård", [AccountRole.lecturer])

    async def owns_two(session, user_id):
        return 2

    async def owns_negative(session, user_id):
        return -3

    monkeypatch.setattr(service, "_REVOKE_BLOCKERS", {})
    service.register_revoke_blocker(AccountRole.lecturer, owns_two)
    service.register_revoke_blocker(AccountRole.lecturer, owns_negative)
    async with client() as c:
        await as_user(c)
        response = await revoke(c, bard)
    assert response.status_code == 409
    assert response.json()["error"]["fields"] == {"classes": 2}


async def test_an_unknown_user_or_role_is_refused(admin):
    async with client() as c:
        await as_user(c)
        missing = uuid.uuid7()
        for response in (await grant(c, missing), await revoke(c, missing)):
            assert response.status_code == 404
            assert response.json()["error"]["code"] == "not_found"
        assert (await grant(c, admin, "student")).status_code == 422
        assert (await revoke(c, admin, "student")).status_code == 422
        assert (await revoke(c, "ikke-en-id")).status_code == 422
    assert audit_rows() == []
