"""`platform/authz` (Story 3.3, AD-12, FR-2, FR-5): the policies, and how a route that declares
one answers for each User."""

import uuid
from dataclasses import dataclass, field
from typing import Annotated

import httpx
import pytest
from fastapi import APIRouter, Depends
from sqlalchemy import delete, update

from app.main import create_app
from app.modules.identity import service
from app.modules.identity.models import user_roles, users
from app.modules.identity.schemas import AccountRole
from app.platform import auth, authz
from app.platform.db import get_sessionmaker
from tests.identity.helpers import login

PASSWORD = "et langt nok passord"


@dataclass
class P:
    roles: list[str] = field(default_factory=list)
    id: uuid.UUID = field(default_factory=uuid.uuid4)


ADMIN = P(["admin"])
LECTURER = P(["lecturer"])
BOTH = P(["admin", "lecturer"])
NONE = P([])

ADMIN_ACTIONS = (
    "admin_area.view",
    "users.list",
    "users.manage",
    "institutions.manage",
    "audit.read",
)


@pytest.mark.parametrize("action", ADMIN_ACTIONS)
def test_only_the_admin_role_lists_and_manages_users(action):
    assert authz.can(ADMIN, action)
    assert authz.can(BOTH, action)
    assert not authz.can(LECTURER, action)
    assert not authz.can(NONE, action)


def test_only_the_lecturer_role_opens_the_laererhjem():
    assert authz.can(LECTURER, "lecturer_home.view")
    assert authz.can(BOTH, "lecturer_home.view")
    assert not authz.can(ADMIN, "lecturer_home.view")
    assert not authz.can(NONE, "lecturer_home.view")


@pytest.mark.parametrize("action", ["student_answers.read", "ai_assessments.read"])
def test_no_account_role_reads_student_answers_or_ai_assessments(action):
    """FR-5: the Admin sees all Users but no Student answers or AI assessments."""
    for user in (ADMIN, LECTURER, BOTH, NONE):
        assert not authz.can(user, action)


def test_every_logged_in_user_reads_their_own_session():
    for user in (ADMIN, LECTURER, BOTH, NONE):
        assert authz.can(user, "session.read")


def test_any_user_may_ask_for_their_enrolled_classes_held_to_the_student_scope():
    """Story 4.5: the policy is open; `classes_enrolled_by` decides, from the User's own Roster
    entries that are not removed."""
    for user in (ADMIN, LECTURER, BOTH, NONE):
        assert authz.can(user, "classes.read_enrolled")
    sql = str(authz.classes_enrolled_by(NONE).compile(compile_kwargs={"literal_binds": False}))
    assert "FROM roster_entries" in sql
    assert "roster_entries.user_id = " in sql and "roster_entries.removed_at IS NULL" in sql


def test_an_unknown_action_is_an_error_never_an_allow():
    with pytest.raises(KeyError):
        authz.can(ADMIN, "users.lsit")
    with pytest.raises(KeyError):
        authz.require("users.lsit")


def test_the_module_documents_where_class_scoped_helpers_go():
    assert "classes_visible_to(user)" in (authz.__doc__ or "")


# A route with an item id behind an admin policy, as Story 3.9 will add. Its handler answers 404
# for an item that is not there, so the test shows the policy answers first.
ITEMS = {uuid.UUID(int=1)}
probe = APIRouter(prefix="/api/probe")


@probe.get("/items/{item_id}")
async def get_item(item_id: uuid.UUID, _: Annotated[object, Depends(authz.require("users.list"))]):
    from app.platform.errors import error_response

    if item_id not in ITEMS:
        return error_response(404, "not_found", "No such item.")
    return {"id": str(item_id)}


def probe_client() -> httpx.AsyncClient:
    app = create_app()
    app.include_router(probe)
    transport = httpx.ASGITransport(app=app, client=("203.0.113.9", 50000))
    return httpx.AsyncClient(transport=transport, base_url="https://t")


async def make_user(email: str, roles: list[AccountRole]) -> uuid.UUID:
    return await service.create_user(email=email, name="Kari", password=PASSWORD, roles=roles)


async def test_a_refusal_is_the_same_whether_or_not_the_item_exists(identity_db):
    await make_user("kari@example.com", [AccountRole.lecturer])
    async with probe_client() as c:
        assert (await login(c, "kari@example.com", PASSWORD)).status_code == 200
        there = await c.get(f"/api/probe/items/{uuid.UUID(int=1)}")
        missing = await c.get(f"/api/probe/items/{uuid.UUID(int=2)}")
    assert there.status_code == missing.status_code == 403
    assert there.json() == missing.json()
    assert there.json()["error"]["code"] == "forbidden"


async def test_the_admin_passes_the_policy(identity_db):
    await make_user("kari@example.com", [AccountRole.admin])
    async with probe_client() as c:
        await login(c, "kari@example.com", PASSWORD)
        assert (await c.get(f"/api/probe/items/{uuid.UUID(int=1)}")).status_code == 200
        assert (await c.get(f"/api/probe/items/{uuid.UUID(int=2)}")).status_code == 404


async def test_no_session_is_401_before_any_policy(identity_db):
    async with probe_client() as c:
        response = await c.get(f"/api/probe/items/{uuid.UUID(int=1)}")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


async def test_a_granted_or_revoked_role_counts_at_the_next_request(identity_db):
    """FR-2: same login, same cookie; the roles are read from the database every time."""
    user_id = await make_user("kari@example.com", [AccountRole.lecturer])
    item = f"/api/probe/items/{uuid.UUID(int=1)}"
    async with probe_client() as c:
        await login(c, "kari@example.com", PASSWORD)
        assert (await c.get(item)).status_code == 403
        async with get_sessionmaker().begin() as s:
            await s.execute(user_roles.insert().values(user_id=user_id, role="admin"))
        assert (await c.get(item)).status_code == 200
        assert (await c.get("/api/auth/me")).json()["user"]["roles"] == ["admin", "lecturer"]
        async with get_sessionmaker().begin() as s:
            await s.execute(delete(user_roles).where(user_roles.c.role == "admin"))
        assert (await c.get(item)).status_code == 403


async def test_a_deactivated_user_is_refused_on_every_request(identity_db):
    user_id = await make_user("kari@example.com", [AccountRole.admin])
    async with probe_client() as c:
        await login(c, "kari@example.com", PASSWORD)
        assert (await c.get(f"/api/probe/items/{uuid.UUID(int=1)}")).status_code == 200
        async with get_sessionmaker().begin() as s:
            await s.execute(update(users).where(users.c.id == user_id).values(is_active=False))
        cookie = c.cookies.get(auth.COOKIE_NAME)
        for path in (f"/api/probe/items/{uuid.UUID(int=1)}", "/api/auth/me"):
            # The refusal clears the cookie, so each request sends it afresh.
            c.cookies.set(auth.COOKIE_NAME, cookie)
            response = await c.get(path)
            assert response.status_code == 401
            assert response.json()["error"]["code"] == "session_expired"
        # Once cleared, nothing is sent: a plain «not logged in».
        c.cookies.clear()
        assert (await c.get("/api/auth/me")).json()["error"]["code"] == "not_authenticated"
