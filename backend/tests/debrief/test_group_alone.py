"""Continue alone when the group is not there (Story 9.12, FR-43, AD-8, AD-9, AD-21).

A Student of a shared Debrief session goes on as a Personal debrief by leaving (joined or not),
by dropping out (two minutes without an SSE heartbeat, judged by a command or the sweep) or by the
sweep's 48-hour fallback; final, with what they saved kept and no pointer gate. The group no
longer waits for them, and once the opener has gone the earliest-joined Student still there may
move on. Presence is `debrief.commands.touch` on each heartbeat: no lock, no event."""

import uuid
from datetime import timedelta

from app.modules.debrief import commands
from app.modules.debrief import service as debrief
from app.modules.messaging import delivery
from app.modules.ops import sweep
from app.modules.progress import service as progress
from app.modules.sessions import service as sessions
from app.platform import events
from app.platform.db import get_sessionmaker
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.debrief.test_debrief import home, open_, refused
from tests.debrief.test_group import debrief_step, played, user_id
from tests.debrief.test_quiz import conflict
from tests.messaging.helpers import rows
from tests.sessions.test_lock import _empty
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]


def topics(emitted: list[tuple]) -> set[str]:
    return {topic for topic, _ in emitted}


def seen_recently(who: str) -> bool:
    [(recent,)] = rows(
        "SELECT last_seen_at > now() - interval '1 minute' FROM debrief_members WHERE user_id = %s",
        user_id(who),
    )
    return recent


async def test_leaving_and_dropping_out_hand_the_group_on(klass, emitted):
    session_id, _ = await played(klass, 4, ordering=4)
    a, b, c, d = (email(i) for i in range(4))
    debrief_id = (await open_(a, session_id)).json()["id"]
    path = f"/api/debriefs/{debrief_id}"
    for who in (b, c):
        assert (await call(who, "POST", f"{path}/join")).status_code == 200

    # Presence: each heartbeat of the stream runs `touch` (registered at import), which writes
    # `last_seen_at` and emits nothing.
    execute("UPDATE debrief_members SET last_seen_at = last_seen_at - interval '10 minutes'")
    emitted.clear()
    await events.heartbeat(user_id(a))
    assert emitted == [] and COMMAND_TOPICS["debrief.touch"] == frozenset()
    assert seen_recently(a) and not seen_recently(b)
    execute("UPDATE debrief_members SET last_seen_at = now()")

    # A, the opener, leaves before sending: alone from step 1, and B, the earliest joined, may
    # move on now. A second leave changes nothing; A cannot rejoin.
    emitted.clear()
    left = await call(a, "POST", f"{path}/leave")
    assert left.status_code == 200
    assert topics(emitted) == COMMAND_TOPICS["debrief.leave"] == {"debrief"}
    group = left.json()["group"]
    assert (group["alone"], group["alone_from"], group["joined"], group["members"]) == (
        "left",
        1,
        False,
        [],
    )
    assert (await call(b, "GET", path)).json()["group"]["opener"] is True
    assert rows("SELECT opener_id FROM debrief_sessions") == [(user_id(b),)]
    emitted.clear()
    assert (await call(a, "POST", f"{path}/leave")).status_code == 200
    assert emitted == []
    conflict(await call(a, "POST", f"{path}/join"), "group_closed")
    refused(await call(a, "POST", f"{path}/steps/2/done"), "explanation_required")

    # A goes on as a Personal debrief: the Explanation gate holds, the pointer gate does not.
    refused(await call(a, "GET", f"{path}/steps/2"), "explanation_required")
    assert (
        await call(a, "POST", f"{path}/explanation", json={"text": "Alene."})
    ).status_code == 201
    assert (await call(a, "GET", f"{path}/steps/3")).status_code == 200
    assert (await call(a, "GET", f"{path}/reflection")).status_code == 200
    assert (await call(b, "GET", path)).json()["group"]["step"] == 1
    refused(await call(b, "GET", f"{path}/steps/2"), "explanation_required")

    # D never joined and goes alone from the join panel: from step 1, no longer offered to join.
    assert debrief_step(await home(d))["group_open"] is True
    alone = (await call(d, "POST", f"{path}/leave")).json()["group"]
    assert (alone["alone"], alone["alone_from"]) == ("left", 1)
    assert debrief_step(await home(d))["group_open"] is False
    assert debrief_step(await home(a))["group_open"] is False
    conflict(await call(d, "POST", f"{path}/join"), "group_closed")

    # B sends; C is listed by the sweep as silent, but heartbeats before the act: the act judges
    # again under the lock and drops nobody.
    assert (await call(b, "POST", f"{path}/explanation", json={"text": "B."})).status_code == 201
    stale(c)
    [(now,)] = rows("SELECT now()")
    [(game_id,)] = rows("SELECT game_id FROM debrief_sessions")
    due = await debrief.due_dropouts(now)
    assert due == [(str(game_id), str(user_id(c)))]
    await events.heartbeat(user_id(c))
    emitted.clear()
    for item in due:
        await debrief.drop_out_due(item, now)
    assert emitted == [] and (await call(c, "GET", path)).json()["group"]["alone"] is None

    # C sends: step 2. B's own command counts as presence: silent B finishing the step is kept
    # and seen now.
    assert (await call(c, "POST", f"{path}/explanation", json={"text": "C."})).status_code == 201
    stale(b)
    done = (await call(b, "POST", f"{path}/steps/2/done")).json()["group"]
    assert (done["step"], done["alone"], done["joined"]) == (2, None, True)
    assert seen_recently(b)

    # C falls silent. B, the opener now, moves on before the wait: the move-on's own settle drops
    # C, the group of B alone has finished step 2, so the pointer is on 3 (no `too_early`).
    stale(c)
    emitted.clear()
    moved = await call(b, "POST", f"{path}/move-on")
    assert moved.status_code == 200 and moved.json()["group"]["step"] == 3
    assert topics(emitted) == COMMAND_TOPICS["debrief.move_on"]
    group = (await call(c, "GET", path)).json()["group"]
    assert (group["alone"], group["alone_from"], group["joined"]) == ("dropout", 2, False)

    # The opener gone (a deleted account sets it to NULL): B still may move on, and the move-on
    # stores it.
    execute("UPDATE debrief_sessions SET opener_id = NULL")
    assert (await call(b, "GET", path)).json()["group"]["opener"] is True
    conflict(await call(b, "POST", f"{path}/move-on"), "too_early")
    assert rows("SELECT opener_id FROM debrief_sessions") == [(user_id(b),)]
    execute("UPDATE debrief_sessions SET step_opened_at = step_opened_at - interval '1 hour'")
    assert (await call(b, "POST", f"{path}/move-on")).json()["group"]["step"] == 4

    # C returns: a Personal debrief, the Explanation kept, the reflection questions open.
    assert (await call(c, "GET", f"{path}/reflection")).status_code == 200
    refused(await call(c, "POST", f"{path}/steps/3/done"), "forbidden")

    # From step 4 there is nothing to leave and nothing falls back.
    emitted.clear()
    assert (await call(b, "POST", f"{path}/leave")).json()["group"]["alone"] is None
    assert emitted == []
    assert await debrief.due_fallbacks(now + timedelta(days=30)) == []
    assert await commands.open_personal_fallback(uuid.UUID(debrief_id)) is False


def stale(who: str) -> None:
    """Two silent minutes and more, in database time."""
    execute(
        "UPDATE debrief_members SET last_seen_at = now() - interval '3 minutes' WHERE user_id = %s",
        user_id(who),
    )


async def test_a_group_that_never_met_falls_back_after_48_hours(klass, emitted):
    session_id, _ = await played(klass, 3, ordering=3)
    a, b, c = email(0), email(1), email(2)
    debrief_id = (await open_(a, session_id)).json()["id"]
    path = f"/api/debriefs/{debrief_id}"

    # B joins and falls silent: the sweep's dropout makes B go alone through `leave`. C never
    # opens it.
    assert (await call(b, "POST", f"{path}/join")).status_code == 200
    stale(b)
    [(now,)] = rows("SELECT now()")
    emitted.clear()
    for item in await debrief.due_dropouts(now):
        await debrief.drop_out_due(item, now)
    assert topics(emitted) == COMMAND_TOPICS["debrief.leave"]
    assert await debrief.due_dropouts(now) == []
    group = (await call(b, "GET", path)).json()["group"]
    assert (group["alone"], group["alone_from"]) == ("dropout", 1)

    # The due time is a column: the Game's finish time (or the open, for a Game finished without
    # its finished Week state) plus 48 hours.
    [(due, exact)] = rows(
        "SELECT s.fallback_due_at, s.fallback_due_at = coalesce("
        " (SELECT w.created_at FROM game_weeks w WHERE w.game_id = s.game_id AND w.finished),"
        " s.opened_at) + interval '48 hours' FROM debrief_sessions s"
    )
    assert exact
    assert await debrief.due_fallbacks(due - timedelta(seconds=1)) == []
    assert await debrief.due_fallbacks(due) == [debrief_id]

    # A, still alone in the group, and C, who never joined, fall back and are told; B goes alone
    # already and is not.
    emitted.clear()
    assert await debrief.fallback_due(debrief_id, due) is True
    assert topics(emitted) == COMMAND_TOPICS["debrief.open_personal_fallback"]
    assert COMMAND_TOPICS["debrief.open_personal_fallback"] == {"debrief", "user"}
    told = rows("SELECT user_id, dedupe_key FROM notices WHERE kind = 'debrief_fallback'")
    assert sorted(told) == sorted(
        (user_id(who), f"debrief_fallback:{debrief_id}:{user_id(who)}") for who in (a, c)
    )
    for who in (a, c):
        group = (await call(who, "GET", path)).json()["group"]
        assert (group["alone"], group["alone_from"]) == ("fallback", 1)
    assert (await call(b, "GET", path)).json()["group"]["alone"] == "dropout"
    conflict(await call(c, "POST", f"{path}/join"), "group_closed")
    assert debrief_step(await home(c))["group_open"] is False

    async def context(who: str):
        async with get_sessionmaker()() as s:
            return await sessions.debrief_fallback_mail_context(
                s, user_id(who), uuid.UUID(session_id), due
            )

    assert "class_name" in (await context(a) or {})
    # Left out of the digest once the Student has finished the Debrief.
    await progress.record_step(user_id(c), uuid.UUID(session_id), progress.Step.DEBRIEF, due)
    assert await context(c) is None

    # Once only.
    emitted.clear()
    assert await debrief.fallback_due(debrief_id, due) is False
    assert emitted == []
    assert await debrief.due_fallbacks(due) == []
    assert rows("SELECT count(*) FROM notices WHERE kind = 'debrief_fallback'") == [(2,)]
    assert (await call(a, "POST", f"{path}/explanation", json={"text": "A."})).status_code == 201
    assert (await call(a, "GET", f"{path}/reflection")).status_code == 200


async def test_a_student_who_missed_the_group_opens_a_personal_debrief_at_once(klass, emitted):
    session_id, _ = await played(klass, 3, ordering=3)
    a, b, c = email(0), email(1), email(2)
    debrief_id = (await open_(a, session_id)).json()["id"]
    path = f"/api/debriefs/{debrief_id}"

    # A goes through the shared steps; the group (A) is on step 4. Hjem no longer offers B to join.
    assert (await call(a, "POST", f"{path}/explanation", json={"text": "A."})).status_code == 201
    for step in (2, 3):
        assert (await call(a, "POST", f"{path}/steps/{step}/done")).status_code == 200
    assert debrief_step(await home(b))["group_open"] is False

    # B opens it: a Personal debrief at once, no 48 hours; a second open changes nothing.
    emitted.clear()
    group = (await open_(b, session_id)).json()["group"]
    assert (group["alone"], group["alone_from"], group["joined"]) == ("missed", 1, False)
    assert topics(emitted) == {"debrief"} <= COMMAND_TOPICS["debrief.open"]
    emitted.clear()
    assert (await open_(b, session_id)).json()["group"]["alone"] == "missed"
    assert emitted == []
    conflict(await call(b, "POST", f"{path}/join"), "group_closed")
    refused(await call(b, "GET", f"{path}/steps/2"), "explanation_required")
    assert (await call(b, "POST", f"{path}/explanation", json={"text": "B."})).status_code == 201
    assert (await call(b, "GET", f"{path}/reflection")).status_code == 200
    # A, who was in the group, is not «missed».
    assert (await open_(a, session_id)).json()["group"]["alone"] is None
    # C asks to join without opening it first: the same, never a member of a finished group.
    group = (await call(c, "POST", f"{path}/join")).json()["group"]
    assert (group["alone"], group["joined"]) == ("missed", False)
    conflict(await call(c, "POST", f"{path}/join"), "group_closed")


async def test_a_personal_debrief_has_nobody_to_leave(klass):
    session_id, _ = await played(klass, 2, ordering=1)
    opened = (await open_(email(1), session_id)).json()
    conflict(await call(email(1), "POST", f"/api/debriefs/{opened['id']}/leave"), "not_group")
    assert await commands.open_personal_fallback(uuid.UUID(opened["id"])) is False
    assert rows("SELECT fallback_due_at FROM debrief_sessions") == [(None,)]


def test_the_sweep_runs_the_dropout_and_the_fallback_and_the_mail_knows_the_notice():
    actions = {action.name: action for action in sweep.DUE_ACTIONS}
    assert actions["debrief.dropouts"].find is debrief.due_dropouts
    assert actions["debrief.dropouts"].act is debrief.drop_out_due
    assert actions["debrief.fallback"].find is debrief.due_fallbacks
    assert actions["debrief.fallback"].act is debrief.fallback_due
    assert delivery.DEBRIEF_FALLBACK_KIND == commands.FALLBACK_NOTICE
    assert delivery.KINDS[commands.FALLBACK_NOTICE].mode == delivery.DIGEST
