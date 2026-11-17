import json
from contextlib import contextmanager

import psycopg

from app.platform import events
from tests.conftest import libpq_dsn


def query(url: str, sql: str, params: tuple = ()) -> list[tuple]:
    with psycopg.connect(libpq_dsn(url)) as conn:
        return conn.execute(sql, params).fetchall()


def execute(url: str, sql: str, params: tuple = ()) -> None:
    with psycopg.connect(libpq_dsn(url), autocommit=True) as conn:
        conn.execute(sql, params)


def counts(url: str) -> tuple[int, int, int]:
    (row,) = query(
        url,
        "SELECT (SELECT count(*) FROM games), (SELECT count(*) FROM seats), "
        "(SELECT count(*) FROM seat_occupancy)",
    )
    return row


def tamper(url: str, sql: str, params: tuple = ()) -> None:
    """Change stored rows past their append-only triggers, as an after-the-fact edit would."""
    with psycopg.connect(libpq_dsn(url), autocommit=True) as conn:
        conn.execute("SET session_replication_role = replica")
        conn.execute(sql, params)


async def play_week(game_id: str) -> object:
    """Place every missing Order of the open Week (Guided Order or the stored reference Order)
    and return the last `OrderPlaced`."""
    from app.engine import guided_order
    from app.modules.games import commands, service

    game = await service.get_game(game_id)
    placed = None
    week = (await service.seat_state(game_id, game.seats[0].id)).week
    for seat in game.seats:
        turn = await service.open_turn(game_id, seat.id, week)
        if turn.ordered_at is not None:
            continue
        if turn.guided:
            order, by = guided_order(game.settings), "guided"
        else:
            order, by = turn.rule_based_reference_order, "rule_based"
        placed = await commands.place_order(game_id, seat.role, week, order, by)
    return placed


async def play_to_end(game_id: str) -> None:
    """Play every Week of a started Game with Guided and reference Orders; the order source
    places those of the Seats no Student holds."""
    from app.modules.games import service

    while (await service.get_game(game_id)).lifecycle != "finished":
        await play_week(game_id)


@contextmanager
def listening(url: str):
    """Collect the event payloads committed while the block runs (read with `.drain()`)."""
    conn = psycopg.connect(libpq_dsn(url), autocommit=True)
    conn.execute(f"LISTEN {events.CHANNEL}")

    class Events:
        def drain(self, timeout: float = 0.5) -> list[dict]:
            return [json.loads(n.payload) for n in conn.notifies(timeout=timeout)]

    try:
        yield Events()
    finally:
        conn.close()


def seat_student(url: str, game_id: str, *roles: str) -> None:
    """Give each Seat of `roles` a `student` occupant before the start, as allocation will
    (Epic 5). No order source places a Student's Order, so the test places it."""
    import uuid

    for role in roles:
        execute(
            url,
            "INSERT INTO seat_occupancy (id, seat_id, from_week, occupant_kind, reason) "
            "SELECT %s, id, 1, 'student', 'initial' FROM seats WHERE game_id = %s AND role = %s",
            (uuid.uuid7(), game_id, role),
        )
