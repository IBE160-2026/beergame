import hashlib
import json
import os
import re
import uuid
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg import sql

from app.platform import events
from tests.conftest import RUN_TMP, kept_connection, libpq_dsn


def query(url: str, sql: str, params: tuple = ()) -> list[tuple]:
    return kept_connection(url).execute(sql, params).fetchall()


def execute(url: str, sql: str, params: tuple = ()) -> None:
    kept_connection(url).execute(sql, params)


def counts(url: str) -> tuple[int, int, int]:
    (row,) = query(
        url,
        "SELECT (SELECT count(*) FROM games), (SELECT count(*) FROM seats), "
        "(SELECT count(*) FROM seat_occupancy)",
    )
    return row


def tamper(url: str, sql: str, params: tuple = ()) -> None:
    """Change stored rows past their append-only triggers, as an after-the-fact edit would."""
    conn = kept_connection(url)
    with conn.transaction():
        conn.execute("SET LOCAL session_replication_role = replica")
        conn.execute(sql, params)


async def play_week(game_id: str) -> object:
    """Complete the open Week: in a Guided Week every Student Seat views it (its Order was
    placed when the Week opened); otherwise place every missing Order (the stored reference
    Order). Returns the last `OrderPlaced`, or None when only views were needed."""
    from app.modules.games import commands, service

    game = await service.get_game(game_id)
    placed = None
    week = (await service.seat_state(game_id, game.seats[0].id)).week
    for seat in game.seats:
        turn = await service.open_turn(game_id, seat.id, week)
        if turn.guided:
            if seat.occupant_kind == "student" and turn.viewed_at is None:
                student = seat.user_id or student_of(game_id, seat.role)
                await commands.view_week(game_id, seat.role, week, actor=student)
            continue
        if turn.ordered_at is not None:
            continue
        placed = await commands.place_order(
            game_id, seat.role, week, turn.rule_based_reference_order, "rule_based"
        )
    return placed


async def play_to_end(game_id: str) -> None:
    """Play every Week of a started Game with Guided and reference Orders; the order source
    places those of the Seats no Student holds."""
    from app.modules.games import service

    while (await service.get_game(game_id)).lifecycle != "finished":
        await play_week(game_id)


_ONE_GAME = {
    "games": "SELECT * FROM games WHERE id = {}",
    "seats": "SELECT * FROM seats WHERE game_id = {}",
    "seat_occupancy": (
        "SELECT o.* FROM seat_occupancy o JOIN seats s ON s.id = o.seat_id WHERE s.game_id = {}"
    ),
    "game_weeks": "SELECT * FROM game_weeks WHERE game_id = {}",
    "seat_turns": "SELECT * FROM seat_turns WHERE game_id = {}",
    "seat_weeks": "SELECT * FROM seat_weeks WHERE game_id = {}",
    "game_checks": "SELECT * FROM game_checks WHERE game_id = {}",
    "game_summaries": "SELECT * FROM game_summaries WHERE game_id = {}",
}
"""Every stored row of one Game, table by table in the order they can be inserted."""

_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_played: dict[object, dict[str, str]] = {}


def _dump(url: str, game_id: str) -> dict[str, str]:
    conn = kept_connection(url)
    with conn.transaction(), conn.cursor() as cur:
        dumped = {}
        for table, select in _ONE_GAME.items():
            statement = sql.SQL("COPY ({}) TO STDOUT").format(
                sql.SQL(select).format(sql.Literal(game_id))
            )
            with cur.copy(statement) as copy:
                dumped[table] = b"".join(bytes(block) for block in copy).decode()
        return dumped


def _restore(url: str, dumped: dict[str, str], keep: set[str] = frozenset()) -> str:
    """Store a copy of a dumped Game under new ids (UUIDv7, drawn in the order of the old ones,
    so every ordering by id is kept), but the ids in `keep`; returns the new Game id."""
    old = sorted(set(_UUID.findall("".join(dumped.values()))) - keep)
    new = {value: str(uuid.uuid7()) for value in old}
    game_id = new[_UUID.search(dumped["games"]).group()]
    conn = kept_connection(url)
    with conn.transaction(), conn.cursor() as cur:
        for table, rows in dumped.items():
            with cur.copy(sql.SQL("COPY {} FROM STDIN").format(sql.Identifier(table))) as copy:
                copy.write(_UUID.sub(lambda m: new.get(m.group(), m.group()), rows))
    return game_id


def class_game_copies(
    url: str, session_id: object, game_id: str, numbers: range, keep: set | None = None
) -> list[str]:
    """Copies of a not-started Class game under new ids in the same Class session, one per game
    number in `numbers`: its rows copied, not built again command by command, which made the
    100-game tests (Stories 8.10, 8.12, 8.14) slow. The ids in `keep` stay as they are (the
    Students and the session)."""
    dumped = _dump(url, game_id)
    columns = {
        table: [
            name
            for (name,) in query(
                url,
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s "
                "ORDER BY ordinal_position",
                (table,),
            )
        ]
        for table in ("games", "game_summaries")
    }
    keep = {str(value) for value in keep or ()}
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
        made.append(_restore(url, copy, keep))
    # `_restore` gives every other id a new value; the copies stay in the Class session.
    for table, key in (("games", "id"), ("game_summaries", "game_id")):
        execute(
            url,
            f"UPDATE {table} SET class_session_id = %s WHERE {key} = ANY(%s::uuid[])",
            (session_id, made),
        )
    return made


def _shared_file(key: object) -> Path | None:
    """Where the pytest-xdist workers of this run share the Game remembered under `key`, so it
    is played once per run rather than once per worker: the run's temporary directory, which
    pytest removes a few runs later (`RUN_TMP`, set in `tests/conftest.py`). None outside
    pytest-xdist."""
    run = os.environ.get(RUN_TMP)
    if not run:
        return None
    name = hashlib.sha256(repr(key).encode()).hexdigest()[:32]
    return Path(run) / "played" / f"{name}.json"


def stored_copy(url: str, key: object) -> str | None:
    """A new copy of the Game remembered under `key`, or None before one is remembered."""
    if key not in _played:
        shared = _shared_file(key)
        if shared is None or not shared.exists():
            return None
        _played[key] = json.loads(shared.read_text(encoding="utf-8"))
    return _restore(url, _played[key])


def remember(url: str, key: object, game_id: str) -> None:
    """Remember the stored rows of the Game for `stored_copy`, in this worker and for the
    others (written whole, then renamed, so no worker reads half a file)."""
    _played[key] = _dump(url, game_id)
    shared = _shared_file(key)
    if shared is not None:
        shared.parent.mkdir(exist_ok=True)
        part = shared.with_suffix(f".{os.getpid()}.part")
        part.write_text(json.dumps(_played[key]), encoding="utf-8")
        try:
            os.replace(part, shared)
        except PermissionError:  # Windows: another worker is reading the copy it wrote first
            part.unlink()


async def played_once(url: str, key: object, play) -> str:
    """The id of a Game that `await play()` stores. The first call with `key` plays it; later
    calls, in any test, store a copy of its rows under new ids instead of playing the same
    Game again. Only for tests that read a played Game, never for tests of the play itself."""
    copy = stored_copy(url, key)
    if copy is not None:
        return copy
    game_id = await play()
    remember(url, key, game_id)
    return game_id


async def classic_game(url: str, seed: int = 7) -> str:
    """A finished Classic simulation Game of four Rule-based players, played once per seed and
    session (`played_once`)."""
    from app.engine import GameSettings
    from app.modules.games import commands

    async def play() -> str:
        game_id = await commands.create("simulation", GameSettings(), seed=seed)
        await commands.start(game_id)  # four Rule-based players: finished on return
        await play_to_end(game_id)
        return game_id

    return await played_once(url, ("classic", seed), play)


@contextmanager
def listening(url: str):
    """Collect the event payloads committed while the block runs (read with `.drain()`)."""
    conn = psycopg.connect(libpq_dsn(url), autocommit=True)
    conn.execute(f"LISTEN {events.CHANNEL}")

    class Events:
        def drain(self, timeout: float = 5.0) -> list[dict]:
            """Every event committed so far. Postgres delivers notifications in commit order,
            so a marker this connection sends now arrives after all of them: reading up to it
            needs no fixed wait."""
            marker = {"drain": str(uuid.uuid4())}
            conn.execute("SELECT pg_notify(%s, %s)", (events.CHANNEL, json.dumps(marker)))
            received = []
            for notify in conn.notifies(timeout=timeout):
                payload = json.loads(notify.payload)
                if payload == marker:
                    return received
                received.append(payload)
            raise AssertionError(f"the drain marker did not arrive within {timeout} s")

    try:
        yield Events()
    finally:
        conn.close()


def student_of(game_id: str, role: str) -> uuid.UUID:
    """The id `seat_student` gives the Student of the Seat of `role`."""
    return uuid.uuid5(uuid.NAMESPACE_URL, f"student:{game_id}:{role}")


def seat_student(url: str, game_id: str, *roles: str, anonymous: bool = False) -> None:
    """Give each Seat of `roles` a `student` occupant before the start, as allocation will
    (Epic 5), with the id `student_of` gives (none when `anonymous`: no `user:` event, and no
    view). Outside Guided Weeks no order source places a Student's Order, so the test places
    it; in a Guided Week the test views it (`view`)."""
    for role in roles:
        execute(
            url,
            "INSERT INTO seat_occupancy (id, seat_id, from_week, occupant_kind, reason, user_id) "
            "SELECT %s, id, 1, 'student', 'initial', %s FROM seats "
            "WHERE game_id = %s AND role = %s",
            (uuid.uuid7(), None if anonymous else student_of(game_id, role), game_id, role),
        )


async def view(game_id: str, role: str, week: int) -> bool:
    """The Student `seat_student` seated in `role` opens the Guided Week `week` (Story 6.10)."""
    from app.modules.games import commands

    return await commands.view_week(game_id, role, week, actor=student_of(game_id, role))
