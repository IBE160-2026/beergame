"""The CSRF guard (AD-11): every mutating /api request carries `X-Requested-With: olspillet`."""

import pytest

from tests.identity.helpers import CSRF, client


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
async def test_a_mutation_without_the_header_is_refused_before_the_handler(method):
    async with client() as c:
        response = await c.request(method, "/api/auth/logout")
    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "csrf_header_missing",
            "message": "Mutating requests must carry X-Requested-With: olspillet.",
            "fields": {},
        }
    }
    assert "set-cookie" not in response.headers  # logout did not run


async def test_a_wrong_header_value_is_refused():
    async with client() as c:
        response = await c.post("/api/auth/logout", headers={"X-Requested-With": "XMLHttpRequest"})
    assert response.status_code == 403


async def test_a_mutation_with_the_header_reaches_the_handler():
    async with client() as c:
        response = await c.post("/api/auth/logout", headers=CSRF)
    assert response.status_code == 204


async def test_reads_and_webhooks_need_no_header():
    async with client() as c:
        assert (await c.get("/api/auth/me")).status_code == 401  # reached the route
        webhook = await c.post("/api/webhooks/resend")
    assert webhook.status_code == 404  # no such route yet, but not refused by the guard
    assert "csrf_header_missing" not in webhook.text


async def test_the_guard_covers_the_bare_api_path_but_not_other_paths():
    async with client() as c:
        assert (await c.post("/api")).status_code == 403
        assert (await c.post("/apix")).status_code == 404
