"""The question set and a Class session's selection of it, «Spørsmål og vekter» (Story 11.1,
FR-52, FR-53, FR-80, FR-18, FR-66, AD-4, AD-12, AD-23): the draft version 1 stored by migration
0121 and version 2 (Story 11.5, Interactive items with their tables) shipped as a file and stored by
migration 0124, the content load, the set's rules, the block's read and «Lagre vekter»,
the Start-date lock's pin and its refusal of a draft in production, and «Lag kopi». The api's
clock is fixed and moved by hand; the database clock is never read."""

import importlib
import json
import re
import shutil
import uuid
from datetime import timedelta
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.modules.content import __main__ as cli
from app.modules.content import service as content
from app.modules.sessions import service as sessions
from app.modules.tests import selection
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import EMAIL, call, shared
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import mails, rows
from tests.sessions.test_dates import PLAN, START, at, iso, new_session, refusal
from tests.sessions.test_lab_hours import sweep_at
from tests.sessions.test_rerun import copy, flag

__all__ = ["clock", "emitted", "klass", "shared"]

MINUTE = timedelta(minutes=1)
SHIPPED = "01a1f9a0-0000-7000-8000-"
UNSHIPPED = (
    f"DELETE FROM content_records WHERE version > 1 AND left(id::text, {len(SHIPPED)}) <> "
    f"'{SHIPPED}'"
)
"""Every content version a test published, and none a migration stored."""
CHANGE_ROW = "UPDATE test_selections SET adapted_weight = 30 WHERE class_session_id = %s"
SET = json.loads((cli.SHIPPED / "question_set.json").read_text(encoding="utf-8"))
"""The shipped question set: version 2 since Story 11.5 (migration 0124), the latest."""
V = 2


@pytest.fixture(autouse=True)
def _empty(ai_db, mail_db, games_db):
    execute(UNSHIPPED)
    yield
    execute(UNSHIPPED)


def path(session_id: str) -> str:
    return f"/api/class-sessions/{session_id}/question-set"


async def read(session_id: str, email: str = EMAIL["owner"]) -> dict:
    response = await call(email, "GET", path(session_id))
    assert response.status_code == 200, response.text
    return response.json()


async def put(session_id: str, body: dict, email: str = EMAIL["owner"]):
    return await call(email, "PUT", path(session_id), json=body)


def body_of(block: dict, **changes) -> dict:
    """The block as «Lagre vekter» would send it, with `changes` laid over."""
    body = {
        "weights": {item["id"]: item["weight"] for item in block["items"]},
        "excluded": [item["id"] for item in block["items"] if item["excluded"]],
        "adapted_weight": block["adapted"]["weight"],
    }
    return {**body, **changes}


def stored(session_id: str) -> list[tuple]:
    return rows(
        "SELECT question_set_version, excluded, weights, adapted_weight FROM test_selections "
        "WHERE class_session_id = %s",
        session_id,
    )


async def planned(class_id: str) -> str:
    session_id = await new_session(class_id)
    saved = await call(
        EMAIL["owner"],
        "PUT",
        f"/api/class-sessions/{session_id}",
        json={"ai_mode": "rule_based", "dates": iso(PLAN)},
    )
    assert saved.status_code == 200
    return session_id


def snapshot_pin(session_id: str) -> dict:
    [(pin,)] = rows(
        "SELECT snapshot->'session_runtime'->'pins'->'question_set' FROM class_sessions "
        "WHERE id = %s",
        session_id,
    )
    return pin


def in_production(monkeypatch) -> None:
    """Only the question set's own check sees production: the rest of the lock runs as in tests."""
    monkeypatch.setattr(selection, "get_settings", lambda: SimpleNamespace(app_env="production"))


# The record and the content load.


async def test_the_latest_version_is_the_shipped_draft_file_and_the_migrations_literal():
    """Version 2 (Story 11.5) is the shipped file and migration 0124's literal; version 1 stays
    migration 0121's literal, its table and number items without a table of their own."""
    first = importlib.import_module("migrations.versions.0121_question_set").QUESTION_SET_V1
    assert (await content.get("question_set", 1)).model_dump(mode="json") == {
        **first,
        "items": [{**item, "interactive": None} for item in first["items"]],
        "replacements": [{**item, "interactive": None} for item in first["replacements"]],
    }
    migration = importlib.import_module("migrations.versions.0124_question_set_interactive")
    assert migration.QUESTION_SET_V2 == SET
    version, found = await content.question_set(None)
    assert version == V and found.model_dump(mode="json") == SET
    # Every table item and every number item of its own has its table, none says «øl».
    for item in (*found.items, *found.replacements):
        assert (item.interactive is not None) == item.needs_interactive(), item.id
        if item.interactive:
            text = json.dumps(item.interactive.model_dump(), ensure_ascii=False)
            assert not re.search(r"\bøl\b", text, re.IGNORECASE) and "enheter" in text
    assert found.status == "draft"
    assert sum(item.weight for item in found.items) + found.adapted_weight == 100
    assert found.adapted_weight == 30
    # Every Starting task item referenced by id, its text not copied.
    _, task = await content.starting_task(None)
    refs = {item.starting_task_item for item in found.items} - {None}
    assert refs == {item.id for item in task.items}
    for item in found.items:
        assert all(item.title != t.prompt for t in task.items)


async def test_the_load_of_the_shipped_files_publishes_nothing_and_a_change_once(tmp_path):
    assert await cli.load(cli.SHIPPED) == (
        [
            f"question_set unchanged (v{V})",
            "scoring_guide unchanged (v1)",
            "adapted_templates unchanged (v2)",
        ],
        [],
    )
    assert await content.latest_version("question_set") == V
    shutil.copy(cli.SHIPPED / "question_set.json", tmp_path / "question_set.json")
    approved = {**SET, "status": "approved"}
    (tmp_path / "question_set.json").write_text(json.dumps(approved), encoding="utf-8")
    assert await cli.load(tmp_path) == ([f"question_set v{V + 1}"], [])
    assert await cli.load(tmp_path) == ([f"question_set unchanged (v{V + 1})"], [])
    assert (await content.question_set(None))[1].status == "approved"
    # The older shipped draft never supersedes the newer version.
    assert await cli.load(cli.SHIPPED) == (
        [
            f"question_set unchanged (v{V})",
            "scoring_guide unchanged (v1)",
            "adapted_templates unchanged (v2)",
        ],
        [],
    )
    assert await content.latest_version("question_set") == V + 1


def _with(**changes) -> dict:
    return json.loads(json.dumps({**SET, **changes}))


def _item(index: int, **changes) -> dict:
    items = json.loads(json.dumps(SET["items"]))
    items[index] = {**items[index], **changes}
    return _with(items=items)


async def test_the_load_refuses_with_stable_codes_and_stores_nothing(tmp_path):
    files = {
        "question_set.json": _item(4, type="diagram"),
        "made_up.json": {"x": 1},
    }
    for name, body in files.items():
        (tmp_path / name).write_text(json.dumps(body), encoding="utf-8")
    done, refused = await cli.load(tmp_path)
    assert done == []
    assert [line.split(": ")[:2] for line in refused] == [
        ["question_set.json", "unknown_item_type"],
        ["made_up.json", "unknown_kind"],
    ]
    # A Starting task item not referenced, and a set breaking a rule.
    (tmp_path / "made_up.json").unlink()
    own = SET["items"][7]["interactive"]  # a number item with its own column
    (tmp_path / "question_set.json").write_text(
        json.dumps(_item(0, starting_task_item=None, interactive=own)), encoding="utf-8"
    )
    assert (await cli.load(tmp_path))[1][0].split(": ")[1] == "starting_task_items_missing"
    # An Interactive item without its table (Story 11.5).
    for index in (5, 7):
        (tmp_path / "question_set.json").write_text(
            json.dumps(_item(index, interactive=None)), encoding="utf-8"
        )
        assert (await cli.load(tmp_path))[1][0].split(": ")[1] == "interactive_missing"
    (tmp_path / "question_set.json").write_text(json.dumps(_item(0, weight=2)), encoding="utf-8")
    assert (await cli.load(tmp_path))[1][0].split(": ")[1] == "invalid_record"
    assert await content.latest_version("question_set") == V
    # A file that does not decode, and a folder that is not there.
    (tmp_path / "question_set.json").write_bytes(bytes([0xFF, 0xFE, 0x7B]))
    assert (await cli.load(tmp_path))[1][0].split(": ")[1] == "invalid_record"
    assert (await cli.load(tmp_path / "nowhere"))[1][0].split(": ")[1] == "no_folder"


async def test_the_load_publishes_the_starting_task_before_the_question_set(tmp_path):
    """A new Starting task item and the question set item that references it, in one load."""
    _, task = await content.starting_task(None)
    more = task.model_dump(mode="json")
    extra = {**more["items"][0], "id": "extra"}
    more["items"].append(extra)
    items = json.loads(json.dumps(SET["items"]))
    items[1] = {**items[1], "weight": 2}
    ekstra = {**items[0], "id": "startoppgave-ekstra", "starting_task_item": "extra", "weight": 1}
    items.append(ekstra)
    (tmp_path / "starting_task.json").write_text(json.dumps(more), encoding="utf-8")
    (tmp_path / "question_set.json").write_text(json.dumps(_with(items=items)), encoding="utf-8")
    done, refused = await cli.load(tmp_path)
    assert refused == [] and done == ["starting_task v2", f"question_set v{V + 1}"]


def test_the_load_command_exits_1_on_a_refusal(monkeypatch, capsys):
    async def refused(folder):
        return [], ["question_set.json: unknown_item_type: items: 'diagram'"]

    monkeypatch.setattr(cli, "load", refused)
    assert cli.main(["load"]) == 1
    assert "unknown_item_type" in capsys.readouterr().err


@pytest.mark.parametrize(
    "bad",
    [
        _item(3, tags=[]),  # no item uses the Explanation's wording
        _item(4, tags=["explanation-wording"]),  # two do
        _item(5, tags=["quantity"]),  # no unseen Demand pattern
        _item(7, tags=[]),  # one item in another business
        _item(8, tags=["other-business"]),  # a long answer in another business
        _with(adapted_weight=29),  # the weights sum to 99
        _with(replacements=SET["replacements"][:1]),  # replacements carry 15, not 30
        _item(3, answer_key="z"),  # a choice item with no answer among its options
        _item(8, scoring_rule=None),  # a long answer with no scoring rule
        _item(3, options=["a", "b", "b"]),  # a choice item repeating an option
        _item(8, starting_task_item="to-ship"),  # a Starting task item on a long answer
        # Interactive items (Story 11.5):
        _item(3, interactive=SET["items"][5]["interactive"]),  # a table on a choice item
        _item(0, interactive=SET["items"][7]["interactive"]),  # and on a Starting task item
        _item(7, interactive=SET["items"][5]["interactive"]),  # a number item: two columns
        _item(5, interactive={**SET["items"][5]["interactive"], "rows": ["Uke 1"]}),
        _item(5, interactive={**SET["items"][5]["interactive"], "asked": "Antall øl"}),
        _item(5, interactive={**SET["items"][5]["interactive"], "criteria": []}),
        _item(
            7,  # a number item has no flow
            interactive={
                **SET["items"][7]["interactive"],
                "criteria": [
                    {
                        "code": "K1",
                        "weight": 100,
                        "check": {
                            "kind": "flow",
                            "inflow": "mangler",
                            "outflow": "mangler",
                            "start": 0,
                        },
                    }
                ],
            },
        ),
    ],
)
async def test_a_set_that_breaks_a_rule_is_not_stored(bad):
    with pytest.raises(ValidationError):
        await content.publish("question_set", bad)
    assert await content.latest_version("question_set") == V


async def test_a_set_with_no_quantity_item_is_not_stored():
    items = [
        {**item, "tags": [t for t in item["tags"] if t != "quantity"]} for item in SET["items"]
    ]
    with pytest.raises(ValidationError):
        await content.publish("question_set", _with(items=items))


# The block and «Lagre vekter».


async def test_the_block_lists_the_draft_defaults_with_the_adapted_line(klass):
    session_id = await new_session(klass)
    block = await read(session_id)
    assert (block["version"], block["draft"], block["outdated"], block["pinned"]) == (
        V,
        True,
        False,
        False,
    )
    assert (block["open"], block["can_change"], block["sum"]) == (True, True, 100)
    assert [item["id"] for item in block["items"]] == [item["id"] for item in SET["items"]]
    first = block["items"][0]
    assert first == {
        "id": "startoppgave-sende",
        "type": "number",
        "title": SET["items"][0]["title"],
        "weight": 3,
        "default_weight": 3,
        "excluded": False,
        "quantity": True,
        "starting_task": True,
    }
    assert block["adapted"] == {"weight": 30, "default_weight": 30, "replacements": 2}
    assert stored(session_id) == []


async def test_the_owner_saves_a_selection_and_the_staff_are_told(klass, emitted):
    session_id = await new_session(klass)
    block = await read(session_id)
    weights = body_of(block)["weights"] | {"langsvar-forsinkelse": 15}
    # A quantity item taken out (its 3 % moved) and the Adapted items down to 28 %.
    wanted = body_of(block, weights=weights, excluded=["startoppgave-sende"], adapted_weight=28)
    emitted.clear()
    response = await put(session_id, wanted)
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["sum"] == 100 and saved["adapted"]["weight"] == 28
    taken = next(item for item in saved["items"] if item["id"] == "startoppgave-sende")
    assert (taken["excluded"], taken["quantity"]) == (True, True)
    assert emitted == [("session", session_id)]
    assert {t for t, _ in emitted} == COMMAND_TOPICS["tests.save_question_set"]
    [(version, excluded, stored_weights, adapted)] = stored(session_id)
    assert (version, excluded, adapted) == (V, ["startoppgave-sende"], 28)
    assert stored_weights["langsvar-forsinkelse"] == 15
    audited = rows(
        "SELECT change FROM audit_events "
        "WHERE action = %s AND target_ids->>'class_session_id' = %s",
        selection.SELECTION_CHANGED,
        session_id,
    )
    assert [change["excluded"] for (change,) in audited] == [["startoppgave-sende"]]
    assert (await read(session_id)) == saved


async def test_a_sum_other_than_100_is_refused_and_nothing_is_stored(klass):
    session_id = await new_session(klass)
    block = await read(session_id)
    refused = await put(session_id, body_of(block, adapted_weight=25))
    assert refusal(refused) == (422, "weights_not_100", {"weights": "sum"})
    # Taking an item out without moving its weight leaves 95 % too.
    refused = await put(session_id, body_of(block, excluded=["flervalg-arsaker"]))
    assert refusal(refused)[1] == "weights_not_100"
    assert stored(session_id) == []


async def test_a_selection_that_does_not_fit_the_set_is_refused(klass):
    session_id = await new_session(klass)
    block = await read(session_id)
    weights = body_of(block)["weights"]
    unknown = await put(session_id, body_of(block, weights={**weights, "nope": 0}))
    assert refusal(unknown) == (422, "validation_error", {"weights": "items"})
    missing = dict(weights)
    missing.pop("flervalg-arsaker")
    assert refusal(await put(session_id, body_of(block, weights=missing)))[2] == {
        "weights": "items"
    }
    out = await put(session_id, body_of(block, excluded=["nope"]))
    assert refusal(out) == (422, "validation_error", {"excluded": "unknown_item"})
    everything = body_of(block, excluded=list(weights), adapted_weight=100)
    assert refusal(await put(session_id, everything))[2] == {"excluded": "all"}
    too_big = await put(session_id, body_of(block, adapted_weight=101))
    assert refusal(too_big)[:2] == (422, "invalid_request")
    assert stored(session_id) == []


async def test_from_the_start_date_the_block_is_read_only_and_a_save_refused(klass, monkeypatch):
    session_id = await planned(klass)
    block = await read(session_id)
    at(monkeypatch, START + MINUTE)
    assert (await read(session_id))["open"] is False
    refused = await put(session_id, body_of(block))
    assert refusal(refused) == (409, "session_locked", {"question_set": "locked"})
    assert stored(session_id) == []


@pytest.mark.parametrize("role", ["assistant", "lecturer_assistant"])
async def test_an_assistant_lecturer_reads_the_block_but_cannot_save(shared, role):
    session_id = await new_session(shared)
    block = await read(session_id, EMAIL[role])
    assert (block["can_change"], block["open"]) == (False, True)
    refused = await put(session_id, body_of(block), EMAIL[role])
    assert refusal(refused)[:2] == (403, "forbidden")
    assert stored(session_id) == []


async def test_an_outsider_and_an_archived_class(shared):
    session_id = await new_session(shared)
    response = await call(EMAIL["outsider"], "GET", path(session_id))
    assert response.status_code == 403
    response = await call(EMAIL["owner"], "GET", path(str(uuid.uuid4())))
    assert response.status_code == 403
    block = await read(session_id)
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, shared)
    assert (await read(session_id))["can_change"] is False
    assert refusal(await put(session_id, body_of(block)))[:2] == (409, "class_archived")


# The Start-date lock.


async def test_the_lock_pins_the_saved_selection_and_the_block_reads_the_pin(klass):
    session_id = await planned(klass)
    block = await read(session_id)
    weights = body_of(block)["weights"] | {"flervalg-arsaker": 10}
    wanted = body_of(block, weights=weights, adapted_weight=25)
    assert (await put(session_id, wanted)).status_code == 200
    assert await sessions.lock(uuid.UUID(session_id), now=START) is True
    pin = snapshot_pin(session_id)
    assert pin == {"version": V, "excluded": [], "weights": weights, "adapted_weight": 25}
    # A row changed behind the api's back after the lock does not change what the block shows.
    execute(CHANGE_ROW, session_id)
    after = await read(session_id)
    assert (after["pinned"], after["open"], after["adapted"]["weight"]) == (True, False, 25)


async def test_in_production_a_draft_set_refuses_the_lock_and_the_owner_is_told(klass, monkeypatch):
    session_id = await planned(klass)
    in_production(monkeypatch)
    await sweep_at(START + MINUTE)
    refused = "SELECT locked_at, lock_refused_reason FROM class_sessions WHERE id = %s"
    assert rows(refused, session_id) == [(None, "question_set_draft")]
    item = (await call(EMAIL["owner"], "GET", f"/api/class-sessions/{session_id}")).json()
    assert (item["lock_refused"], item["lock_refused_reason"]) == (True, "question_set_draft")
    told = [mail for mail in mails() if mail.to == EMAIL["owner"]]
    assert len(told) == 1 and "utkast som ikke er godkjent" in told[0].text
    # An approved version published: the next sweep locks on it.
    assert await content.publish("question_set", {**SET, "status": "approved"}) == V + 1
    await sweep_at(START + 2 * MINUTE)
    assert snapshot_pin(session_id)["version"] == V + 1
    item = (await call(EMAIL["owner"], "GET", f"/api/class-sessions/{session_id}")).json()
    assert item["lock_refused_reason"] is None


async def test_outside_production_a_draft_set_locks(klass):
    session_id = await planned(klass)
    assert await sessions.lock_due(uuid.UUID(session_id), START) is True
    assert snapshot_pin(session_id)["version"] == V


async def test_a_selection_on_an_older_version_gives_way_to_the_latest_defaults(klass):
    session_id = await planned(klass)
    block = await read(session_id)
    assert (
        await put(
            session_id,
            body_of(
                block,
                adapted_weight=20,
                weights={**body_of(block)["weights"], "langsvar-informasjon": 20},
            ),
        )
    ).status_code == 200
    assert await content.publish("question_set", {**SET, "status": "approved"}) == V + 1
    now = await read(session_id)
    assert (now["version"], now["outdated"], now["draft"], now["adapted"]["weight"]) == (
        V + 1,
        True,
        False,
        30,
    )
    # What the block shows is what the lock pins.
    await sessions.lock(uuid.UUID(session_id), now=START)
    assert snapshot_pin(session_id) == {
        "version": V + 1,
        "excluded": [],
        "weights": {item["id"]: item["weight"] for item in SET["items"]},
        "adapted_weight": 30,
    }


# «Lag kopi».


async def test_a_copy_takes_the_selection_or_its_pin(klass, monkeypatch):
    flag(monkeypatch, True)
    source = await planned(klass)
    block = await read(source)
    weights = body_of(block)["weights"] | {"langsvar-forsinkelse": 15}
    wanted = body_of(block, weights=weights, excluded=["startoppgave-sende"], adapted_weight=28)
    assert (await put(source, wanted)).status_code == 200
    copied = await copy(klass, source)
    assert copied.status_code == 201
    assert stored(copied.json()["id"]) == stored(source)
    assert (await read(copied.json()["id"]))["adapted"]["weight"] == 28
    # Once locked, the pin is copied, whatever the row says.
    await sessions.lock(uuid.UUID(source), now=START)
    execute(CHANGE_ROW, source)
    again = (await copy(klass, source)).json()["id"]
    assert stored(again)[0][3] == 28
    # A source with no selection gives the defaults, nothing stored.
    plain = (await copy(klass, await new_session(klass))).json()["id"]
    assert stored(plain) == []
