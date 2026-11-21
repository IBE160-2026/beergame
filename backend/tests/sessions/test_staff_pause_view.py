"""Story 8.7 through the api: a Lecturer pauses a Class game from Spillstyring or the Varselbånd
with an agreed time (`POST /api/games/{id}/pause`), changes it (`PUT …/pause/agreed-time`) and ends
the Pause (`DELETE …/pause`). Spillinnsikt reads «Pause siden …, satt av deg.» with the agreed time;
the Students read «Pause til to. 19:00, satt av faglæreren.» and never a name; an Assistant
lecturer and a Student are refused through `platform/authz` (FR-89, AD-2, AD-10, AD-12, AD-19).

One short Class game (`short_game`: two Students, Uke 1 Guided) per test."""

from datetime import datetime, timedelta

from tests.classes.test_classes import LECTURER, OTHER, make
from tests.classes.test_staff import ASSISTANT, EMAIL, call, put_staff
from tests.messaging.helpers import rows
from tests.sessions.test_game_end import _empty, clock, klass, short_game
from tests.sessions.test_game_insight import insight
from tests.sessions.test_overview import overview
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import home

__all__ = ["_empty", "clock", "klass"]

LECTURER_ASSISTANT = EMAIL["lecturer_assistant"]


def db_now() -> datetime:
    [(now,)] = rows("SELECT clock_timestamp()")
    return now


async def staff_pause(who: str, game_id: str, resume_at: datetime | None):
    body = {"resume_at": None if resume_at is None else resume_at.isoformat()}
    return await call(who, "POST", f"/api/games/{game_id}/pause", json=body)


async def change_time(who: str, game_id: str, resume_at: datetime | None):
    body = {"resume_at": None if resume_at is None else resume_at.isoformat()}
    return await call(who, "PUT", f"/api/games/{game_id}/pause/agreed-time", json=body)


async def end(who: str, game_id: str):
    return await call(who, "DELETE", f"/api/games/{game_id}/pause")


def parse(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


async def test_a_lecturer_pauses_with_a_time_changes_it_and_ends_it(klass):
    session_id, game_id, _ = await short_game(klass)
    before = (await insight(LECTURER, game_id)).json()
    assert (before["can_pause"], before["pause"]) == (True, None)
    board = (await overview(LECTURER, session_id)).json()
    assert board["can_pause"] is True
    assert board["play_deadline"] == before["play_deadline"] is not None

    agreed = (db_now() + timedelta(hours=2)).replace(microsecond=0)
    answer = await staff_pause(LECTURER, game_id, agreed)
    assert answer.status_code == 200
    body = answer.json()
    assert body["status"] == "paused"
    pause = body["pause"]
    assert (pause["by"], pause["mine"], parse(pause["resume_at"])) == ("Bard", True, agreed)
    assert body["can_pause"] is True  # «Endre avtalt tid» and «Avslutt pausen» stay

    # Every Student reads the Lecturer's line with the agreed time, and no name.
    for who in (email(0), email(1)):
        game = (await home(who))["game"]
        line = game["pause"]
        assert (line["state"], line["name"], line["staff"], line["mine"]) == (
            "paused",
            None,
            True,
            False,
        )
        assert parse(line["resume_at"]) == agreed
        assert game["can_pause"] is False

    # «Uten avtalt tid» on «Endre avtalt tid» clears it; the line has no time then.
    cleared = await change_time(LECTURER, game_id, None)
    assert cleared.status_code == 200
    assert cleared.json()["pause"]["resume_at"] is None
    assert (await home(email(0)))["game"]["pause"]["resume_at"] is None

    ended = await end(LECTURER, game_id)
    assert ended.status_code == 200
    assert ended.json()["pause"] is None
    line = (await home(email(1)))["game"]["pause"]
    assert (line["state"], line["name"], line["staff"]) == ("ended", None, True)
    assert (await end(LECTURER, game_id)).json()["error"]["code"] == "not_paused"

    actions = [
        action
        for (action,) in rows(
            "SELECT action FROM audit_events WHERE target_ids->>'game_id' = %s ORDER BY id",
            game_id,
        )
    ]
    assert actions == ["game.paused", "game.pause_time_set", "game.resumed"]


async def test_the_lecturer_gives_a_students_pause_a_time(klass):
    _, game_id, _ = await short_game(klass)
    assert (await call(email(0), "POST", f"/api/me/games/{game_id}/pause")).status_code == 200
    student_name = rows("SELECT name FROM users WHERE email = %s", email(0))[0][0]
    paused = (await insight(LECTURER, game_id)).json()["pause"]
    assert (paused["by"], paused["mine"], paused["resume_at"]) == (student_name, False, None)

    agreed = (db_now() + timedelta(hours=1)).replace(microsecond=0)
    assert (await change_time(LECTURER, game_id, agreed)).status_code == 200
    # Only the Lecturer's agreed time shows, and the line then names the Lecturer.
    line = (await home(email(1)))["game"]["pause"]
    assert (line["name"], parse(line["resume_at"])) == (student_name, agreed)
    # A second Pause is told who came first.
    again = await staff_pause(LECTURER, game_id, None)
    assert again.status_code == 409
    assert again.json()["error"]["fields"]["acted_by"]["kind"] == "student"


async def test_a_time_outside_the_range_is_refused(klass):
    _, game_id, _ = await short_game(klass)
    deadline = parse((await insight(LECTURER, game_id)).json()["play_deadline"])
    assert deadline is not None
    for at in (db_now() - timedelta(minutes=1), deadline + timedelta(minutes=1)):
        answer = await staff_pause(LECTURER, game_id, at)
        assert (answer.status_code, answer.json()["error"]["code"]) == (422, "time_out_of_range")
    naive = await call(
        LECTURER, "POST", f"/api/games/{game_id}/pause", json={"resume_at": "2030-01-01T10:00"}
    )
    assert naive.status_code == 422
    assert (await insight(LECTURER, game_id)).json()["pause"] is None


async def test_an_assistant_a_student_and_others_are_refused(klass):
    session_id, game_id, _ = await short_game(klass)
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    soon = db_now() + timedelta(hours=1)
    refused = [
        await staff_pause(ASSISTANT, game_id, None),
        await staff_pause(email(0), game_id, soon),
        await staff_pause(OTHER, game_id, None),
        await staff_pause(LECTURER, "not-an-id", None),
        await change_time(ASSISTANT, game_id, soon),
        await end(ASSISTANT, game_id),
        await end(email(0), game_id),
    ]
    assert {r.status_code for r in refused} == {403}
    assert (await insight(ASSISTANT, game_id)).json()["can_pause"] is False
    assert (await overview(ASSISTANT, session_id)).json()["can_pause"] is False
    # The Student route takes no time: a body with one pauses without it.
    student = await call(
        email(0), "POST", f"/api/me/games/{game_id}/pause", json={"resume_at": soon.isoformat()}
    )
    assert student.status_code == 200
    assert student.json()["pause"]["resume_at"] is None
    assert rows("SELECT resume_at FROM games WHERE id = %s", game_id) == [(None,)]
    # The Assistant lecturer can neither change the time nor end it.
    assert (await change_time(ASSISTANT, game_id, soon)).status_code == 403
    assert (await end(ASSISTANT, game_id)).status_code == 403
    # Nor can a Lecturer who is only an Assistant lecturer in this Class (the Class staff role).
    put_staff(klass, await make(LECTURER_ASSISTANT), "assistant")
    for answer in (
        await staff_pause(LECTURER_ASSISTANT, game_id, None),
        await change_time(LECTURER_ASSISTANT, game_id, soon),
        await end(LECTURER_ASSISTANT, game_id),
    ):
        assert answer.status_code == 403
    assert (await insight(LECTURER_ASSISTANT, game_id)).json()["can_pause"] is False
    assert (await overview(LECTURER_ASSISTANT, session_id)).json()["can_pause"] is False


async def test_a_students_refusal_never_carries_the_lecturers_id(klass):
    _, game_id, _ = await short_game(klass)
    assert (await staff_pause(LECTURER, game_id, None)).status_code == 200
    second = await call(email(0), "POST", f"/api/me/games/{game_id}/pause")
    assert second.status_code == 409
    assert second.json()["error"]["fields"]["acted_by"] == {"kind": "staff", "user_id": None}
    # The Lecturer is told who paused first, by id.
    again = await staff_pause(LECTURER, game_id, None)
    assert again.json()["error"]["fields"]["acted_by"]["user_id"] is not None
    # An omitted time is refused, never read as «Uten avtalt tid».
    omitted = await call(LECTURER, "PUT", f"/api/games/{game_id}/pause/agreed-time", json={})
    assert omitted.status_code == 422
