"""The Group debrief (Story 9.11, FR-43, FR-16, AD-8, AD-9, AD-12, AD-21).

In a Group-debrief Class session whose finished Class game at least two active Students played
(each with an Order of their own), the first open makes the Debrief session shared: the opener
joined, the game's other Students told. Joined Students share one step pointer over steps 1 to 3:
it moves when all have finished the step, or when the opener moves on after the minimum wait.
From the reflection questions on, each Student works alone. A Personal debrief, or a game with
one active Student, has none of it. One short Class game, its Students ordering themselves, then
marked finished, serves each test."""

import uuid
from datetime import UTC, datetime

from app.modules.games import commands as games_commands
from app.modules.ops import sweep
from app.modules.progress import service as progress
from app.modules.sessions import service as sessions
from app.platform.db import get_sessionmaker
from app.platform.events import stream
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.debrief.test_debrief import LOCKED, finish, home, open_, refused
from tests.debrief.test_quiz import conflict
from tests.games.helpers import play_week
from tests.messaging.helpers import rows
from tests.sessions.test_allocation import open_ as draw
from tests.sessions.test_allocation import students
from tests.sessions.test_allocation_confirm import confirm
from tests.sessions.test_dates import OUTSIDER
from tests.sessions.test_lock import _empty, dated
from tests.sessions.test_start_game import start, task_done
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]


SHORT = {
    "guided_weeks": 0,
    "weeks": 2,
    "demand": {"kind": "step", "start": 4, "new_level": 8, "change_week": 2},
}
"""Two Uker the Students order themselves; the game finishes with the second."""


async def played(klass: str, n: int, ordering: int, mode: str = "group") -> tuple[str, str]:
    """A locked Class session with `n` Students in one Class game of two Uker, played (the first
    `ordering` Students order themselves, the rest of the Seats by rule) to its end. Returns the
    session and game ids."""
    seated = await students(klass, n)
    session_id = await dated(klass)
    saved = await call(
        LECTURER,
        "PUT",
        f"/api/class-sessions/{session_id}",
        json={"ai_mode": "rule_based", "debrief_mode": mode, "game_settings": SHORT},
    )
    assert saved.status_code == 200, saved.text
    assert (await confirm(session_id, (await draw(session_id)).json()["draft"])).status_code == 200
    await sweep.run(LOCKED)
    game_id = (await home(email(0)))["game"]["id"]
    for user_id in seated:
        await task_done(user_id, session_id)
    assert (await start(email(0), game_id)).status_code == 200
    for week in (1, 2):
        for i in range(ordering):
            role = (await home(email(i)))["game"]["role"]
            await games_commands.place_order(game_id, role, week, 4, "student", actor=seated[i])
        if ordering < n:
            # The other Student Seats by rule; the AI players have ordered at the Week's opening.
            await play_week(game_id)
    finish(game_id)
    for each in seated:
        await progress.record_step(
            each, uuid.UUID(session_id), progress.Step.CLASS_GAME, datetime.now(UTC)
        )
    return session_id, game_id


def user_id(who: str) -> uuid.UUID:
    [(found,)] = rows("SELECT id FROM users WHERE email = %s", who)
    return found


def debrief_step(item: dict) -> dict:
    return next(s for s in item["steps"] if s["step"] == "debrief")


async def mail_context(who: str, session_id: str):
    async with get_sessionmaker()() as s:
        return await sessions.group_debrief_opened_mail_context(
            s, user_id(who), uuid.UUID(session_id), datetime.now(UTC)
        )


async def test_the_group_shares_a_step_pointer(klass, emitted):
    session_id, _ = await played(klass, 3, ordering=3)
    a, b, c = email(0), email(1), email(2)

    # A opens: shared, A the opener and joined; B and C are told (notice, `user` event) and their
    # Hjem offers to join.
    emitted.clear()
    opened = await open_(a, session_id)
    assert opened.status_code == 200
    mine = opened.json()
    debrief_id = mine["id"]
    path = f"/api/debriefs/{debrief_id}"
    group = mine["group"]
    assert (group["step"], group["joined"], group["opener"]) == (1, True, True)
    assert [(m["you"], m["sent"], m["done"]) for m in group["members"]] == [(True, False, False)]
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["debrief.open"] == {"debrief", "user"}
    told = rows(
        "SELECT user_id, dedupe_key FROM notices WHERE kind = 'group_debrief_opened' ORDER BY 1"
    )
    assert {u for u, _ in told} == {user_id(b), user_id(c)}
    assert all(key.startswith(f"group_debrief_opened:{debrief_id}:") for _, key in told)
    assert debrief_step(await home(b))["group_open"] is True
    assert debrief_step(await home(a))["group_open"] is False
    assert (await mail_context(b, session_id)) is not None

    # The event stream follows the Debrief of the Student's own game only.
    assert debrief_id in (await stream.resolve_scope(user_id(b))).debriefs
    await make(OUTSIDER, roles=())
    assert debrief_id not in (await stream.resolve_scope(user_id(OUTSIDER))).debriefs

    # B opens the page: the same session, not joined, no names; then joins.
    seen = (await open_(b, session_id)).json()["group"]
    assert (seen["joined"], seen["opener"], seen["members"]) == (False, False, [])
    emitted.clear()
    joined = await call(b, "POST", f"{path}/join")
    assert joined.status_code == 200
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["debrief.join"]
    assert joined.json()["group"]["joined"] is True
    emitted.clear()
    assert (await call(b, "POST", f"{path}/join")).status_code == 200
    assert emitted == []
    assert debrief_step(await home(b))["group_open"] is False
    assert (await mail_context(b, session_id)) is None
    refused(await call(OUTSIDER, "POST", f"{path}/join"), "forbidden")

    # A sends; B writes. A sees who has sent, never the text; the reveal stays locked for A.
    emitted.clear()
    sent = await call(a, "POST", f"{path}/explanation", json={"text": "Min forklaring."})
    assert sent.status_code == 201
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["debrief.save_explanation"]
    group = (await call(a, "GET", path)).json()["group"]
    assert group["step"] == 1
    assert [(m["you"], m["sent"]) for m in group["members"]] == [(True, True), (False, False)]
    assert "Min forklaring" not in str((await call(b, "GET", path)).json())
    refused(await call(a, "GET", f"{path}/steps/2"), "step_locked")
    refused(await call(a, "GET", f"{path}/reflection"), "step_locked")
    refused(await call(b, "GET", f"{path}/steps/2"), "explanation_required")

    # B sends: every joined Student has finished step 1, so the pointer moves to 2.
    assert (await call(b, "POST", f"{path}/explanation", json={"text": "Min."})).status_code == 201
    group = (await call(a, "GET", path)).json()["group"]
    assert group["step"] == 2 and group["move_on_at"] > group["step_opened_at"]
    assert (await call(a, "GET", f"{path}/steps/2")).status_code == 200
    refused(await call(a, "GET", f"{path}/steps/3"), "step_locked")

    # Finishing a step: C (not joined) is refused, a step not open yet is refused.
    refused(await call(c, "POST", f"{path}/steps/2/done"), "explanation_required")
    conflict(await call(a, "POST", f"{path}/steps/3/done"), "step_not_open")
    emitted.clear()
    done = await call(a, "POST", f"{path}/steps/2/done")
    assert done.status_code == 200 and done.json()["group"]["step"] == 2
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["debrief.complete_step"]
    emitted.clear()
    assert (await call(a, "POST", f"{path}/steps/2/done")).status_code == 200
    assert emitted == []

    # The opener moves on: too early first, with the time it becomes possible; then, once the
    # step has been open the wait, for everyone. Nobody else may.
    early = await call(a, "POST", f"{path}/move-on")
    conflict(early, "too_early")
    assert early.json()["error"]["fields"]["available_at"]
    refused(await call(b, "POST", f"{path}/move-on"), "forbidden")
    execute("UPDATE debrief_sessions SET step_opened_at = step_opened_at - interval '1 hour'")
    emitted.clear()
    moved = await call(a, "POST", f"{path}/move-on")
    assert moved.status_code == 200 and moved.json()["group"]["step"] == 3
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["debrief.move_on"]
    assert (await call(b, "GET", f"{path}/steps/3")).status_code == 200
    # A step the pointer has passed is no longer open.
    conflict(await call(b, "POST", f"{path}/steps/2/done"), "step_not_open")

    # A late joiner without an Explanation stays on step 1; after saving, they enter step 3.
    assert (await call(c, "POST", f"{path}/join")).status_code == 200
    refused(await call(c, "GET", f"{path}/steps/2"), "explanation_required")
    assert (await call(c, "POST", f"{path}/explanation", json={"text": "Sent."})).status_code == 201
    assert (await call(c, "GET", f"{path}/steps/3")).status_code == 200
    refused(await call(c, "GET", f"{path}/reflection"), "step_locked")

    # Everyone finishes step 3: the pointer reaches 4, and each works alone from there.
    for who in (a, b, c):
        assert (await call(who, "POST", f"{path}/steps/3/done")).status_code == 200
    assert (await call(c, "GET", path)).json()["group"]["step"] == 4
    assert (await call(c, "GET", f"{path}/reflection")).status_code == 200
    conflict(await call(a, "POST", f"{path}/steps/3/done"), "step_not_open")
    assert (await call(a, "POST", f"{path}/move-on")).json()["group"]["step"] == 4


async def test_a_personal_debrief_shares_nothing(klass):
    session_id, _ = await played(klass, 2, ordering=2, mode="personal")
    a = email(0)
    opened = (await open_(a, session_id)).json()
    path = f"/api/debriefs/{opened['id']}"
    assert opened["group"] is None
    assert rows("SELECT count(*) FROM notices WHERE kind = 'group_debrief_opened'") == [(0,)]
    conflict(await call(a, "POST", f"{path}/join"), "not_group")
    conflict(await call(a, "POST", f"{path}/move-on"), "not_group")
    assert (await call(a, "POST", f"{path}/explanation", json={"text": "Min."})).status_code == 201
    conflict(await call(a, "POST", f"{path}/steps/2/done"), "not_group")
    # No pointer gate: the reflection questions follow the Explanation at once.
    assert (await call(a, "GET", f"{path}/reflection")).status_code == 200
    assert debrief_step(await home(email(1)))["group_open"] is False


async def test_one_active_student_opens_a_personal_debrief(klass):
    session_id, _ = await played(klass, 2, ordering=1)
    opened = (await open_(email(1), session_id)).json()
    assert opened["group"] is None
    assert rows("SELECT shared FROM debrief_sessions") == [(False,)]
