"""The Game data export of a Class session (Story 14.8, cut list, FR-88, AD-12, AD-13, AD-14,
AD-15, AD-17, C-2).

«Last ned spilldata (CSV)» in the Klasseøkt's «Eksport» block downloads one row per Game, Week and
Seat of the Decision log, for every Game `scope.reporting_games` counts in the Class session: the
Class games, the make-up games and the Replays, each with its purpose in its own column. Lecturer
test Games, simulations and every Game of a Control test Class session are never in it (AD-13).
Only while `FEATURE_GAME_DATA_EXPORT` is on (AD-17), and only for the Lecturers of the Class
(`game_data.export`).

The columns are the fixed allow-list `COLUMNS`: no AI score, AI feedback or Indicative letter,
and no name, e-mail, `user_id`, Seat id or Game id (C-2, AD-14). A Seat is its game and Role, with
the occupant kind `student` or `ai`. Who decided an Order is the Decision log's `decided_by`, and
`mark` the one AD-15 mapping (`games.seat_mark`): a fallback first, then a switch or Takeover.

The file is for the Lecturer's own tools: headers and values are the stored codes, the dialect is
the Completion export's (`completion_export.csv_lines`: UTF-8 with BOM, `;`, the decimal comma).
Built at request time and streamed, never stored."""

from __future__ import annotations

import uuid
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from app.engine.settings import ROLES
from app.modules.games import service as games
from app.modules.games.service import GameDataRow, OccupantKind, Purpose, SessionGame
from app.modules.reports import scope
from app.modules.reports.completion_export import Value, csv_lines
from app.modules.reports.report import ReportRefused
from app.modules.sessions import service as sessions
from app.platform import audit, auth, authz
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

__all__ = [
    "COLUMNS",
    "CSV_TYPE",
    "DOWNLOADED_AUDIT",
    "EXPORT",
    "GameData",
    "enabled",
    "export",
    "file_name",
    "game_keys",
    "row_values",
    "to_csv",
]

EXPORT = "game_data.export"
"""The Class action of the Game data export: the Class's owners only."""

DOWNLOADED_AUDIT = "game_data_export.downloaded"

CSV_TYPE = "text/csv; charset=utf-8"

COLUMNS: tuple[str, ...] = (
    "purpose",
    "game",
    "week",
    "role",
    "incoming_order",
    "incoming_delivery",
    "inventory",
    "backlog",
    "order",
    "cost",
    "decided_by",
    "mark",
    "occupant",
)
"""The allow-list of the file's columns, in order (FR-88). Nothing else is written: no AI score,
AI feedback or Indicative letter (C-2), no name or id (AD-14). A test holds it to a literal."""

PURPOSE_ORDER: tuple[Purpose, ...] = (Purpose.CLASS, Purpose.MAKEUP, Purpose.REPLAY)
"""The purposes in the file's order: the Class games first; any other after them."""
_PURPOSE_RANK = {purpose: index for index, purpose in enumerate(PURPOSE_ORDER)}

STUDENT, AI = "student", "ai"
"""The occupant kinds the file names: a Student, or any AI player (LLM, Rule-based, scripted)."""


def enabled() -> bool:
    """`FEATURE_GAME_DATA_EXPORT` (AD-17): whether the export exists at all."""
    return get_settings().feature_game_data_export


@dataclass(frozen=True)
class GameData:
    """What the download sends: the rows in `COLUMNS` order, how many Games they come from and
    the Class session's number."""

    rows: list[tuple[Value, ...]]
    games: int
    number: int | None


def game_keys(found: Sequence[SessionGame]) -> dict[uuid.UUID, tuple[Purpose, int]]:
    """Each Game's key in the file (pure): its purpose and, for a Class game, its game number;
    a make-up game or a Replay has none, so it is numbered 1, 2, … within its purpose in the order
    the Games were made (their UUIDv7 ids). A Class game without a number is left out."""
    keys: dict[uuid.UUID, tuple[Purpose, int]] = {}
    counts: dict[Purpose, int] = {}
    for game in sorted(found, key=lambda each: each.game_id.bytes):
        if game.purpose == Purpose.CLASS:
            if game.number is not None:
                keys[game.game_id] = (game.purpose, game.number)
            continue
        counts[game.purpose] = counts.get(game.purpose, 0) + 1
        keys[game.game_id] = (game.purpose, counts[game.purpose])
    return keys


def row_values(key: tuple[Purpose, int], row: GameDataRow) -> tuple[Value, ...]:
    """One Decision log row in `COLUMNS` order (pure)."""
    mark = games.seat_mark(row.decided_by, row.fallback, row.occupant_kind, row.reason)
    purpose, game = key
    return (
        str(purpose),
        game,
        row.week,
        row.role,
        row.incoming_order,
        row.incoming_delivery,
        row.inventory,
        row.backlog,
        row.order,
        row.cost,
        row.decided_by,
        "" if mark is None else str(mark),
        STUDENT if row.occupant_kind == OccupantKind.STUDENT else AI,
    )


_ROLE_INDEX = {str(role): index for index, role in enumerate(ROLES)}


async def export(user: authz.Principal, class_session_id: uuid.UUID) -> GameData | None:
    """The rows of the Game data export for a Lecturer of the Class. None (403) for anyone else
    and a Class session that does not exist; raises `ReportRefused("data_deleted")` once the
    Class session's Student data is deleted. A fixed number of reads whatever the number of Games
    (NFR-3)."""
    row = await sessions.staff_session_row(user, class_session_id, EXPORT)
    if row is None:
        return None
    if sessions.data_deleted(row, auth.utcnow()):
        raise ReportRefused("data_deleted")
    async with get_sessionmaker()() as s:
        keys = game_keys(await scope.reporting_games(s, class_session_id))
        logged = await games.game_data_rows(s, list(keys))
        heading = await sessions.report_heading(s, class_session_id, user.id)
    ordered = sorted(
        logged,
        key=lambda each: (
            _PURPOSE_RANK.get(keys[each.game_id][0], len(_PURPOSE_RANK)),
            keys[each.game_id][1],
            each.week,
            _ROLE_INDEX.get(each.role, len(_ROLE_INDEX)),
        ),
    )
    return GameData(
        rows=[row_values(keys[each.game_id], each) for each in ordered],
        games=len(keys),
        number=None if heading is None else heading.number,
    )


async def record_download(
    user: authz.Principal, class_session_id: uuid.UUID, found: GameData
) -> None:
    """One audit row per download, once the rows are read: the Class session, how many Games and
    rows the file holds (AD-14)."""
    async with get_sessionmaker().begin() as s:
        await audit.record(
            s,
            user.id,
            DOWNLOADED_AUDIT,
            {"class_session_id": class_session_id},
            {"games": found.games, "rows": len(found.rows)},
            auth.utcnow(),
        )


def file_name(number: int | None) -> str:
    """The file name the browser saves."""
    return "spilldata.csv" if number is None else f"spilldata-klasseokt-{number}.csv"


def to_csv(rows: Sequence[Sequence[Value]]) -> Iterator[bytes]:
    """The file, one line at a time (`completion_export.csv_lines` with `COLUMNS`)."""
    return csv_lines(COLUMNS, rows)
