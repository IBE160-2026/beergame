"""Open the Individual test with the own-work statement (Story 11.3, FR-51, FR-45, FR-5, AD-9,
AD-12, AD-16, AD-23).

`GET /api/me/class-sessions/{id}/test` answers `statement` (no item), `open` (the attempt's frozen
items) or `closed`; `POST …` accepts the statement through `tests.commands.open_attempt`: one
`test_attempts` row with the pinned question set version and selection, the frozen item list and
the effective Test deadline, the Debrief follow-up closed in the same transaction. The gate is the
`replay` step. The api's clock is fixed and moved by hand; the database clock is never read."""

import asyncio
import uuid

from app.modules.debrief import follow_up
from app.modules.identity.schemas import AccountRole
from app.modules.ops import sweep
from app.modules.progress import service as progress
from app.modules.tests import commands
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import rows
from tests.sessions.test_allocation import open_
from tests.sessions.test_allocation_confirm import confirm
from tests.sessions.test_dates import DAY, PLAN, START, TEST, at, save
from tests.sessions.test_lock import MINUTE, _empty, dated
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import home

__all__ = ["_empty", "clock", "emitted", "klass"]

BEFORE = ("class_game", "debrief", "quiz_passed", "replay")


def path(session_id: str) -> str:
    return f"/api/me/class-sessions/{session_id}/test"


async def replayed(user_id: uuid.UUID, session_id: str) -> None:
    for step in BEFORE:
        await progress.record_step(user_id, uuid.UUID(session_id), step, NOW)


def attempts(session_id: str) -> list[tuple]:
    return rows(
        "SELECT id::text, user_id, question_set_version, selection, items, statement_accepted_at, "
        "effective_deadline, status FROM test_attempts WHERE class_session_id = %s",
        session_id,
    )


async def locked_session(klass: str, n: int = 2) -> tuple[str, list]:
    session_id, seated = await confirmed(klass, n)
    await sweep.run(START + MINUTE)  # locks the session and pins its question set selection
    return session_id, seated


def code(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


async def test_the_test_opens_after_the_replay_with_the_statement_first_and_once(klass, emitted):
    session_id, seated = await locked_session(klass)
    me = email(0)

    # Before the Replay: the step is locked on Hjem and the api refuses both ways (AD-16).
    test_step = next(s for s in (await home(me))["steps"] if s["step"] == "test")
    assert test_step["state"] == "locked"
    assert code(await call(me, "GET", path(session_id))) == (403, "replay_required")
    assert code(await call(me, "POST", path(session_id))) == (403, "replay_required")
    await progress.record_step(seated[0], uuid.UUID(session_id), "class_game", NOW)
    assert code(await call(me, "POST", path(session_id))) == (403, "replay_required")
    assert attempts(session_id) == []

    # With the Replay: the statement, and no item before it is accepted.
    await replayed(seated[0], session_id)
    statement = await call(me, "GET", path(session_id))
    assert statement.status_code == 200
    assert statement.json() == {
        "state": "statement",
        "test_deadline": TEST.isoformat().replace("+00:00", "Z"),
        "opened_at": None,
        "items": [],
    }
    assert not await follow_up.closed(seated[0], uuid.UUID(session_id))

    # Accepted: one attempt, the frozen items in the set's order, the follow-up closed (FR-45).
    emitted.clear()
    opened = await call(me, "POST", path(session_id))
    assert opened.status_code == 201
    body = opened.json()
    assert body["state"] == "open" and body["opened_at"] is not None
    [(attempt_id, user_id, version, selection, items, accepted, deadline, status)] = attempts(
        session_id
    )
    [(pin,)] = rows(
        "SELECT snapshot->'session_runtime'->'pins'->'question_set' FROM class_sessions "
        "WHERE id = %s",
        session_id,
    )
    assert (user_id, status, accepted, deadline) == (seated[0], "open", NOW, TEST)
    assert (version, selection) == (pin["version"], pin)
    assert [item["id"] for item in items] == [item["id"] for item in body["items"]]
    assert [item["number"] for item in body["items"]] == list(range(1, len(items) + 1))
    assert all(set(item) == {"id", "number", "type", "title"} for item in body["items"])
    assert all(item["weight"] == pin["weights"][item["id"]] for item in items)
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["tests.open_attempt"]
    assert emitted == [("user", str(seated[0]))]  # once: the follow-up's closure carries it
    assert await follow_up.closed(seated[0], uuid.UUID(session_id))

    # Again and on another device: the same attempt, no statement, nothing new emitted.
    emitted.clear()
    again = await call(me, "POST", path(session_id))
    assert (again.status_code, again.json()) == (200, body)
    assert (await call(me, "GET", path(session_id))).json() == body
    assert len(attempts(session_id)) == 1 and attempts(session_id)[0][0] == attempt_id
    assert emitted == []


async def test_two_opens_at_once_make_one_attempt(klass):
    session_id, seated = await locked_session(klass)
    await replayed(seated[0], session_id)
    first, second = await asyncio.gather(
        call(email(0), "POST", path(session_id)), call(email(0), "POST", path(session_id))
    )
    assert sorted([first.status_code, second.status_code]) == [200, 201]
    assert first.json() == second.json()
    assert len(attempts(session_id)) == 1


async def test_an_open_that_lost_the_race_returns_the_attempt_made_first(klass, monkeypatch):
    """The unique key, not the read before it, keeps one attempt: an open that read no attempt
    just before another committed conflicts on insert and answers the other one (200)."""
    session_id, seated = await locked_session(klass)
    await replayed(seated[0], session_id)
    made = await call(email(0), "POST", path(session_id))
    real = commands.attempt_of
    reads = []

    async def stale_once(s, user_id, class_session_id):
        reads.append(user_id)
        return None if len(reads) == 1 else await real(s, user_id, class_session_id)

    monkeypatch.setattr(commands, "attempt_of", stale_once)
    raced = await call(email(0), "POST", path(session_id))
    assert (raced.status_code, raced.json()) == (200, made.json())
    assert len(reads) == 2 and len(attempts(session_id)) == 1


async def test_after_the_test_deadline_with_no_attempt_it_is_closed(klass, monkeypatch):
    session_id, seated = await locked_session(klass)
    await replayed(seated[0], session_id)
    await replayed(seated[1], session_id)
    assert (await call(email(1), "POST", path(session_id))).status_code == 201
    at(monkeypatch, TEST)
    closed = await call(email(0), "GET", path(session_id))
    assert closed.json()["state"] == "closed" and closed.json()["items"] == []
    assert code(await call(email(0), "POST", path(session_id))) == (409, "test_deadline_passed")
    assert [row[1] for row in attempts(session_id)] == [seated[1]]
    # A Student who opened it in time still reads their items, and opening again is no refusal.
    assert (await call(email(1), "GET", path(session_id))).json()["state"] == "open"
    assert (await call(email(1), "POST", path(session_id))).status_code == 200


async def test_no_one_else_reaches_an_attempt_and_a_refusal_reveals_nothing(klass):
    session_id, seated = await locked_session(klass)
    await replayed(seated[0], session_id)
    assert (await call(email(0), "POST", path(session_id))).status_code == 201
    await make("admin@x.no", roles=(AccountRole.admin,))
    unknown = str(uuid.uuid7())
    for who, target in (
        (email(1), session_id),  # another Student of the Class, no Replay
        (LECTURER, session_id),  # the Class's owner
        ("admin@x.no", session_id),  # the Admin, no membership
        (email(0), unknown),  # a session that does not exist
        (email(0), "not-an-id"),
    ):
        for method in ("GET", "POST"):
            refused = await call(who, method, path(target))
            if who == email(1):
                # Their own session: the gate, never the other Student's attempt.
                assert code(refused) == (403, "replay_required")
            else:
                assert code(refused) == (403, "forbidden")
    assert len(attempts(session_id)) == 1


async def test_items_taken_out_are_not_in_the_attempt(klass):
    session_id, seated = await confirmed(klass, 1)
    block = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}/question-set")).json()
    out, keep = block["items"][0], block["items"][1]
    weights = {item["id"]: item["weight"] for item in block["items"]}
    weights[keep["id"]] += weights[out["id"]]
    saved = await call(
        LECTURER,
        "PUT",
        f"/api/class-sessions/{session_id}/question-set",
        json={
            "weights": weights,
            "excluded": [out["id"]],
            "adapted_weight": block["adapted"]["weight"],
        },
    )
    assert saved.status_code == 200, saved.text
    await sweep.run(START + MINUTE)
    await replayed(seated[0], session_id)
    opened = (await call(email(0), "POST", path(session_id))).json()
    ids = [item["id"] for item in opened["items"]]
    assert out["id"] not in ids
    assert ids == [item["id"] for item in block["items"] if item["id"] != out["id"]]
    [row] = attempts(session_id)
    assert next(i for i in row[4] if i["id"] == keep["id"])["weight"] == weights[keep["id"]]


async def test_a_moved_test_deadline_moves_open_attempts(klass):
    session_id, seated = await confirmed(klass, 2)
    other_id = await dated(klass)  # a second Class session of the same Students
    assert (await confirm(other_id, (await open_(other_id)).json()["draft"])).status_code == 200
    await sweep.run(START + MINUTE)
    for user, session in ((seated[0], session_id), (seated[1], session_id), (seated[0], other_id)):
        await replayed(user, session)
    for who, session in ((email(0), session_id), (email(1), session_id), (email(0), other_id)):
        assert (await call(who, "POST", path(session))).status_code == 201
    # A handed-in attempt keeps the deadline it had (Story 11.10 writes these).
    execute(
        "UPDATE test_attempts SET status = 'submitted', submitted_at = %s WHERE user_id = %s",
        NOW,
        seated[1],
    )
    later = TEST + 2 * DAY
    moved = await save(session_id, {**PLAN, "test_deadline": later})
    assert moved.status_code == 200, moved.text
    deadlines = {row[1]: row[6] for row in attempts(session_id)}
    assert deadlines == {seated[0]: later, seated[1]: TEST}
    assert [row[6] for row in attempts(other_id)] == [TEST]  # another Class session: untouched
    assert (await call(email(0), "GET", path(session_id))).json()["test_deadline"] == (
        later.isoformat().replace("+00:00", "Z")
    )


async def test_a_session_locked_before_the_pin_opens_on_the_selection_in_force(klass):
    session_id, seated = await locked_session(klass, 1)
    execute(
        "UPDATE class_sessions SET snapshot = snapshot #- '{session_runtime,pins,question_set}' "
        "WHERE id = %s",
        session_id,
    )
    await replayed(seated[0], session_id)
    opened = (await call(email(0), "POST", path(session_id))).json()
    block = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}/question-set")).json()
    [row] = attempts(session_id)
    assert row[2] == block["version"]
    assert [item["id"] for item in opened["items"]] == [
        item["id"] for item in block["items"] if not item["excluded"]
    ]
    assert {item["id"]: item["weight"] for item in row[4]} == {
        item["id"]: item["weight"] for item in block["items"] if not item["excluded"]
    }
