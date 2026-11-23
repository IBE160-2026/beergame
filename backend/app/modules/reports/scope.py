"""The data scope of every report, statistic, export, funnel and Completion query (AD-13).

`reporting_games()`, `reporting_students()` and `reporting_seat_holders()` are subqueries for
`WHERE … IN (…)`. They leave out Lecturer test Games and simulation Games (`games.purpose`), and
are the one place that narrows the scope further:

- the Games of a Class session of kind `control_test` (Story 12.7, AD-27) are no reporting Games,
  so its Students are no reporting seat holders either;
- Users marked `is_test_student` (Story 12.8) are no reporting Students: the same mark
  `identity.service.test_students` reads.

Tables are named by name only, as in `platform/authz`, so this module imports no feature module.
"""

from sqlalchemy import Select, column, or_, select, table

EXCLUDED_PURPOSES = ("lecturer_test", "simulation")
"""The Game purposes no report counts (AD-13)."""
EXCLUDED_SESSION_KINDS = ("control_test",)
"""The Class session kinds no report counts (Story 12.7, AD-27; `sessions.service.CONTROL_TEST`)."""

_games = table("games", column("id"), column("purpose"), column("class_session_id"))
_seats = table("seats", column("id"), column("game_id"))
_seat_occupancy = table("seat_occupancy", column("seat_id"), column("user_id"))
_users = table("users", column("id"), column("is_test_student"))
_class_sessions = table("class_sessions", column("id"), column("kind"))


def reporting_games() -> Select:
    """The ids of the Games reports count: every Game but Lecturer test Games, simulations and
    the Games of a Control test."""
    excluded_sessions = select(_class_sessions.c.id).where(
        _class_sessions.c.kind.in_(EXCLUDED_SESSION_KINDS)
    )
    return select(_games.c.id).where(
        _games.c.purpose.not_in(EXCLUDED_PURPOSES),
        or_(
            _games.c.class_session_id.is_(None),
            _games.c.class_session_id.not_in(excluded_sessions),
        ),
    )


def reporting_students() -> Select:
    """The ids of the Users reports count as Students: every User but a test student (Story
    12.8, AD-13)."""
    return select(_users.c.id).where(_users.c.is_test_student.is_not(True))


def reporting_seat_holders() -> Select:
    """`(class_session_id, user_id)` of every reporting Student who holds or has held a Seat in a
    reporting Game of that Class session: the Students of a Class session as reports count them.
    A Lecturer who only played a test Game is not among them."""
    return (
        select(_games.c.class_session_id, _seat_occupancy.c.user_id)
        .join(_seats, _seats.c.game_id == _games.c.id)
        .join(_seat_occupancy, _seat_occupancy.c.seat_id == _seats.c.id)
        .where(
            _games.c.id.in_(reporting_games()),
            _games.c.class_session_id.is_not(None),
            _seat_occupancy.c.user_id.in_(reporting_students()),
        )
    )
