"""Shared pieces for the `app.ai` tests."""

import copy
import json
from pathlib import Path

import psycopg

from tests.conftest import libpq_dsn

CONFIGS = Path(__file__).resolve().parents[2] / "ai-configs"
MOCK = json.loads((CONFIGS / "mock.json").read_text(encoding="utf-8"))


def mock_config(**changes: object) -> dict:
    """The shipped mock config with top-level fields replaced."""
    data = copy.deepcopy(MOCK)
    data.update(changes)
    return data


def query(url: str, sql: str, params: tuple = ()) -> list[tuple]:
    with psycopg.connect(libpq_dsn(url)) as conn:
        return conn.execute(sql, params).fetchall()
