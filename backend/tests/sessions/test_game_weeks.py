"""The Matrisevegg's week read (Story 7.2, FR-39, FR-5, AD-1, AD-13, AD-25, NFR-7):
`GET /api/games/{id}/weeks` answers the Class's staff with every opened Week of a Class game, per
Role the Netto lager, the Order and the Kost per uke as the engine stored them, with an `ETag` tied
to the Game's version; anyone else, a test Game and a Game that does not exist get the same 403.

One short Class game (`short_game`, 6 Weeks) serves each test; the api's clock is fixed."""

import uuid
from decimal import Decimal

from app.engine import GameSettings
from app.modules.games import commands
from app.modules.identity.schemas import AccountRole
from tests.classes.test_classes import LECTURER, OTHER, make
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.messaging.helpers import rows
from tests.sessions.test_game_end import _empty, clock, emitted, klass, play_weeks, short_game
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]

ADMIN = "admin-only@x.no"
CHAIN = ["retailer", "wholesaler", "distributor", "factory"]


async def weeks(who: str, game_id: str, **kw):
    return await call(who, "GET", f"/api/games/{game_id}/weeks", **kw)


def stored(game_id: str) -> dict[tuple[int, str], tuple[int, Decimal]]:
    """Netto lager and the week's cost per (Week, Role), read from the stored Week states."""
    found = rows(
        "SELECT w.week, s->>'role', (s->>'inventory')::int - (s->>'backlog')::int, "
        "(s->>'cost')::numeric FROM game_weeks w, jsonb_array_elements(w.state->'seats') s "
        "WHERE w.game_id = %s AND NOT w.finished",
        game_id,
    )
    return {(week, role): (net, cost) for week, role, net, cost in found}


def orders(game_id: str) -> dict[tuple[int, str], int]:
    found = rows(
        'SELECT w.week, s.role, w."order" FROM seat_weeks w JOIN seats s ON s.id = w.seat_id '
        "WHERE w.game_id = %s",
        game_id,
    )
    return {(week, role): order for week, role, order in found}


async def test_staff_read_every_opened_week_as_stored_and_the_open_week_has_no_order(klass):
    _, game_id, _ = await short_game(klass)
    await play_weeks(game_id, 2)  # Weeks 1 and 2 have run; Week 3 is open
    response = await weeks(LECTURER, game_id)
    assert response.status_code == 200
    body = response.json()
    assert body["game_id"] == game_id
    assert [week["week"] for week in body["weeks"]] == [1, 2, 3]
    values, placed = stored(game_id), orders(game_id)
    for week in body["weeks"]:
        assert [seat["role"] for seat in week["seats"]] == CHAIN
        for seat in week["seats"]:
            key = (week["week"], seat["role"])
            net, cost = values[key]
            assert seat["net_inventory"] == net
            assert isinstance(seat["cost"], str) and Decimal(seat["cost"]) == cost
            assert seat["order"] == placed.get(key)
    # Weeks 1–2 are complete; the open Week's Student Seats have not ordered.
    assert all(s["order"] is not None for w in body["weeks"][:2] for s in w["seats"])
    assert any(s["order"] is None for s in body["weeks"][2]["seats"])
    [(version,)] = rows("SELECT version FROM games WHERE id = %s", game_id)
    assert body["version"] == version
    assert response.headers["etag"] == f'"v{version}"'
    assert response.headers["cache-control"] == "private, no-cache"
    # An Assistant lecturer of the Class reads the same.
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    assistant = await weeks(ASSISTANT, game_id)
    assert (assistant.status_code, assistant.json()) == (200, body)
    # Once finished, the finished state after the last Week adds no Week of its own.
    await play_weeks(game_id, 99)
    body = (await weeks(LECTURER, game_id)).json()
    assert [week["week"] for week in body["weeks"]] == list(range(1, 7))
    assert all(s["order"] is not None for w in body["weeks"] for s in w["seats"])


async def test_a_repeat_with_the_etag_answers_304_until_the_game_changes(klass):
    _, game_id, seated = await short_game(klass)
    first = await weeks(LECTURER, game_id)
    etag = first.headers["etag"]
    repeat = await weeks(LECTURER, game_id, headers={"If-None-Match": etag})
    assert (repeat.status_code, repeat.content, repeat.headers["etag"]) == (304, b"", etag)
    weak = await weeks(LECTURER, game_id, headers={"If-None-Match": f'"other", W/{etag}'})
    assert weak.status_code == 304
    [(role,)] = rows(
        "SELECT s.role FROM seat_occupancy o JOIN seats s ON s.id = o.seat_id "
        "WHERE s.game_id = %s AND o.user_id = %s",
        game_id,
        seated[0],
    )
    await commands.view_week(game_id, role, 1, actor=seated[0])
    changed = await weeks(LECTURER, game_id, headers={"If-None-Match": etag})
    assert changed.status_code == 200
    assert changed.headers["etag"] != etag


async def test_anyone_but_the_staff_and_any_unlisted_game_is_refused_the_same(klass):
    session_id, game_id, _ = await short_game(klass)
    await make(ADMIN, roles=(AccountRole.admin,))
    test_game = await commands.create(
        "lecturer_test", GameSettings(), class_session_id=uuid.UUID(session_id)
    )
    refused = [
        await weeks(email(0), game_id),  # a Student of the Class, seated in the game
        await weeks(OTHER, game_id),  # a Lecturer of another Class
        await weeks(ADMIN, game_id),  # an Admin not attached to the Class
        await weeks(LECTURER, str(test_game)),  # a test Game is in no staff list (AD-13)
        await weeks(LECTURER, str(uuid.uuid7())),  # no such Game
        await weeks(LECTURER, "not-an-id"),
    ]
    assert {r.status_code for r in refused} == {403}
    assert len({r.content for r in refused}) == 1


async def test_a_class_game_that_has_not_started_has_no_weeks(klass):
    session_id, _ = await confirmed(klass, 2)
    [(game_id,)] = rows(
        "SELECT id FROM games WHERE class_session_id = %s ORDER BY game_number LIMIT 1",
        session_id,
    )
    response = await weeks(LECTURER, str(game_id))
    assert response.status_code == 200
    assert response.json()["weeks"] == []
