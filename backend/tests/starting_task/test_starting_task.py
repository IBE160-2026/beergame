"""The Starting task (Story 6.3, FR-85, AD-1, AD-16, AD-23): a seated Student in a locked Class
session answers the pinned content's items once each, scored by computed rules, then the final
question, which records `progress` `starting_task` and ends `briefing_first`. Any other game is
refused alike. The api's clock is fixed and the sweep is handed its `now`."""

import uuid

import pytest

from app.modules.content import service as content
from app.modules.ops import sweep
from app.modules.progress import service as progress
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import call
from tests.sessions.test_dates import START
from tests.sessions.test_lock import MINUTE
from tests.sessions.test_open_games import confirmed, games_of
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import _empty, clock, game_of, home, klass

__all__ = ["_empty", "clock", "klass"]

V1_ITEMS = ["to-ship", "backlog", "position"]


@pytest.fixture(autouse=True)
def only_version_1():
    """Version 1 is the migration's; a test that publishes more removes them again."""
    execute("DELETE FROM content_records WHERE version > 1")
    yield
    execute("DELETE FROM content_records WHERE version > 1")


def path(game_id: str, tail: str = "") -> str:
    return f"/api/me/games/{game_id}/starting-task{tail}"


async def seated_game(klass: str, n: int = 1) -> tuple[str, str]:
    """A locked Class session with `n` seated Students; (session id, Student 0's game id)."""
    session_id, _ = await confirmed(klass, n)
    await sweep.run(START + MINUTE)
    return session_id, (await home(email(0)))["game"]["id"]


async def send(game_id: str, item_id: str, answer, who: str = email(0)):
    return await call(
        who, "POST", path(game_id, "/answers"), json={"item_id": item_id, "answer": answer}
    )


async def test_a_student_answers_each_item_once_and_finishes(klass):
    session_id, game_id = await seated_game(klass)
    first = await call(email(0), "GET", path(game_id))
    assert first.status_code == 200
    task = first.json()
    assert task["version"] == 1 and [i["id"] for i in task["items"]] == V1_ITEMS
    assert task["done"] is False and task["played_before"] is None
    # No answer key before an answer: only the given rows.
    assert all(item["result"] is None for item in task["items"])
    position = task["items"][2]
    assert [(r["label"], r["value"]) for r in position["rows"]] == [
        ("Lager", 0),
        ("Restordre", 13),
        ("På vei", 16),
    ]
    assert position["prompt"] == "Regn posisjonen for én Uke."

    # Wrong, then the same item again: the first answer is kept (stored once).
    wrong = (await send(game_id, "position", 5)).json()["items"][2]["result"]
    assert wrong == {
        "answer": 5,
        "correct": False,
        "expected": 3,
        "terms": [{"sign": 1, "value": 0}, {"sign": -1, "value": 13}, {"sign": 1, "value": 16}],
    }
    again = (await send(game_id, "position", 3)).json()["items"][2]["result"]
    assert again == wrong

    # The final question waits for every item.
    early = await call(email(0), "POST", path(game_id, "/final"), json={"choice": "no"})
    assert early.status_code == 409 and early.json()["error"]["code"] == "items_open"

    # Resume: on another device the answered item shows, the others are open.
    resumed = (await call(email(0), "GET", path(game_id))).json()
    assert [item["result"] is not None for item in resumed["items"]] == [False, False, True]

    right = (await send(game_id, "to-ship", 17)).json()["items"][0]["result"]
    assert right["correct"] is True and right["expected"] == 17
    assert (await send(game_id, "backlog", 13)).json()["items"][1]["result"]["correct"] is True
    assert (await home(email(0)))["game"]["briefing_first"] is True

    done = await call(email(0), "POST", path(game_id, "/final"), json={"choice": "skipped"})
    assert done.status_code == 200
    assert (done.json()["done"], done.json()["played_before"]) == (True, "skipped")
    assert await progress.has_step(
        (await _user(email(0))), uuid.UUID(session_id), progress.Step.STARTING_TASK
    )
    # A repeat changes nothing; the briefing no longer comes first.
    repeat = await call(email(0), "POST", path(game_id, "/final"), json={"choice": "yes"})
    assert repeat.json()["played_before"] == "skipped"
    assert (await game_of(email(0), game_id)).json()["briefing_first"] is False
    stored = _rows(session_id)
    assert stored == [
        ("backlog", 13, True, None, 1),
        ("played_before", None, None, "skipped", 1),
        ("position", 5, False, None, 1),
        ("to-ship", 17, True, None, 1),
    ]


async def _user(address: str) -> uuid.UUID:
    from tests.conftest import TEST_DATABASE_URL, kept_connection

    (found,) = (
        kept_connection(TEST_DATABASE_URL)
        .execute("SELECT id FROM users WHERE email = %s", (address,))
        .fetchone()
    )
    return found


def _rows(session_id: str) -> list[tuple]:
    from tests.conftest import TEST_DATABASE_URL, kept_connection

    return (
        kept_connection(TEST_DATABASE_URL)
        .execute(
            "SELECT item_id, answer, correct, choice, content_version FROM starting_task_answers "
            "WHERE class_session_id = %s ORDER BY item_id",
            (session_id,),
        )
        .fetchall()
    )


async def test_bad_answers_and_unknown_items_are_refused(klass):
    _, game_id = await seated_game(klass)
    for bad in (1.5, "3", None):
        response = await send(game_id, "position", bad)
        assert response.status_code == 422, bad
        assert response.json()["error"]["code"] == "invalid_request"
    missing = await call(email(0), "POST", path(game_id, "/answers"), json={"item_id": "position"})
    assert missing.status_code == 422
    for unknown_id in ("nothing", "played_before"):  # the final question is no item
        unknown = await send(game_id, unknown_id, 3)
        assert unknown.status_code == 422 and unknown.json()["error"]["code"] == "unknown_item"
    choice = await call(email(0), "POST", path(game_id, "/final"), json={"choice": "maybe"})
    assert choice.status_code == 422


async def test_other_games_and_unknown_ids_are_refused_alike(klass):
    session_id, game_id = await seated_game(klass, 5)  # two Class games
    other = next(g[0] for g in games_of(session_id) if g[0] != game_id)
    refusals = [
        await call(email(0), "GET", path(other)),
        await call(email(0), "GET", path(str(uuid.uuid7()))),
        await call(email(0), "GET", path("not-a-uuid")),
        await send(other, "position", 3),
        await call(email(0), "POST", path(other, "/final"), json={"choice": "no"}),
    ]
    assert {r.status_code for r in refusals} == {403}
    assert len({r.content for r in refusals}) == 1
    assert _rows(session_id) == []


async def test_the_session_keeps_the_version_its_lock_pinned(klass):
    """AD-23: a new version reaches sessions locked after it, never one locked before."""
    _, game_id = await seated_game(klass)
    body = (await content.get(content.Kind.STARTING_TASK, 1)).model_dump(mode="json")
    body["items"] = body["items"][2:]  # only the position item
    assert await content.publish("starting_task", body) == 2
    task = (await call(email(0), "GET", path(game_id))).json()
    assert task["version"] == 1 and [i["id"] for i in task["items"]] == V1_ITEMS


async def test_a_session_locked_before_the_pin_takes_the_latest_version(klass):
    session_id, game_id = await seated_game(klass)
    execute(
        "UPDATE class_sessions SET snapshot = jsonb_set(snapshot, '{session_runtime,pins}', "
        "'{}'::jsonb) WHERE id = %s",
        session_id,
    )
    body = (await content.get(content.Kind.STARTING_TASK, 1)).model_dump(mode="json")
    body["items"] = body["items"][2:]
    await content.publish("starting_task", body)
    task = (await call(email(0), "GET", path(game_id))).json()
    assert task["version"] == 2 and [i["id"] for i in task["items"]] == ["position"]
    # Once begun, the Student stays on that version even if another is published.
    await send(game_id, "position", 3)
    await content.publish("starting_task", body)
    assert (await call(email(0), "GET", path(game_id))).json()["version"] == 2


async def test_a_finished_game_with_no_orders_still_offers_the_starting_task(klass):
    """FR-85: the game's end does not close the task; `briefing_first` holds until it is done."""
    session_id, game_id = await seated_game(klass)
    execute(
        "INSERT INTO game_weeks (game_id, week, finished, state) VALUES (%s, 1, true, '{}')",
        game_id,
    )
    assert (await home(email(0)))["game"]["briefing_first"] is True
    assert (await call(email(0), "GET", path(game_id))).status_code == 200
    for item_id, answer in (("to-ship", 17), ("backlog", 13), ("position", 3)):
        assert (await send(game_id, item_id, answer)).status_code == 200
    done = await call(email(0), "POST", path(game_id, "/final"), json={"choice": "unknown"})
    assert done.json()["done"] is True
    assert (await home(email(0)))["game"]["briefing_first"] is False
