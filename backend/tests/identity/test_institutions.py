"""Creating, renaming and listing Institutions through the api, and the read functions other
modules use (Story 3.11, FR-3, AD-12, AD-15). The api's clock is fixed; the database clock is
never read."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.main import create_app
from app.modules.identity import service
from app.modules.identity.schemas import AccountRole
from app.platform import auth
from tests.identity.helpers import CSRF, client, login
from tests.messaging.helpers import rows
from tests.test_authz_rules import api_routes

PASSWORD = "hemmelig-passord"
ADMIN = "kari.admin@example.com"
LECTURER = "bard@example.com"
NOW = datetime(2026, 11, 18, 12, 1, tzinfo=UTC)


@pytest.fixture
def clock(monkeypatch):
    times = {"now": NOW}
    monkeypatch.setattr(auth, "utcnow", lambda: times["now"])
    return times


@pytest.fixture
async def admin(identity_db):
    return await service.create_user(
        email=ADMIN, name="Kari Admin", password=PASSWORD, roles=[AccountRole.admin]
    )


async def as_user(c, email: str = ADMIN):
    assert (await login(c, email, PASSWORD)).status_code == 200


async def create(c, name: str):
    return await c.post("/api/admin/institutions", json={"name": name}, headers=CSRF)


async def rename(c, institution_id, name: str):
    return await c.patch(
        f"/api/admin/institutions/{institution_id}", json={"name": name}, headers=CSRF
    )


def audit_rows() -> list[tuple]:
    return rows(
        "SELECT actor_user_id, action, target_ids, change, occurred_at FROM audit_events "
        "ORDER BY occurred_at, id"
    )


def stored() -> list[tuple]:
    return rows("SELECT name, created_at, updated_at FROM institutions ORDER BY id")


async def test_creating_stores_the_trimmed_name_with_one_audit_row(admin, clock):
    async with client() as c:
        await as_user(c)
        response = await create(c, "  USN   Bø ")
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "USN Bø"
    assert datetime.fromisoformat(body["created_at"]) == NOW
    assert stored() == [("USN Bø", NOW, NOW)]
    [(actor, action, target, change, at)] = audit_rows()
    assert (actor, action, change, at) == (admin, "institution.created", {"name": "USN Bø"}, NOW)
    assert target == {"institution_id": body["id"]}


@pytest.mark.parametrize("taken", ["usn bø", "USN BØ", " Usn  Bø "])
async def test_a_name_already_used_in_any_case_is_refused_and_nothing_is_stored(
    admin, clock, taken
):
    async with client() as c:
        await as_user(c)
        assert (await create(c, "USN Bø")).status_code == 201
        response = await create(c, taken)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "institution_name_taken"
    assert len(stored()) == 1
    assert len(audit_rows()) == 1


@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("", "name_empty"),
        ("   ", "name_empty"),
        ("x" * 201, "name_too_long"),
        ("kontakt@usn.no", "name_invalid"),
        ("USN\x00", "name_invalid"),
    ],
)
async def test_a_bad_name_answers_its_reason_and_nothing_is_stored(admin, clock, name, code):
    async with client() as c:
        await as_user(c)
        response = await create(c, name)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert response.json()["error"]["fields"] == {"name": code}
    assert stored() == []
    assert audit_rows() == []


async def test_a_name_of_200_characters_is_taken(admin, clock):
    async with client() as c:
        await as_user(c)
        assert (await create(c, "x" * 200)).status_code == 201


async def test_renaming_stores_the_new_name_with_the_old_and_new_in_the_audit_row(admin, clock):
    async with client() as c:
        await as_user(c)
        created = (await create(c, "USN")).json()
        clock["now"] = NOW + timedelta(hours=1)
        response = await rename(c, created["id"], "USN Bø")
    assert response.status_code == 200
    assert response.json() == {**created, "name": "USN Bø"}
    assert stored() == [("USN Bø", NOW, NOW + timedelta(hours=1))]
    renamed = audit_rows()[-1]
    assert renamed[1:] == (
        "institution.renamed",
        {"institution_id": created["id"]},
        {"old_name": "USN", "new_name": "USN Bø"},
        NOW + timedelta(hours=1),
    )
    assert renamed[0] == admin


async def test_renaming_to_the_same_name_writes_nothing_and_a_change_of_case_is_a_rename(
    admin, clock
):
    async with client() as c:
        await as_user(c)
        created = (await create(c, "Usn")).json()
        same = await rename(c, created["id"], " Usn ")
        assert same.status_code == 200
        assert len(audit_rows()) == 1
        case = await rename(c, created["id"], "USN")
    assert case.status_code == 200
    assert case.json()["name"] == "USN"
    assert audit_rows()[-1][3] == {"old_name": "Usn", "new_name": "USN"}


async def test_renaming_to_another_institutions_name_or_an_unknown_id_is_refused(admin, clock):
    async with client() as c:
        await as_user(c)
        await create(c, "USN")
        other = (await create(c, "NTNU")).json()
        taken = await rename(c, other["id"], "usn")
        unknown = await rename(c, uuid.uuid7(), "HVL")
        bad = await rename(c, other["id"], " ")
    assert taken.status_code == 409
    assert taken.json()["error"]["code"] == "institution_name_taken"
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "not_found"
    assert bad.status_code == 422
    assert bad.json()["error"]["fields"] == {"name": "name_empty"}
    assert sorted(name for name, *_ in stored()) == ["NTNU", "USN"]
    assert len(audit_rows()) == 2


async def test_two_creates_of_one_name_at_once_store_one(admin, clock):
    async with client() as a, client() as b:
        await as_user(a)
        await as_user(b)
        answers = await asyncio.gather(create(a, "USN"), create(b, "usn"))
    assert sorted(r.status_code for r in answers) == [201, 409]
    assert len(stored()) == 1
    assert len(audit_rows()) == 1


async def test_a_rename_and_a_create_of_one_name_at_once_store_it_once(admin, clock):
    async with client() as a, client() as b:
        await as_user(a)
        await as_user(b)
        other = (await create(a, "NTNU")).json()
        answers = await asyncio.gather(rename(a, other["id"], "USN"), create(b, "usn"))
    assert sorted(r.status_code for r in answers) in ([200, 409], [201, 409])
    assert [name.lower() for name, *_ in stored()].count("usn") == 1


async def test_names_are_compared_with_the_databases_lower_case(admin, clock):
    """Python lower-cases «İ» to two characters, Postgres to one: the check must use the same
    function as the unique index, or the index answers with a 500."""
    async with client() as c:
        await as_user(c)
        [(lowered,)] = rows("SELECT lower('İzmir')")
        assert lowered != "İzmir".lower()  # the case this test is about
        assert (await create(c, lowered)).status_code == 201
        response = await create(c, "İzmir")
    assert response.status_code == 409


async def test_the_list_is_newest_first_in_pages_of_the_list_envelope(admin, clock):
    async with client() as c:
        await as_user(c)
        ids = [(await create(c, name)).json()["id"] for name in ("A", "B", "C")]
        first = (await c.get("/api/admin/institutions", params={"limit": 2})).json()
        second = (
            await c.get(
                "/api/admin/institutions", params={"limit": 2, "cursor": first["next_cursor"]}
            )
        ).json()
        bad = await c.get("/api/admin/institutions", params={"cursor": "bm9wZQ"})
        unknown = await c.get(
            "/api/admin/institutions", params={"cursor": service._encode_cursor(uuid.uuid7())}
        )
    assert unknown.status_code == 422
    assert unknown.json()["error"]["fields"] == {"cursor": "invalid_cursor"}
    assert [item["id"] for item in first["items"]] == ids[:0:-1]
    assert first["items"][0]["name"] == "C"
    assert datetime.fromisoformat(first["items"][0]["created_at"]) == NOW
    assert [item["id"] for item in second["items"]] == ids[:1]
    assert second["next_cursor"] is None
    assert bad.status_code == 422
    assert bad.json()["error"]["fields"] == {"cursor": "invalid_cursor"}


async def test_an_empty_list_has_no_items(admin, clock):
    async with client() as c:
        await as_user(c)
        response = await c.get("/api/admin/institutions")
    assert response.json() == {"items": [], "next_cursor": None}


async def test_only_an_admin_passes_the_policy(admin, clock):
    await service.create_user(
        email=LECTURER, name="Bård Hansen", password=PASSWORD, roles=[AccountRole.lecturer]
    )
    async with client() as lecturer, client() as nobody:
        await as_user(lecturer, LECTURER)
        some = uuid.uuid7()
        answers = [
            await lecturer.get("/api/admin/institutions"),
            await create(lecturer, "USN"),
            await rename(lecturer, some, "USN"),
        ]
        anonymous = [
            await nobody.get("/api/admin/institutions"),
            await create(nobody, "USN"),
            await rename(nobody, some, "USN"),
        ]
    assert [r.status_code for r in answers] == [403, 403, 403]
    assert [r.status_code for r in anonymous] == [401, 401, 401]
    assert stored() == []


async def test_other_modules_read_institutions_by_name_and_by_id(admin, clock):
    async with client() as c:
        await as_user(c)
        usn = (await create(c, "usn")).json()
        await create(c, "NTNU")
    listed = await service.list_institutions()
    assert [i.name for i in listed] == ["NTNU", "usn"]
    found = await service.get_institution(uuid.UUID(usn["id"]))
    assert found is not None and found.name == "usn" and found.created_at == NOW
    assert await service.get_institution(uuid.uuid7()) is None


def test_no_delete_route_exists():
    methods = {
        method
        for path, route_methods, _ in api_routes(create_app())
        if path.startswith("/api/admin/institutions")
        for method in route_methods
    }
    # PUT is the operator mark (Story 12.7), on its own path.
    assert methods == {"GET", "POST", "PATCH", "PUT"}
