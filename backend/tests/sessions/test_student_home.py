"""The Student's Hjem (Story 6.1, FR-5, FR-22, FR-34, AD-3, AD-10, AD-12, AD-16): from the Start
date `/api/me/class-sessions` carries the Student's Class game, read through
`games.service.student_game` and `games.views.table_status`, with its four Seats Fabrikk first and
every AI player as `ai`; before it, also after a confirmed allocation, no game. Stegene's states
come from `progress`. `/api/me/games/{id}` answers the Student's own game and refuses every other
one the same. The api's clock is fixed and the sweep is handed its `now`."""

import uuid

from app.engine import GameSettings
from app.modules.games import commands as games_commands
from app.modules.ops import sweep
from app.modules.progress import service as progress
from app.modules.sessions.service import game_rules
from tests.classes.test_classes import make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import call
from tests.sessions.test_dates import OUTSIDER, START, student_of
from tests.sessions.test_lock import MINUTE, _empty
from tests.sessions.test_open_games import confirmed, games_of, holders
from tests.sessions.test_settings import save
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "klass"]

FABRIKK_FIRST = ["factory", "distributor", "wholesaler", "retailer"]
ALL_LOCKED = [
    {"step": step, "state": "locked"}
    for step in ("class_game", "debrief", "quiz", "replay", "test", "report")
]


async def home(who: str) -> dict:
    response = await call(who, "GET", "/api/me/class-sessions")
    assert response.status_code == 200
    [item] = response.json()["items"]
    return item


async def game_of(who: str, game_id: str):
    return await call(who, "GET", f"/api/me/games/{game_id}")


async def test_before_the_start_date_there_is_no_game_and_every_step_is_locked(klass):
    session_id, _ = await confirmed(klass, 2)
    item = await home(email(0))
    assert item["id"] == session_id
    assert item["game"] is None and item["steps"] == ALL_LOCKED
    # The Student holds a Seat already, but the game route waits for the Start date too.
    [game] = games_of(session_id)
    assert (await game_of(email(0), game[0])).status_code == 403


async def test_from_the_start_date_the_student_sees_game_role_and_seats(klass):
    session_id, seated = await confirmed(klass, 2)
    await sweep.run(START + MINUTE)  # locks the session and opens its games with AI players
    item = await home(email(0))
    game = item["game"]
    [stored] = games_of(session_id)
    assert game["id"] == stored[0] and game["number"] == 1
    assert [seat["role"] for seat in game["seats"]] == FABRIKK_FIRST
    mine = [seat for seat in game["seats"] if seat["mine"]]
    assert len(mine) == 1 and mine[0]["role"] == game["role"]
    assert mine[0]["holder"] == "student" and mine[0]["name"]
    students = [seat for seat in game["seats"] if seat["holder"] == "student"]
    ai = [seat for seat in game["seats"] if seat["holder"] == "ai"]
    assert len(students) == 2 and len(ai) == 2
    assert all(seat["name"] is None for seat in ai)
    # Stegene: Klassespill is the current step, the five later ones locked.
    assert [s["state"] for s in item["steps"]] == ["current", *["locked"] * 5]
    # The game route gives the same card; another User's view differs only in `mine`.
    own = await game_of(email(0), stored[0])
    assert own.status_code == 200 and own.json() == game
    other = (await game_of(email(1), stored[0])).json()
    [theirs] = [seat for seat in other["seats"] if seat["mine"]]
    assert theirs["role"] == other["role"] != game["role"] and theirs["holder"] == "student"
    # People only: no AI kind, model or user id reaches the Student (AD-3, FR-34).
    text = own.text
    assert not any(word in text for word in ("rule_based", "llm", "user_id", str(seated[1])))


async def test_a_done_step_moves_the_current_step_on(klass):
    session_id, seated = await confirmed(klass, 1)
    await sweep.run(START + MINUTE)
    sid = uuid.UUID(session_id)
    await progress.record_step(seated[0], sid, "class_game", NOW)
    await progress.record_step(seated[0], sid, "class_game", NOW)  # idempotent
    steps = (await home(email(0)))["steps"]
    assert [s["state"] for s in steps] == ["done", "current", *["locked"] * 4]
    # Each Stegene step is marked done by its own `progress` step; the Forklaring and the
    # Starting task are no step of Stegene.
    for step in ("starting_task", "explanation", "debrief", "quiz_passed"):
        await progress.record_step(seated[0], sid, step, NOW)
    steps = (await home(email(0)))["steps"]
    assert [s["state"] for s in steps] == ["done", "done", "done", "current", "locked", "locked"]
    for step in ("replay", "test_submitted", "assessment_ready"):
        await progress.record_step(seated[0], sid, step, NOW)
    assert {s["state"] for s in (await home(email(0)))["steps"]} == {"done"}


async def test_a_student_moved_before_the_start_sees_only_the_new_game(klass):
    session_id, seated = await confirmed(klass, 5)  # four in game 1, one in game 2
    games = {number: game_id for game_id, number, *_ in games_of(session_id)}
    role, user = next((r, u) for number, r, kind, _, u in holders(session_id) if number == 1 and u)
    free = next(r for number, r, kind, _, u in holders(session_id) if number == 2 and not u)
    await games_commands.move_seat(games[1], role, games[2], free)
    await sweep.run(START + MINUTE)
    who = email(seated.index(uuid.UUID(user)))
    game = (await home(who))["game"]
    assert (game["id"], game["role"]) == (games[2], free)
    assert [s["role"] for s in game["seats"] if s["mine"]] == [free]
    # The game the Student left is not theirs any more.
    assert (await game_of(who, games[1])).status_code == 403
    assert (await game_of(who, games[2])).status_code == 200


async def test_another_students_game_and_any_unknown_id_are_refused_alike(klass):
    session_id, _ = await confirmed(klass, 5)  # two Class games
    await sweep.run(START + MINUTE)
    games = games_of(session_id)
    mine = (await home(email(0)))["game"]["id"]
    other = next(g[0] for g in games if g[0] != mine)
    await make(OUTSIDER, roles=())
    refusals = [
        await game_of(email(0), other),
        await game_of(email(0), str(uuid.uuid7())),
        await game_of(email(0), "not-a-uuid"),
        await game_of(OUTSIDER, mine),
    ]
    assert {r.status_code for r in refusals} == {403}
    assert len({r.content for r in refusals}) == 1


async def test_a_student_with_no_seat_after_the_start_sees_no_game(klass):
    await confirmed(klass, 1)
    await sweep.run(START + MINUTE)
    await student_of(klass, "late@x.no")  # registers after the lock; not seated yet
    item = await home("late@x.no")
    assert item["game"] is None and item["steps"] == ALL_LOCKED


async def test_a_classmate_removed_after_the_start_has_no_name(klass):
    session_id, seated = await confirmed(klass, 2)
    await sweep.run(START + MINUTE)
    execute("UPDATE roster_entries SET removed_at = %s WHERE user_id = %s", NOW, seated[1])
    item = await home(email(0))
    seats = item["game"]["seats"]
    gone = [s for s in seats if s["holder"] == "student" and not s["mine"]]
    assert len(gone) == 1 and gone[0]["name"] is None
    # The removed Student reads the game no more, and is refused as for any other game.
    refused = await game_of(email(1), item["game"]["id"])
    unknown = await game_of(email(1), str(uuid.uuid7()))
    assert refused.status_code == 403 and refused.content == unknown.content
    # Nor does anyone once the Class is archived (Story 4.10): Hjem lists it no more.
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, klass)
    assert (await game_of(email(0), item["game"]["id"])).status_code == 403


CLASSIC_RULES = {
    "order_delay": 2,
    "shipping_delay": 2,
    "production_delay": 2,
    "guided_weeks": 4,
    "holding_cost": "0.50",
    "backorder_cost": "1.00",
}


async def test_the_briefing_comes_first_until_the_starting_task_is_done(klass):
    """Story 6.2: nothing is stored for "briefing read"; `briefing_first` holds until
    `progress` has `starting_task`, on Hjem and on the game route alike."""
    session_id, seated = await confirmed(klass, 1)
    await sweep.run(START + MINUTE)
    game = (await home(email(0)))["game"]
    assert game["briefing_first"] is True and game["rules"] == CLASSIC_RULES
    assert (await game_of(email(0), game["id"])).json() == game
    # The rules hold only what the briefing states: no Weeks, demand, seed or largest Order.
    assert set(game["rules"]) == set(CLASSIC_RULES)
    await progress.record_step(seated[0], uuid.UUID(session_id), "starting_task", NOW)
    after = (await home(email(0)))["game"]
    assert after["briefing_first"] is False and after["rules"] == CLASSIC_RULES
    assert (await game_of(email(0), game["id"])).json()["briefing_first"] is False


async def test_the_briefing_states_the_sessions_own_rules(klass):
    """Story 6.2: a Lecturer's changed delays, Veiledede uker and rates reach the briefing, read
    from the snapshot the lock froze."""
    session_id, _ = await confirmed(klass, 1)
    changed = {
        "order_delay": 3,
        "shipping_delay": 1,
        "production_delay": 2,
        "guided_weeks": 0,
        "holding_cost": "0.75",
        "backorder_cost": "2.00",
    }
    assert (await save(session_id, changed)).status_code == 200
    await sweep.run(START + MINUTE)
    # The snapshot wins over the session's settings, should those ever differ after the lock.
    execute(
        "UPDATE class_sessions SET game_settings = %s::jsonb WHERE id = %s",
        GameSettings().model_dump_json(),
        session_id,
    )
    game = (await home(email(0)))["game"]
    assert game["rules"] == changed
    assert (await game_of(email(0), game["id"])).json()["rules"] == changed


def test_the_rules_come_from_the_settings_until_the_lock_has_stored_its_snapshot():
    """Story 6.2: between the Start date and the sweep's lock there is no snapshot yet; the
    session's own settings, which no longer change, give the rules."""
    stored = GameSettings(order_delay=3, guided_weeks=1).model_dump(mode="json")
    frozen = GameSettings(order_delay=1).model_dump(mode="json")
    assert game_rules({"snapshot_settings": None, "game_settings": stored}).order_delay == 3
    assert game_rules({"snapshot_settings": None, "game_settings": stored}).guided_weeks == 1
    assert game_rules({"snapshot_settings": frozen, "game_settings": stored}).order_delay == 1
