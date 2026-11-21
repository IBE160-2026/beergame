"""Creating and reading Classes through the api, the Class scope of `platform/authz`, the Lecturer
revoke blocker and the local demo Class (Story 4.1, FR-2, FR-5, FR-6, AD-12, AD-17). The api's
clock is fixed; the database clock is never read."""

import uuid
from datetime import UTC, datetime

import pytest
import structlog.testing
from sqlalchemy import select

from app.modules.classes import seed
from app.modules.classes.models import classes
from app.modules.identity import service
from app.modules.identity.schemas import AccountRole
from app.platform import auth
from app.platform.db import get_sessionmaker
from tests.conftest import enter_production
from tests.identity.helpers import CSRF, client, login
from tests.messaging.helpers import rows

PASSWORD = "hemmelig-passord"
LECTURER = "bard@example.com"
OTHER = "kari@example.com"
NOW = datetime(2026, 11, 18, 12, 1, tzinfo=UTC)


@pytest.fixture
def clock(monkeypatch):
    monkeypatch.setattr(auth, "utcnow", lambda: NOW)


async def make(email: str, roles=(AccountRole.lecturer,)) -> uuid.UUID:
    return await service.create_user(
        email=email, name=email.split("@")[0].title(), password=PASSWORD, roles=list(roles)
    )


async def institution(name: str = "USN Bø") -> uuid.UUID:
    created = await service.create_institution(None, name, now=NOW)  # type: ignore[arg-type]
    return created.id


@pytest.fixture
async def setup(identity_db, clock):
    return {"lecturer": await make(LECTURER), "institution": await institution()}


async def as_user(c, email: str = LECTURER):
    """Sign `c` in as `email`: the cookie a login would set, issued here without the login
    request and its rate-limit and password work (the login is tested in
    `tests/identity/test_login.py`). An address no login would accept, not an active User with a
    password, goes through the login, so the assertion shows the refusal."""
    found = rows(
        "SELECT id, session_version FROM users "
        "WHERE email = %s AND is_active AND password_hash IS NOT NULL",
        service.normalise_email(email),
    )
    if not found:
        assert (await login(c, email, PASSWORD)).status_code == 200
        return
    [(user_id, version)] = found
    token = auth.issue_token(user_id, auth.utcnow(), session_version=version)
    c.cookies.set(auth.COOKIE_NAME, token, domain=SESSION_COOKIE_DOMAIN)


SESSION_COOKIE_DOMAIN = "t.local"
"""Where the cookie jar keeps the login's host-only cookie for the test client's `https://t`."""


async def create(c, **body):
    return await c.post("/api/classes", json=body, headers=CSRF)


def stored() -> list[tuple]:
    return rows("SELECT name, course_code, institution_id, created_at, archived_at FROM classes")


def staff() -> list[tuple]:
    return rows("SELECT class_id, user_id, role, added_at FROM class_staff")


async def test_creating_stores_the_class_and_its_owner(setup):
    async with client() as c:
        await as_user(c)
        response = await create(
            c,
            name="  class-of-1994 ",
            institution_id=str(setup["institution"]),
            course_code=" IBE160 ",
        )
    assert response.status_code == 201
    body = response.json()
    assert (body["name"], body["course_code"], body["institution_name"]) == (
        "class-of-1994",
        "IBE160",
        "USN Bø",
    )
    assert (body["staff_role"], body["archived"]) == ("owner", False)
    assert stored() == [("class-of-1994", "IBE160", setup["institution"], NOW, None)]
    assert staff() == [(uuid.UUID(body["id"]), setup["lecturer"], "owner", NOW)]


@pytest.mark.parametrize("code", [None, "", "   "])
async def test_a_class_needs_no_course_code(setup, code):
    async with client() as c:
        await as_user(c)
        body = {"name": "a   b", "institution_id": str(setup["institution"])}
        if code is not None:
            body["course_code"] = code
        response = await create(c, **body)
    assert response.status_code == 201
    assert (response.json()["name"], response.json()["course_code"]) == ("a b", None)
    assert stored()[0][:2] == ("a b", None)


@pytest.mark.parametrize(
    ("body", "fields"),
    [
        ({}, {"name": "name_empty", "institution_id": "institution_missing"}),
        (
            {"name": "  ", "institution_id": None},
            {"name": "name_empty", "institution_id": "institution_missing"},
        ),
        ({"name": "x" * 201, "known": True}, {"name": "name_too_long"}),
        ({"name": "a\u0007b", "known": True}, {"name": "name_invalid"}),
        (
            {"name": "Ok", "institution_id": str(uuid.uuid4())},
            {"institution_id": "institution_unknown"},
        ),
        (
            {"name": "Ok", "known": True, "course_code": "C" * 51},
            {"course_code": "course_code_too_long"},
        ),
        (
            {"name": "Ok", "known": True, "course_code": "A\u0000"},
            {"course_code": "course_code_invalid"},
        ),
    ],
)
async def test_a_refused_field_is_named_and_nothing_is_stored(setup, body, fields):
    if body.pop("known", False):
        body["institution_id"] = str(setup["institution"])
    async with client() as c:
        await as_user(c)
        response = await create(c, **body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert response.json()["error"]["fields"] == fields
    assert stored() == []
    assert staff() == []


async def test_the_list_holds_only_the_users_own_classes_by_name(setup):
    await make(OTHER)
    async with client() as c, client() as other:
        await as_user(c)
        await as_user(other, OTHER)
        for name in ("beta", "Alfa"):
            await create(c, name=name, institution_id=str(setup["institution"]))
        await create(other, name="Kari sin", institution_id=str(setup["institution"]))
        mine = (await c.get("/api/classes")).json()["items"]
        theirs = (await other.get("/api/classes")).json()["items"]
    assert [(item["name"], item["course_code"]) for item in mine] == [
        ("Alfa", None),
        ("beta", None),
    ]
    assert [item["name"] for item in theirs] == ["Kari sin"]


async def test_a_foreign_unknown_or_malformed_class_is_the_same_refusal(setup):
    await make(OTHER)
    async with client() as c, client() as other:
        await as_user(c)
        await as_user(other, OTHER)
        own = (await create(c, name="Min", institution_id=str(setup["institution"]))).json()
        assert (await c.get(f"/api/classes/{own['id']}")).json()["name"] == "Min"
        answers = [
            await other.get(f"/api/classes/{own['id']}"),
            await other.get(f"/api/classes/{uuid.uuid4()}"),
            await other.get("/api/classes/ikke-en-id"),
        ]
    assert {(a.status_code, a.json()["error"]["code"]) for a in answers} == {(403, "forbidden")}
    assert len({a.text for a in answers}) == 1


@pytest.mark.parametrize("roles", [(AccountRole.admin,), ()])
async def test_only_a_lecturer_reaches_the_classes(setup, roles):
    await make(OTHER, roles)
    async with client() as c:
        await as_user(c, OTHER)
        answers = [
            await c.get("/api/classes"),
            await c.get("/api/classes/institutions"),
            await create(c, name="X", institution_id=str(setup["institution"])),
        ]
    assert [a.status_code for a in answers] == [403, 403, 403]
    assert stored() == []


async def test_the_institution_choices_are_every_institution_by_name(setup):
    await institution("alfa")
    async with client() as c:
        await as_user(c)
        response = await c.get("/api/classes/institutions")
    assert [item["name"] for item in response.json()["items"]] == ["alfa", "USN Bø"]


async def test_revoking_the_lecturer_role_of_an_owner_is_blocked_with_the_count(setup):
    await make("admin@example.com", (AccountRole.admin,))
    async with client() as lecturer, client() as admin_c:
        await as_user(lecturer)
        await create(lecturer, name="Min", institution_id=str(setup["institution"]))
        await as_user(admin_c, "admin@example.com")
        blocked = await admin_c.delete(
            f"/api/admin/users/{setup['lecturer']}/roles/lecturer", headers=CSRF
        )
        assert blocked.status_code == 409
        assert blocked.json()["error"]["code"] == "role_revoke_blocked"
        assert blocked.json()["error"]["fields"] == {"classes": 1}
        assert rows("SELECT role FROM user_roles WHERE user_id = %s", setup["lecturer"]) == [
            ("lecturer",)
        ]
        # An archived Class keeps nothing: the revoke goes through.
        assert len(rows("UPDATE classes SET archived_at = %s RETURNING id", NOW)) == 1
        allowed = await admin_c.delete(
            f"/api/admin/users/{setup['lecturer']}/roles/lecturer", headers=CSRF
        )
    assert allowed.status_code == 200


async def test_local_seeds_one_demo_class_for_the_demo_lecturer_once(identity_db, monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    assert await seed.ensure_demo_class() is False  # no demo Lecturer yet
    lecturer = await make(seed.DEMO_LECTURER)
    assert await seed.ensure_demo_class() is True
    assert await seed.ensure_demo_class() is False
    [(name, code, institution_id, _, archived)] = stored()
    assert (name, code, archived) == ("class-of-1994", "IBE160", None)
    assert rows("SELECT name FROM institutions WHERE id = %s", institution_id) == [
        ("Demohøgskolen",)
    ]
    assert [(row[1], row[2]) for row in staff()] == [(lecturer, "owner")]


async def test_the_seed_reuses_an_institution_with_the_demo_name_in_any_case(
    identity_db, monkeypatch
):
    monkeypatch.setenv("APP_ENV", "local")
    existing = await institution("DEMOHØGSKOLEN")
    await make(seed.DEMO_LECTURER)
    assert await seed.ensure_demo_class() is True
    assert stored()[0][2] == existing
    assert rows("SELECT count(*) FROM institutions") == [(1,)]


@pytest.mark.parametrize("env", ["test", "production"])
async def test_no_demo_class_outside_local(identity_db, monkeypatch, env):
    if env == "production":
        enter_production(monkeypatch)
        monkeypatch.setenv("DATABASE_URL", identity_db)
    else:
        monkeypatch.setenv("APP_ENV", env)
    await make(seed.DEMO_LECTURER)
    assert await seed.ensure_demo_class() is False
    async with get_sessionmaker().begin() as s:
        assert (await s.execute(select(classes))).first() is None


async def test_a_database_error_while_seeding_is_logged_not_raised(monkeypatch):
    from sqlalchemy.exc import DBAPIError

    async def fail():
        raise DBAPIError("SELECT", {}, ConnectionError("down"))

    monkeypatch.setattr(seed, "ensure_demo_class", fail)
    with structlog.testing.capture_logs() as logs:
        await seed.ensure_demo_class_logged()
    assert [(e["event"], e["error_code"]) for e in logs] == [("demo_class_failed", "db_error")]
