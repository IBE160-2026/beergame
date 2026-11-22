"""The two guards of AD-12 (Story 3.3, NFR-7): every API route declares a `platform/authz`
policy, and no module compares account roles itself. Both run in CI with the backend tests."""

import ast
from pathlib import Path

import pytest
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, iter_route_contexts

from app.main import create_app
from app.platform import authz

APP = Path(__file__).parents[1] / "app"

PUBLIC_ROUTES = {
    # Login and logout: logout needs no session, it only clears the cookie (Story 3.2).
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/logout"),
    ("GET", "/api/health"),
    # Password reset (Story 3.6): a forgotten password has no session.
    ("POST", "/api/auth/password-reset"),
    ("POST", "/api/auth/password-reset/check"),
    ("POST", "/api/auth/password-reset/confirm"),
    # The dev mailbox (Story 3.6), mounted only outside production (`test_dev_mailbox.py`).
    ("GET", "/api/dev/mailbox/latest"),
    # Invitation acceptance (Story 3.8): the invitee has no session yet.
    ("POST", "/api/auth/invitation/check"),
    ("POST", "/api/auth/invitation/accept"),
    ("POST", "/api/auth/invitation/accept-login"),
    ("POST", "/api/auth/invitation/renewal"),
    # The lecturer-access request from the Landing (Story 3.13): the visitor has no account.
    ("POST", "/api/auth/access-request"),
    # The local dev bounce (Story 4.6), mounted only outside production like the dev mailbox.
    ("POST", "/api/dev/mailbox/bounce"),
    # The local dev lock (Story 6.15), mounted only outside production like the dev mailbox.
    ("POST", "/api/dev/class-sessions/{class_session_id}/lock"),
    # Story 9.11: the local dev back-dating of a Group debrief step, never in production.
    ("POST", "/api/dev/debriefs/{debrief_id}/backdate"),
    ("POST", "/api/dev/games/{game_id}/seats/{seat}/narrate"),
    # The mail provider's events (Story 4.6): admitted by their Svix signature.
    ("POST", "/api/webhooks/resend"),
    # Later stories add theirs here, and only these kinds: webhooks (signature-checked), and dev
    # routes that are never mounted in production.
}


def policies(dependant: Dependant) -> list[object]:
    found = []
    for dep in dependant.dependencies:
        if isinstance(dep.call, authz.Policy) or dep.call is authz.public:
            found.append(dep.call)
        found += policies(dep)
    return found


def api_routes(app) -> list[tuple[str, set[str], APIRoute]]:
    """(path, methods, route) of every API route, through included routers. FastAPI's own docs
    and schema routes are plain Starlette routes and are not counted. A policy given only to
    `include_router(dependencies=...)` is not seen here, so the walk fails safe: declare it on
    the route or on the `APIRouter`."""
    return [
        (ctx.path, set(ctx.methods or ()), ctx.route)
        for ctx in iter_route_contexts(app.routes)
        if isinstance(ctx.route, APIRoute)
    ]


def test_every_route_declares_a_policy_and_public_ones_are_on_the_list():
    routes = api_routes(create_app())
    assert len(routes) >= 4, routes
    public = set()
    for path, methods, route in routes:
        declared = policies(route.dependant)
        assert declared, f"{sorted(methods)} {path} declares no authz policy"
        if authz.public in declared:
            public |= {(method, path) for method in methods}
    assert public <= PUBLIC_ROUTES, f"public routes off the list: {sorted(public - PUBLIC_ROUTES)}"
    # No stale entry: one would silently let a later route at that path go out without a policy.
    assert PUBLIC_ROUTES <= public, f"listed but not public: {sorted(PUBLIC_ROUTES - public)}"


def test_the_route_walk_sees_a_policy_and_its_absence():
    from fastapi import APIRouter, Depends, FastAPI

    app = FastAPI()
    router = APIRouter()

    @router.get("/a", dependencies=[Depends(authz.require("users.list"))])
    async def a():
        return None

    @router.get("/b")
    async def b():
        return None

    app.include_router(router)
    found = {path: policies(route.dependant) for path, _, route in api_routes(app)}
    assert [repr(p) for p in found["/a"]] == ["require('users.list')"]
    assert found["/b"] == []


ROLE_NAMES = {"admin", "lecturer"}


def _is_role_operand(node: ast.expr) -> bool:
    if isinstance(node, ast.Constant) and node.value in ROLE_NAMES:
        return True
    if isinstance(node, ast.Name) and node.id in ("AccountRole", "roles"):
        return True
    if isinstance(node, ast.Attribute):
        if node.attr in ("roles", "ADMIN", "LECTURER"):
            return True
        return isinstance(node.value, ast.Name) and node.value.id == "AccountRole"
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return any(_is_role_operand(e) for e in node.elts)
    return False


def role_comparisons(source: str) -> list[int]:
    """Lines with a comparison on an account role: `role == "admin"`, `AccountRole.admin in
    user.roles`, `"lecturer" not in roles` and the like. Seat roles (Detaljist …) do not count."""
    lines = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Compare) and any(
            _is_role_operand(operand) for operand in (node.left, *node.comparators)
        ):
            lines.append(node.lineno)
    return lines


def test_no_module_compares_account_roles():
    """Modules ask `authz.can(user, action, resource)` instead (AD-12)."""
    for path in sorted((APP / "modules").rglob("*.py")):
        found = role_comparisons(path.read_text(encoding="utf-8"))
        assert not found, f"{path.relative_to(APP)}:{found} compares account roles; use authz.can"


@pytest.mark.parametrize(
    "source",
    [
        'if role == "admin": pass',
        "if AccountRole.admin in user.roles: pass",
        'ok = "lecturer" not in roles',
        'ok = user.roles == ["admin"]',
        "ok = authz.ADMIN in principal.roles",
        "ok = r is AccountRole.lecturer",
    ],
)
def test_the_role_check_catches(source):
    assert role_comparisons(source) == [1]


@pytest.mark.parametrize(
    "source",
    [
        "if role == CUSTOMER_FACING: pass",  # a Seat's Rolle, not an account role
        "ok = state.role == PRODUCING",
        'ok = authz.can(user, "users.list")',
        "roles = [AccountRole(r) for r in rows]",
    ],
)
def test_the_role_check_lets_through(source):
    assert role_comparisons(source) == []


def test_can_holds_a_class_action_to_the_staff_role():
    """Story 4.1 (AD-12): a Class action on a resource needs a staff role in the Class that the
    action allows, on top of the account role."""
    import uuid

    class User:
        id = uuid.uuid4()
        roles = ("lecturer",)

    class Staff:
        def __init__(self, role):
            self.staff_role = role

    assert authz.can(User(), "classes.read")
    assert authz.can(User(), "classes.manage", Staff("owner"))
    assert not authz.can(User(), "classes.manage", Staff("assistant"))
    assert not authz.can(User(), "classes.read", object())
    User.roles = ("admin",)
    assert not authz.can(User(), "classes.read", Staff("owner"))
