"""The reporting scope (Story 13.1, AD-13, AD-27): which Games and which Students a report, a
statistic, an export, the funnel or Completion counts.

- `reporting_games` leaves out `lecturer_test` and `simulation` Games and every Game of a Control
  test Class session; a Replay is a reporting Game, with its `end_reason`.
- `reporting_students` is the registered Students of the Class less test students, and nobody
  for a Control test Class session.

Control test Class sessions (`kind=control_test`, Story 12.7) are read through
`sessions.service.kind_of`, test students (`is_test_student`, Story 12.8) through
`identity.service.test_students`; both are registered in the hooks below, which a test may swap.

The same scope as SQL, for the queries that read many Class sessions at once (the pseudonymised
export of Story 15.4): `reporting_game_ids()`, `reporting_student_ids()` and
`reporting_seat_holders()` are subqueries for `WHERE … IN (…)`. They read the same marks the
hooks' defaults read (`class_sessions.kind`, `users.is_test_student`, `games.purpose`), naming
the tables by name only, as in `platform/authz`.
"""

import uuid
from collections.abc import Awaitable, Callable, Collection

from sqlalchemy import Select, column, or_, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.classes import service as classes
from app.modules.games import service as games
from app.modules.games.service import Purpose, SessionGame
from app.modules.identity import service as identity
from app.modules.sessions import service as sessions

__all__ = [
    "EXCLUDED_SESSION_KINDS",
    "REPORTING_PURPOSES",
    "is_reporting_session",
    "register_control_test_sessions",
    "register_test_students",
    "reporting_game_ids",
    "reporting_games",
    "reporting_seat_holders",
    "reporting_student_ids",
    "reporting_students",
]

REPORTING_PURPOSES: frozenset[Purpose] = frozenset({Purpose.CLASS, Purpose.REPLAY, Purpose.MAKEUP})
"""The Game purposes reports count (AD-13): never `lecturer_test` or `simulation`."""
EXCLUDED_SESSION_KINDS = (sessions.CONTROL_TEST,)
"""The Class session kinds no report counts (Story 12.7, AD-27)."""

ControlTestSessions = Callable[[AsyncSession, Collection[uuid.UUID]], Awaitable[set[uuid.UUID]]]
"""`(session, class_session_ids)` → those of them that are Control test Class sessions."""
TestStudents = Callable[[AsyncSession, Collection[uuid.UUID]], Awaitable[set[uuid.UUID]]]
"""`(session, user_ids)` → those of them that are test students."""


async def _control_test_sessions(
    session: AsyncSession, ids: Collection[uuid.UUID]
) -> set[uuid.UUID]:
    """Those of `ids` whose `kind` is `control_test` (Story 12.7)."""
    return {
        each
        for each in ids
        if await sessions.kind_of(each, session=session) == sessions.CONTROL_TEST
    }


_control_tests: list[ControlTestSessions] = [_control_test_sessions]
_test_students: list[TestStudents] = [identity.test_students]


def register_control_test_sessions(read: ControlTestSessions) -> None:
    """Set the read that names Control test Class sessions (Story 12.7's `kind`)."""
    _control_tests[:] = [read]


def register_test_students(read: TestStudents) -> None:
    """Set the read that names test students (Story 12.8's `is_test_student`)."""
    _test_students[:] = [read]


async def is_reporting_session(session: AsyncSession, class_session_id: uuid.UUID) -> bool:
    """Whether reports count the Class session at all: never a Control test (AD-27)."""
    return class_session_id not in await _control_tests[0](session, [class_session_id])


async def reporting_students(session: AsyncSession, class_session_id: uuid.UUID) -> list[uuid.UUID]:
    """The Students reports count in the Class session, sorted by id: the Class's registered
    Students (`classes.registered_students`) less test students; none for a Control test Class
    session or an unknown one. In the caller's `session`."""
    class_id = await sessions.class_id_of(session, class_session_id)
    if class_id is None or not await is_reporting_session(session, class_session_id):
        return []
    registered = await classes.registered_students(class_id)
    excluded = await _test_students[0](session, registered)
    return sorted((user for user in registered if user not in excluded), key=str)


async def reporting_games(
    session: AsyncSession,
    class_session_id: uuid.UUID,
    purposes: Collection[Purpose] | None = None,
) -> list[SessionGame]:
    """The Games of the Class session that reports count, each with its purpose and `end_reason`:
    those of `REPORTING_PURPOSES` (narrowed to `purposes` when given); none for a Control test
    Class session. In the caller's `session`."""
    if not await is_reporting_session(session, class_session_id):
        return []
    wanted = REPORTING_PURPOSES if purposes is None else REPORTING_PURPOSES & set(purposes)
    return [g for g in await games.session_games(session, class_session_id) if g.purpose in wanted]


_games = table("games", column("id"), column("purpose"), column("class_session_id"))
_seats = table("seats", column("id"), column("game_id"))
_seat_occupancy = table("seat_occupancy", column("seat_id"), column("user_id"))
_users = table("users", column("id"), column("is_test_student"))
_class_sessions = table("class_sessions", column("id"), column("kind"))


def reporting_game_ids() -> Select:
    """The ids of the Games reports count, as a subquery over every Class session (Story 15.4):
    those of `REPORTING_PURPOSES`, never a Game of a Control test Class session."""
    excluded_sessions = select(_class_sessions.c.id).where(
        _class_sessions.c.kind.in_(EXCLUDED_SESSION_KINDS)
    )
    return select(_games.c.id).where(
        _games.c.purpose.in_(sorted(p.value for p in REPORTING_PURPOSES)),
        or_(
            _games.c.class_session_id.is_(None),
            _games.c.class_session_id.not_in(excluded_sessions),
        ),
    )


def reporting_student_ids() -> Select:
    """The ids of the Users reports count as Students, as a subquery: every User but a test
    student (Story 12.8, AD-13)."""
    return select(_users.c.id).where(_users.c.is_test_student.is_not(True))


def reporting_seat_holders() -> Select:
    """`(class_session_id, user_id)` of every reporting Student who holds or has held a Seat in a
    reporting Game of that Class session (Story 15.4). A Lecturer who only played a test Game is
    not among them."""
    return (
        select(_games.c.class_session_id, _seat_occupancy.c.user_id)
        .join(_seats, _seats.c.game_id == _games.c.id)
        .join(_seat_occupancy, _seat_occupancy.c.seat_id == _seats.c.id)
        .where(
            _games.c.id.in_(reporting_game_ids()),
            _games.c.class_session_id.is_not(None),
            _seat_occupancy.c.user_id.in_(reporting_student_ids()),
        )
    )
