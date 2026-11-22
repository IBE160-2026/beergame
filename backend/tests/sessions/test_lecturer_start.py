"""Story 8.10 through the api: a Lecturer starts one Class game from Spillstyring
(`POST /api/games/{id}/start`) or every game not started from the «Start spill» page
(`GET`/`POST /api/class-sessions/{id}/start-games`), one `games.commands.start` per Game; the
Oversikt counts the games that may start (FR-22, AD-2, AD-12, AD-15, UX-DR52, NFR-7). Nothing may
start before the lock; Assistant lecturers, Students and outsiders are refused. The api's clock is
fixed and the sweep is handed its `now`."""

import uuid

from app.modules.games import commands as games_commands
from app.modules.games.models import SNAPSHOT_COLUMNS
from app.modules.ops import sweep
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import _dump, _restore
from tests.messaging.helpers import rows
from tests.sessions.test_dates import OUTSIDER, START
from tests.sessions.test_game_end import _empty, clock, klass
from tests.sessions.test_game_insight import insight
from tests.sessions.test_lock import MINUTE
from tests.sessions.test_open_games import confirmed, games_of
from tests.sessions.test_orders import code
from tests.sessions.test_overview import overview, user_name
from tests.sessions.test_start_game import start, task_done
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import home

__all__ = ["_empty", "clock", "klass"]


def start_one(who: str, game_id: str):
    return call(who, "POST", f"/api/games/{game_id}/start")


def page(who: str, session_id: str):
    return call(who, "GET", f"/api/class-sessions/{session_id}/start-games")


def start_all(who: str, session_id: str, game_ids: list[str]):
    return call(
        who, "POST", f"/api/class-sessions/{session_id}/start-games", json={"game_ids": game_ids}
    )


async def student_of(game_id: str, count: int) -> str:
    """The address of a Student the allocation seated in the game."""
    for i in range(count):
        if (await home(email(i)))["game"]["id"] == game_id:
            return email(i)
    raise AssertionError(f"no Student in {game_id}")


def user_id(address: str) -> str:
    return str(rows("SELECT id FROM users WHERE email = %s", address)[0][0])


async def outsiders(klass: str) -> tuple[str, ...]:
    """An Assistant lecturer of the Class and a Lecturer of none: both are refused."""
    assistant = await make(ASSISTANT, roles=())
    put_staff(klass, assistant, "assistant")
    await make(OUTSIDER, roles=())
    return ASSISTANT, OUTSIDER


async def test_a_lecturer_starts_one_game_and_a_late_press_names_who_started_it(klass):
    session_id, seated = await confirmed(klass, 5)  # two Class games
    first, second = (g[0] for g in games_of(session_id))
    refused = await outsiders(klass)

    # Before the lock no start is offered anywhere, and the api refuses one.
    assert (await overview(LECTURER, session_id)).json()["startable"] == 0
    assert (await insight(LECTURER, first)).json()["can_start"] is False
    assert code(await start_one(LECTURER, first)) == (409, "game_not_ready")
    assert (await page(LECTURER, session_id)).json()["games"] == []

    await sweep.run(START + MINUTE)  # locked: each game has its snapshot
    assert (await overview(LECTURER, session_id)).json()["startable"] == 2
    seen = (await insight(LECTURER, first)).json()
    assert (seen["can_start"], seen["started_by"], seen["started_at"]) == (True, None, None)
    # An Assistant lecturer gets neither the action nor the count, and the api refuses them.
    assert (await overview(ASSISTANT, session_id)).json()["startable"] == 0
    assert (await insight(ASSISTANT, first)).json()["can_start"] is False
    student = await student_of(first, 5)
    for who in (*refused, student):
        assert code(await start_one(who, first)) == (403, "forbidden")

    answer = await start_one(LECTURER, first)
    assert answer.status_code == 200
    body = answer.json()
    assert body["status"] != "not_started" and body["can_start"] is False
    assert body["started_by"] == user_name(LECTURER) and body["started_at"] is not None
    [(actor, action)] = rows(
        "SELECT actor_user_id::text, action FROM audit_events WHERE target_ids->>'game_id' = %s",
        first,
    )
    assert (actor, action) == (user_id(LECTURER), "game.started")
    # Its Students read it started.
    assert (await home(student))["game"]["status"] == "running"

    # A Student of the other game presses first: the Lecturer's press says who, by id.
    other = await student_of(second, 5)
    await task_done(uuid.UUID(user_id(other)), session_id)
    assert (await start(other, second)).status_code == 200
    late = await start_one(LECTURER, second)
    assert code(late) == (409, "game_already_started")
    fields = late.json()["error"]["fields"]
    assert fields["acted_by"] == {"kind": "student", "user_id": user_id(other)}
    assert fields["acted_at"] is not None
    # Spillinnsikt, read again, names them.
    assert (await insight(LECTURER, second)).json()["started_by"] == user_name(other)
    assert (await overview(LECTURER, session_id)).json()["startable"] == 0
    assert len(seated) == 5


async def test_the_page_lists_the_games_not_started_and_the_batch_skips_the_rest(klass):
    session_id, _ = await confirmed(klass, 9)  # three Class games
    ids = [g[0] for g in games_of(session_id)]
    refused = await outsiders(klass)

    # Before the lock nothing starts: every listed id is skipped.
    early = await start_all(LECTURER, session_id, ids)
    assert early.json() == {"started": 0, "skipped": 3}

    await sweep.run(START + MINUTE)
    assert (await start_one(LECTURER, ids[0])).status_code == 200
    listed = (await page(LECTURER, session_id)).json()
    assert [g["game_id"] for g in listed["games"]] == ids[1:]
    assert all(g["status"] == "not_started" and len(g["seats"]) == 4 for g in listed["games"])
    assert listed["class_session_id"] == session_id and listed["session_number"] >= 1
    for who in refused:
        assert code(await page(who, session_id)) == (403, "forbidden")
        assert code(await start_all(who, session_id, ids)) == (403, "forbidden")

    # A game of AI players alone is never offered: it would play itself out (Story 8.14's).
    ai_only = await games_commands.create("class", class_session_id=session_id, game_number=9)
    [frozen] = rows(
        "SELECT settings, demand_series, demand_seed, rules_version, session_runtime FROM games "
        "WHERE id = %s",
        ids[1],
    )
    snapshot = dict(zip(SNAPSHOT_COLUMNS, frozen, strict=True))
    await games_commands.set_snapshot(ai_only, snapshot, keep_students=[])
    assert ai_only not in [g["game_id"] for g in (await page(LECTURER, session_id)).json()["games"]]
    assert (await overview(LECTURER, session_id)).json()["startable"] == 2
    assert (await insight(LECTURER, ai_only)).json()["can_start"] is False
    assert code(await start_one(LECTURER, ai_only)) == (409, "game_not_ready")

    # The started game, the AI game and an id of no game here are skipped; the others start.
    foreign = str(uuid.uuid7())
    done = await start_all(LECTURER, session_id, [*ids, ai_only, foreign, ids[1]])
    assert done.status_code == 200
    assert done.json() == {"started": 2, "skipped": 3}
    lifecycles = {game_id: lifecycle for game_id, _, lifecycle, *_ in games_of(session_id)}
    assert [lifecycles[g] for g in ids] == ["running"] * 3 and lifecycles[ai_only] == "not_started"
    # A repeat is safe: nothing is left to start.
    assert (await start_all(LECTURER, session_id, ids)).json() == {"started": 0, "skipped": 3}
    assert (await page(LECTURER, session_id)).json()["games"] == []
    # An empty list is refused by the body's own rule.
    assert (await start_all(LECTURER, session_id, [])).status_code == 422


def _copies(session_id: str, game_id: str, numbers: range) -> list[str]:
    """Copies of the not-started Class game under new ids in the same Class session, one per game
    number in `numbers` (their rows copied, not played: no game per number is built)."""
    dumped = _dump(TEST_DATABASE_URL, game_id)
    columns = {
        table: [
            name
            for (name,) in rows(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s "
                "ORDER BY ordinal_position",
                table,
            )
        ]
        for table in ("games", "game_summaries")
    }
    made = []
    for number in numbers:
        copy = dict(dumped)
        for table, names in columns.items():
            if not copy[table]:
                continue
            at = names.index("game_number")
            lines = []
            for line in copy[table].splitlines():
                values = line.split("\t")
                values[at] = str(number)
                lines.append("\t".join(values))
            copy[table] = "\n".join(lines) + "\n"
        made.append(_restore(TEST_DATABASE_URL, copy))
    # `_restore` gives every id a new value; the copies stay in the Class session.
    for table, key in (("games", "id"), ("game_summaries", "game_id")):
        execute(
            f"UPDATE {table} SET class_session_id = %s WHERE {key} = ANY(%s::uuid[])",
            session_id,
            made,
        )
    return made


async def test_a_hundred_class_games_start_in_one_action(klass):
    session_id, _ = await confirmed(klass, 4)  # one Class game, four Students
    await sweep.run(START + MINUTE)
    [(first, *_)] = games_of(session_id)
    ids = [first, *_copies(session_id, first, range(2, 101))]
    assert (await overview(LECTURER, session_id)).json()["startable"] == 100
    done = await start_all(LECTURER, session_id, ids)
    assert done.json() == {"started": 100, "skipped": 0}
    assert rows(
        "SELECT count(*) FROM games WHERE class_session_id = %s AND lifecycle = 'running' "
        "AND started_by IS NOT NULL",
        session_id,
    ) == [(100,)]


async def test_one_failing_start_never_stops_the_others(klass, monkeypatch):
    session_id, _ = await confirmed(klass, 9)  # three Class games
    ids = [g[0] for g in games_of(session_id)]
    await sweep.run(START + MINUTE)
    original = games_commands.start

    async def failing(game_id: str, *, actor=None) -> int:
        if game_id == ids[0]:
            raise games_commands.CommandError("game_already_started", "meanwhile", 409)
        if game_id == ids[1]:
            raise RuntimeError("the database went away")
        return await original(game_id, actor=actor)

    monkeypatch.setattr(games_commands, "start", failing)
    done = await start_all(LECTURER, session_id, ids)
    assert (done.status_code, done.json()) == (200, {"started": 1, "skipped": 2})
    assert [lifecycle for _, _, lifecycle, *_ in games_of(session_id)] == [
        "not_started",
        "not_started",
        "running",
    ]
