"""Story 8.9 through the api: a Lecturer gives one Student Tilrettelegging on the Studentside
(`/api/class-sessions/{id}/students/{user_id}[/adjustment]`); it is stored, audited and announced,
the Student's Class game recomputes the open turn times at once, the Student alone reads it on Hjem,
and Spillinnsikt marks the Seat for the Lecturer only (FR-17, FR-36, FR-89, AD-8, AD-12, AD-14,
AD-15, UX-DR52, UX-DR53). Also the Oversikt's `_next_due` over every waited-for Seat (Story 8.1's
deferred item). One short Class game (`three_students_in_uke_2`) for the flow."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.games.service import ClassGameSummary, GameStatus, SummaryWait
from app.modules.sessions.overview import _next_due
from app.platform import events
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.messaging.helpers import rows
from tests.sessions.test_dates import OUTSIDER
from tests.sessions.test_game_end import _empty, clock, klass
from tests.sessions.test_game_insight import insight
from tests.sessions.test_orders import code, order
from tests.sessions.test_overview import overview
from tests.sessions.test_pause_view import three_students_in_uke_2
from tests.sessions.test_student_home import home

__all__ = ["_empty", "clock", "klass"]

HOUR = timedelta(hours=1)


@pytest.fixture
def emitted(monkeypatch) -> list[tuple[str, str]]:
    """Every `events.emit` call, still emitted."""
    calls: list[tuple[str, str]] = []
    original = events.emit

    async def spy(session, topic, item_id, version=None):
        calls.append((topic, item_id))
        await original(session, topic, item_id, version)

    monkeypatch.setattr(events, "emit", spy)
    return calls


def user_id(address: str) -> str:
    return str(rows("SELECT id FROM users WHERE email = %s", address)[0][0])


def page_path(session_id: str, student: str) -> str:
    return f"/api/class-sessions/{session_id}/students/{student}"


async def save(who: str, session_id: str, student: str, body: dict):
    return await call(who, "PUT", f"{page_path(session_id, student)}/adjustment", json=body)


def due_and_insert(game_id: str, user: str) -> tuple:
    [found] = rows(
        "SELECT t.wait_started_at, t.takeover_due_at, t.insert_allowed_at FROM seat_turns t "
        "JOIN seats s ON s.id = t.seat_id JOIN games g ON g.id = t.game_id "
        "WHERE t.game_id = %s AND t.week = 2 AND s.id IN (SELECT o.seat_id FROM seat_occupancy o "
        "WHERE o.user_id = %s)",
        game_id,
        user,
    )
    return found


async def test_a_lecturer_gives_a_student_more_time_and_the_game_follows_at_once(klass):
    session_id, game_id, by_role = await three_students_in_uke_2(klass)
    (sara_role, sara), (_, third), (jonas_role, jonas) = by_role.items()
    jonas_id = user_id(jonas)

    # The Studentside: no Tilrettelegging yet, the class share for the form's help line.
    page = await call(LECTURER, "GET", page_path(session_id, jonas_id))
    assert page.status_code == 200
    body = page.json()
    assert (body["user_id"], body["adjustment"], body["class_share"]) == (jonas_id, None, 80)
    assert body["name"] == rows("SELECT name FROM users WHERE email = %s", jonas)[0][0]

    # Sara orders Uke 2: the game waits for Jonas on the class limit.
    assert (await order(sara, game_id, 2, {"order": 4})).status_code in (200, 204)
    wait, due, insert = due_and_insert(game_id, jonas_id)
    assert due == insert == wait + 24 * HOUR

    saved = await save(LECTURER, session_id, jonas_id, {"time_factor": 2, "share_percent": 60})
    assert saved.status_code == 200
    assert saved.json()["adjustment"] == {"time_factor": 2.0, "share_percent": 60}
    # Recomputed in the same request: his own limit is twice the class's.
    assert due_and_insert(game_id, jonas_id) == (wait, wait + 48 * HOUR, wait + 48 * HOUR)
    # The Varselbånd follows: the game's earliest due time is now another Student's.
    alert = (await overview(LECTURER, session_id)).json()["alert"]
    assert alert["game_id"] == game_id and alert["user_id"] != jonas_id
    # Audited by ids and values; no name.
    [(actor, change, target)] = rows(
        "SELECT actor_user_id, change, target_ids FROM audit_events "
        "WHERE action = 'student_adjustment.saved' AND target_ids->>'user_id' = %s",
        jonas_id,
    )
    assert str(actor) == user_id(LECTURER)
    assert change == {"time_factor": "2.0", "share_percent": 60, "was": None}
    assert target == {"class_session_id": session_id, "user_id": jonas_id}

    # Only Jonas reads it on Hjem; the others read nothing of it.
    mine = await home(jonas)
    assert mine["adjustment"] == {"time_factor": 2.0, "share_percent": 60}
    for other in (sara, third):
        assert (await home(other))["adjustment"] is None

    # Spillinnsikt marks his Seat for the Lecturer, and the names lead to the Studentside.
    seen = (await insight(LECTURER, game_id)).json()
    assert seen["can_adjust"] is True
    marked = {seat["role"] for seat in seen["seats"] if seat["extra_time"]}
    assert marked == {jonas_role}
    # An Assistant lecturer sees neither. Story 12.5: they open the Studentside, but without
    # «Tilrettelegging» and «Frister»; they cannot save it, like an outsider.
    assistant = await make(ASSISTANT, roles=())
    put_staff(klass, assistant, "assistant")
    as_assistant = (await insight(ASSISTANT, game_id)).json()
    assert as_assistant["can_adjust"] is False
    assert not any(seat["extra_time"] for seat in as_assistant["seats"])
    page = await call(ASSISTANT, "GET", page_path(session_id, jonas_id))
    assert page.status_code == 200 and page.headers["cache-control"] == "no-store"
    body = page.json()
    assert (body["can_manage"], body["adjustment"], body["deadlines"]) == (False, None, None)
    assert (await call(LECTURER, "GET", page_path(session_id, jonas_id))).json()["can_manage"]
    await make(OUTSIDER, roles=())
    for who in (OUTSIDER, sara):
        assert code(await call(who, "GET", page_path(session_id, jonas_id))) == (403, "forbidden")
    for who in (ASSISTANT, OUTSIDER, sara):
        refused = await save(who, session_id, jonas_id, {"time_factor": 3})
        assert code(refused) == (403, "forbidden")

    # Back to the class: «Som klassen» and the class share store no Tilrettelegging.
    back = await save(LECTURER, session_id, jonas_id, {"time_factor": 1, "share_percent": 80})
    assert back.json()["adjustment"] is None
    assert back.headers["cache-control"] == "no-store"
    # Nothing about him is kept; the audit says what it was.
    assert rows("SELECT count(*) FROM student_adjustments WHERE user_id = %s", jonas_id) == [(0,)]
    [last] = rows(
        "SELECT change FROM audit_events WHERE action = 'student_adjustment.saved' "
        "AND target_ids->>'user_id' = %s ORDER BY id DESC LIMIT 1",
        jonas_id,
    )
    assert last[0]["was"] == {"time_factor": "2.0", "share_percent": 60}
    assert due_and_insert(game_id, jonas_id) == (wait, wait + 24 * HOUR, wait + 24 * HOUR)
    assert (await home(jonas))["adjustment"] is None


async def test_the_form_is_judged_and_only_students_of_the_class_have_a_studentside(klass, emitted):
    session_id, _, by_role = await three_students_in_uke_2(klass)
    jonas = list(by_role.values())[-1]
    jonas_id = user_id(jonas)
    for body, fields in (
        ({"time_factor": 1.2}, {"time_factor": "not_offered"}),
        ({"time_factor": 0.5}, {"time_factor": "not_offered"}),
        ({"time_factor": 1.5, "share_percent": 81}, {"share_percent": "out_of_range"}),
        ({"time_factor": 1.5, "share_percent": -1}, {"share_percent": "out_of_range"}),
    ):
        refused = await save(LECTURER, session_id, jonas_id, body)
        assert code(refused) == (422, "invalid_adjustment")
        assert refused.json()["error"]["fields"] == fields
    # No field for a reason: an unknown field is refused, nothing is stored.
    extra = await save(LECTURER, session_id, jonas_id, {"time_factor": 2, "reason": "x"})
    assert extra.status_code == 422
    assert rows("SELECT count(*) FROM student_adjustments WHERE user_id = %s", jonas_id) == [(0,)]
    # A share of 0 and 1,5 × are kept; Hjem says only what differs from the class.
    saved = await save(LECTURER, session_id, jonas_id, {"time_factor": 1.5, "share_percent": 0})
    assert saved.json()["adjustment"] == {"time_factor": 1.5, "share_percent": 0}
    assert (await home(jonas))["adjustment"] == {
        "time_factor": 1.5,
        "share_percent": 0,
    }
    emitted.clear()
    only_share = await save(LECTURER, session_id, jonas_id, {"time_factor": 1, "share_percent": 50})
    # The Student's Hjem and the Class session's staff pages hear of it, also with no turn moved.
    assert {("user", jonas_id), ("session", session_id)} <= set(emitted)
    assert only_share.json()["adjustment"] == {"time_factor": 1.0, "share_percent": 50}
    assert (await home(jonas))["adjustment"] == {
        "time_factor": None,
        "share_percent": 50,
    }
    # The class lowers its share below his: his reads as the class's own, never above it.
    execute("UPDATE class_sessions SET required_share_percent = 40 WHERE id = %s", session_id)
    assert (await home(jonas))["adjustment"] is None
    page = (await call(LECTURER, "GET", page_path(session_id, jonas_id))).json()
    assert (page["class_share"], page["adjustment"]) == (40, None)
    # A Lecturer of another Class is refused like anyone outside it.
    await make("annen-faglaerer@x.no")
    assert code(await call("annen-faglaerer@x.no", "GET", page_path(session_id, jonas_id))) == (
        403,
        "forbidden",
    )
    other = await save("annen-faglaerer@x.no", session_id, jonas_id, {"time_factor": 3})
    assert code(other) == (403, "forbidden")
    # The Lecturer's own id, a stranger and a malformed id: not a Student of the Class.
    for other in (user_id(LECTURER), str(uuid.uuid7()), "not-an-id"):
        assert code(await call(LECTURER, "GET", page_path(session_id, other))) == (
            403,
            "forbidden",
        )
    # An archived Class takes no change.
    execute("UPDATE classes SET archived_at = now() WHERE id = %s", klass)
    archived = await save(LECTURER, session_id, jonas_id, {"time_factor": 2})
    assert code(archived) == (409, "class_archived")


# `_next_due` (pure): every waited-for Seat's own due time counts.

NOW = datetime(2026, 11, 22, 12, tzinfo=UTC)


def summary(*dues: datetime | None, status: GameStatus = GameStatus.WAITING) -> ClassGameSummary:
    waits = tuple(
        SummaryWait(role=role, user_id=None, since=NOW - HOUR, takeover_due_at=due)
        for role, due in zip(("retailer", "wholesaler", "factory"), dues, strict=False)
    )
    found = [due for due in dues if due is not None]
    return ClassGameSummary(
        game_id=uuid.uuid7(),
        game_number=1,
        status=status,
        week=2,
        version=1,
        chain_cost=None,
        wait_started_at=NOW - HOUR,
        waiting_for=waits,
        seats=(),
        takeover_due_at=min(found, default=None),
    )


def test_the_oversikt_reads_again_at_the_next_seats_due_time():
    # The game's earliest due time has passed (the sweep acts on it), a later Seat's is ahead.
    mixed = summary(NOW - HOUR, NOW + 24 * HOUR)
    assert _next_due([mixed], NOW) == NOW + 24 * HOUR
    assert _next_due([mixed, summary(NOW + 2 * HOUR)], NOW) == NOW + 2 * HOUR
    # A paused game and a game with nothing ahead give nothing.
    assert _next_due([summary(NOW + HOUR, status=GameStatus.PAUSED)], NOW) is None
    assert _next_due([summary(NOW - HOUR, None)], NOW) is None
