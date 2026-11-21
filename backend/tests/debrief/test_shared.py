"""The shared screen of a Group debrief (Story 9.13, FR-74, FR-43, AD-12, AD-21).

`GET /api/debriefs/{id}/shared` answers a Student joined to a shared Debrief session with the
chain by Role only: locked, with no chain data, while a joined Student has not sent their
Explanation; everyone else gets the same 403 `forbidden` as for an id that is not one. Its schema
has no text field, so no name, Explanation, answer or moment can be in it."""

import uuid
from decimal import Decimal
from typing import get_args

from pydantic import BaseModel

from app.engine.settings import Role
from app.modules.debrief.schemas import SharedOut
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.debrief.test_debrief import open_, refused
from tests.debrief.test_group import played
from tests.sessions.test_dates import OUTSIDER
from tests.sessions.test_lock import _empty
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "klass"]

PRIVATE = {
    "user_id",
    "name",
    "names",
    "text",
    "explanation",
    "answer",
    "answers",
    "moments",
    "members",
    "email",
    "reflection",
}


def _models(model: type[BaseModel]) -> list[type[BaseModel]]:
    """The model and every model its fields refer to, through lists and unions."""
    found: list[type[BaseModel]] = []

    def walk(kind: object) -> None:
        if isinstance(kind, type) and issubclass(kind, BaseModel) and kind not in found:
            found.append(kind)
            for field in kind.model_fields.values():
                walk(field.annotation)
        for arg in get_args(kind):
            walk(arg)

    walk(model)
    return found


def _leaves(kind: object) -> set[object]:
    args = get_args(kind)
    return set().union(*(_leaves(a) for a in args)) if args else {kind}


def test_the_shared_schema_has_no_name_and_no_free_text():
    # In the OpenAPI schema the route publishes: no property named like a person or their text.
    schema = SharedOut.model_json_schema(mode="serialization")
    models = [schema, *schema.get("$defs", {}).values()]
    names = {key for each in models for key in each.get("properties", {})}
    assert names & PRIVATE == set()
    # And no field of any model in it can hold text: ids, numbers, flags, the Role enum and the
    # shared models only (no `str`, `Any` or `dict`).
    models = _models(SharedOut)
    allowed = {uuid.UUID, int, bool, Decimal, Role, type(None), list, *models}
    for model in models:
        for key, field in model.model_fields.items():
            assert _leaves(field.annotation) <= allowed, f"{model.__name__}.{key}"


async def test_the_shared_screen_shows_the_chain_to_joined_students_only(klass):
    session_id, _ = await played(klass, 3, ordering=3)
    a, b, c = email(0), email(1), email(2)
    debrief_id = (await open_(a, session_id)).json()["id"]
    path = f"/api/debriefs/{debrief_id}"
    shared = f"{path}/shared"
    assert (await call(b, "POST", f"{path}/join")).status_code == 200

    # A has sent, B writes: locked, no demand and no chain data.
    assert (
        await call(a, "POST", f"{path}/explanation", json={"text": "Min forklaring."})
    ).status_code == 201
    locked = await call(a, "GET", shared)
    assert locked.status_code == 200
    body = locked.json()
    assert (body["locked"], body["chain"], body["step"]) == (True, None, 1)
    assert body["debrief_id"] == debrief_id and body["class_session_id"] == session_id

    # Everyone not joined: C (a Student of the game who never joined), the Lecturer, an outsider,
    # an id that is not one, a malformed id: the same refusal.
    refused(await call(c, "GET", shared), "forbidden")
    refused(await call(LECTURER, "GET", shared), "forbidden")
    await make(OUTSIDER, roles=())
    refused(await call(OUTSIDER, "GET", shared), "forbidden")
    refused(await call(a, "GET", f"/api/debriefs/{uuid.uuid4()}/shared"), "forbidden")
    refused(await call(a, "GET", "/api/debriefs/not-an-id/shared"), "forbidden")

    # B sends: open, four Roles Fabrikk first, costs adding up to the chain's.
    assert (await call(b, "POST", f"{path}/explanation", json={"text": "Min."})).status_code == 201
    body = (await call(b, "GET", shared)).json()
    assert (body["locked"], body["step"]) == (False, 2)
    chain = body["chain"]
    assert [r["role"] for r in chain["roles"]] == [
        "factory",
        "distributor",
        "wholesaler",
        "retailer",
    ]
    assert chain["last_week"] == 2
    for role in chain["roles"]:
        assert [w["week"] for w in role["weeks"]] == [1, 2]
        assert all(w["net_inventory"] == w["inventory"] - w["backlog"] for w in role["weeks"])
        assert Decimal(role["holding_cost"]) + Decimal(role["backorder_cost"]) == Decimal(
            role["total_cost"]
        )
    assert sum(Decimal(r["total_cost"]) for r in chain["roles"]) == Decimal(chain["total_cost"])
    assert Decimal(chain["holding_cost"]) + Decimal(chain["backorder_cost"]) == Decimal(
        chain["total_cost"]
    )
    assert "Min forklaring" not in str(body) and "Min." not in str(body)

    # C joins late without an Explanation: locked again; C goes alone: open again, C refused.
    assert (await call(c, "POST", f"{path}/join")).status_code == 200
    again = (await call(a, "GET", shared)).json()
    assert (again["locked"], again["chain"]) == (True, None)
    assert (await call(c, "GET", shared)).json()["locked"] is True
    assert (await call(c, "POST", f"{path}/leave")).status_code == 200
    assert (await call(a, "GET", shared)).json()["locked"] is False
    refused(await call(c, "GET", shared), "forbidden")


async def test_a_personal_debrief_has_no_shared_screen(klass):
    session_id, _ = await played(klass, 2, ordering=2, mode="personal")
    a = email(0)
    debrief_id = (await open_(a, session_id)).json()["id"]
    assert (
        await call(a, "POST", f"/api/debriefs/{debrief_id}/explanation", json={"text": "X."})
    ).status_code == 201
    refused(await call(a, "GET", f"/api/debriefs/{debrief_id}/shared"), "forbidden")
