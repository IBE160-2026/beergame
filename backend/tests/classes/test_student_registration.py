"""Registering as a Student through a Student Invitation (Story 4.5, FR-1, FR-4, FR-5, FR-7,
FR-8, FR-9, AD-11, AD-12, AD-17): Â«Du er invitertÂ» for a Student link, the one acceptance
transaction, an existing account joining, used and expired links, the Student scope and the local
demo Students. The api's clock is fixed (2026-11-19 09:00 UTC, 10:00 in Oslo) and moved by the
test; the database clock is never read, and nothing is ordered by a timestamp."""

import uuid
from datetime import UTC, datetime

import pytest

from app.modules.classes import seed
from app.modules.identity import service
from app.platform import auth, events
from app.platform.config import get_settings
from tests.classes.test_classes import OTHER, PASSWORD, as_user, make
from tests.classes.test_roster_send import send, staged_id
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.identity.helpers import CSRF, client, login
from tests.messaging.helpers import rows

__all__ = ["clock", "klass"]  # fixtures from `test_roster_upload`

NEW_PASSWORD = "mitt-nye-passord"


@pytest.fixture(autouse=True)
def _empty_mail(mail_db):
    """The mail tables empty, before `klass` makes its Users."""


@pytest.fixture
def emitted(monkeypatch) -> list[tuple]:
    """Every `events.emit` call, still emitted."""
    calls: list[tuple] = []
    original = events.emit

    async def spy(session, topic, item_id, version=None):
        calls.append((topic, item_id))
        await original(session, topic, item_id, version)

    monkeypatch.setattr(events, "emit", spy)
    return calls


async def invite(class_id: str, *addresses: str, valid_days: int = 14) -> dict[str, str]:
    """Send Student Invitations to the Class as its owner; address â†’ link token."""
    async with client() as c:
        await as_user(c)
        response = await send(
            c, class_id, await staged_id(c, class_id, " ".join(addresses)), valid_days
        )
    assert response.status_code == 201
    found = rows(
        "SELECT email, id FROM invitations WHERE kind = 'student' AND class_id = %s", class_id
    )
    return {email: auth.link_token(service.INVITATION, inv_id) for email, inv_id in found}


async def second_class(name: str = "class-of-1995") -> str:
    async with client() as c:
        await as_user(c)
        [institution] = rows("SELECT id FROM institutions")
        created = await c.post(
            "/api/classes", json={"name": name, "institution_id": str(institution[0])}, headers=CSRF
        )
    return created.json()["id"]


async def check(c, token: str):
    return await c.post("/api/auth/invitation/check", json={"token": token}, headers=CSRF)


async def accept(c, token: str, name: str = " Ola  Nordmann ", password: str = NEW_PASSWORD):
    body = {"token": token, "name": name, "password": password}
    return await c.post("/api/auth/invitation/accept", json=body, headers=CSRF)


async def accept_login(c, token: str, password: str):
    return await c.post(
        "/api/auth/invitation/accept-login",
        json={"token": token, "password": password},
        headers=CSRF,
    )


def entry(email: str) -> tuple:
    return rows(
        "SELECT registration, user_id, removed_at, class_id FROM roster_entries WHERE email = %s",
        email,
    )


def users(email: str) -> list[tuple]:
    return rows("SELECT id FROM users WHERE email = %s", email)


def set_clock(monkeypatch, when: datetime) -> None:
    monkeypatch.setattr(auth, "utcnow", lambda: when)


async def test_a_student_link_names_the_class_the_lecturer_and_the_days_left(klass):
    rows("UPDATE classes SET course_code = 'IBE160' RETURNING id")
    tokens = await invite(klass, "ola@x.no")
    async with client() as c:
        response = await check(c, tokens["ola@x.no"])
    assert response.status_code == 200
    assert response.json() == {
        "kind": "student",
        "email": "ola@x.no",
        "role": None,
        "valid_days": 14,
        "has_account": False,
        "class_name": "class-of-1994",
        "course_code": "IBE160",
        "invited_by": "Bard",
    }


async def test_the_days_left_count_down_to_one_on_the_last_day(klass, monkeypatch):
    tokens = await invite(klass, "ola@x.no", valid_days=3)
    days = []
    for when in (
        datetime(2026, 11, 20, 22, 59, tzinfo=UTC),  # 23:59 on the 20th in Oslo
        datetime(2026, 11, 22, 22, 59, tzinfo=UTC),  # the last day, 22 November
    ):
        set_clock(monkeypatch, when)
        async with client() as c:
            days.append((await check(c, tokens["ola@x.no"])).json()["valid_days"])
    assert days == [2, 1]


async def test_accepting_creates_the_student_links_the_roster_and_logs_in(klass, emitted):
    tokens = await invite(klass, "ola@x.no")
    async with client() as c:
        response = await accept(c, tokens["ola@x.no"])
        me = await c.get("/api/auth/me")
        enrolled = await c.get("/api/classes/enrolled")
    assert response.status_code == 200
    user = response.json()["user"]
    assert (user["email"], user["name"], user["roles"]) == ("ola@x.no", "Ola Nordmann", [])
    assert me.json()["user"]["id"] == user["id"]
    [(registration, user_id, removed, class_id)] = entry("ola@x.no")
    assert (registration, str(user_id), removed, str(class_id)) == (
        "registered",
        user["id"],
        None,
        klass,
    )
    assert rows("SELECT accepted_at FROM invitations") == [(NOW,)]
    assert rows("SELECT count(*) FROM user_roles WHERE user_id = %s", user["id"]) == [(0,)]
    assert ("user", user["id"]) in emitted
    assert enrolled.json() == {
        "items": [{"id": klass, "name": "class-of-1994", "course_code": None}]
    }
    async with client() as c:
        again = await accept(c, tokens["ola@x.no"])
    assert again.status_code == 410 and again.json()["error"]["code"] == "invitation_link_invalid"
    assert len(users("ola@x.no")) == 1


async def test_an_existing_account_joins_with_its_password_and_no_second_user(klass, emitted):
    other_class = await second_class()
    first = await invite(klass, "ola@x.no")
    async with client() as c:
        assert (await accept(c, first["ola@x.no"])).status_code == 200
    second = await invite(other_class, "ola@x.no")
    async with client() as c:
        checked = await check(c, second["ola@x.no"])
        made = await accept(c, second["ola@x.no"])
        joined = await accept_login(c, second["ola@x.no"], NEW_PASSWORD)
        enrolled = await c.get("/api/classes/enrolled")
    assert checked.json()["has_account"] is True
    assert made.status_code == 409 and made.json()["error"]["code"] == "account_exists"
    assert joined.status_code == 200
    [(user_id,)] = users("ola@x.no")
    assert joined.json()["user"]["id"] == str(user_id)
    assert {(r[0], r[1]) for r in entry("ola@x.no")} == {("registered", user_id)}
    assert [item["name"] for item in enrolled.json()["items"]] == ["class-of-1994", "class-of-1995"]
    assert emitted.count(("user", str(user_id))) == 2


async def test_a_lecturer_joining_as_student_keeps_the_role(klass):
    tokens = await invite(klass, OTHER)
    async with client() as c:
        wrong = await accept_login(c, tokens[OTHER], "feil-passord")
        joined = await accept_login(c, tokens[OTHER], PASSWORD)
    assert wrong.status_code == 401 and wrong.json()["error"]["code"] == "invalid_credentials"
    assert joined.status_code == 200
    assert joined.json()["user"]["roles"] == ["lecturer"]
    assert entry(OTHER)[0][0] == "registered"


async def test_an_expired_or_used_link_is_refused_and_can_ask_for_a_new_one(klass, monkeypatch):
    tokens = await invite(klass, "ola@x.no", "kari@x.no", valid_days=1)
    async with client() as c:
        assert (await accept(c, tokens["kari@x.no"])).status_code == 200
    set_clock(monkeypatch, datetime(2026, 11, 20, 23, 0, tzinfo=UTC))  # midnight after the 20th
    async with client() as c:
        expired = await check(c, tokens["ola@x.no"])
        refused = await accept(c, tokens["ola@x.no"])
        used = await check(c, tokens["kari@x.no"])
        renewal = await c.post(
            "/api/auth/invitation/renewal", json={"token": tokens["ola@x.no"]}, headers=CSRF
        )
        used_renewal = await c.post(
            "/api/auth/invitation/renewal", json={"token": tokens["kari@x.no"]}, headers=CSRF
        )
    assert {expired.status_code, refused.status_code, used.status_code} == {410}
    assert (renewal.status_code, used_renewal.status_code) == (202, 202)
    assert users("ola@x.no") == [] and entry("ola@x.no")[0][:2] == ("invited", None)
    marked = rows(
        "SELECT e.email FROM invitations i JOIN roster_entries e ON e.id = i.roster_entry_id "
        "WHERE i.renewal_requested_at IS NOT NULL"
    )
    assert marked == [("ola@x.no",)]


async def test_a_removed_roster_address_or_a_voided_link_cannot_register(klass):
    tokens = await invite(klass, "ola@x.no", "kari@x.no")
    rows("UPDATE roster_entries SET removed_at = %s WHERE email = 'ola@x.no' RETURNING id", NOW)
    rows("UPDATE invitations SET voided_at = %s WHERE email = 'kari@x.no' RETURNING id", NOW)
    async with client() as c:
        answers = [
            await call(c, tokens[address])
            for address in ("ola@x.no", "kari@x.no")
            for call in (check, accept)
        ]
    assert [a.status_code for a in answers] == [410] * 4
    assert users("ola@x.no") == [] and users("kari@x.no") == []


async def test_an_address_removed_while_the_form_is_open_leaves_nothing_behind(klass, monkeypatch):
    tokens = await invite(klass, "ola@x.no")
    real_check = service.check_invitation

    async def check_then_remove(token, *, now):
        checked = await real_check(token, now=now)
        rows("UPDATE roster_entries SET removed_at = %s RETURNING id", NOW)
        return checked

    monkeypatch.setattr(service, "check_invitation", check_then_remove)
    async with client() as c:
        accepted = await accept(c, tokens["ola@x.no"])
    assert accepted.status_code == 410
    assert users("ola@x.no") == []
    assert rows("SELECT accepted_at FROM invitations") == [(None,)]


async def test_an_address_removed_while_logging_in_leaves_nothing_behind(klass, monkeypatch):
    tokens = await invite(klass, OTHER)  # an existing account, as for the Lecturer joining above
    real_check = service.check_invitation

    async def check_then_remove(token, *, now):
        checked = await real_check(token, now=now)
        rows("UPDATE roster_entries SET removed_at = %s RETURNING id", NOW)
        return checked

    monkeypatch.setattr(service, "check_invitation", check_then_remove)
    async with client() as c:
        joined = await accept_login(c, tokens[OTHER], PASSWORD)
    assert joined.status_code == 410
    assert joined.json()["error"]["code"] == "invitation_link_invalid"
    assert rows("SELECT accepted_at FROM invitations") == [(None,)]
    assert entry(OTHER)[0][:2] == ("invited", None)


async def test_student_acceptance_is_rate_limited_per_link(klass, monkeypatch):
    monkeypatch.setenv("INVITATION_ACCEPT_RATE_LIMIT_PER_INVITATION", "2")
    get_settings.cache_clear()
    tokens = await invite(klass, "ola@x.no")
    async with client() as c:
        await accept_login(c, tokens["ola@x.no"], "x")
        await accept_login(c, tokens["ola@x.no"], "x")
        third = await accept(c, tokens["ola@x.no"])
    get_settings.cache_clear()
    assert third.status_code == 429 and int(third.headers["Retry-After"]) > 0
    assert users("ola@x.no") == []


async def test_a_student_reads_only_their_own_classes(klass):
    other_class = await second_class()
    tokens = await invite(klass, "ola@x.no")
    async with client() as c:
        await accept(c, tokens["ola@x.no"])
        own = await c.get(f"/api/classes/enrolled/{klass}")
        foreign = await c.get(f"/api/classes/enrolled/{other_class}")
        unknown = await c.get(f"/api/classes/enrolled/{uuid.uuid4()}")
        malformed = await c.get("/api/classes/enrolled/ikke-en-id")
        staff_view = await c.get(f"/api/classes/{klass}")
    assert own.status_code == 200 and own.json()["name"] == "class-of-1994"
    for refused in (foreign, unknown, malformed, staff_view):
        assert refused.status_code == 403 and refused.json()["error"]["code"] == "forbidden"
    async with client() as c:
        assert (await c.get("/api/classes/enrolled")).status_code == 401
        await as_user(c)  # the owner is staff, not a Student, of the Class
        assert (await c.get("/api/classes/enrolled")).json() == {"items": []}
        assert (await c.get(f"/api/classes/enrolled/{klass}")).status_code == 403


async def test_a_removed_student_loses_the_class_but_keeps_the_account_and_other_classes(klass):
    other_class = await second_class()
    first = await invite(klass, "ola@x.no")
    async with client() as c:
        await accept(c, first["ola@x.no"])
    second = await invite(other_class, "ola@x.no")
    async with client() as c:
        await accept_login(c, second["ola@x.no"], NEW_PASSWORD)
    rows("UPDATE roster_entries SET removed_at = %s WHERE class_id = %s RETURNING id", NOW, klass)
    async with client() as c:
        assert (await login(c, "ola@x.no", NEW_PASSWORD)).status_code == 200
        gone = await c.get(f"/api/classes/enrolled/{klass}")
        kept = await c.get(f"/api/classes/enrolled/{other_class}")
        listed = await c.get("/api/classes/enrolled")
    assert gone.status_code == 403 and kept.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [other_class]


async def test_local_seeds_eight_registered_demo_students_once(identity_db, monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    assert await seed.ensure_demo_students() == 0  # no demo Class yet
    await make(seed.DEMO_LECTURER)
    existing = await make("student@example.com", roles=())
    assert await seed.ensure_demo_class() is True
    assert await seed.ensure_demo_students() == 8
    assert await seed.ensure_demo_students() == 0
    seeded = rows(
        "SELECT e.email, e.registration, e.user_id = u.id FROM roster_entries e "
        "JOIN users u ON u.email = e.email"
    )
    assert sorted(seeded) == sorted(
        [(email, "registered", True) for email, _ in seed.DEMO_STUDENTS]
    )
    assert users("student@example.com") == [(existing,)]  # reused, not changed
    assert rows("SELECT name FROM users WHERE email = 'student@example.com'") == [("Student",)]
    async with client() as c:
        assert (await login(c, "student8@example.com", seed.DEMO_PASSWORD)).status_code == 200
        [item] = (await c.get("/api/classes/enrolled")).json()["items"]
    assert (item["name"], item["course_code"]) == ("class-of-1994", "IBE160")


@pytest.mark.parametrize("env", ["test", "production"])
async def test_no_demo_students_outside_local(identity_db, monkeypatch, env):
    from tests.conftest import enter_production

    monkeypatch.setenv("APP_ENV", "local")
    await make(seed.DEMO_LECTURER)
    await seed.ensure_demo_class()
    if env == "production":
        enter_production(monkeypatch)
        monkeypatch.setenv("DATABASE_URL", identity_db)
    else:
        monkeypatch.setenv("APP_ENV", env)
    get_settings.cache_clear()
    assert await seed.ensure_demo_students() == 0
    assert rows("SELECT count(*) FROM roster_entries") == [(0,)]
