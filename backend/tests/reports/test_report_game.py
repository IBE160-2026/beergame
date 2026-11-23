"""Story 13.8 (FR-58, FR-34, FR-17, AD-13, AD-15): the Student report's game section.

`report_data.build_report_data` is called directly, as the `reports-single` job calls it: for a
Student with only a Class game played to its end, for a Student whose finished Oppfølgingsspill
is their game, and for a Student with no game yet. The section holds the Student's Seat, the
chain by Role only and the marks of the one AD-15 mapping; no other Student's name or id. The
pipeline around it (snapshot, print route, PDF) is `test_student_report.py` and the e2e."""

import json
import uuid
from datetime import UTC, datetime

from app.modules.classes import service as classes
from app.modules.reports import report_data
from app.modules.sessions import service as sessions
from app.platform.db import get_sessionmaker
from tests.classes.test_classes import LECTURER
from tests.classes.test_student_registration import emitted
from tests.reports.test_makeup import give
from tests.sessions.test_game_end import WEEKS, _empty, clock, klass, play_weeks, short_game
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_start_game import start
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]

NOW = datetime(2026, 12, 1, 12, tzinfo=UTC)


async def built(user_id: uuid.UUID, session_id: str) -> report_data.ReportDataOut:
    async with get_sessionmaker()() as s:
        return await report_data.build_report_data(
            s, user_id, uuid.UUID(session_id), report_data.ReportOptions(), now=NOW
        )


def game_of(data: report_data.ReportDataOut) -> report_data.ReportGameOut | None:
    kinds = [section.kind for section in data.sections]
    assert kinds == ["completion", "game"]
    section = data.sections[1]
    assert isinstance(section, report_data.GameSectionOut)
    return section.game


async def test_a_played_class_game_is_documented_with_the_chain_by_role_only(klass):
    session_id, game_id, (a, b) = await short_game(klass)
    await play_weeks(game_id, WEEKS)
    data = await built(a, session_id)
    game = game_of(data)
    assert game is not None
    assert (game.makeup, game.weeks_played, game.weeks_total, game.finished) == (
        False,
        WEEKS,
        WEEKS,
        True,
    )
    assert game.game_number is not None
    assert game.seat.role == game.role and game.seat.week == WEEKS
    assert game.total_cost == game.seat.total_cost
    assert game.last_order is not None
    assert [row.week for row in game.demand] == list(range(1, WEEKS + 1))
    assert [role.role for role in game.roles] == [
        "retailer",
        "wholesaler",
        "distributor",
        "factory",
    ]
    for role in game.roles:
        assert [week.week for week in role.weeks] == list(range(1, WEEKS + 1))
        assert {week.holder for week in role.weeks} <= {"student", "ai"}
    holders = {role.role: role.weeks[0].holder for role in game.roles}
    assert list(holders.values()).count("student") == 2
    assert holders[game.role] == "student"

    # The other Student is there by Role only: no name, no id in what the print route reads.
    async with get_sessionmaker()() as s:
        names = await classes.student_names(await _class_of(s, session_id, a), [a, b], session=s)
    dumped = json.dumps(data.model_dump(mode="json"), ensure_ascii=False)
    assert names[b] not in dumped and str(b) not in dumped and str(a) not in dumped


async def _class_of(s, session_id: str, user_id: uuid.UUID) -> uuid.UUID:
    heading = await sessions.report_heading(s, uuid.UUID(session_id), user_id)
    assert heading is not None
    return heading.class_id


async def test_a_finished_makeup_is_the_game_section_headed_oppfolgingsspill(klass, emitted):
    session_id, game_id, (a, b) = await short_game(klass)
    await play_weeks(game_id, WEEKS)
    answer = await give(LECTURER, session_id, b)
    assert answer.status_code == 200, answer.text
    makeup_id = answer.json()["makeup"]["game_id"]
    assert (await start(email(1), makeup_id)).status_code == 200
    await play_weeks(makeup_id, WEEKS)

    mine = game_of(await built(b, session_id))
    assert mine is not None and mine.makeup and mine.game_number is None
    # The make-up is a game of its own against AI players: one Student Seat, theirs.
    holders = [role.weeks[-1].holder for role in mine.roles]
    assert holders.count("student") == 1
    # The other Student's report still documents the Class game.
    theirs = game_of(await built(a, session_id))
    assert theirs is not None and not theirs.makeup and theirs.game_number is not None


async def test_a_student_with_no_game_gets_the_section_saying_so(klass):
    session_id, (a,) = await confirmed(klass, 1)
    assert game_of(await built(a, session_id)) is None
