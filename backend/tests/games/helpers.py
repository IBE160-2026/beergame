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
