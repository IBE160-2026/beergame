"""The data scope of every report, statistic, export, funnel and Completion query (AD-13).

`reporting_games()`, `reporting_students()` and `reporting_seat_holders()` are subqueries for
`WHERE … IN (…)`. They leave out Lecturer test Games and simulation Games (`games.purpose`), and
are the one place that later stories narrow further:

- Story 12.7 adds Class sessions of kind `control_test` (AD-27) to `reporting_games()`;
- Story 12.8 adds Users marked `is_test_student` to `reporting_students()`.

Neither column exists on this branch yet, so today every User is a reporting Student. Tables are
named by name only, as in `platform/authz`, so this module imports no feature module.
"""

from sqlalchemy import Select, column, select, table

EXCLUDED_PURPOSES = ("lecturer_test", "simulation")
"""The Game purposes no report counts (AD-13)."""

_games = table("games", column("id"), column("purpose"), column("class_session_id"))
_seats = table("seats", column("id"), column("game_id"))
_seat_occupancy = table("seat_occupancy", column("seat_id"), column("user_id"))
_users = table("users", column("id"))


def reporting_games() -> Select:
    """The ids of the Games reports count: every Game but Lecturer test Games and simulations."""
    return select(_games.c.id).where(_games.c.purpose.not_in(EXCLUDED_PURPOSES))


def reporting_students() -> Select:
    """The ids of the Users reports count as Students: every User, until Story 12.8 marks test
    Students."""
    return select(_users.c.id)


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
