"""Verify a restored database: `python -m app.ops.verify_restore <database_url>` (Story 15.11,
NFR-4, AD-4).

It reads a restored copy of the database and replays each finished Game through the engine at its
stored `rules_version`, checking the stored Week states, the books and the Decision log (the
finished-game check of FR-29, without storing a check). One line per Game, then pass or fail.

It changes no data: everything is read in one `REPEATABLE READ, READ ONLY` transaction on a
connection of its own, so a write would be refused by Postgres. It prints no secret: never the
URL, and of an error only its type.

Exit status: 0 when at least one Game was checked and every one verifies; 1 when a Game fails;
2 when nothing could be checked (no connection, no schema, no finished Game, an unknown `--game`).
"""

import argparse
import asyncio
import sys
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.modules.games import service as games

PASS, FAIL, CANNOT = 0, 1, 2
CONNECT_TIMEOUT_S = 10


@dataclass(frozen=True)
class GameResult:
    game_id: str
    rules_version: int | None
    rules: tuple[str, ...]
    """The rules of the violations found (`replay`, `conservation`, …); empty when it verifies."""
    refused: str | None = None
    """Why the Game could not be replayed (`rules_version_unsupported`, …)."""

    @property
    def ok(self) -> bool:
        return self.refused is None and not self.rules


@dataclass(frozen=True)
class RestoreCheck:
    revision: str | None
    results: tuple[GameResult, ...]
    problem: str | None = None
    """Why nothing could be checked."""

    @property
    def status(self) -> int:
        if self.problem is not None or not self.results:
            return CANNOT
        return PASS if all(result.ok for result in self.results) else FAIL


def engine_url(database_url: str) -> str:
    """psycopg 3 for any Postgres URL form, as the app's settings do."""
    for prefix in ("postgresql://", "postgres://"):
        if database_url.startswith(prefix):
            return "postgresql+psycopg://" + database_url[len(prefix) :]
    return database_url


async def _revision(session: AsyncSession) -> str | None:
    exists = await session.scalar(text("SELECT to_regclass('alembic_version') IS NOT NULL"))
    if not exists:
        return None
    return await session.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))


async def _check_game(conn: AsyncConnection, session: AsyncSession, game_id: uuid.UUID):
    """One Game's result. A Game whose rows cannot be read or replayed fails by itself, under a
    savepoint, so the other Games are still checked."""
    try:
        async with conn.begin_nested():
            version, violations = await games.replay_check(session, game_id)
    except games.ViewError as refused:
        return GameResult(str(game_id), None, (), refused=refused.code)
    except Exception as exc:  # the type only, as everywhere in this command
        return GameResult(str(game_id), None, (), refused=type(exc).__name__)
    found = tuple(dict.fromkeys(violation.rule for violation in violations))
    return GameResult(str(game_id), version, found)


async def verify(
    database_url: str, *, game_ids: Sequence[str] = (), limit: int | None = None
) -> RestoreCheck:
    """Replay the finished Games of the database at `database_url` (or only `game_ids`; with
    `limit`, the newest that many), reading only."""
    try:
        wanted = list(dict.fromkeys(uuid.UUID(value) for value in game_ids))
    except ValueError:
        return RestoreCheck(None, (), problem="a --game value is not a Game id")
    engine = create_async_engine(
        engine_url(database_url),
        poolclass=NullPool,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_S},
    )
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            session = AsyncSession(bind=conn)
            revision = await _revision(session)
            if revision is None:
                return RestoreCheck(None, (), problem="the database has no schema of this app")
            finished = await games.finished_game_ids_in(session)
            if wanted:
                unknown = [str(game) for game in wanted if game not in finished]
                if unknown:
                    return RestoreCheck(
                        revision, (), problem=f"no finished Game {', '.join(unknown)}"
                    )
                finished = wanted
            elif limit is not None:
                finished = finished[-limit:] if limit > 0 else []
            results = [await _check_game(conn, session, game) for game in finished]
            await conn.rollback()
    except Exception as exc:  # the type only: a driver's message can name the host and user
        return RestoreCheck(None, (), problem=f"cannot read the database ({type(exc).__name__})")
    finally:
        await engine.dispose()
    if not results:
        return RestoreCheck(revision, (), problem="the database has no finished Game")
    return RestoreCheck(revision, tuple(results))


def report_lines(check: RestoreCheck) -> list[str]:
    lines = [f"database revision: {check.revision or 'unknown'}"]
    for result in check.results:
        version = "?" if result.rules_version is None else str(result.rules_version)
        if result.refused is not None:
            verdict = f"FAILED ({result.refused})"
        elif result.rules:
            verdict = f"FAILED ({', '.join(result.rules)})"
        else:
            verdict = "verified"
        lines.append(f"game {result.game_id} rules_version {version}: {verdict}")
    passed = sum(result.ok for result in check.results)
    if check.status == CANNOT:
        lines.append(f"result: cannot verify: {check.problem or 'no finished Game'}")
    elif check.status == FAIL:
        lines.append(f"result: FAIL: {passed} of {len(check.results)} finished Games verify")
    else:
        lines.append(f"result: pass: {passed} of {len(check.results)} finished Games verify")
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.ops.verify_restore",
        description="Replay the finished Games of a restored database; changes no data.",
    )
    parser.add_argument("database_url", help="the restored copy (never printed)")
    parser.add_argument(
        "--game", action="append", default=[], help="check only this Game id (repeatable)"
    )
    parser.add_argument("--limit", type=int, help="check only the newest N finished Games")
    return parser


def main(argv: Sequence[str] | None = None, *, out: Callable[[str], object] = print) -> int:
    args = build_parser().parse_args(argv)
    if args.game and args.limit is not None:
        out("result: cannot verify: give --game or --limit, not both")
        return CANNOT
    if args.limit is not None and args.limit < 1:
        out("result: cannot verify: --limit must be at least 1")
        return CANNOT
    # psycopg's async mode cannot run on Windows' default Proactor loop.
    factory = asyncio.SelectorEventLoop if sys.platform == "win32" else asyncio.new_event_loop
    check = asyncio.run(
        verify(args.database_url, game_ids=args.game, limit=args.limit), loop_factory=factory
    )
    for line in report_lines(check):
        out(line)
    return check.status


if __name__ == "__main__":
    raise SystemExit(main())
