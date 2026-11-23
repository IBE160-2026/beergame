"""Story 13.1 at the api (FR-17, AD-13, AD-16, AD-25, AD-27): the one Completion assembler
`reports.service.completion_status`, the reporting scope, the Oversikt's Trakt through
`reports.service.funnel`, and Hjem's per-step `counts` and `requirement_met`.

One short Class game (6 Weeks, 1 Guided Week: 5 Weeks to order in) per test, as in
`tests/sessions/test_game_end.py`; the clocks are passed in."""

import uuid

from app.modules.games import commands
from app.modules.games import service as games_service
from app.modules.ops import sweep
from app.modules.progress import service as progress
from app.modules.reports import scope
from app.modules.reports import service as reports
from app.modules.sessions import service as sessions
from app.platform.db import get_sessionmaker
from tests.classes.test_classes import LECTURER
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW
from tests.sessions.test_dates import PLAY, START, student_of
from tests.sessions.test_game_end import _empty, clock, klass, play_weeks, short_game
from tests.sessions.test_lock import MINUTE
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_overview import overview
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import home

__all__ = ["_empty", "clock", "klass"]

WEEKS = 6
LATER_STEPS = ("debrief", "quiz_passed", "replay", "test_submitted")
FIVE = ("class_game", *LATER_STEPS)
HJEM_STEP = {"class_game": "class_game", "debrief": "debrief", "quiz": "quiz_passed"}


def obligatory(session_id: str, on: bool = True) -> None:
    execute("UPDATE class_sessions SET obligatory = %s WHERE id = %s", on, session_id)


def explanation(user: uuid.UUID, session_id: str, game_id: str, text: str) -> None:
    execute(
        "INSERT INTO debrief_explanations (user_id, class_session_id, game_id, text, length, "
        "saved_at) VALUES (%s, %s, %s, %s, %s, %s)",
        user,
        session_id,
        game_id,
        text,
        len(text),
        NOW,
    )


async def every_later_step(user: uuid.UUID, session_id: str) -> None:
    for step in LATER_STEPS:
        await progress.record_step(user, uuid.UUID(session_id), step, NOW)


def counts(item: dict) -> dict[str, bool | None]:
    return {step["step"]: step["counts"] for step in item["steps"]}


async def test_a_student_who_ordered_every_week_and_did_every_step_meets_the_requirement(klass):
    session_id, game_id, seated = await short_game(klass)
    sid = uuid.UUID(session_id)
    obligatory(session_id)
    await play_weeks(game_id, WEEKS)
    me = seated[0]

    status = await reports.completion_status(me, sid)
    game = status.step("class_game")
    assert (game.recorded, game.done) == (True, True)
    assert (status.ordered_share, status.playout_share, status.weeks_after_guided) == (100, 0, 5)
    assert status.required_share == 80
    assert status.requirement_met is False  # nothing after the Class game yet
    item = await home(email(0))
    assert item["requirement_met"] is False
    assert counts(item) == {
        "class_game": True,
        "debrief": False,
        "quiz": False,
        "replay": False,
        "test": False,
        "report": None,
    }

    await every_later_step(me, session_id)
    explanation(me, session_id, game_id, "  " + "x" * 49 + "  ")  # 49 characters, trimmed
    status = await reports.completion_status(me, sid)
    debrief = status.step("debrief")
    assert (debrief.recorded, debrief.recorded_at, debrief.done) == (True, NOW, False)
    assert status.requirement_met is False
    item = await home(email(0))
    assert counts(item)["debrief"] is False and item["requirement_met"] is False

    other = seated[1]
    await every_later_step(other, session_id)
    explanation(other, session_id, game_id, "y" * 50)
    assert (await reports.completion_status(other, sid)).requirement_met is True
    item = await home(email(1))
    assert item["requirement_met"] is True
    assert all(value is not False for value in counts(item).values())


async def test_a_session_that_is_not_obligatory_shows_no_requirement_on_hjem(klass):
    session_id, game_id, seated = await short_game(klass)
    await play_weeks(game_id, WEEKS)
    status = await reports.completion_status(seated[0], uuid.UUID(session_id))
    assert status.requirement_met is None and status.step("class_game").done is True
    item = await home(email(0))
    assert item["requirement_met"] is None
    assert set(counts(item).values()) == {None}


async def _played_out(klass) -> tuple[str, str, list[uuid.UUID]]:
    """The short game with Weeks 1 and 2 played, then played out at the Play deadline."""
    session_id, game_id, seated = await short_game(klass)
    obligatory(session_id)
    await play_weeks(game_id, 2)
    await sweep.run(PLAY)
    for _ in range(WEEKS + 2):
        if (await games_service.get_game(game_id)).lifecycle == "finished":
            break
        await commands.advance(game_id)
    assert (await games_service.get_game(game_id)).lifecycle == "finished"
    return session_id, game_id, seated


async def test_playout_weeks_count_as_not_ordered_and_hjem_says_the_step_does_not_count(klass):
    session_id, _, seated = await _played_out(klass)
    status = await reports.completion_status(seated[0], uuid.UUID(session_id))
    game = status.step("class_game")
    assert (game.recorded, game.done) == (True, False)
    # Week 2 ordered of the 5 after the Guided Week; Weeks 3 to 6 played in the playout.
    assert (status.ordered_share, status.playout_share) == (20, 80)
    assert (status.ordered_weeks, status.playout_weeks) == (1, 4)
    item = await home(email(0))
    [step] = [s for s in item["steps"] if s["step"] == "class_game"]
    assert (step["state"], step["counts"]) == ("done", False)
    # No share and no number of Weeks reaches the Student.
    assert not {"ordered_share", "playout_share", "required_share", "completion"} & set(item)
    assert all("share" not in key for step in item["steps"] for key in step)


async def test_an_adjusted_share_is_the_students_own_requirement(klass):
    session_id, _, seated = await _played_out(klass)
    execute(
        "INSERT INTO student_adjustments (class_session_id, user_id, time_factor, share_percent, "
        "updated_at) VALUES (%s, %s, 1.0, 20, %s)",
        session_id,
        seated[0],
        NOW,
    )
    status = await reports.completion_status(seated[0], uuid.UUID(session_id))
    assert status.required_share == 20
    assert status.step("class_game").done is True
    assert counts(await home(email(0)))["class_game"] is True
    assert (await home(email(0)))["adjustment"]["share_percent"] == 20


async def test_the_reporting_scope_leaves_out_test_data(klass, monkeypatch):
    """AD-13, AD-27: a lecturer test Game, a simulation Game, a Control test Class session and a
    test student are left out; a Replay is a reporting Game with its `end_reason`."""
    session_id, game_id, seated = await short_game(klass)
    sid = uuid.UUID(session_id)
    kinds = {}
    for purpose, end in (
        ("lecturer_test", None),
        ("simulation", None),
        ("replay", "test_deadline"),
    ):
        kinds[purpose] = uuid.uuid7()
        execute(
            "INSERT INTO games (id, purpose, lifecycle, version, class_session_id, end_reason) "
            "VALUES (%s, %s, 'finished', 1, %s, %s)",
            kinds[purpose],
            purpose,
            session_id,
            end,
        )
    async with get_sessionmaker()() as s:
        found = {g.game_id: g for g in await scope.reporting_games(s, sid)}
        assert set(found) == {uuid.UUID(game_id), kinds["replay"]}
        assert found[kinds["replay"]].end_reason == "test_deadline"
        assert [g.game_id for g in await scope.reporting_games(s, sid, ["replay"])] == [
            kinds["replay"]
        ]
        assert set(await scope.reporting_students(s, sid)) == set(seated)

    # Story 12.8's own mark, read through `identity.service.test_students`: no reporting Student.
    execute("UPDATE users SET is_test_student = true WHERE id = %s", seated[1])
    async with get_sessionmaker()() as s:
        assert await scope.reporting_students(s, sid) == [seated[0]]
    execute("UPDATE users SET is_test_student = false WHERE id = %s", seated[1])

    # A test student (Story 12.8's mark, through the hook) is no reporting Student.
    async def tests_students(session, ids):
        return {seated[1]} & set(ids)

    monkeypatch.setattr(scope, "_test_students", [tests_students])
    async with get_sessionmaker()() as s:
        assert await scope.reporting_students(s, sid) == [seated[0]]
    assert await reports.completion_status(seated[1], sid) is None
    assert (await reports.funnel(sid)).registered == 1
    trakt = {
        s["stage"]: s["count"] for s in (await overview(LECTURER, session_id)).json()["funnel"]
    }
    assert trakt["registered"] == 1  # the Oversikt reads the scope too

    # A Control test Class session (Story 12.7's kind, through the hook) counts nothing.
    async def control_tests(session, ids):
        return {sid} & set(ids)

    monkeypatch.setattr(scope, "_control_tests", [control_tests])
    async with get_sessionmaker()() as s:
        assert await scope.reporting_games(s, sid) == []
        assert await scope.reporting_students(s, sid) == []
    assert await reports.completion_status(seated[0], sid) is None
    assert (await reports.funnel(sid)).registered == 0
    trakt = {
        s["stage"]: s["count"] for s in (await overview(LECTURER, session_id)).json()["funnel"]
    }
    assert set(trakt.values()) == {0}


async def test_the_funnel_counts_step_events_as_the_completion_status_records_them(klass):
    """Each of the five stages equals the Students whose Completion status has that step
    recorded; a recorded step that does not count still counts in the Trakt."""
    session_id, game_id, seated = await short_game(klass, 3)
    sid = uuid.UUID(session_id)
    obligatory(session_id)
    await play_weeks(game_id, WEEKS)
    await progress.record_step(seated[0], sid, "debrief", NOW)  # no Explanation: does not count
    await progress.record_step(seated[0], sid, "quiz_passed", NOW)
    await progress.record_step(seated[1], sid, "debrief", NOW)
    await progress.record_step(seated[2], sid, "test_submitted", NOW)
    statuses = [await reports.completion_status(user, sid) for user in seated]
    trakt = await reports.funnel(sid)
    by_step = {step.value: count for step, count in trakt.steps}
    for step in FIVE:
        assert by_step[step] == sum(status.step(step).recorded for status in statuses), step
    assert trakt.registered == len(seated)
    # The Oversikt reads the same Trakt.
    staff = {
        s["stage"]: s["count"] for s in (await overview(LECTURER, session_id)).json()["funnel"]
    }
    assert {step: staff[step] for step in FIVE} == {step: by_step[step] for step in FIVE}
    assert staff["registered"] == len(seated)
    # Who met the requirement is the assembler's figure, not the Trakt's.
    assert sum(bool(status.requirement_met) for status in statuses) == 0


async def test_an_obligatory_session_without_a_game_shows_no_requirement_yet(klass):
    """A Student registered after the lock and not seated has no game: Hjem carries no
    requirement line and no step says whether it counts."""
    session_id, _ = await confirmed(klass, 1)
    obligatory(session_id)
    await sweep.run(START + MINUTE)
    await student_of(klass, "late@x.no")
    item = await home("late@x.no")
    assert item["game"] is None and item["requirement_met"] is None
    assert set(counts(item).values()) == {None}


async def test_an_unknown_session_or_a_stranger_has_no_status(klass):
    session_id, _, _ = await short_game(klass)
    assert await reports.completion_status(uuid.uuid7(), uuid.UUID(session_id)) is None
    assert await reports.completion_status(uuid.uuid7(), uuid.uuid7()) is None


def test_reports_registers_its_assembler_once():
    """The provider in `sessions` is the assembler; another one is refused."""
    assert sessions._completion == [reports.completion_status]

    async def other(user_id, class_session_id):
        return None

    try:
        sessions.register_completion(other, reports._funnel_in)
    except ValueError:
        pass
    else:
        raise AssertionError("a second Completion provider was accepted")
    sessions.register_completion(reports.completion_status, reports._funnel_in)  # the same again
