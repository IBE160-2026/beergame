"""The Scoring guide and a Class session's edit of it, «Sensorveiledning» (Story 11.2, FR-81, FR-18,
FR-66, AD-12, AD-23, AD-27): the draft version 1 shipped as a file and stored by migration 0122,
the load's criteria rule, the block's read and «Lagre sensorveiledning», the Test-deadline lock's
pin, `is_checked` and «Lag kopi». The api's clock is fixed and moved by hand; the database clock
is never read."""

import importlib
import json
import uuid
from datetime import timedelta

import psycopg
import pytest

from app.modules.content import __main__ as cli
from app.modules.content import service as content
from app.modules.sessions import service as sessions
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import EMAIL, call, shared
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import rows
from tests.sessions.test_dates import PLAN, TEST, at, iso, new_session, refusal
from tests.sessions.test_rerun import copy, flag

__all__ = ["clock", "emitted", "klass", "shared"]

MINUTE = timedelta(minutes=1)
SHIPPED = "01a1f9a0-0000-7000-8000-"
UNSHIPPED = (
    f"DELETE FROM content_records WHERE version > 1 AND left(id::text, {len(SHIPPED)}) <> "
    f"'{SHIPPED}'"
)
"""Every content version a test published (edits included), and none a migration stored."""
V1 = json.loads((cli.SHIPPED / "scoring_guide.json").read_text(encoding="utf-8"))
FIRST = V1["questions"][0]["id"]
SECOND = V1["questions"][1]["id"]


@pytest.fixture(autouse=True)
def _empty(ai_db, mail_db):
    execute(UNSHIPPED)
    yield
    execute(UNSHIPPED)


def path(session_id: str) -> str:
    return f"/api/class-sessions/{session_id}/scoring-guide"


async def read(session_id: str, email: str = EMAIL["owner"]) -> dict:
    response = await call(email, "GET", path(session_id))
    assert response.status_code == 200, response.text
    return response.json()


async def put(session_id: str, guides: dict, email: str = EMAIL["owner"]):
    return await call(email, "PUT", path(session_id), json={"guides": guides})


def question(block: dict, qid: str) -> dict:
    return next(q for q in block["questions"] if q["id"] == qid)


def edits(session_id: str) -> list[tuple]:
    """The Scoring guide versions made for the Class session: (version, body)."""
    return rows(
        "SELECT version, body FROM content_records WHERE kind = 'scoring_guide' "
        "AND class_session_id = %s ORDER BY version",
        session_id,
    )


def pointer(session_id: str) -> list[tuple]:
    return rows(
        "SELECT scoring_guide_id, base_id, pinned_at FROM test_scoring_guides "
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


# The record and the load.


async def test_version_1_is_the_shipped_draft_file_and_the_migrations_literal():
    migration = importlib.import_module("migrations.versions.0122_scoring_guide")
    assert migration.SCORING_GUIDE_V1 == V1
    assert await content.latest_version("scoring_guide") == 1
    found: content.ScoringGuide = await content.get("scoring_guide", 1)
    assert found.model_dump(mode="json") == V1
    assert found.status == "draft"
    assert [step.step for step in found.scale] == [0, 1, 2, 3, 4]
    assert all(5 <= len(q.criteria) <= 8 for q in found.questions)
    assert all(sum(c.weight for c in q.criteria) == 100 for q in found.questions)
    # A guide for every long-answer question of the shipped question set, replacements included,
    # and for the Adapted item templates.
    _, question_set = await content.question_set(None)
    long_rules = {
        item.scoring_rule
        for item in (*question_set.items, *question_set.replacements)
        if item.type == "long"
    }
    assert long_rules == {q.id for q in found.questions if q.kind == "long"}
    assert any(q.kind == "adapted" for q in found.questions)


@pytest.mark.parametrize("count", [4, 9])
async def test_the_load_refuses_a_question_with_fewer_than_5_or_more_than_8_criteria(
    tmp_path, count
):
    body = json.loads(json.dumps(V1))
    body["questions"][0]["criteria"] = [
        {"code": f"K{n}", "text": f"Kriterium {n}", "weight": 1} for n in range(count)
    ]
    (tmp_path / "scoring_guide.json").write_text(json.dumps(body), encoding="utf-8")
    done, refused = await cli.load(tmp_path)
    assert done == []
    assert [line.split(": ")[1] for line in refused] == ["criteria_count"]
    assert await content.latest_version("scoring_guide") == 1


async def test_the_load_refuses_other_shape_errors_as_invalid_record_and_publishes_a_change(
    tmp_path,
):
    weights = json.loads(json.dumps(V1))
    weights["questions"][0]["criteria"][0]["weight"] = 21  # 101 together
    (tmp_path / "scoring_guide.json").write_text(json.dumps(weights), encoding="utf-8")
    assert (await cli.load(tmp_path))[1][0].split(": ")[1] == "invalid_record"
    scale = {**V1, "scale": V1["scale"][:4]}
    (tmp_path / "scoring_guide.json").write_text(json.dumps(scale), encoding="utf-8")
    assert (await cli.load(tmp_path))[1][0].split(": ")[1] == "invalid_record"
    approved = {**V1, "status": "approved"}
    (tmp_path / "scoring_guide.json").write_text(json.dumps(approved), encoding="utf-8")
    assert await cli.load(tmp_path) == (["scoring_guide v2"], [])
    assert await cli.load(tmp_path) == (["scoring_guide unchanged (v2)"], [])


async def test_no_version_is_checked_until_a_control_test_marks_it():
    """AD-27: `is_checked` is the only answer; a version no Control test checked (Story 12.10
    writes `scoring_guide_checks`) is unchecked, and so is any version with no model config."""
    record = await content.latest_version("scoring_guide")
    assert record == 1
    assert await content.is_checked(uuid.uuid4(), None) is False
    assert await content.is_checked(uuid.uuid4(), uuid.uuid4()) is False


# The block.


async def test_a_new_class_session_reads_the_default_guide_unchanged(klass):
    session_id = await new_session(klass)
    block = await read(session_id)
    assert block["version"] == 1 and block["draft"] is True
    assert block["edited"] is False and block["outdated"] is False
    assert block["checked"] is False and block["pinned"] is False
    assert block["open"] is True and block["can_change"] is True
    assert [step["step"] for step in block["scale"]] == [0, 1, 2, 3, 4]
    assert [q["id"] for q in block["questions"]] == [q["id"] for q in V1["questions"]]
    first = question(block, FIRST)
    assert first["changed"] is False
    assert first["guide"] == first["standard_guide"] == V1["questions"][0]["guide"]
    assert [c["code"] for c in first["criteria"]] == [
        c["code"] for c in V1["questions"][0]["criteria"]
    ]
    assert pointer(session_id) == [] and edits(session_id) == []


async def test_an_edit_makes_a_new_version_for_the_session_and_the_earlier_one_stays(
    klass, emitted
):
    session_id = await planned(klass)
    emitted.clear()
    response = await put(session_id, {FIRST: "Se etter forsinkelsen i kjeden.\nSterkt: tall."})
    assert response.status_code == 200, response.text
    block = response.json()
    assert block["edited"] is True and block["version"] > 1
    assert question(block, FIRST)["changed"] is True
    assert question(block, FIRST)["guide"] == "Se etter forsinkelsen i kjeden.\nSterkt: tall."
    assert question(block, FIRST)["standard_guide"] == V1["questions"][0]["guide"]
    assert question(block, SECOND)["changed"] is False
    # The criteria, the scale and the titles are as before.
    assert question(block, FIRST)["criteria"] == [
        {"code": c["code"], "text": c["text"], "weight": c["weight"]}
        for c in V1["questions"][0]["criteria"]
    ]
    [(version, body)] = edits(session_id)
    assert version == block["version"]
    assert body["questions"][1:] == V1["questions"][1:]
    assert body["questions"][0]["criteria"] == V1["questions"][0]["criteria"]
    # The earlier version is unchanged, and the latest default is still version 1.
    assert (await content.get("scoring_guide", 1)).model_dump(mode="json") == V1
    assert await content.latest_version("scoring_guide") == 1
    [(guide_id, base_id, pinned_at)] = pointer(session_id)
    assert str(guide_id) == block["version_id"] and pinned_at is None
    assert base_id == uuid.UUID(f"{SHIPPED}000000000122")
    assert emitted == [("session", session_id)]
    assert {topic for topic, _ in emitted} <= COMMAND_TOPICS["tests.save_scoring_guide"]
    [(details,)] = rows(
        "SELECT change FROM audit_events WHERE action = 'scoring_guide.edited' "
        "AND target_ids->>'class_session_id' = %s",
        session_id,
    )
    assert details == {"scoring_guide_id": block["version_id"], "version": block["version"]}
    assert "Se etter" not in json.dumps(details)
    # A reload keeps it; a second edit builds on it and keeps the first.
    assert await read(session_id) == block
    again = (await put(session_id, {SECOND: "Andre tekst."})).json()
    assert question(again, FIRST)["changed"] is True and question(again, SECOND)["changed"]
    assert len(edits(session_id)) == 2
    # Typed back to the default text, the question reads «Standard» again.
    back = (await put(session_id, {SECOND: V1["questions"][1]["guide"]})).json()
    assert question(back, SECOND)["changed"] is False


async def test_an_unchanged_save_stores_nothing(klass, emitted):
    session_id = await planned(klass)
    emitted.clear()
    response = await put(session_id, {FIRST: V1["questions"][0]["guide"]})
    assert response.status_code == 200
    assert response.json()["edited"] is False
    assert edits(session_id) == [] and pointer(session_id) == [] and emitted == []


@pytest.mark.parametrize(
    ("guides", "fields"),
    [
        ({"nowhere": "Tekst"}, {"nowhere": "unknown_question"}),
        ({FIRST: ""}, {FIRST: "invalid"}),
        ({FIRST: "   \n "}, {FIRST: "invalid"}),
        ({FIRST: "Tekst\u0000"}, {FIRST: "invalid"}),
    ],
)
async def test_an_unknown_question_or_an_empty_text_is_refused(klass, guides, fields):
    session_id = await planned(klass)
    refused = await put(session_id, guides)
    assert refusal(refused) == (422, "validation_error", fields)
    assert edits(session_id) == [] and pointer(session_id) == []


async def test_a_text_over_the_limit_is_refused_by_the_api(klass):
    session_id = await planned(klass)
    refused = await put(session_id, {FIRST: "x" * 4001})
    assert refused.status_code == 422
    assert edits(session_id) == []


async def test_from_the_original_test_deadline_an_edit_is_refused_before_the_sweep(
    klass, monkeypatch
):
    session_id = await planned(klass)
    at(monkeypatch, TEST - MINUTE)
    assert (await put(session_id, {FIRST: "Før fristen."})).status_code == 200
    at(monkeypatch, TEST)
    refused = await put(session_id, {FIRST: "Etter fristen."})
    assert refusal(refused) == (409, "scoring_guide_locked", {"scoring_guide": "locked"})
    assert len(edits(session_id)) == 1
    block = await read(session_id)
    assert block["open"] is False and block["pinned"] is False
    assert question(block, FIRST)["guide"] == "Før fristen."


@pytest.mark.parametrize("role", ["assistant", "lecturer_assistant"])
async def test_an_assistant_lecturer_reads_the_block_but_cannot_save(shared, role):
    session_id = await planned(shared)
    block = await read(session_id, EMAIL[role])
    assert block["can_change"] is False and block["open"] is True
    refused = await put(session_id, {FIRST: "Tekst"}, EMAIL[role])
    assert (refused.status_code, refused.json()["error"]["code"]) == (403, "forbidden")
    assert edits(session_id) == []


async def test_a_stranger_and_a_missing_session_get_the_same_answer(klass):
    session_id = await planned(klass)
    for target in (session_id, str(uuid.uuid4()), "not-an-id"):
        response = await call(EMAIL["outsider"], "GET", path(target))
        assert (response.status_code, response.json()["error"]["code"]) == (403, "forbidden")


async def test_an_archived_class_reads_the_block_as_unchangeable_and_refuses_a_save(klass):
    session_id = await planned(klass)
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, klass)
    assert (await read(session_id))["can_change"] is False
    refused = await put(session_id, {FIRST: "Tekst"})
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "class_archived"


async def test_a_newer_default_leaves_the_edit_in_force_and_says_so(klass):
    session_id = await planned(klass)
    edited = (await put(session_id, {FIRST: "Egen tekst."})).json()
    newer = json.loads(json.dumps(V1))
    newer["questions"][1]["guide"] = "Ny standardtekst."
    await content.publish("scoring_guide", newer)
    block = await read(session_id)
    assert block["version_id"] == edited["version_id"]
    assert block["outdated"] is True
    assert question(block, FIRST)["guide"] == "Egen tekst."
    # A session that never edited reads the new default.
    fresh = await read(await new_session(klass))
    assert fresh["outdated"] is False and fresh["version"] > edited["version"]
    assert question(fresh, SECOND)["guide"] == "Ny standardtekst."


# The Test-deadline lock.


async def test_the_test_deadline_lock_pins_the_edited_guide_once(klass, monkeypatch):
    session_id = await planned(klass)
    edited = (await put(session_id, {FIRST: "Låst tekst."})).json()
    late = TEST + 5 * MINUTE
    assert await sessions.lock_test(uuid.UUID(session_id), now=late) is True
    [(guide_id, _, pinned_at)] = pointer(session_id)
    assert str(guide_id) == edited["version_id"] and pinned_at == TEST
    assert await sessions.lock_test(uuid.UUID(session_id), now=late + MINUTE) is False
    assert pointer(session_id)[0][2] == TEST
    at(monkeypatch, late)
    block = await read(session_id)
    assert block["pinned"] is True and block["open"] is False
    assert block["version_id"] == edited["version_id"]
    assert question(block, FIRST)["guide"] == "Låst tekst."
    refused = await put(session_id, {FIRST: "Etter."})
    assert refusal(refused) == (409, "scoring_guide_locked", {"scoring_guide": "locked"})
    # The database refuses a change of the pinned row too, but lets the editor's id go when the
    # User is deleted (`updated_by` is ON DELETE SET NULL).
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute(
            "UPDATE test_scoring_guides SET pinned_at = NULL WHERE class_session_id = %s",
            session_id,
        )
    execute(
        "UPDATE test_scoring_guides SET updated_by = NULL WHERE class_session_id = %s", session_id
    )
    assert pointer(session_id)[0][2] == TEST


async def test_a_session_that_never_edited_is_pinned_on_the_latest_default(klass):
    session_id = await planned(klass)
    assert await sessions.lock_test(uuid.UUID(session_id), now=TEST) is True
    [(guide_id, base_id, pinned_at)] = pointer(session_id)
    assert guide_id == base_id == uuid.UUID(f"{SHIPPED}000000000122")
    assert pinned_at == TEST
    # A newer default published after the pin does not change what the session uses.
    newer = {**V1, "status": "approved"}
    await content.publish("scoring_guide", newer)
    block = await read(session_id)
    assert block["version"] == 1 and block["pinned"] is True and block["draft"] is True


async def test_the_sweep_imports_the_guide_pinner():
    from app.modules.ops import sweep  # noqa: F401
    from app.modules.tests import guide

    assert guide.pin_guide in sessions._test_pinners


# «Lag kopi».


async def test_a_copy_carries_an_edited_guide_by_its_version_id_but_not_its_pin(klass, monkeypatch):
    flag(monkeypatch, True)
    source = await planned(klass)
    edited = (await put(source, {FIRST: "Kopiert tekst."})).json()
    await sessions.lock_test(uuid.UUID(source), now=TEST)
    copied = await copy(klass, source)
    assert copied.status_code == 201, copied.text
    target = copied.json()["id"]
    [(guide_id, base_id, pinned_at)] = pointer(target)
    assert str(guide_id) == edited["version_id"] and pinned_at is None
    assert base_id == uuid.UUID(f"{SHIPPED}000000000122")
    block = await read(target)
    assert block["version_id"] == edited["version_id"]
    assert question(block, FIRST)["changed"] is True and block["open"] is True
    # A source on the default copies nothing: the copy reads the latest default.
    plain = (await copy(klass, await new_session(klass))).json()["id"]
    assert pointer(plain) == []
