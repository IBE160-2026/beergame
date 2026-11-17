import json

import psycopg
import pytest

from app.platform import events
from app.platform.db import get_sessionmaker
from tests.conftest import libpq_dsn


def test_payload_holds_topic_id_and_version_only():
    assert json.loads(events.payload("game", "g1", 3)) == {
        "topic": "game",
        "id": "g1",
        "version": 3,
    }
    assert json.loads(events.payload("user", "u1")) == {
        "topic": "user",
        "id": "u1",
        "version": None,
    }


@pytest.mark.parametrize(
    ("topic", "version", "message"),
    [
        ("seat", None, "unknown event topic"),
        ("game", None, "carries the Game's version"),
        ("session", 2, "carries no version"),
    ],
)
def test_payload_refuses_what_ad8_forbids(topic, version, message):
    with pytest.raises(ValueError, match=message):
        events.payload(topic, "x", version)


def listener(url: str) -> psycopg.Connection:
    conn = psycopg.connect(libpq_dsn(url), autocommit=True)
    conn.execute(f"LISTEN {events.CHANNEL}")
    return conn


async def test_emit_is_delivered_on_commit(test_database):
    with listener(test_database) as conn:
        async with get_sessionmaker().begin() as session:
            await events.emit(session, "game", "g1", 7)
        received = [json.loads(n.payload) for n in conn.notifies(timeout=2, stop_after=1)]
    assert received == [{"topic": "game", "id": "g1", "version": 7}]


async def test_emit_in_a_rolled_back_transaction_announces_nothing(test_database):
    with listener(test_database) as conn:
        async with get_sessionmaker()() as session:
            await events.emit(session, "session", "s1")
            await session.rollback()
        assert list(conn.notifies(timeout=0.5)) == []
