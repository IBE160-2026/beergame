"""Authorization: who may do what (AD-12, FR-5, NFR-7, Story 3.3).

Every API route declares a policy as a FastAPI dependency: `Depends(authz.require(action))`, or
`Depends(authz.public)` for the short public list (login, logout, password reset, Invitation
acceptance, the lecturer-access request, health, webhooks). `tests/test_authz_rules.py` walks the
routes and fails on a route without a policy, and on a role comparison inside `app/modules/`:
modules ask `can(user, action, resource)`, they never compare roles themselves.

- `current_principal` reads the session cookie and loads the User and their roles from the
  database on every request, through the loader `identity` registers at app start
  (`register_principal_loader`). A role granted or revoked takes effect at the next request. No
  cookie is `NotAuthenticated`; a cookie that is expired or tampered, whose User is deleted or
  deactivated, or that is older than the User's session version (a deactivation or a password
  reset since, Story 3.10), is `SessionExpired`.
- A policy runs before the route handler, so a refusal is the same 403 `forbidden` whether or not
  the item exists: the answer never reveals what is there.
- The account roles are `admin` and `lecturer`. A Student is not an account role: Class
  membership makes them (Epic 4). `assistant` is a session role (Story 4.9): the principal holds
  it while the User is Assistant lecturer of at least one Class, read from `class_staff` on every
  request (`identity.service.register_session_roles`), never stored or granted. Class-scoped
  helpers are added here by the epic that creates the tables they join; until a Class-scoped
  grant exists no role reads Student answers or AI assessments, the Admin role included.
- Classes (Story 4.1, AD-12): `classes_visible_to(user)` is the scope every `classes` repository
  query on Class rows joins through: the ids of the Classes the User is staff of. A Class action
  (`classes.read`, `classes.manage`) also takes the resource, which carries the User's
  `staff_role` in that Class: `can(user, "classes.manage", resource)` holds only for a staff role
  the action allows. A Class outside the scope is never loaded, so it is refused the same as one
  that does not exist (FR-5).
- Students (Story 4.5): `classes_enrolled_by(user)` is the scope of a Student's own Classes, from
  the Roster entries linked to the User and not removed. `classes.read_enrolled` is open to every
  logged-in User; the scope decides what they see.
- Games (Story 6.1): `own_seat(user, game)` is the scope of a Student's own Class games, the
  Games in which they hold or have held a Seat. `games.read_own` is open to every logged-in User;
  the scope decides.
- Messages (Story 7.10): `messages_addressed_to(user)` is the scope of a Student's own Messages,
  those with a recipient row for the User in a Class the User is still a Student in, not archived.
- Events (Story 6.4): `class_sessions_staffed_by(user)` and `class_games_staffed_by(user)` give the
  `session:` and `game:` topics of a User's Class staff roles; with `own_seat` they decide what
  `GET /api/events` forwards.

This module imports no `app.modules` code.
"""

import uuid
from collections.abc import Awaitable, Callable, Collection
from typing import Any, Protocol

from fastapi import Request
from sqlalchemy import Select, column, select, table

from app.platform import auth

ADMIN = "admin"
LECTURER = "lecturer"
ASSISTANT = "assistant"


class Principal(Protocol):
    """The logged-in User as `authz` sees it: an id and the account roles."""

    id: uuid.UUID
    roles: Collection[str]


class NotAuthenticated(Exception):
    """No session: the request carried no session cookie (401 `not_authenticated`)."""


class SessionExpired(NotAuthenticated):
    """A session cookie was sent but holds no usable session: expired, tampered, or its User is
    gone or deactivated (401 `session_expired`). The web app then asks the User to log in again
    and returns them to the same page (Story 3.4); a first visit never sees that message."""


class Forbidden(Exception):
    """The User's roles do not allow the action (403 `forbidden`)."""


ANY_USER = "any_user"
"""A policy marker: every logged-in User, whatever roles they hold."""

POLICIES: dict[str, frozenset[str]] = {
    # The Admin-område (FR-1–FR-3, FR-69).
    "admin_area.view": frozenset({ADMIN}),
    "users.list": frozenset({ADMIN}),
    "users.manage": frozenset({ADMIN}),
    "institutions.manage": frozenset({ADMIN}),
    "audit.read": frozenset({ADMIN}),
    # The Lærerhjem and the Classes on it (Story 4.1). The Class actions are also held to the
    # User's staff role in the Class (`CLASS_STAFF_ROLES`). An Assistant lecturer reads the
    # Classes they are staff of and nothing else (Story 4.9).
    "lecturer_home.view": frozenset({LECTURER, ASSISTANT}),
    "classes.create": frozenset({LECTURER}),
    "classes.read": frozenset({LECTURER, ASSISTANT}),
    "classes.manage": frozenset({LECTURER}),
    # A Class's sessions (Story 5.1): its owners create and save them, its Assistant lecturers
    # read them. Held to the User's staff role in the Class (`CLASS_STAFF_ROLES`).
    "class_sessions.read": frozenset({LECTURER, ASSISTANT}),
    "class_sessions.manage": frozenset({LECTURER}),
    # The Oversikt of a Class session (Story 7.1, FR-39): its Class's staff, held to the User's
    # staff role in the Class like the actions above.
    "class_sessions.overview": frozenset({LECTURER, ASSISTANT}),
    # Spillinnsikt (Story 7.7, FR-62): one Game week by week, with the full chain, the demand
    # series and the number of Weeks, for the staff of its Class only.
    "games.insight": frozenset({LECTURER, ASSISTANT}),
    # A Message to a Student, a Class game or a whole Class session (Story 7.9, FR-40): the staff
    # of its Class, Lecturers and Assistant lecturers alike.
    "messages.send": frozenset({LECTURER, ASSISTANT}),
    # The Messages sent in a Class session (Story 7.10): its Class's staff, like the send.
    "messages.read_sent": frozenset({LECTURER, ASSISTANT}),
    # A Student's own Messages on Hjem (Story 7.10): any User, held to `messages_addressed_to`.
    "messages.read_own": frozenset({ANY_USER}),
    # The Class sessions of the Classes a User is a Student in, with their dates (Story 5.2): any
    # User, held to `classes_enrolled_by`.
    "class_sessions.read_enrolled": frozenset({ANY_USER}),
    # The Classes a User is a Student in (Story 4.5): any User, held to `classes_enrolled_by`.
    "classes.read_enrolled": frozenset({ANY_USER}),
    # A Student's own Class game (Story 6.1): any User, held to `own_seat`; any other game is
    # refused the same as one that does not exist (FR-5).
    "games.read_own": frozenset({ANY_USER}),
    # Story 6.5: a Student starts their own Class game; the service checks it is theirs.
    "games.start_own": frozenset({ANY_USER}),
    # Story 6.10: a Student plays their own Class game (opens a Guided Week; Orders from 6.12);
    # the service checks the Seat is theirs.
    "games.play_own": frozenset({ANY_USER}),
    # The Starting task in the Student's own Class game (Story 6.3): any User, held to
    # `own_seat` like the game itself.
    "starting_task.answer_own": frozenset({ANY_USER}),
    # The Student's own Debrief (Story 9.2): any User, held to `own_seat` through
    # `games.service.student_game`; the service refuses every other Debrief alike.
    "debriefs.own": frozenset({ANY_USER}),
    # A Student's Explanation (Story 9.3, FR-41, AD-12): the Class's owners and Assistant
    # lecturers (`CLASS_STAFF_ROLES`); never another Student, never an Admin without a staff role.
    "explanations.read": frozenset({LECTURER, ASSISTANT}),
    # A Student's Debrief summary (Story 9.8, FR-47, AD-12): the same readers as the Explanation.
    "debrief_summaries.read": frozenset({LECTURER, ASSISTANT}),
    # The Debrief quiz of a Class session with its answer keys and exclusions (Story 9.10, FR-46,
    # AD-12): its owners and Assistant lecturers read it; only its owners take questions out.
    "debrief_quiz.read": frozenset({LECTURER, ASSISTANT}),
    "debrief_quiz.exclude": frozenset({LECTURER}),
    # The «KI-vurdering» switch of a Class session (Story 12.1, FR-61, AD-12): its Class's staff
    # read it with the Class session (`class_sessions.read`); only its owners change it.
    "ai_assessment.change": frozenset({LECTURER}),
    # The question set selection of a Class session, «Spørsmål og vekter» (Story 11.1, FR-52,
    # AD-12): its Class's staff read it with the Class session (`class_sessions.read`); only its
    # owners change it.
    "question_set.change": frozenset({LECTURER}),
    # The Scoring guide of a Class session, «Sensorveiledning» (Story 11.2, FR-81, AD-12): its
    # Class's staff read it with the Class session (`class_sessions.read`); only its owners edit
    # it.
    "scoring_guide.change": frozenset({LECTURER}),
    # The own session.
    "session.read": frozenset({ANY_USER}),
    # The live event stream (Story 6.4, AD-8): any User; the scope decides which topics it sends.
    "events.read": frozenset({ANY_USER}),
    # FR-5: no account role grants these. Epic 4+ adds the Class-scoped grants.
    "student_answers.read": frozenset(),
    "ai_assessments.read": frozenset(),
}
"""Action → the account roles that may do it. Closed: an unknown action is a KeyError."""


OWNER = "owner"
"""The staff role of the Lecturer who created a Class (Story 4.1); co-owners share it (4.9)."""
ASSISTANT_STAFF = "assistant"
"""The staff role of an Assistant lecturer in one Class (Story 4.9)."""

CLASS_STAFF_ROLES: dict[str, frozenset[str]] = {
    "classes.read": frozenset({OWNER, ASSISTANT_STAFF}),
    "classes.manage": frozenset({OWNER}),
    "class_sessions.read": frozenset({OWNER, ASSISTANT_STAFF}),
    "class_sessions.manage": frozenset({OWNER}),
    "explanations.read": frozenset({OWNER, ASSISTANT_STAFF}),
    "debrief_summaries.read": frozenset({OWNER, ASSISTANT_STAFF}),
    "debrief_quiz.read": frozenset({OWNER, ASSISTANT_STAFF}),
    "debrief_quiz.exclude": frozenset({OWNER}),
    "ai_assessment.change": frozenset({OWNER}),
    "question_set.change": frozenset({OWNER}),
    "scoring_guide.change": frozenset({OWNER}),
    "class_sessions.overview": frozenset({OWNER, ASSISTANT_STAFF}),
    "games.insight": frozenset({OWNER, ASSISTANT_STAFF}),
    "messages.send": frozenset({OWNER, ASSISTANT_STAFF}),
    "messages.read_sent": frozenset({OWNER, ASSISTANT_STAFF}),
}
"""Class action → the staff roles in the Class that may do it. Later stories add theirs."""


class ClassResource(Protocol):
    """A Class as `can` sees it: the asking User's staff role in it."""

    staff_role: str


def can(user: Principal, action: str, resource: Any = None) -> bool:
    """Whether `user` may do `action`. A Class action on a `resource` also needs a staff role in
    that Class the action allows; with no resource only the account roles are checked (the
    route's policy, before any Class is loaded)."""
    allowed = POLICIES[action]
    if not (ANY_USER in allowed or not allowed.isdisjoint(user.roles)):
        return False
    if resource is not None and action in CLASS_STAFF_ROLES:
        return getattr(resource, "staff_role", None) in CLASS_STAFF_ROLES[action]
    return True


_class_staff = table("class_staff", column("class_id"), column("user_id"), column("role"))
"""`classes.class_staff` by name only: `platform` imports no module code."""


def classes_visible_to(user: Principal | uuid.UUID) -> Select:
    """The ids of the Classes `user` (a principal or a User id) is staff of, as a subquery for
    `WHERE classes.id IN (...)`. Every `classes` repository query on Class rows joins through it
    (AD-12)."""
    user_id = user if isinstance(user, uuid.UUID) else user.id
    return select(_class_staff.c.class_id).where(_class_staff.c.user_id == user_id)


_roster_entries = table(
    "roster_entries", column("class_id"), column("user_id"), column("removed_at")
)
"""`identity.roster_entries` by name only, for the Student scope."""


def classes_enrolled_by(user: Principal | uuid.UUID) -> Select:
    """The ids of the Classes `user` is a Student in (Story 4.5, FR-5, FR-7): a Roster entry
    linked to the User and not removed. A subquery for `WHERE classes.id IN (...)`; every query on
    a Student's Classes joins through it, so another Class reads as one that does not exist."""
    user_id = user if isinstance(user, uuid.UUID) else user.id
    return select(_roster_entries.c.class_id).where(
        _roster_entries.c.user_id == user_id, _roster_entries.c.removed_at.is_(None)
    )


_seats = table("seats", column("id"), column("game_id"))
_seat_occupancy = table("seat_occupancy", column("id"), column("seat_id"), column("user_id"))
"""`games.seats` and `games.seat_occupancy` by name only, for the own-Seat scope."""


def own_seat(user: Principal | uuid.UUID, game: uuid.UUID | None = None) -> Select:
    """The ids of the Games in which `user` holds or has held a Seat (Story 6.1, AD-12, FR-5):
    a Seat with an occupancy row naming the User. A subquery for `WHERE games.id IN (...)`; every
    query on a Student's own game joins through it, so another game reads as one that does not
    exist. `game` narrows it to one Game."""
    user_id = user if isinstance(user, uuid.UUID) else user.id
    query = (
        select(_seats.c.game_id)
        .join(_seat_occupancy, _seat_occupancy.c.seat_id == _seats.c.id)
        .where(_seat_occupancy.c.user_id == user_id)
    )
    if game is not None:
        query = query.where(_seats.c.game_id == game)
    return query


def seat_held_by(user: Principal | uuid.UUID) -> Select:
    """The ids of the Games in which `user` holds a Seat now: the Seat's latest occupancy row (by
    UUIDv7 id) names the User. Narrower than `own_seat`, which also keeps Games the User left
    (a move, Student choice, a removal): the `game:<id>` topics a Student's event stream forwards
    (follow-up review of Story 6.4, FR-5)."""
    user_id = user if isinstance(user, uuid.UUID) else user.id
    later = _seat_occupancy.alias("later")
    return (
        select(_seats.c.game_id)
        .join(_seat_occupancy, _seat_occupancy.c.seat_id == _seats.c.id)
        .where(
            _seat_occupancy.c.user_id == user_id,
            ~select(later.c.id)
            .where(later.c.seat_id == _seat_occupancy.c.seat_id, later.c.id > _seat_occupancy.c.id)
            .exists(),
        )
    )


_class_sessions = table("class_sessions", column("id"), column("class_id"))
_games = table("games", column("id"), column("class_session_id"))
"""`sessions.class_sessions` and `games.games` by name only, for the staff event scope."""


def class_sessions_staffed_by(user: Principal | uuid.UUID) -> Select:
    """The ids of the Class sessions of the Classes `user` is staff of (Story 6.4, AD-8): the
    `session:<id>` topics their event stream forwards. A Student is never staff, so never gets
    one."""
    return select(_class_sessions.c.id).where(
        _class_sessions.c.class_id.in_(classes_visible_to(user))
    )


def class_games_staffed_by(user: Principal | uuid.UUID) -> Select:
    """The ids of the Class games of those Class sessions (Story 6.4, AD-8): with `own_seat`, the
    `game:<id>` topics a User's event stream forwards."""
    return select(_games.c.id).where(_games.c.class_session_id.in_(class_sessions_staffed_by(user)))


_debrief_sessions = table("debrief_sessions", column("id"), column("game_id"))
"""`debrief.debrief_sessions` by name only, for the Debrief event scope."""


def debriefs_of(user: Principal | uuid.UUID) -> Select:
    """The ids of the Debrief sessions of the Games in which `user` holds or has held a Seat
    (Story 9.11, AD-8, AD-21): the `debrief:<id>` topics their event stream forwards. An event
    names only the id; every read behind it is the Debrief's own, held to the Student's game."""
    return select(_debrief_sessions.c.id).where(_debrief_sessions.c.game_id.in_(own_seat(user)))


_messages = table("messages", column("id"), column("class_session_id"))
_classes = table("classes", column("id"), column("archived_at"))
_message_recipients = table("message_recipients", column("message_id"), column("user_id"))
"""`messaging.messages` and `messaging.message_recipients` by name only, for the Message scope."""


def messages_addressed_to(user: Principal | uuid.UUID) -> Select:
    """The ids of the Messages written to `user` (Story 7.10, AD-12, FR-5): a recipient row names
    the User, and the Message's Class session is of a Class the User is a Student in now
    (`classes_enrolled_by`) and that is not archived (Story 4.10: nothing in an archived Class is
    open to a Student). A subquery for `WHERE messages.id IN (...)`; every read of a
    Student's Messages joins through it, so a Message to anyone else reads as none at all."""
    user_id = user if isinstance(user, uuid.UUID) else user.id
    return (
        select(_message_recipients.c.message_id)
        .join(_messages, _messages.c.id == _message_recipients.c.message_id)
        .join(_class_sessions, _class_sessions.c.id == _messages.c.class_session_id)
        .join(_classes, _classes.c.id == _class_sessions.c.class_id)
        .where(
            _message_recipients.c.user_id == user_id,
            _class_sessions.c.class_id.in_(classes_enrolled_by(user_id)),
            _classes.c.archived_at.is_(None),
        )
    )


PrincipalLoader = Callable[[uuid.UUID, int], Awaitable[Principal | None]]
"""`(user_id, session_version)` → the active User, or None when the User is gone, deactivated, or
the session is older than the User's session version."""
_loader: PrincipalLoader | None = None


def register_principal_loader(loader: PrincipalLoader) -> None:
    """Called once by `create_app()` with `identity.service.load_user`."""
    global _loader
    _loader = loader


async def load_principal(user_id: uuid.UUID, session_version: int) -> Principal | None:
    """The active User through the registered loader, or None: what a long-lived request (the
    event stream, Story 6.4) asks again when the User may have been deactivated meanwhile."""
    if _loader is None:  # pragma: no cover - create_app() always registers it
        raise RuntimeError("no principal loader registered")
    return await _loader(user_id, session_version)


async def current_principal(request: Request) -> Principal:
    """FastAPI dependency: the active User of the session cookie, read from the database."""
    if _loader is None:  # pragma: no cover - create_app() always registers it
        raise RuntimeError("no principal loader registered")
    token = request.cookies.get(auth.COOKIE_NAME)
    if not token:
        raise NotAuthenticated
    session = auth.read_session(token)
    user = await _loader(session.user_id, session.version) if session else None
    if user is None:
        raise SessionExpired
    return user


class Policy:
    """`require(action)`: a dependency that returns the principal, or raises `Forbidden`."""

    def __init__(self, action: str) -> None:
        POLICIES[action]  # a typo fails at import, not at the first request
        self.action = action

    async def __call__(self, request: Request) -> Principal:
        user = await current_principal(request)
        if not can(user, self.action):
            raise Forbidden
        return user

    def __repr__(self) -> str:
        return f"require({self.action!r})"


def require(action: str) -> Policy:
    return Policy(action)


async def public() -> None:
    """The policy of a public route. Only the routes on the public list may use it."""
