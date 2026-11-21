"""The end of a Class game (Story 6.18, FR-28, FR-29, AD-2, AD-3, AD-9, AD-13, AD-16): the Order
that completes the last Week finishes the Game in the same transaction and records `class_game`
for every Student it ever seated; `GET /api/me/games/{id}/result` answers the chain's cost per
Role and per Uke only once it has finished; the sweep runs the finished-game check later.

One short Class game (6 Weeks, 1 Guided Week, set before the lock) serves each test, so no test
plays the Classic 36 Weeks."""

import json
import uuid

from app.modules.games import commands
from app.modules.games import service as games_service
from app.modules.ops import sweep
from app.modules.progress import service as progress
from tests.classes.test_classes import make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.sessions.test_dates import OUTSIDER, START
from tests.sessions.test_lock import MINUTE
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_start_game import start, task_done
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import _empty, clock, home, klass

__all__ = ["_empty", "clock", "emitted", "klass"]

WEEKS = 6
DETALJIST_FIRST = ["retailer", "wholesaler", "distributor", "factory"]


async def result(who: str, game_id: str):
    return await call(who, "GET", f"/api/me/games/{game_id}/result")


async def short_game(klass: str, students: int = 2) -> tuple[str, str, list[uuid.UUID]]:
    """A started Class game of `WEEKS` Weeks with one Guided Week: (session, game, Students)."""
    session_id, seated = await confirmed(klass, students)
    execute(
        "UPDATE class_sessions SET game_settings = game_settings || %s::jsonb WHERE id = %s",
        json.dumps({"weeks": WEEKS, "guided_weeks": 1}),
        session_id,
    )
    await sweep.run(START + MINUTE)  # locks the session: the snapshot holds the short game
    game_id = (await home(email(0)))["game"]["id"]
    for user in seated:
        await task_done(user, session_id)
    assert (await start(email(0), game_id)).status_code == 200
    return session_id, game_id, seated


async def play_weeks(game_id: str, through: int) -> None:
    """From the open Week on, every Student Seat views the Guided Week or orders, until Week
    `through` has run. A Seat an AI player took over orders by itself."""
    while (game := await games_service.get_game(game_id)).lifecycle != "finished":
        week = (await games_service.seat_state(game_id, game.seats[0].id)).week
        if week > through:
            return
        for seat in game.seats:
            if seat.occupant_kind != "student":
                continue
            if week == 1:
                await commands.view_week(game_id, seat.role, week, actor=seat.user_id)
            else:
                await commands.place_order(
                    game_id, seat.role, week, 4 + week, "student", actor=seat.user_id
                )


async def test_the_last_order_finishes_the_game_and_records_every_student_ever_seated(
    klass, emitted
):
    session_id, game_id, seated = await short_game(klass)
    await play_weeks(game_id, 3)
    # An AI player takes over the second Student's Seat: they are still recorded at the end.
    replaced = next(
        s for s in (await games_service.get_game(game_id)).seats if str(s.user_id) == str(seated[1])
    )
    await commands.switch_to_rule_based(game_id, replaced.role, "takeover_inactivity")
    assert not await progress.has_step(seated[0], uuid.UUID(session_id), "class_game")
    await play_weeks(game_id, WEEKS - 1)
    emitted.clear()
    await play_weeks(game_id, WEEKS)  # only Week 6's Orders are left
    assert (await games_service.get_game(game_id)).lifecycle == "finished"
    for user in seated:
        assert await progress.has_step(user, uuid.UUID(session_id), "class_game")
    topics = set(emitted)
    assert {("game", game_id), ("session", session_id)} <= topics
    assert {("user", str(user)) for user in seated} <= topics
    # Hjem: the game reads finished, and Stegene moves on to the Debrief.
    item = await home(email(0))
    assert item["game"]["status"] == "finished"
    assert [s["state"] for s in item["steps"]][:2] == ["done", "current"]


async def test_the_result_is_the_chain_per_role_and_week_only_once_finished_and_checked_later(
    klass,
):
    _, game_id, _ = await short_game(klass, students=1)
    running = await result(email(0), game_id)
    assert running.status_code == 409
    assert running.json()["error"]["code"] == "game_not_finished"
    await play_weeks(game_id, WEEKS)
    response = await result(email(0), game_id)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"roles", "chain", "weeks"}
    assert [row["role"] for row in body["roles"]] == DETALJIST_FIRST
    summary = await games_service.game_summary(game_id)
    # The chain total and each Role's total are the finished Week state's (the summary's).
    assert float(body["chain"]["total_cost"]) == float(summary.chain_cost)
    assert {row["role"]: float(row["total_cost"]) for row in body["roles"]} == {
        role: float(cost) for role, cost in summary.total_cost
    }
    for row in [*body["roles"], body["chain"], *body["weeks"]]:
        assert float(row["holding_cost"]) + float(row["backorder_cost"]) == float(row["total_cost"])
    assert [w["week"] for w in body["weeks"]] == list(range(1, WEEKS + 1))
    assert body["weeks"][-1] | {"week": None} == body["chain"] | {"week": None}
    totals = [float(w["total_cost"]) for w in body["weeks"]]
    assert totals == sorted(totals)  # running sums never fall
    # Roles only: no names, no demand, no settings (FR-14, AD-3).
    text = response.text
    assert "name" not in text and "demand" not in text and "settings" not in text
    # Any other game is refused alike (FR-5).
    await make(OUTSIDER, roles=())
    refusals = [
        await result(OUTSIDER, game_id),
        await result(email(0), str(uuid.uuid7())),
        await result(email(0), "not-a-uuid"),
    ]
    assert {r.status_code for r in refusals} == {403}
    assert len({r.content for r in refusals}) == 1
    # The end did not wait for the finished-game check: the sweep runs it, once (AD-9).
    assert summary.check is None
    done = await sweep.run(START + 2 * MINUTE)
    assert done["games.verify_finished"] == 1
    check = (await games_service.game_summary(game_id)).check
    assert check is not None and check.ok
    again = await sweep.run(START + 3 * MINUTE)
    assert again["games.verify_finished"] == 0
