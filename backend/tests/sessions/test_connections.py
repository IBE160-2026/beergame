"""One pooled connection at a time per request (docs/ops/connection-budget.md): the pool has no
overflow and a 5-second timeout, so a request that holds a connection while it waits for a second
can starve. When a Week moves on, every open page of the game reads Hjem, the game and the play
envelope at once; with each of those reads holding two, ten of them held the whole pool and waited
for each other until all failed at the timeout (seen in the e2e suite, which plays real games on
the stack). Each Student route a live update or a press brings is checked here: it never holds
more than one connection at once."""

from contextlib import contextmanager

from sqlalchemy import event

from app.platform import db
from tests.classes.test_classes import as_user
from tests.identity.helpers import CSRF, client
from tests.sessions.test_game_end import _empty, clock, klass, short_game
from tests.sessions.test_student_choice import email
from tests.sessions.test_time_proposal import db_time, deadline_in

__all__ = ["_empty", "clock", "klass"]


@contextmanager
def most_held():
    """The most connections checked out of the pool at one moment inside the block. The calls
    here run one after the other, so any moment with two is one request holding two."""
    pool = db.get_engine().sync_engine.pool
    seen = {"now": 0, "most": 0}

    def out(*_):
        seen["now"] += 1
        seen["most"] = max(seen["most"], seen["now"])

    def back(*_):
        seen["now"] -= 1

    event.listen(pool, "checkout", out)
    event.listen(pool, "checkin", back)
    try:
        yield seen
    finally:
        event.remove(pool, "checkout", out)
        event.remove(pool, "checkin", back)


async def held(who: str, method: str, path: str, **kw) -> int:
    async with client() as c:
        await as_user(c, who)
        with most_held() as seen:
            response = await c.request(method, path, headers=CSRF, **kw)
    assert response.status_code < 300, (path, response.status_code, response.text)
    return seen["most"]


async def test_the_student_routes_of_a_running_game_hold_one_connection_at_a_time(klass):
    session_id, game_id, _ = await short_game(klass)
    deadline_in(session_id, "7 days")
    reads = {
        "the signed-in User": ("GET", "/api/auth/me"),  # one read of its own: the measure holds
        "Hjem": ("GET", "/api/me/class-sessions"),
        "the game": ("GET", f"/api/me/games/{game_id}"),
        "the play envelope": ("GET", f"/api/me/games/{game_id}/play"),
    }
    found = {name: await held(email(0), *route) for name, route in reads.items()}
    proposed = await held(
        email(0),
        "POST",
        f"/api/me/games/{game_id}/time-proposal",
        json={"at": db_time("1 day").isoformat()},
    )
    found["a proposed time"] = proposed
    async with client() as c:
        await as_user(c, email(1))
        game = (await c.get(f"/api/me/games/{game_id}")).json()
    proposal = game["time_proposal"]["id"]
    found["an accepted time"] = await held(
        email(1), "POST", f"/api/me/games/{game_id}/time-proposal/{proposal}/accept"
    )
    found["a viewed Guided Week"] = await held(
        email(0), "POST", f"/api/me/games/{game_id}/weeks/1/view"
    )
    await held(email(1), "POST", f"/api/me/games/{game_id}/weeks/1/view")  # Week 2 opens
    found["an Order"] = await held(
        email(0), "POST", f"/api/me/games/{game_id}/weeks/2/order", json={"order": 4}
    )
    found["the play envelope after it"] = await held(
        email(0), "GET", f"/api/me/games/{game_id}/play"
    )
    assert found == dict.fromkeys(found, 1)
