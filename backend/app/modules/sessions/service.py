"""Class sessions (Stories 5.1 to 5.5, FR-11, FR-12, FR-13, FR-15, FR-16, FR-18, FR-78, AD-4,
AD-6, AD-17). Other modules import only this file.

A Lecturer who owns or co-owns a Class creates a Class session from the Klasse page. It is filled
in with the engine's Classic `GameSettings` (this module holds no second copy of a value), a
demand seed the server draws through `engine.demand.new_seed`, AI mode LLM players, Group
debrief, an Inactivity limit of 24 hours and not obligatory. In the same transaction it gets the
active default model config (`ai.config.active_default`) and its budget row
(`ai.budget.set_budget`). With no active default it is created with Rule-based players, no config
and no budget, and the answer says why (`llm_unavailable`).

The four dates (Story 5.2) are saved with «Lagre Klasseøkt»: Start date < Play deadline < Debrief
deadline < Test deadline among those set, a changed date never in the past, a date that has passed
never moved (`deadline_passed`), and none cleared once the session is locked. `is_locked` is the
one lock predicate; `effective_debrief_deadline` and `effective_test_deadline` are the only way
another module reads a Student's deadline.

The Game settings (Story 5.3), the Demand pattern and its seed (Story 5.4) are saved with «Lagre
Klasseøkt» too, and a draft can be judged without saving (`check_settings`). Both lay the draft
over the stored settings and judge it with the engine's `validate` and `warnings` only (AD-1):
this module and the web app hold no rule. `demand_series_of` gives the staff the series the
engine materialises from the stored pattern and seed.

AI mode, Effort level and Debrief mode (Story 5.5) are saved with «Lagre Klasseøkt» too. The
Effort levels, their default and their effect lines are the model config's
(`ai.config.offered_effort_levels`), and the AI player descriptions are
`players.service.describe`'s: this module names no level and writes no description. With
Rule-based players no Effort level is in force (NULL).

Lab hours (Story 5.6) are added, changed and removed on their own, at any time, the Start-date
lock aside: each change tells every registered Student through `platform/notify` with a digest
kind (`LAB_HOUR_KINDS`), whose mail reads the Lab hour at send time
(`lab_hour_mail_context`). A removed Lab hour is kept, cancelled, so that mail can still name it.
`current_lab_hour` is the only way another module learns whether a Lab hour is on.

The obligatory mark, its required share of Weeks and the Inactivity limit (Story 5.7) are saved
with «Lagre Klasseøkt» and lock at the Start date. Switching the mark on tells every registered
Student through a digest notice (`OBLIGATORY_NOTICE`, mail read at send time by
`obligatory_mail_context`). `required_share` is the one source of the share for Story 8.9 and
Epic 13; nothing here computes Completion with it.

The allocation (Story 5.8, FR-20) is a stored draft, one per Class session: opening the
«Fordeling» block draws one from the registered Students with a fresh seed through the pure
`allocation.allocate` when none is stored, and «Kjør fordeling på nytt» replaces it under a new id.
The preview always shows the stored draft, with names resolved at read time
(`classes.service.student_names`); no Game, Seat or notice exists until it is confirmed.

«Bekreft fordeling» (Story 5.9) commits the draft the Lecturer is looking at, by id and revision,
through `games.commands` in one transaction: one Class game per group with no settings (its
snapshot comes at the lock) and one `student` Seat per Student, then a digest notice per Student
(`ALLOCATION_NOTICE`, mail read at send time by `allocation_mail_context`). A confirmed allocation
is never drawn again. The Lærerhjem names the unlocked sessions whose allocation is not confirmed.
Until the lock a Student can be moved to a free Seat or two swapped (Story 5.10), in the draft by
its revision and, once confirmed, in the Class games too through `games.commands.move_seat`.

At the Start date the sweep's `sessions.lock` (Story 5.11) locks the Class session through
`lock`, which Epic 8 also calls to start early: one transaction sets `locked_at` and stores the
frozen snapshot of `build_snapshot`, with the pins of every provider registered through
`register_pin_provider`. With LLM players and no usable provider key the lock is refused, the
owners and the Admins are told once, and the next sweep tries again. With no confirmed allocation
the lock allocates first, and after it `open_games` gives every Class game the snapshot and its AI
players through `games.commands.set_snapshot` (Story 5.12).

24 hours before each Play, Debrief and Test deadline the sweep's `sessions.send_deadline_reminder`
(Story 5.14) records a `deadline_reminders` row for that deadline time and enqueues a digest
notice (`DEADLINE_REMINDER_NOTICE`) per Student of `reminder_recipients`; the mail is read at send
time by `deadline_reminder_mail_context`. A moved deadline has a new time and a new reminder.

Every mutation passes one guard, `_writable`, which asks `classes.service.is_writable` inside the
mutation's transaction and raises `classes.service.ClassArchived` (409 `class_archived`) for an
archived Class. Who may do what is `platform/authz`'s: `class_sessions.read`,
`class_sessions.manage` (held to the User's staff role in the Class) and
`class_sessions.read_enrolled` (held to `authz.classes_enrolled_by`).
"""

import secrets
import uuid
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import structlog
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import budget, config
from app.engine import RULES_VERSION, GameSettings
from app.engine.demand import DemandFixed, DemandRandom, DemandStep, DemandStepNoise, new_seed
from app.engine.settings import (
    CAPACITY_RANGE,
    DEMAND_RANGES,
    RANGES,
    ROLES,
    Range,
    Role,
    demand_series,
    validate,
    warnings,
)
from app.modules.classes import service as classes
from app.modules.content import service as content
from app.modules.games import commands as games_commands
from app.modules.games import service as games_service
from app.modules.identity import service as identity
from app.modules.players import service as players
from app.modules.progress import service as progress
from app.modules.sessions import allocation, repo
from app.modules.sessions.models import (
    DATE_NAMES,
    DEADLINE_NAMES,
    MAX_REQUIRED_SHARE_PERCENT,
    MIN_INACTIVITY_LIMIT_HOURS,
    MIN_REQUIRED_SHARE_PERCENT,
    PLACE_MAX_LENGTH,
)
from app.modules.sessions.schemas import (
    AiDescriptionsOut,
    AiMode,
    AllocationConfirmIn,
    AllocationDraftOut,
    AllocationGameOut,
    AllocationMethod,
    AllocationMoveIn,
    AllocationOut,
    AllocationSeatOut,
    AllocationStudentOut,
    ClassSessionListItem,
    ClassSessionListOut,
    ClassSessionOut,
    CopiedFromOut,
    CopySourceListOut,
    CopySourceOut,
    DateKind,
    DateName,
    DatesIn,
    DeadlineName,
    DebriefMode,
    DebriefRelease,
    DebriefState,
    DemandSeriesOut,
    EnrolledLabHourOut,
    EnrolledSessionListOut,
    EnrolledSessionOut,
    GameResultOut,
    GameRulesOut,
    LabHourIn,
    LabHourOut,
    LecturerOverviewOut,
    LlmUnavailable,
    NextDate,
    NextDeadline,
    OfferedEffortLevelOut,
    PlayOut,
    PlayTurnOut,
    ProposalPersonOut,
    ReplacedLevelOut,
    RoleCapacityOut,
    SeatChoiceGameOut,
    SeatChoiceIn,
    SeatChoiceOut,
    SeatChoiceSeatOut,
    SeatRef,
    SessionRef,
    SettingProblem,
    SettingsCheckOut,
    SettingWarning,
    StepOut,
    StudentGameOut,
    TableSeatOut,
    TableStatusOut,
    TestGameRefOut,
    TimeProposalOut,
    WaitingClass,
    WaitingReason,
)
from app.platform import auth, authz, events, notify
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

log = structlog.get_logger(__name__)

DEFAULT_DEBRIEF_MODE = DebriefMode.group
DEFAULT_INACTIVITY_LIMIT_HOURS = 24
DEFAULT_OBLIGATORY = False
NO_DEFAULT_MODEL: LlmUnavailable = "no_default_model"

LAB_HOUR_ADDED = "lab_hour_added"
LAB_HOUR_CHANGED = "lab_hour_changed"
LAB_HOUR_CANCELLED = "lab_hour_cancelled"
LAB_HOUR_KINDS = (LAB_HOUR_ADDED, LAB_HOUR_CHANGED, LAB_HOUR_CANCELLED)
"""The notice kinds of Lab hours, all `digest` in `messaging.delivery` (Story 5.6, AD-9)."""

OBLIGATORY_NOTICE = "class_session_obligatory"
"""The notice kind sent when a Class session is marked obligatory, `digest` (Story 5.7, AD-9)."""

MAX_LAB_HOUR = timedelta(hours=12)
"""The longest Lab hour: hours in a room, so `current_lab_hour` stays meaningful."""

OSLO = ZoneInfo("Europe/Oslo")

DATE_KINDS: dict[str, DateKind] = {
    "start_at": "start",
    "play_deadline": "play",
    "debrief_deadline": "debrief",
    "test_deadline": "test",
}


class LlmUnavailableError(Exception):
    """LLM players were chosen while no model config is the default (`llm_unavailable`)."""


class _FieldsError(Exception):
    code = ""

    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__(fields)
        self.fields = fields


class SessionLocked(_FieldsError):
    """A setting was changed on a locked Class session (409 `session_locked`)."""

    code = "session_locked"


class AllocationChanged(_FieldsError):
    """The draft confirmed is not the Class session's current one (409 `allocation_changed`):
    `{"draft": "changed"}` when another draw or edit replaced it, `{"draft":
    "students_removed"}` when this confirm took out Students no longer on the Roster."""

    code = "allocation_changed"


class AllocationConfirmed(_FieldsError):
    """The allocation is confirmed, so it is never drawn again (409 `allocation_confirmed`)."""

    code = "allocation_confirmed"


class InvalidMove(_FieldsError):
    """A move or swap that the draft cannot take (422 `invalid_move`, Story 5.10): `{"to":
    "same"}`, `{"from"|"to": "unknown"}` (no such game in the draft), `{"from": "empty"}` (no
    Student there) or `{"from": "last_student"}` (the game would be left without a Student)."""

    code = "invalid_move"


class SeatCommandRefused(_FieldsError):
    """`games.commands.move_seat` refused a confirmed allocation's move (Story 5.10); its code
    and status are the command's, and nothing is committed."""

    def __init__(self, code: str, status: int) -> None:
        super().__init__({"allocation": code})
        self.code = code
        self.status = status


class DeadlinePassed(_FieldsError):
    """A date that has passed was moved (409 `deadline_passed`); `fields` names each one."""

    code = "deadline_passed"


class InvalidEffortLevel(_FieldsError):
    """The Effort level is not one the model config offers here (422 `invalid_effort_level`,
    `{"effort_level": "not_offered"}`)."""

    code = "invalid_effort_level"


class InvalidDates(_FieldsError):
    """The dates break a rule (422 `invalid_dates`): `fields` maps each date in question to
    `past`, `order` (not after an earlier date), `before` (not before a later date that did not
    change) or `required`."""

    code = "invalid_dates"


class InvalidSessionValues(_FieldsError):
    """The obligatory share or the Inactivity limit breaks its rule (422
    `invalid_session_values`): `required_share_percent` `out_of_range` (outside 1 to 100),
    `inactivity_limit_hours` `below_minimum` (under 20)."""

    code = "invalid_session_values"


class InvalidLabHour(_FieldsError):
    """The Lab hour breaks a rule (422 `invalid_lab_hour`): `place` `required` or `too_long`;
    `ends_at` `not_after_start`, `too_long` (more than `MAX_LAB_HOUR`) or `past`."""

    code = "invalid_lab_hour"


class LabHourEnded(Exception):
    """The Lab hour has ended and no longer changes or goes (409 `lab_hour_ended`)."""

    code = "lab_hour_ended"


class SeatTaken(_FieldsError):
    """Another occupant holds the Seat a Student asked for (409 `seat_taken`, Story 5.17)."""

    code = "seat_taken"


class InvalidSeat(_FieldsError):
    """The request names no Seat of the Class session's games (422 `invalid_seat`)."""

    code = "invalid_seat"


class FeatureDisabled(_FieldsError):
    """A cut-list setting was sent while its flag is off (422 `feature_disabled`, AD-17): a
    non-empty `capacity` while `FEATURE_CAPACITY` is off (Story 5.15), or a view of
    `info_visibility` switched on while `FEATURE_INFO_VISIBILITY` is off (Story 5.16), or Student
    choice while `FEATURE_STUDENT_CHOICE` is off (Story 5.17), or a copy while `FEATURE_RERUN`
    is off (Story 5.18)."""

    code = "feature_disabled"


class InvalidSettings(Exception):
    """The Game settings break the engine's rules (422 `invalid_settings`): one problem per
    setting, with the range that applies."""

    code = "invalid_settings"

    def __init__(self, problems: dict[str, SettingProblem]) -> None:
        super().__init__(sorted(problems))
        self.problems = problems


def classic_settings() -> GameSettings:
    """The engine's Classic preset with a fresh seed drawn by the server (FR-13)."""
    return GameSettings(demand_seed=new_seed(secrets.token_bytes(16)))


def is_classic(settings: GameSettings) -> bool:
    """Whether `settings` is the Classic preset, whatever its demand seed."""
    return settings.model_copy(update={"demand_seed": None}) == GameSettings()


ClassSessionLike = ClassSessionOut | Mapping[str, Any]
"""A Class session as `ClassSessionOut` or as its row."""


def _bound(value: object) -> str | None:
    return None if value is None else str(value)


def range_of(field: str) -> Range | None:
    """The engine's range of a setting the Klasseøkt edits: `RANGES` for the Game settings,
    `DEMAND_RANGES` for the seed and the Demand pattern's fields (`demand.start`)."""
    if field in RANGES:
        return RANGES[field]
    if field == "demand_seed":
        return DEMAND_RANGES["demand_seed"]
    if field.startswith("capacity."):
        return CAPACITY_RANGE
    if field.startswith("demand."):
        return DEMAND_RANGES.get(field.removeprefix("demand."))
    return None


def _problem(
    code: str, field: str, minimum: object = None, maximum: object = None, *, ranged: bool = False
) -> SettingProblem:
    """One refused setting. `ranged` takes the bounds from the engine's ranges, for a value the
    engine never saw (wrong type or below zero); the engine's own errors bring theirs, or none."""
    allowed = range_of(field)
    if ranged and allowed is not None:
        minimum, maximum = allowed.minimum, allowed.maximum
    return SettingProblem(
        code=code,
        minimum=_bound(minimum),
        maximum=_bound(maximum),
        decimal_places=allowed.decimal_places if allowed is not None else None,
    )


DEMAND_FIELDS = frozenset(
    name
    for model in (DemandFixed, DemandStep, DemandRandom, DemandStepNoise)
    for name in model.model_fields
    if name != "kind"
)
"""The fields of the engine's Demand patterns, reported as `demand.<name>`."""


def _parse_problem(error: Mapping[str, Any], data: Mapping[str, Any], stored: GameSettings):
    """The setting and problem of one pydantic error on a draft. Inside the Demand pattern the
    field is `demand.<name>` with its range (the change Week: 1 to the draft's Weeks); a pattern
    with no known `kind`, an unknown key or not an object is `demand` `invalid`."""
    loc = error["loc"]
    field = str(loc[0]) if loc else "game_settings"
    out_of_range = error["type"] in ("greater_than_equal", "greater_than")
    if field == "demand":
        name = str(loc[2]) if len(loc) > 2 else ""
        if name not in DEMAND_FIELDS or error["type"] == "extra_forbidden":
            return "demand", _problem("invalid", "demand")
        weeks = data.get("weeks")
        allowed = RANGES["weeks"]
        if not (type(weeks) is int and allowed.minimum <= weeks <= allowed.maximum):
            weeks = stored.weeks
        if name == "values" and error["type"] == "too_short":
            # An empty series: one value per Week, as the engine says of any other length.
            return "demand.values", _problem("fixed_series_length", "demand.values", weeks, weeks)
        code = "out_of_range" if out_of_range else "not_a_number"
        if name == "change_week":
            last = weeks
            return "demand.change_week", _problem(code, "demand.change_week", 1, last)
        return f"demand.{name}", _problem(code, f"demand.{name}", ranged=True)
    if field == "capacity":
        # One Role's value that is not a whole number: `capacity.<role>` with its range. An unknown
        # Role, a Role outside the chain or a map that is not one: `capacity` `invalid`.
        if len(loc) == 2 and str(loc[1]) in CAPACITY_ROLES:
            return f"capacity.{loc[1]}", _problem("not_a_number", f"capacity.{loc[1]}", ranged=True)
        return "capacity", _problem("invalid", "capacity")
    if out_of_range:
        code = "out_of_range"
    else:
        code = "not_a_number" if range_of(field) is not None else "invalid"
    return field, _problem(code, field, ranged=True)


CAPACITY_ROLES = frozenset(role.value for role in Role)
"""The keys a capacity map may hold, as the api names them (`capacity.retailer`)."""

EDITABLE_SETTINGS = frozenset({*RANGES, "demand", "demand_seed", "capacity", "info_visibility"})
"""The Game settings a Lecturer changes through the Klasseøkt: those the engine gives a range
(Story 5.3), the Demand pattern with its seed (Story 5.4), the capacity (Story 5.15) and
Information visibility (Story 5.16), the last two only while their flag is on."""


def capacity_enabled() -> bool:
    """`FEATURE_CAPACITY` (AD-17): whether the Klasseøkt offers a shipping capacity (Story 5.15)."""
    return get_settings().feature_capacity


def info_visibility_enabled() -> bool:
    """`FEATURE_INFO_VISIBILITY` (AD-17): whether the Klasseøkt offers Information visibility
    (Story 5.16)."""
    return get_settings().feature_info_visibility


VIEWS = ("upstream", "downstream")
"""The views of `info_visibility`, as the api names them; a view left out is off."""


def _shows_a_new_neighbour(value: object, stored: Mapping[str, Any]) -> bool:
    """Whether a draft's `info_visibility` switches on a view that is off as stored; switching a
    view off never counts. A value that is not a map of views with boolean values is left to the
    engine, which refuses it as `invalid` whatever the flag."""
    if not isinstance(value, Mapping) or not set(value) <= set(VIEWS):
        return False
    if any(type(view) is not bool for view in value.values()):
        return False
    return any(value.get(side) is True and stored.get(side) is not True for side in VIEWS)


def _sets_capacity(value: object) -> bool:
    """Whether a draft's `capacity` caps anything: None and an empty map cap no Seat."""
    return value is not None and value != {}


def judge_settings(
    stored: GameSettings, draft: Mapping[str, Any]
) -> tuple[GameSettings | None, dict[str, SettingProblem], list[SettingWarning]]:
    """`draft` laid over `stored` and judged by the engine alone (FR-12, AD-1): the settings (None
    when they do not even parse), the errors by setting, and the warnings on settings without an
    error. A value of the wrong type is `not_a_number` and a negative one `out_of_range`, both
    with the setting's range, as the engine's own range errors. The other settings of a draft
    that does not parse are still judged, with the unreadable ones at their stored values, so
    one mistyped field hides no error or warning elsewhere. A key outside `EDITABLE_SETTINGS`
    (the chain) is `not_editable` and never laid over. While `FEATURE_CAPACITY` is off a draft
    that caps a Seat other than as stored is `capacity` `feature_disabled` (Story 5.15); a
    capacity stored before the flag went off is kept (sent back unchanged or left out) and judged
    as stored, so it never blocks another setting. None or `{}` clears it. Information visibility
    follows the same rule while `FEATURE_INFO_VISIBILITY` is off (Story 5.16): a draft that
    switches on a view that is off as stored is `info_visibility` `feature_disabled`; switching a
    view off is always allowed."""
    base = stored.model_dump(mode="json")
    problems: dict[str, SettingProblem] = {
        key: _problem("not_editable", key) for key in draft if key not in EDITABLE_SETTINGS
    }
    flag = capacity_enabled()
    stored_capacity = base.get("capacity")
    sent = draft.get("capacity")
    if not flag and _sets_capacity(sent) and sent != stored_capacity:
        problems["capacity"] = _problem("feature_disabled", "capacity")
    views_flag = info_visibility_enabled()
    views = draft.get("info_visibility")
    if not views_flag and _shows_a_new_neighbour(views, base["info_visibility"]):
        problems["info_visibility"] = _problem("feature_disabled", "info_visibility")
    data = {**base, **{key: value for key, value in draft.items() if key not in problems}}
    # Top-level settings that do not parse: judged at their stored values, their rules unsaid.
    unreadable: set[str] = set()
    try:
        settings: GameSettings | None = GameSettings.model_validate(data)
    except ValidationError as exc:
        for error in exc.errors():
            if error["loc"]:
                unreadable.add(str(error["loc"][0]))
            field, found = _parse_problem(error, data, stored)
            problems.setdefault(field, found)
        settings = None
        rest = {key: value for key, value in data.items() if key not in unreadable}
        try:
            judged = GameSettings.model_validate({**base, **rest})
        except ValidationError:
            return None, problems, []
    else:
        judged = settings
    enabled = flag or judged.capacity == stored.capacity
    # With the flag off, views stored earlier may stay or go off; only a new one is refused.
    views_enabled = views_flag or not _shows_a_new_neighbour(
        judged.info_visibility.model_dump(), stored.info_visibility.model_dump()
    )
    for found in validate(judged, capacity_enabled=enabled, info_visibility_enabled=views_enabled):
        if found.field not in problems and found.field.split(".")[0] not in unreadable:
            problems[found.field] = _problem(found.code, found.field, found.minimum, found.maximum)
    risky = [
        SettingWarning(code=w.code, field=w.field, values=w.values)
        for w in warnings(judged)
        if w.field not in problems
    ]
    return settings, problems, risky


def _value(class_session: ClassSessionLike, name: str) -> Any:
    if isinstance(class_session, ClassSessionOut):
        return getattr(class_session, name)
    return class_session[name]


def is_locked(class_session: ClassSessionLike, *, now: datetime | None = None) -> bool:
    """The one predicate of the Start-date lock points (FR-18): true once the session is locked
    (`locked_at`, Story 5.11, also an early lock) or its Start date has passed. Settings then
    answer `session_locked`; deadlines that have not passed still move."""
    locked_at = (
        class_session.locked_at
        if isinstance(class_session, ClassSessionOut)
        else class_session.get("locked_at")
    )
    if locked_at is not None:
        return True
    start = _value(class_session, "start_at")
    return start is not None and start <= (now or auth.utcnow())


def required_share(class_session: ClassSessionLike) -> int:
    """The share of Weeks the Class session requires, a whole percent from 1 to 100 (Story 5.7,
    FR-17): the one source Story 8.9 and Epic 13 read. It is stored whether or not the session is
    obligatory; whether a requirement applies is the obligatory mark's to say."""
    return _value(class_session, "required_share_percent")


def effective_debrief_deadline(
    user: authz.Principal | uuid.UUID, class_session: ClassSessionLike
) -> datetime | None:
    """The Student's Debrief deadline, the only way another module reads it. For now the Class
    session's own; Epic 11 adds a per-Student extension here without changing callers."""
    return _value(class_session, "debrief_deadline")


def effective_test_deadline(
    user: authz.Principal | uuid.UUID, class_session: ClassSessionLike
) -> datetime | None:
    """The Student's Test deadline, the only way another module reads it. For now the Class
    session's own; Epic 11 adds a per-Student extension here without changing callers."""
    return _value(class_session, "test_deadline")


def _passed(row: Mapping[str, Any], now: datetime) -> list[DateName]:
    return [name for name in DATE_NAMES if row[name] is not None and row[name] <= now]  # type: ignore[misc]


def _play_time_warning(row: Mapping[str, Any], settings: GameSettings) -> bool:
    """Whether the Start date leaves too little time to the Play deadline for the Weeks. Never
    while `min_play_minutes_per_week` is unset (SM-11)."""
    per_week = get_settings().min_play_minutes_per_week
    if per_week is None or row["start_at"] is None or row["play_deadline"] is None:
        return False
    return row["play_deadline"] - row["start_at"] < timedelta(minutes=per_week * settings.weeks)


def judge_dates(
    stored: Mapping[str, Any], wanted: DatesIn, *, now: datetime, locked: bool
) -> dict[str, datetime | None]:
    """The dates that change, in UTC and to the whole minute, or raises `DeadlinePassed` or
    `InvalidDates` (FR-18). The date fields hold whole minutes, so a date equal to the stored one
    to the minute is unchanged; unchanged dates are never judged, so a passed Start date can be
    sent again as it was."""
    values: dict[str, datetime | None] = {}
    for name in DATE_NAMES:
        value = _minute(getattr(wanted, name))
        values[name] = stored[name] if value == _minute(stored[name]) else value
    changed = {name: v for name, v in values.items() if v != stored[name]}
    passed = {
        name: "passed" for name in changed if stored[name] is not None and stored[name] <= now
    }
    if passed:
        raise DeadlinePassed(passed)
    wrong: dict[str, str] = {}
    for name, value in changed.items():
        if value is None:
            if locked:
                wrong[name] = "required"
        elif value <= now:
            wrong[name] = "past"
    if wrong:
        raise InvalidDates(wrong)
    present = [(name, v) for name, v in values.items() if v is not None]
    order: dict[str, str] = {}
    for i, (name, value) in enumerate(present):
        for earlier_name, earlier in present[:i]:
            if value <= earlier:
                # The later date of the pair, unless only the earlier one changed: the reason
                # then stands under the date the Lecturer can change.
                if name not in changed and earlier_name in changed:
                    order[earlier_name] = "before"
                else:
                    order[name] = "order"
    if order:
        raise InvalidDates(order)
    return changed


def _minute(value: datetime | None) -> datetime | None:
    """`value` in UTC, cut to the whole minute the date fields hold."""
    return value.astimezone(UTC).replace(second=0, microsecond=0) if value is not None else None


async def _writable(s: AsyncSession, class_id: uuid.UUID) -> None:
    """The one guard before every change to a Class session (FR-6): the Class takes changes.
    Holds a share lock on the Class row, so an archive cannot commit in the middle."""
    if not await classes.is_writable(class_id, session=s):
        log.info("class_session_refused", class_id=str(class_id), error_code="class_archived")
        raise classes.ClassArchived


async def _class_for(
    user: authz.Principal, class_id: uuid.UUID, action: str
) -> classes.ClassOut | None:
    """The Class when `user` may do `action` on its Class sessions, else None (FR-5: one answer
    for a Class outside the User's scope, one that does not exist, and a role that may not)."""
    found = await classes.get_class(user, class_id)
    if found is None or not authz.can(user, action, found):
        return None
    return found


async def create_session(
    user: authz.Principal, class_id: uuid.UUID, *, now: datetime
) -> ClassSessionOut | None:
    """«Lag Klasseøkt»: one transaction stores the Class session with its defaults, its model
    config and budget row when a default is active, and emits `session:<id>`. None when the User
    may not manage the Class; raises `ClassArchived`."""
    if await _class_for(user, class_id, "class_sessions.manage") is None:
        return None
    session_id = uuid.uuid7()
    settings = classic_settings()
    async with get_sessionmaker().begin() as s:
        await _writable(s, class_id)
        default = await config.active_default(session=s)
        offered = await config.offered_effort_levels(default.id, session=s) if default else []
        await repo.insert_session(
            s,
            id=session_id,
            class_id=class_id,
            game_settings=settings.model_dump(mode="json"),
            ai_mode=(AiMode.llm if default else AiMode.rule_based).value,
            debrief_mode=DEFAULT_DEBRIEF_MODE.value,
            inactivity_limit_hours=DEFAULT_INACTIVITY_LIMIT_HOURS,
            obligatory=DEFAULT_OBLIGATORY,
            required_share_percent=get_settings().completion_default_share_percent,
            model_config_id=default.id if default else None,
            # The config's default level; `active_default` only returns a config that offers one.
            effort_level=offered[0].name if offered else None,
            created_by=user.id,
            created_at=now,
        )
        if default is not None:
            await budget.set_budget(budget.BudgetScope.class_session(session_id), session=s)
        await events.emit(s, "session", str(session_id))
    log.info(
        "class_session_created",
        class_session_id=str(session_id),
        class_id=str(class_id),
        model_config_id=str(default.id) if default else None,
    )
    return await get_session(user, session_id)


def _in_force(row: Mapping[str, Any], offered: list[config.OfferedLevel]) -> str | None:
    """The Effort level in force for an LLM row: the stored one, or the config's default for a
    row stored before the level was (or None when the config offers nothing here)."""
    if row["effort_level"] is not None:
        return row["effort_level"]
    return offered[0].name if offered else None


def _decimal(value: Decimal | None) -> str | None:
    """A measured figure as a decimal string without the column's trailing zeros."""
    return None if value is None else format(value.normalize(), "f")


async def _levels_out(
    config_id: uuid.UUID | None, offered: list[config.OfferedLevel]
) -> list[OfferedEffortLevelOut]:
    """The offered levels with the config's label and effect line and the measured figures."""
    if config_id is None or not offered:
        return []
    found = await config.get(config_id)
    out = []
    for level in offered:
        spec = found.effort_level(level.name) if found else None
        out.append(
            OfferedEffortLevelOut(
                name=level.name,
                label=spec.label if spec else None,
                effect=spec.effect if spec else None,
                default=level.default,
                time_per_order_median_s=_decimal(level.measurement.time_per_order_median_s),
                cost_per_game_usd=_decimal(level.measurement.cost_per_game_usd),
            )
        )
    return out


def ai_descriptions() -> AiDescriptionsOut:
    """The description of each AI player type, as `players.service.describe` gives it (FR-33)."""
    return AiDescriptionsOut(
        llm=players.describe(AiMode.llm.value).text,
        rule_based=players.describe(AiMode.rule_based.value).text,
    )


async def get_session(user: authz.Principal, session_id: uuid.UUID) -> ClassSessionOut | None:
    """The Class session, or None when the User may not read its Class (or it does not exist)."""
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, session_id)
        number = await repo.number_of(s, session_id, row["class_id"]) if row else 0
        labs = await repo.lab_hours_of(s, [session_id]) if row else []
    if row is None:
        return None
    found = await _class_for(user, row["class_id"], "class_sessions.read")
    if found is None:
        return None
    test_game = await _latest_test_game(user, session_id) if lecturer_test_enabled() else None
    unavailable = None
    config_id = row["model_config_id"]
    if config_id is None:
        default = await config.active_default()
        if default is None:
            unavailable = NO_DEFAULT_MODEL
        else:
            config_id = default.id
    offered = await config.offered_effort_levels(config_id) if config_id is not None else []
    llm = row["ai_mode"] == AiMode.llm.value
    settings = GameSettings.model_validate(row["game_settings"])
    now = auth.utcnow()
    copied_from, effort_level_replaced = await _copy_notes(user, row)
    return ClassSessionOut(
        id=row["id"],
        class_id=row["class_id"],
        class_name=found.name,
        number=number,
        game_settings=settings,
        is_classic=is_classic(settings),
        ai_mode=AiMode(row["ai_mode"]),
        debrief_mode=DebriefMode(row["debrief_mode"]),
        debrief_release=DebriefRelease(row["debrief_release"]),
        inactivity_limit_hours=row["inactivity_limit_hours"],
        obligatory=row["obligatory"],
        required_share_percent=row["required_share_percent"],
        llm_unavailable=unavailable,
        effort_level=_in_force(row, offered) if llm else None,
        effort_levels=await _levels_out(config_id, offered),
        ai_descriptions=ai_descriptions(),
        provider_unavailable=llm and row["model_config_id"] is not None and not offered,
        saved_at=row["saved_at"],
        created_at=row["created_at"],
        can_manage=authz.can(user, "class_sessions.manage", found) and not found.archived,
        start_at=row["start_at"],
        play_deadline=row["play_deadline"],
        debrief_deadline=row["debrief_deadline"],
        test_deadline=row["test_deadline"],
        locked=is_locked(row, now=now),
        locked_at=row["locked_at"],
        lock_refused=row["locked_at"] is None and row["lock_refused_at"] is not None,
        passed_dates=_passed(row, now),
        play_time_warning=_play_time_warning(row, settings),
        settings_warnings=[
            SettingWarning(code=w.code, field=w.field, values=w.values) for w in warnings(settings)
        ],
        calibrated_settings=GameSettings(),
        lab_hours=[_lab_hour_out(lab, now) for lab in labs],
        capacity_enabled=capacity_enabled(),
        info_visibility_enabled=info_visibility_enabled(),
        allocation_method=row["allocation_method"],
        student_choice_enabled=student_choice_enabled(),
        copied_from=copied_from,
        effort_level_replaced=effort_level_replaced,
        lecturer_test_enabled=lecturer_test_enabled(),
        test_game=test_game,
    )


async def _latest_test_game(user: authz.Principal, session_id: uuid.UUID) -> TestGameRefOut | None:
    """The User's newest test Game in the Class session and where it stands (Story 6.20)."""
    async with get_sessionmaker()() as s:
        found = await games_service.staff_test_games(s, session_id, user.id)
        if not found:
            return None
        play = await games_service.play_status(s, found[0].id)
    return TestGameRefOut(id=found[0].id, status=play.status)


async def list_sessions(user: authz.Principal, class_id: uuid.UUID) -> ClassSessionListOut | None:
    """The Class's sessions for the Klasse page, newest first; None when the User may not read
    the Class."""
    if await _class_for(user, class_id, "class_sessions.read") is None:
        return None
    async with get_sessionmaker().begin() as s:
        rows = await repo.sessions_of(s, class_id)
    return ClassSessionListOut(
        items=[
            ClassSessionListItem(
                id=r["id"], number=r["number"], created_at=r["created_at"], saved_at=r["saved_at"]
            )
            for r in rows
        ],
        rerun_enabled=rerun_enabled(),
    )


async def save_session(
    user: authz.Principal,
    session_id: uuid.UUID,
    ai_mode: AiMode,
    *,
    now: datetime,
    effort_level: str | None = None,
    debrief_mode: DebriefMode | None = None,
    debrief_release: DebriefRelease | None = None,
    dates: DatesIn | None = None,
    game_settings: Mapping[str, Any] | None = None,
    obligatory: bool | None = None,
    required_share_percent: int | None = None,
    inactivity_limit_hours: int | None = None,
    allocation_method: AllocationMethod | None = None,
) -> ClassSessionOut | None:
    """«Lagre Klasseøkt»: saves the Class session as it stands and emits `session:<id>`. LLM
    players on a Class session with no model config take the active default and its budget row
    in the same transaction, or raise `LlmUnavailableError` and change nothing. With LLM players
    the Effort level is `effort_level`, else the one in force, else the config's default; a
    changed level the config does not offer raises `InvalidEffortLevel`. With Rule-based players
    no level is in force. `debrief_mode` and `debrief_release` (Story 9.2), None, keep the stored
    ones. With `game_settings` the
    draft is judged by `judge_settings` and stored, or `InvalidSettings` is raised. With `dates`
    the four dates are replaced under the rules of `judge_dates`; a change emits `user:<id>`
    once per registered Student of the Class. `obligatory`, `required_share_percent` and
    `inactivity_limit_hours` (Story 5.7), None, keep their values; a changed share outside 1 to
    100 or limit under 20 raises `InvalidSessionValues`, and switching the mark on enqueues one
    `OBLIGATORY_NOTICE` per registered Student. Once locked, a changed AI mode, Effort level,
    Debrief mode, Debrief release, Game settings, obligatory mark, share or Inactivity limit raise
    `SessionLocked`. `allocation_method` (Story 5.17), None, keeps the method; a change to
    `student_choice` is judged by `_judge_method` and opens the choice (`_open_student_choice`).
    None when the User may not manage the Class; raises `ClassArchived`."""
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, session_id)
    if row is None or await _class_for(user, row["class_id"], "class_sessions.manage") is None:
        return None
    needs_students = (
        dates is not None or obligatory is True or allocation_method == "student_choice"
    )
    students = await classes.registered_students(row["class_id"]) if needs_students else []
    async with get_sessionmaker().begin() as s:
        await _writable(s, row["class_id"])
        row = await repo.session_row(s, session_id, lock=True)
        if row is None:
            return None
        locked = is_locked(row, now=now)
        changed: dict[str, datetime | None] = {}
        new_settings: GameSettings | None = None
        debrief = debrief_mode.value if debrief_mode is not None else row["debrief_mode"]
        release = debrief_release.value if debrief_release is not None else row["debrief_release"]
        config_id = row["model_config_id"]
        offered = (
            await config.offered_effort_levels(config_id, session=s)
            if config_id is not None and ai_mode is AiMode.llm
            else []
        )
        in_force = _in_force(row, offered) if row["ai_mode"] == AiMode.llm.value else None
        level: str | None = None
        marked = row["obligatory"] if obligatory is None else obligatory
        share = (
            row["required_share_percent"]
            if required_share_percent is None
            else required_share_percent
        )
        limit = (
            row["inactivity_limit_hours"]
            if inactivity_limit_hours is None
            else inactivity_limit_hours
        )
        method: AllocationMethod = allocation_method or row["allocation_method"]
        switching = method != row["allocation_method"]
        try:
            if switching:
                await _judge_method(s, row, method, locked=locked)
            if locked:
                refused = {
                    name: "locked"
                    for name, differs in (
                        ("ai_mode", ai_mode.value != row["ai_mode"]),
                        (
                            "effort_level",
                            ai_mode is AiMode.llm
                            and effort_level is not None
                            and effort_level != in_force,
                        ),
                        ("debrief_mode", debrief != row["debrief_mode"]),
                        ("debrief_release", release != row["debrief_release"]),
                        ("obligatory", marked != row["obligatory"]),
                        ("required_share_percent", share != row["required_share_percent"]),
                        ("inactivity_limit_hours", limit != row["inactivity_limit_hours"]),
                    )
                    if differs
                }
                if refused:
                    raise SessionLocked(refused)
            _judge_values(row, share, limit)
            if game_settings is not None:
                new_settings = _settings_to_store(row, game_settings, locked=locked)
            if dates is not None:
                changed = judge_dates(row, dates, now=now, locked=locked)
                if row["locked_at"] is not None and "start_at" in changed:
                    # Locked early (Epic 8), before the Start date: it no longer moves either.
                    raise SessionLocked({"start_at": "locked"})
            if ai_mode is AiMode.llm:
                if config_id is None:
                    default = await config.active_default(session=s)
                    if default is None:
                        log.info(
                            "class_session_refused",
                            class_session_id=str(session_id),
                            error_code="llm_unavailable",
                        )
                        raise LlmUnavailableError
                    config_id = default.id
                    offered = await config.offered_effort_levels(config_id, session=s)
                    in_force = None
                    await budget.set_budget(budget.BudgetScope.class_session(session_id), session=s)
                if in_force is None:
                    in_force = offered[0].name if offered else None
                level = effort_level if effort_level is not None else in_force
                if level != in_force and level not in {o.name for o in offered}:
                    raise InvalidEffortLevel({"effort_level": "not_offered"})
        except InvalidSettings as refused:
            log.info(
                "class_session_refused",
                class_session_id=str(session_id),
                error_code=refused.code,
                fields=sorted(refused.problems),
            )
            raise
        except _FieldsError as refused:
            log.info(
                "class_session_refused",
                class_session_id=str(session_id),
                error_code=refused.code,
                fields=sorted(refused.fields),
            )
            raise
        await repo.save(
            s,
            session_id,
            now=now,
            ai_mode=ai_mode.value,
            model_config_id=config_id,
            effort_level=level,
            debrief_mode=debrief,
            debrief_release=release,
            dates=changed,
            game_settings=new_settings.model_dump(mode="json") if new_settings else None,
            obligatory=marked,
            required_share_percent=share,
            inactivity_limit_hours=limit,
            allocation_method=method if switching else None,
        )
        if switching and method == "student_choice":
            await _open_student_choice(s, session_id, user.id, students, now)
        await events.emit(s, "session", str(session_id))
        if changed:
            for student in students:
                await events.emit(s, "user", str(student))
        switched_on = marked and not row["obligatory"]
        if switched_on:
            # The moment in the key: a mark switched off and on again later is told again; the
            # mail leaves the notice out if the mark is off when the digest goes (AD-9).
            for student in students:
                await notify.enqueue(
                    s,
                    student,
                    OBLIGATORY_NOTICE,
                    f"{OBLIGATORY_NOTICE}:{session_id}:{now.isoformat()}:{student}",
                    ref=session_id,
                )
    log.info(
        "class_session_saved",
        class_session_id=str(session_id),
        dates=sorted(changed),
        settings_changed=new_settings is not None,
        obligatory_switched_on=switched_on,
        students_told=len(students) if switched_on else 0,
        student_choice_opened=switching,
    )
    if changed and locked:
        # After the start a moved deadline holds for the whole Class session (FR-18).
        log.info(
            "class_session_dates_moved", class_session_id=str(session_id), dates=sorted(changed)
        )
    return await get_session(user, session_id)


def _judge_values(row: Mapping[str, Any], share: int, limit: int) -> None:
    """Raises `InvalidSessionValues` for a changed share outside 1 to 100 or a changed Inactivity
    limit under 20 (FR-17, FR-36). An unchanged value is never judged."""
    wrong: dict[str, str] = {}
    if share != row["required_share_percent"] and not (
        MIN_REQUIRED_SHARE_PERCENT <= share <= MAX_REQUIRED_SHARE_PERCENT
    ):
        wrong["required_share_percent"] = "out_of_range"
    if limit != row["inactivity_limit_hours"] and limit < MIN_INACTIVITY_LIMIT_HOURS:
        wrong["inactivity_limit_hours"] = "below_minimum"
    if wrong:
        raise InvalidSessionValues(wrong)


def _settings_to_store(
    row: Mapping[str, Any], draft: Mapping[str, Any], *, locked: bool
) -> GameSettings | None:
    """The Game settings to store from a draft, or None when they do not change. Raises
    `FeatureDisabled` for a capacity or a view while its flag is off, `SessionLocked` for a
    change once locked and `InvalidSettings` for a draft the engine refuses. An unchanged draft
    is never judged, so a locked session can be saved as it stands."""
    stored = GameSettings.model_validate(row["game_settings"])
    settings, problems, _ = judge_settings(stored, draft)
    disabled = {key: p.code for key, p in problems.items() if p.code == "feature_disabled"}
    if disabled:
        # A capacity or view that differs from the stored one is a change: once locked, that
        # answer wins.
        if locked:
            raise SessionLocked({"game_settings": "locked"})
        raise FeatureDisabled(disabled)
    if any(problem.code == "not_editable" for problem in problems.values()):
        raise InvalidSettings(problems)
    if settings == stored:
        return None
    if locked:
        raise SessionLocked({"game_settings": "locked"})
    if problems or settings is None:
        raise InvalidSettings(problems)
    return settings


async def check_settings(
    user: authz.Principal, session_id: uuid.UUID, draft: Mapping[str, Any], *, now: datetime
) -> SettingsCheckOut | None:
    """What the engine says of a draft of the Game settings, as the Lecturer leaves a field
    (FR-12): errors and warnings, nothing stored. Raises `SessionLocked` once locked. None when
    the User may not manage the Class."""
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, session_id)
    if row is None or await _class_for(user, row["class_id"], "class_sessions.manage") is None:
        return None
    if is_locked(row, now=now):
        raise SessionLocked({"game_settings": "locked"})
    stored = GameSettings.model_validate(row["game_settings"])
    _, problems, risky = judge_settings(stored, draft)
    return SettingsCheckOut(errors=problems, warnings=risky)


async def demand_series_of(user: authz.Principal, session_id: uuid.UUID) -> DemandSeriesOut | None:
    """The customer demand of every Week of the Class session's games, materialised by the engine
    from the stored pattern and seed (FR-13, AD-1). For its Class's staff only; None otherwise."""
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, session_id)
    if row is None or await _class_for(user, row["class_id"], "class_sessions.read") is None:
        return None
    settings = GameSettings.model_validate(row["game_settings"])
    return DemandSeriesOut(demand=list(demand_series(settings)))


def _next_deadline(
    user: authz.Principal, row: Mapping[str, Any], now: datetime
) -> NextDeadline | None:
    ahead = [
        (at, kind)
        for kind, at in (
            ("play", row["play_deadline"]),
            ("debrief", effective_debrief_deadline(user, row)),
            ("test", effective_test_deadline(user, row)),
        )
        if at is not None and at > now
    ]
    if not ahead:
        return None
    at, kind = min(ahead, key=lambda item: item[0])
    return NextDeadline(kind=kind, at=at)


async def enrolled_sessions(user: authz.Principal) -> EnrolledSessionListOut:
    """The Class sessions of the Classes `user` is a Student in (FR-18, FR-19, AD-3, AD-12): the
    dates, the User's own deadlines and the next one that applies, and the Lab hours that have
    not ended. Never the Game settings, the number of Weeks or the demand. What Epic 6's Hjem
    shows as «Neste frist» and «Labtimer». With `FEATURE_STUDENT_CHOICE` on, a session with
    Student choice says whether the choice is open and, once locked, the Seat the draw gave the
    Student (Story 5.17)."""
    names = {item.id: item.name for item in (await classes.enrolled_classes(user)).items}
    now = auth.utcnow()
    choice = student_choice_enabled()
    async with get_sessionmaker().begin() as s:
        rows = await repo.enrolled_sessions(s, user)
        labs = await repo.lab_hours_of(s, [row["id"] for row in rows], ending_after=now)
        drafts = (
            await repo.drafts_of(
                s,
                [
                    row["id"]
                    for row in rows
                    if row["allocation_method"] == "student_choice" and is_locked(row, now=now)
                ],
            )
            if choice
            else {}
        )
        locked = [row for row in rows if row["class_id"] in names and is_locked(row, now=now)]
        done = await progress.steps_of(s, user.id, [row["id"] for row in rows])
        cards = {
            row["id"]: await _student_card(s, user.id, row, done.get(row["id"], set()))
            for row in locked
        }
    upcoming: dict[uuid.UUID, list[EnrolledLabHourOut]] = {}
    for lab in labs:
        upcoming.setdefault(lab["class_session_id"], []).append(
            EnrolledLabHourOut(
                id=lab["id"], starts_at=lab["starts_at"], ends_at=lab["ends_at"], place=lab["place"]
            )
        )
    return EnrolledSessionListOut(
        items=[
            EnrolledSessionOut(
                id=row["id"],
                class_id=row["class_id"],
                class_name=names[row["class_id"]],
                number=row["number"],
                start_at=row["start_at"],
                play_deadline=row["play_deadline"],
                debrief_deadline=effective_debrief_deadline(user, row),
                test_deadline=effective_test_deadline(user, row),
                next_deadline=_next_deadline(user, row, now),
                obligatory=row["obligatory"],
                lab_hours=upcoming.get(row["id"], []),
                seat_choice_open=choice
                and row["allocation_method"] == "student_choice"
                and not is_locked(row, now=now),
                drawn_seat=_drawn_seat(drafts.get(row["id"]), user.id),
                game=cards.get(row["id"]),
                steps=stegene(
                    cards.get(row["id"]) is not None,
                    done.get(row["id"], set()),
                    held=_held(cards.get(row["id"])),
                ),
            )
            for row in rows
            if row["class_id"] in names
        ]
    )


STEGENE: tuple[tuple[str, progress.Step], ...] = (
    ("class_game", progress.Step.CLASS_GAME),
    ("debrief", progress.Step.DEBRIEF),
    ("quiz", progress.Step.QUIZ_PASSED),
    ("replay", progress.Step.REPLAY),
    ("test", progress.Step.TEST_SUBMITTED),
    ("report", progress.Step.ASSESSMENT_READY),
)
"""Stegene's six steps in order (UX-DR29) and the `progress` step that marks each done."""


def stegene(has_game: bool, done: set[progress.Step], *, held: bool = False) -> list[StepOut]:
    """The state of each of Stegene's steps (Story 6.1, AD-10): a done step is `done`; with a
    game the first step not done is `current` and the later ones `locked`; with no game (before
    the Start date, or no Seat yet) every step not done is `locked`. `held` (Story 9.2): the
    Lecturer holds the Debriefs until every Class game has finished, so a Debrief step that would
    be current is `locked` and says so, and no step is current until the release."""
    steps: list[StepOut] = []
    current_given = not has_game
    for name, step in STEGENE:
        if step in done:
            state = "done"
        elif not current_given:
            state, current_given = "current", True
            if name == "debrief" and held:
                steps.append(StepOut(step=name, state="locked", held=True))
                continue
        else:
            state = "locked"
        steps.append(StepOut(step=name, state=state))
    return steps


# Story 9.2: where the Student's Debrief stands, as `debrief.rules.state` judges it. `debrief`
# imports `sessions`, so it registers its rule here instead of `sessions` importing it (AD-25).

DebriefStateProvider = Callable[
    [AsyncSession, uuid.UUID, uuid.UUID, bool], Awaitable[DebriefState | None]
]
"""`(session, user_id, class_session_id, hold)` → `open`, `not_open` or `held`; None when the User
has no Class game in the session."""

_debrief_state: list[DebriefStateProvider] = []


def register_debrief_state(provider: DebriefStateProvider) -> None:
    """`debrief.rules` registers its one availability rule at import. The same one again changes
    nothing; another is refused, so Hjem and the Debrief can never judge differently."""
    if _debrief_state and _debrief_state[0] is not provider:
        raise ValueError("a Debrief state provider is registered already")
    _debrief_state[:] = [provider]


async def _debrief_of(
    s: AsyncSession, user_id: uuid.UUID, row: Mapping[str, Any]
) -> DebriefState | None:
    """The Student's Debrief state in the Class session `row`, read in `s`; None before
    `debrief` has registered its rule (a process that never loads it shows no Debrief state)."""
    if not _debrief_state:
        return None
    hold = row.get("debrief_release") == DebriefRelease.hold.value
    return await _debrief_state[0](s, user_id, row["id"], hold)


def _held(card: StudentGameOut | None) -> bool:
    return card is not None and card.debrief == "held"


@dataclass(frozen=True)
class DebriefSession:
    """A locked Class session as the Debrief reads it (Story 9.2): its id, Class and whether the
    Lecturer holds the Debriefs until all Class games have finished."""

    id: uuid.UUID
    class_id: uuid.UUID
    hold: bool


async def debrief_session_of(
    s: AsyncSession, user: authz.Principal, class_session_id: uuid.UUID
) -> DebriefSession | None:
    """The Class session for the User's Debrief, read in `s`: one of their own
    (`authz.classes_enrolled_by`), in a Class Hjem lists, and locked; None for every other case
    alike (FR-5), as `_own_locked_game` judges a game."""
    listed = {item.id for item in (await classes.enrolled_classes(user, session=s)).items}
    rows = {row["id"]: row for row in await repo.enrolled_sessions(s, user)}
    row = rows.get(class_session_id)
    if row is None or row["class_id"] not in listed or not is_locked(row):
        return None
    return DebriefSession(
        id=row["id"],
        class_id=row["class_id"],
        hold=row["debrief_release"] == DebriefRelease.hold.value,
    )


async def class_staff_may(user: authz.Principal, class_session_id: uuid.UUID, action: str) -> bool:
    """Whether `user` may do the Class action `action` on the Class of the Class session (its
    staff role there, `authz.can`): how another module asks without reading Classes itself
    (Story 9.3: `explanations.read`). False for a session that does not exist."""
    async with get_sessionmaker()() as s:
        row = await repo.session_row(s, class_session_id)
    if row is None:
        return False
    return await _class_for(user, row["class_id"], action) is not None


async def held_debrief_sessions(s: AsyncSession) -> list[uuid.UUID]:
    """The locked Class sessions that hold their Debriefs (Story 9.2), for the sweep's release."""
    return await repo.held_debrief_sessions(s)


def _names_in(
    class_id: uuid.UUID, s: AsyncSession
) -> Callable[[list[uuid.UUID]], Awaitable[dict[uuid.UUID, str]]]:
    """`classes.student_names` for one Class: the names `table_status` shows, read now, in the
    caller's session `s` (one connection per request, `db.reading`)."""

    async def resolve(user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        return await classes.student_names(class_id, user_ids, session=s)

    return resolve


async def _student_card(
    s: AsyncSession, user_id: uuid.UUID, row: Mapping[str, Any], done: set[progress.Step]
) -> StudentGameOut | None:
    """The Student's Class game in a locked Class session, through `games.service.student_game`
    and `table_status` (Story 6.1, AD-3); None when they never held a Seat in it."""
    found = await games_service.student_game(s, user_id, row["id"])
    if found is None:
        return None
    return await _game_out(s, user_id, found, row, done)


def game_rules(row: Mapping[str, Any]) -> GameRulesOut:
    """The rules the briefing states (Story 6.2, FR-84), from the Class session's frozen snapshot
    or, until the lock has stored it, its settings, which a locked session no longer changes
    (`SessionLocked`). Only the delays, the Veiledede uker, the cost rates and, while
    `FEATURE_CAPACITY` is on (read now, Story 6.22), each capped Role's capacity (FR-14, AD-3)."""
    frozen = row["snapshot_settings"]
    settings = GameSettings.model_validate(frozen if frozen is not None else row["game_settings"])
    capacity: list[RoleCapacityOut] = []
    if capacity_enabled():
        for role in settings.roles:
            units = settings.capacity_of(role)
            if units is not None:
                capacity.append(RoleCapacityOut(role=role, units=units))
    return GameRulesOut(
        capacity=capacity,
        order_delay=settings.order_delay,
        shipping_delay=settings.shipping_delay,
        production_delay=settings.production_delay,
        guided_weeks=settings.guided_weeks,
        holding_cost=settings.holding_cost,
        backorder_cost=settings.backorder_cost,
    )


async def _game_out(
    s: AsyncSession,
    user_id: uuid.UUID,
    found: games_service.StudentGame,
    row: Mapping[str, Any],
    done: set[progress.Step],
) -> StudentGameOut:
    table = await games_service.table_status(
        s, found.game_id, user_id, _names_in(row["class_id"], s)
    )
    play = await games_service.play_status(s, found.game_id)
    state: games_service.SeatState | None = None
    turn: PlayTurnOut | None = None
    if play.status == "running":
        # Story 6.17 (AD-3): Hjem's Spillkort reads the numbers from the play envelope's sources,
        # in the same Week as `week`, so Hjem and the play screen never disagree.
        state, turn = await _own_week(s, found, play.week)
    return StudentGameOut(
        id=found.game_id,
        number=found.number,
        role=found.role,
        test_game=found.test_game,
        class_session_id=found.class_session_id,
        seats=_seats_out(table),
        # Story 6.2: the briefing comes first until the Starting task is done (AD-16), where
        # `games.policy` says the pre-play gate applies (Story 6.18).
        briefing_first=found.pre_play_gate and progress.Step.STARTING_TASK not in done,
        rules=game_rules(row),
        status=play.status,
        week=play.week,
        server_now=await games_service.database_now(s),
        seat_state=state,
        turn=turn,
        time_proposal=await _time_proposal_out(s, user_id, found.game_id, row["class_id"]),
        # Story 9.2: a Lecturer's test Game has no Debrief (Story 6.20).
        debrief=None if found.test_game else await _debrief_of(s, user_id, row),
    )


async def _time_proposal_out(
    s: AsyncSession, user_id: uuid.UUID, game_id: uuid.UUID, class_id: uuid.UUID
) -> TimeProposalOut | None:
    """The game's open proposal of a time to play as the reader sees it (Story 6.19, FR-22):
    the names read now, never stored (AD-14)."""
    proposal = await games_service.open_time_proposal(s, game_id)
    if proposal is None:
        return None
    names = await _names_in(class_id, s)([proposal.proposed_by, *proposal.accepted_by])

    def person(other: uuid.UUID) -> ProposalPersonOut:
        return ProposalPersonOut(name=names.get(other), mine=other == user_id)

    return TimeProposalOut(
        id=proposal.id,
        at=proposal.at,
        proposed_by=person(proposal.proposed_by),
        accepted_by=[person(other) for other in proposal.accepted_by],
        can_accept=user_id in proposal.seated
        and user_id != proposal.proposed_by
        and user_id not in proposal.accepted_by,
    )


async def _own_week(
    s: AsyncSession, found: games_service.StudentGame, week: int | None
) -> tuple[games_service.SeatState, PlayTurnOut]:
    """The own Seat's `seat_state` and turn in the open `week` (Stories 6.6 and 6.17), the
    play envelope's numbers, read through `games.views` only, in the caller's session `s`."""
    state = await games_service.seat_state(str(found.game_id), found.role, week, session=s)
    turn = await games_service.open_turn(str(found.game_id), found.role, week, session=s)
    return state, PlayTurnOut(
        guided=turn.guided, order=turn.order, viewed=turn.viewed_at is not None
    )


def _seats_out(table: games_service.TableStatus) -> list[TableSeatOut]:
    return [
        TableSeatOut(
            role=seat.role,
            holder=seat.holder,
            name=seat.name,
            mine=seat.mine,
            ordered=seat.ordered,
            wait_started_at=seat.wait_started_at,
            mark=seat.mark,
        )
        for seat in table.seats
    ]


async def _own_locked_game(
    s: AsyncSession, user: authz.Principal, game_id: str
) -> tuple[games_service.StudentGame, Mapping[str, Any]] | None:
    """The Student's own Class game by id and its Class session row, through `authz.own_seat`,
    once the session is locked, in a Class the User is still a Student in (Story 6.1, FR-5);
    None for every other case alike."""
    try:
        game_uuid = uuid.UUID(game_id)
    except ValueError:
        return None
    found = await games_service.own_game(s, user.id, game_uuid)
    if found is None:
        return None
    if found.test_game:
        return await _own_test_game(s, user, found)
    # The Classes Hjem lists: those the User is a Student in and that are not archived.
    listed = {item.id for item in (await classes.enrolled_classes(user, session=s)).items}
    # The Class session among the User's own (`authz.classes_enrolled_by`), locked.
    rows = {row["id"]: row for row in await repo.enrolled_sessions(s, user)}
    row = rows.get(found.class_session_id)
    if row is None or row["class_id"] not in listed or not is_locked(row):
        return None
    return found, row


async def _own_test_game(
    s: AsyncSession, user: authz.Principal, found: games_service.StudentGame
) -> tuple[games_service.StudentGame, Mapping[str, Any]] | None:
    """A Lecturer's test Game (Story 6.20, AD-12): theirs through `authz.own_seat` (the caller's
    `own_game`), while they are staff of its Class who may read its sessions; at any time, since
    it runs on its own snapshot. The session row it returns states the Game's own settings as the
    rules (`game_rules`), never the session's, which may have changed since."""
    row = await repo.session_row(s, found.class_session_id)
    # The reads below open sessions of their own: give `s`'s connection back first, so the request
    # never holds two (`db.reading`). `s` is a plain read session; its next read takes one again.
    await s.commit()
    if row is None or await _class_for(user, row["class_id"], "class_sessions.read") is None:
        return None
    game = await games_service.get_game(str(found.game_id))
    if game is None or game.settings is None:
        return None
    return found, {**row, "snapshot_settings": game.settings.model_dump(mode="json")}


async def student_game_of(user: authz.Principal, game_id: str) -> StudentGameOut | None:
    """The Student's own Class game by id (Story 6.1, AD-12, FR-5), through `authz.own_seat`, and
    only once its Class session is locked (a Student sees the game from the Start date). None for
    an id that is not one, a Game that does not exist, another Student's game, a Game whose Class
    session has not reached the Start date, or a Class the User is no longer a Student in: the
    route answers each the same."""
    async with get_sessionmaker()() as s:
        own = await _own_locked_game(s, user, game_id)
        if own is None:
            return None
        found, row = own
        done = await progress.steps_of(s, user.id, [row["id"]])
        return await _game_out(s, user.id, found, row, done.get(row["id"], set()))


class GameNotRunning(Exception):
    """The play screen's envelope asked for a game that is not running (Story 6.6)."""


async def student_play_of(user: authz.Principal, game_id: str) -> PlayOut | None:
    """The play screen's envelope (Story 6.6, AD-3) for the Student's own Class game, under
    `student_game_of`'s checks (None for every other id alike): what the Student's own Seat sees
    in the open Week, `games.views.seat_state` and nothing else about the numbers, and who sits
    where, `games.views.table_status`. Raises `GameNotRunning` unless the game is running (or
    playing out)."""
    async with get_sessionmaker()() as s:
        own = await _own_locked_game(s, user, game_id)
        if own is None:
            return None
        found, row = own
        play = await games_service.play_status(s, found.game_id)
        if play.status != "running":
            raise GameNotRunning
        table = await games_service.table_status(
            s, found.game_id, user.id, _names_in(row["class_id"], s)
        )
        state, turn = await _own_week(s, found, play.week)
        now = await games_service.database_now(s)
    return PlayOut(
        seat_state=state,
        turn=turn,
        table_status=TableStatusOut(seats=_seats_out(table)),
        server_now=now,
        # Read again when an AI player's Order falls due (AD-8, AD-20); one already past is the
        # rescue loop's to place, and its event says so.
        next_change_at=next((due for due in table.due_times if due > now), None),
    )


class GameNotFinished(Exception):
    """The game's result was asked for before the game finished (Story 6.18)."""


async def student_result_of(user: authz.Principal, game_id: str) -> GameResultOut | None:
    """«Spillet er ferdig» (Story 6.18, FR-28, AD-3): the chain's cost per Role and per Uke of
    the Student's own Class game, under `student_game_of`'s checks (None for every other id
    alike). Raises `GameNotFinished` until the game has finished, so no chain number leaks during
    play (FR-14). Roles only, never names; no demand."""
    async with get_sessionmaker()() as s:
        own = await _own_locked_game(s, user, game_id)
        if own is None:
            return None
        found, _ = own
    try:
        result = await games_service.chain_result(str(found.game_id))
    except games_service.ViewError as refused:
        if refused.code == "game_not_finished":
            raise GameNotFinished from None
        if refused.status == 404:
            return None
        raise
    return result


class ViewRefused(Exception):
    """A view of a Guided Week the api refuses (Story 6.10), with the command's code:
    `week_not_open`, `week_not_guided`, `game_not_started`, `game_finished`, `seat_not_student`
    or `seat_not_yours`."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


async def view_own_week(user: authz.Principal, game_id: str, week: int) -> bool | None:
    """The Student has the Guided Week `week` of their own Class game on screen (Story 6.10,
    FR-24), under `student_game_of`'s checks (None for every other id alike). Only
    `games.commands.view_week` records it; a Week already viewed counts as done. A Seat the
    Student no longer holds (`seat_not_yours`, a move after the check) and a not-found refusal
    answer None like any other game (FR-5). Raises `ViewRefused` with the command's code
    otherwise: `week_not_open`, `week_not_guided`, `game_not_started`, `game_finished` or
    `seat_not_student`."""
    async with get_sessionmaker()() as s:
        own = await _own_locked_game(s, user, game_id)
    if own is None:
        return None
    found, _ = own
    try:
        await games_commands.view_week(str(found.game_id), found.role, week, actor=user.id)
    except games_commands.CommandError as refused:
        if refused.status == 404 or refused.code == "seat_not_yours":
            return None
        raise ViewRefused(refused.code) from None
    return True


class OrderRefused(Exception):
    """A Student's Order the api refuses (Story 6.12), with the command's code and status:
    409 `order_exists`, `week_not_open`, `game_not_started`, `game_finished`, `seat_not_yours`
    (the Seat changed hands after `_own_locked_game`); 422 `order_invalid`."""

    def __init__(self, code: str, status: int) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


async def place_own_order(
    user: authz.Principal, game_id: str, week: int, order: int
) -> bool | None:
    """The Student's Order for the open `week` of their own Class game (Story 6.12, FR-24, AD-2),
    under `student_game_of`'s checks (None for every other id alike). Only
    `games.commands.place_order` writes it, with the Student as `actor`, so a Seat the Student
    no longer holds is refused there (`seat_not_yours`). A not-found refusal answers None like
    any other game (FR-5); every other refusal raises `OrderRefused` with the command's code."""
    async with get_sessionmaker()() as s:
        own = await _own_locked_game(s, user, game_id)
    if own is None:
        return None
    found, _ = own
    try:
        await games_commands.place_order(
            str(found.game_id), found.role, week, order, "student", actor=user.id
        )
    except games_commands.CommandError as refused:
        if refused.status == 404:
            return None
        raise OrderRefused(refused.code, refused.status) from None
    return True


class StartRefused(Exception):
    """A Student's start the api refuses (Story 6.5): `starting_task_required` before the
    Starting task is done, `game_not_ready` before the lock has given the Game its snapshot."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


async def start_own_game(user: authz.Principal, game_id: str) -> StudentGameOut | None:
    """«Start spillet» (Story 6.5, FR-22, AD-2): the Student starts their own Class game, under
    `student_game_of`'s checks (None for every other id alike), once they have done the Starting
    task (the pre-play gate). Only `games.commands.start` starts it; a Game another Student or the
    Lecturer started first counts as done. Returns the game as it now stands."""
    async with get_sessionmaker()() as s:
        own = await _own_locked_game(s, user, game_id)
        if own is None:
            return None
        found, row = own
        done = await progress.steps_of(s, user.id, [row["id"]])
    if found.pre_play_gate and progress.Step.STARTING_TASK not in done.get(row["id"], set()):
        raise StartRefused("starting_task_required")
    try:
        await games_commands.start(str(found.game_id))
    except games_commands.CommandError as refused:
        if refused.code == "game_not_ready":
            raise StartRefused(refused.code) from None
        if refused.code != "game_already_started":
            raise
    else:
        log.info("student_started_game", game_id=str(found.game_id), user_id=str(user.id))
    return await student_game_of(user, game_id)


class ProposalRefused(Exception):
    """A proposal or acceptance of a time to play the api refuses (Story 6.19), with the
    command's code and status: 409 `game_finished`, `proposal_gone`, `own_proposal`; 422
    `time_out_of_range`."""

    def __init__(self, code: str, status: int) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


def _proposal_refusal(refused: Exception) -> None:
    """None for a refusal that reads as any other game (not found, a Seat no longer held, FR-5);
    every other refusal raises `ProposalRefused`."""
    if not isinstance(refused, games_commands.CommandError):
        raise refused
    if refused.status == 404 or refused.code == "seat_not_yours":
        return None
    raise ProposalRefused(refused.code, refused.status) from None


async def propose_own_time(
    user: authz.Principal, game_id: str, at: datetime
) -> StudentGameOut | None:
    """«Send forslaget til gruppen» (Story 6.19, FR-22): the Student proposes a time to play in
    their own Class game, under `student_game_of`'s checks (None for every other id alike).
    Only `games.commands.propose_time` stores it, between now and the Class session's Play
    deadline. Returns the game as it now stands."""
    async with get_sessionmaker()() as s:
        own = await _own_locked_game(s, user, game_id)
    # A test Game has no group to agree a time with (Story 6.20).
    if own is None or own[0].test_game:
        return None
    found, row = own
    try:
        await games_commands.propose_time(
            str(found.game_id), at, actor=user.id, latest=_play_deadline_of(row["id"])
        )
    except games_commands.CommandError as refused:
        return _proposal_refusal(refused)
    return await student_game_of(user, game_id)


def _play_deadline_of(
    session_id: uuid.UUID,
) -> Callable[[AsyncSession], Awaitable[datetime | None]]:
    """The Class session's Play deadline, read share-locked in the proposal's transaction before
    the Game row lock, so a deadline the Lecturer moves meanwhile is not passed (Story 6.19)."""

    async def read(s: AsyncSession) -> datetime | None:
        row = await repo.session_row(s, session_id, share=True)
        return None if row is None else row["play_deadline"]

    return read


async def accept_own_time(
    user: authz.Principal, game_id: str, proposal_id: str
) -> StudentGameOut | None:
    """«Godta tidspunktet» (Story 6.19, FR-22): the Student accepts the open proposal of their
    own Class game with one press, under `student_game_of`'s checks (None for every other id
    alike). An acceptance already stored counts as done. Returns the game as it now stands."""
    async with get_sessionmaker()() as s:
        own = await _own_locked_game(s, user, game_id)
    if own is None or own[0].test_game:
        return None
    found, _ = own
    try:
        await games_commands.accept_time(str(found.game_id), proposal_id, actor=user.id)
    except games_commands.CommandError as refused:
        return _proposal_refusal(refused)
    return await student_game_of(user, game_id)


TIME_PROPOSED_NOTICE = games_commands.TIME_PROPOSED_NOTICE
"""The `digest` notice of a proposed time to play (Story 6.19); its mail is read at send time by
`time_proposal_mail_context`."""


async def time_proposal_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of a `TIME_PROPOSED_NOTICE`, for `messaging` at send time (Story
    6.19, AD-9): the Class's name, the game number, the proposer's name and the time in
    Europe/Oslo. None, so the notice is left out, when the proposal was replaced, its time has
    passed, the User accepted it or holds no Seat any more, the game has finished, the Class is
    archived or the User is no longer a registered Student of it."""
    if ref is None:
        return None
    proposal = await games_service.time_proposal_by_id(session, ref)
    if proposal is None or proposal.at <= now:
        return None
    # Nothing left to ask of a Student who accepted meanwhile or no longer holds a Seat.
    if user_id in proposal.accepted_by or user_id not in proposal.seated:
        return None
    info = await games_service.game_class_info(session, proposal.game_id)
    if info is None or info[2]:
        return None
    class_session_id, number, _ = info
    row = await repo.session_row(session, class_session_id)
    if row is None:
        return None
    label = await classes.label_of_class(session, row["class_id"])
    if label is None or label.archived:
        return None
    if user_id not in await classes.registered_students(row["class_id"]):
        return None
    names = await classes.student_names(row["class_id"], [proposal.proposed_by])
    return {
        "class_name": label.name,
        "game_number": number,
        "proposer": names.get(proposal.proposed_by),
        "at": proposal.at.astimezone(OSLO),
    }


@dataclass(frozen=True)
class OwnGameSession:
    """The Class session of a Student's own game, and the Starting task version its lock pinned
    (None for a session locked before the pin existed) (Story 6.3)."""

    class_session_id: uuid.UUID
    starting_task_version: int | None


async def own_game_session(user: authz.Principal, game_id: str) -> OwnGameSession | None:
    """The Class session of the Student's own locked Class game, under the same checks as
    `student_game_of`, for the Starting task routes (Story 6.3); None for every other id alike.
    The game's status is not asked: a finished game still offers the Starting task (FR-85)."""
    async with get_sessionmaker()() as s:
        own = await _own_locked_game(s, user, game_id)
        # A test Game has no Starting task, and no step is ever recorded for it (Story 6.20).
        if own is None or own[0].test_game:
            return None
        session_id = own[1]["id"]
        pins = await repo.session_pins(s, session_id)
    return OwnGameSession(session_id, content.pinned_version(pins))


async def lecturer_overview(user: authz.Principal) -> LecturerOverviewOut:
    """The Lærerhjem's «Venter» and «Neste frist» (UX-DR56, AD-12) over the Classes `user` is
    staff of and that are not archived: per Class the sessions that still lack a date or, until
    their lock and once the Class has a registered Student, a confirmed allocation (Story 5.9),
    and the next date across all of them. Empty
    when there is no Class session."""
    active = [item for item in (await classes.list_classes(user)).items if not item.archived]
    if not active:
        return LecturerOverviewOut(waiting=[], next_date=None)
    names = {item.id: item.name for item in active}
    async with get_sessionmaker().begin() as s:
        rows = await repo.staff_sessions(s, user, list(names))
    now = auth.utcnow()
    waiting: dict[uuid.UUID, list[SessionRef]] = {}
    upcoming: list[tuple[datetime, int, Mapping[str, Any]]] = []
    # A Class with no registered Student has nobody to allocate yet: nothing waits for a confirm.
    with_students = {
        class_id
        for class_id in {row["class_id"] for row in rows}
        if await classes.registered_students(class_id)
    }
    for row in rows:
        lacks: list[WaitingReason] = []
        if any(row[name] is None for name in DATE_NAMES):
            lacks.append("dates")
        # Once locked the lock allocates by itself (Story 5.11): nothing is left to confirm.
        if (
            row["class_id"] in with_students
            and not row["confirmed"]
            and not is_locked(row, now=now)
        ):
            lacks.append("allocation")
        if lacks:
            waiting.setdefault(row["class_id"], []).append(
                SessionRef(id=row["id"], number=row["number"], lacks=lacks)
            )
        upcoming += [
            (row[name], index, row)
            for index, name in enumerate(DATE_NAMES)
            if row[name] is not None and row[name] > now
        ]
    next_date = None
    if upcoming:
        at, index, row = min(upcoming, key=lambda item: (item[0], item[1]))
        next_date = NextDate(
            kind=DATE_KINDS[DATE_NAMES[index]],
            at=at,
            session_id=row["id"],
            number=row["number"],
            class_id=row["class_id"],
            class_name=names[row["class_id"]],
        )
    return LecturerOverviewOut(
        waiting=[
            WaitingClass(class_id=item.id, class_name=item.name, sessions=waiting[item.id])
            for item in active
            if item.id in waiting
        ],
        next_date=next_date,
    )


# Lab hours (Story 5.6, FR-19, AD-9).


def _lab_hour_out(row: Mapping[str, Any], now: datetime) -> LabHourOut:
    return LabHourOut(
        id=row["id"],
        starts_at=row["starts_at"],
        ends_at=row["ends_at"],
        place=row["place"],
        ended=row["ends_at"] <= now,
    )


def judge_lab_hour(wanted: LabHourIn, *, now: datetime) -> dict[str, Any]:
    """The values to store of a Lab hour (UTC to the whole minute, the place trimmed), or raises
    `InvalidLabHour` naming each field in question. A Lab hour may have begun; it may not have
    ended."""
    place = wanted.place.strip()
    starts_at = _minute(wanted.starts_at)
    ends_at = _minute(wanted.ends_at)
    assert starts_at is not None and ends_at is not None
    wrong: dict[str, str] = {}
    if not place:
        wrong["place"] = "required"
    elif len(place) > PLACE_MAX_LENGTH:
        wrong["place"] = "too_long"
    if ends_at <= starts_at:
        wrong["ends_at"] = "not_after_start"
    elif ends_at - starts_at > MAX_LAB_HOUR:
        wrong["ends_at"] = "too_long"
    elif ends_at <= now:
        wrong["ends_at"] = "past"
    if wrong:
        raise InvalidLabHour(wrong)
    return {"starts_at": starts_at, "ends_at": ends_at, "place": place}


async def _managed_session(
    user: authz.Principal, session_id: uuid.UUID
) -> Mapping[str, Any] | None:
    """The Class session's row when `user` may manage its Class, else None."""
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, session_id)
    if row is None or await _class_for(user, row["class_id"], "class_sessions.manage") is None:
        return None
    return row


async def _tell_students(
    s: AsyncSession, kind: str, lab_hour_id: uuid.UUID, students: list[uuid.UUID], key: str
) -> None:
    """One notice of `kind` per registered Student, holding ids only (AD-14); each emits
    `user:<id>`."""
    for student in students:
        await notify.enqueue(s, student, kind, f"{kind}:{key}:{student}", ref=lab_hour_id)


def _refused(session_id: uuid.UUID, refused: InvalidLabHour | LabHourEnded) -> None:
    log.info(
        "lab_hour_refused",
        class_session_id=str(session_id),
        error_code=refused.code,
        fields=sorted(refused.fields) if isinstance(refused, InvalidLabHour) else None,
    )


async def add_lab_hour(
    user: authz.Principal, session_id: uuid.UUID, wanted: LabHourIn, *, now: datetime
) -> LabHourOut | None:
    """«Legg til Labtime»: stores the Lab hour, emits `session:<id>` and tells each registered
    Student (`LAB_HOUR_ADDED`). The Start-date lock does not apply. None when the User may not
    manage the Class; raises `ClassArchived` or `InvalidLabHour`."""
    row = await _managed_session(user, session_id)
    if row is None:
        return None
    students = await classes.registered_students(row["class_id"])
    lab_hour_id = uuid.uuid7()
    async with get_sessionmaker().begin() as s:
        await _writable(s, row["class_id"])
        try:
            values = judge_lab_hour(wanted, now=now)
        except InvalidLabHour as refused:
            _refused(session_id, refused)
            raise
        await repo.insert_lab_hour(
            s,
            id=lab_hour_id,
            class_session_id=session_id,
            revision=1,
            created_by=user.id,
            created_at=now,
            updated_at=now,
            **values,
        )
        await events.emit(s, "session", str(session_id))
        await _tell_students(s, LAB_HOUR_ADDED, lab_hour_id, students, str(lab_hour_id))
    log.info(
        "lab_hour_added",
        class_session_id=str(session_id),
        lab_hour_id=str(lab_hour_id),
        students=len(students),
    )
    return LabHourOut(id=lab_hour_id, ended=False, **values)


async def _open_lab_hour(
    s: AsyncSession, session_id: uuid.UUID, lab_hour_id: uuid.UUID, now: datetime
) -> Mapping[str, Any] | None:
    """The Lab hour of this Class session, locked, or None when it is another session's or was
    removed; raises `LabHourEnded` once it has ended."""
    found = await repo.lab_hour_row(s, lab_hour_id, lock=True)
    if found is None or found["class_session_id"] != session_id or found["cancelled_at"]:
        return None
    if found["ends_at"] <= now:
        refused = LabHourEnded()
        _refused(session_id, refused)
        raise refused
    return found


async def change_lab_hour(
    user: authz.Principal,
    session_id: uuid.UUID,
    lab_hour_id: uuid.UUID,
    wanted: LabHourIn,
    *,
    now: datetime,
) -> LabHourOut | None:
    """Changes a Lab hour that has not ended, raises its revision, emits `session:<id>` and tells
    each registered Student (`LAB_HOUR_CHANGED`). Unchanged values store and tell nothing. None
    when the User may not manage the Class or the Lab hour is not this session's; raises
    `ClassArchived`, `LabHourEnded` or `InvalidLabHour`."""
    row = await _managed_session(user, session_id)
    if row is None:
        return None
    students = await classes.registered_students(row["class_id"])
    async with get_sessionmaker().begin() as s:
        await _writable(s, row["class_id"])
        found = await _open_lab_hour(s, session_id, lab_hour_id, now)
        if found is None:
            return None
        try:
            values = judge_lab_hour(wanted, now=now)
        except InvalidLabHour as refused:
            _refused(session_id, refused)
            raise
        if all(values[name] == found[name] for name in values):
            return _lab_hour_out(found, now)
        revision = found["revision"] + 1
        stored = await repo.update_lab_hour(
            s, lab_hour_id, revision=revision, updated_at=now, **values
        )
        await events.emit(s, "session", str(session_id))
        await _tell_students(
            s, LAB_HOUR_CHANGED, lab_hour_id, students, f"{lab_hour_id}:{revision}"
        )
    log.info(
        "lab_hour_changed",
        class_session_id=str(session_id),
        lab_hour_id=str(lab_hour_id),
        revision=revision,
        students=len(students),
    )
    return _lab_hour_out(stored, now)


async def remove_lab_hour(
    user: authz.Principal, session_id: uuid.UUID, lab_hour_id: uuid.UUID, *, now: datetime
) -> bool:
    """Removes a Lab hour that has not ended: it is kept as cancelled and never listed again,
    emits `session:<id>` and tells each registered Student (`LAB_HOUR_CANCELLED`). False when
    the User may not manage the Class or the Lab hour is not this session's; raises
    `ClassArchived` or `LabHourEnded`."""
    row = await _managed_session(user, session_id)
    if row is None:
        return False
    students = await classes.registered_students(row["class_id"])
    async with get_sessionmaker().begin() as s:
        await _writable(s, row["class_id"])
        found = await _open_lab_hour(s, session_id, lab_hour_id, now)
        if found is None:
            return False
        await repo.update_lab_hour(s, lab_hour_id, cancelled_at=now, updated_at=now)
        await events.emit(s, "session", str(session_id))
        await _tell_students(s, LAB_HOUR_CANCELLED, lab_hour_id, students, str(lab_hour_id))
    log.info(
        "lab_hour_removed",
        class_session_id=str(session_id),
        lab_hour_id=str(lab_hour_id),
        students=len(students),
    )
    return True


async def current_lab_hour(
    class_session_id: uuid.UUID, now: datetime, *, session: AsyncSession | None = None
) -> LabHourOut | None:
    """The Lab hour of the Class session that is on at `now` (started, not ended, not removed),
    the earliest started if several; None outside every Lab hour. How Epic 8's «I rommet» asks;
    no other module reads `lab_hours`."""
    if session is not None:
        found = await repo.lab_hour_in_progress(session, class_session_id, now)
    else:
        async with get_sessionmaker().begin() as s:
            found = await repo.lab_hour_in_progress(s, class_session_id, now)
    return None if found is None else _lab_hour_out(found, now)


async def lab_hour_mail_context(
    kind: str, session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of a Lab hour notice, for `messaging` at send time (AD-9): the
    Class's name and the Lab hour's start and end in Europe/Oslo with its place. None, so the
    notice is left out, when the User is no longer a registered Student of the Class, the Class
    is archived, the Lab hour has ended, or (for an added or changed one) it was removed."""
    if ref is None:
        return None
    lab = await repo.lab_hour_row(session, ref)
    if lab is None:
        return None
    if lab["ends_at"] <= now or (kind != LAB_HOUR_CANCELLED and lab["cancelled_at"] is not None):
        return None
    row = await repo.session_row(session, lab["class_session_id"])
    if row is None:
        return None
    label = await classes.label_of_class(session, row["class_id"])
    if label is None or label.archived:
        return None
    if user_id not in await classes.registered_students(row["class_id"]):
        return None
    return {
        "class_name": label.name,
        "starts_at": lab["starts_at"].astimezone(OSLO),
        "ends_at": lab["ends_at"].astimezone(OSLO),
        "place": lab["place"],
    }


async def obligatory_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of an `OBLIGATORY_NOTICE`, for `messaging` at send time (Story
    5.7, AD-9): the Class's name. None, so the notice is left out, when the Class session is gone
    or no longer obligatory, the Class is archived, or the User is no longer a registered Student
    of it."""
    if ref is None:
        return None
    row = await repo.session_row(session, ref)
    if row is None or not row["obligatory"]:
        return None
    label = await classes.label_of_class(session, row["class_id"])
    if label is None or label.archived:
        return None
    if user_id not in await classes.registered_students(row["class_id"]):
        return None
    return {"class_name": label.name}


async def debrief_released_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of a `debrief_released` notice (Story 9.2, AD-9), for `messaging`
    at send time: the Class's name. None, so the notice is left out, when the Class session is
    gone, the Class is archived, or the User is no longer a registered Student of it."""
    if ref is None:
        return None
    row = await repo.session_row(session, ref)
    if row is None:
        return None
    label = await classes.label_of_class(session, row["class_id"])
    if label is None or label.archived:
        return None
    if user_id not in await classes.registered_students(row["class_id"]):
        return None
    return {"class_name": label.name}


# The allocation draft (Story 5.8, FR-20, AD-12, AD-14).

SEAT_ORDER: tuple[Role, ...] = tuple(reversed(ROLES))
"""The Seats of a Class game as the preview lists them: Fabrikk first, Detaljist last."""


async def _allocation_out(
    class_id: uuid.UUID,
    draft: Mapping[str, Any] | None,
    opened: list[games_service.ClassGame] | None = None,
) -> AllocationOut:
    """The block's state: the registered Students now, and the stored draft with its names. Once
    the Class games are open (`opened`, Story 5.12) their games are the Class games as their
    Seats hold them, with their lifecycle, so an AI player shows where a Student was removed."""
    if opened and draft is not None:
        return await _opened_out(class_id, draft, opened)
    registered = await classes.registered_students(class_id)
    if draft is None:
        return AllocationOut(
            registered_count=len(registered),
            missing_count=0,
            draft=None,
            confirmed=False,
            confirmed_at=None,
        )
    placed = [
        allocation.Seat(uuid.UUID(a["user_id"]), a["game_number"], Role(a["role"]))
        for a in draft["assignments"]
    ]
    in_draft = {seat.user_id for seat in placed}
    names = await classes.student_names(class_id, sorted(in_draft))
    games: dict[int, dict[Role, uuid.UUID]] = {}
    for seat in placed:
        games.setdefault(seat.game_number, {})[seat.role] = seat.user_id
    return AllocationOut(
        registered_count=len(registered),
        missing_count=sum(1 for student in registered if student not in in_draft),
        confirmed=draft["confirmed_at"] is not None,
        confirmed_at=draft["confirmed_at"],
        draft=AllocationDraftOut(
            id=draft["id"],
            revision=draft["revision"],
            drawn_at=draft["drawn_at"],
            games=[
                AllocationGameOut(
                    number=number,
                    seats=[
                        AllocationSeatOut(
                            role=role,
                            user_id=games[number].get(role),
                            name=names.get(games[number][role]) if role in games[number] else None,
                        )
                        for role in SEAT_ORDER
                    ],
                )
                for number in sorted(games)
            ],
        ),
    )


async def _opened_out(
    class_id: uuid.UUID,
    draft: Mapping[str, Any],
    opened: list[games_service.ClassGame],
    *,
    is_open: bool = True,
    method: AllocationMethod = "random",
) -> AllocationOut:
    """The Class games as their Seats hold them: once opened (Story 5.12), or, with Student choice
    (Story 5.17), from the save on (`is_open` False: no lifecycle, the games not yet open)."""
    registered = await classes.registered_students(class_id)
    held = {
        seat.user_id
        for game in opened
        for seat in game.seats
        if seat.occupant_kind == games_service.OccupantKind.STUDENT and seat.user_id is not None
    }
    names = await classes.student_names(class_id, sorted(held))
    out: list[AllocationGameOut] = []
    for game in opened:
        by_role = {seat.role: seat for seat in game.seats}
        seats = []
        for role in SEAT_ORDER:
            seat = by_role.get(role.value)
            student = (
                seat.user_id
                if seat is not None and seat.occupant_kind == games_service.OccupantKind.STUDENT
                else None
            )
            seats.append(
                AllocationSeatOut(
                    role=role,
                    user_id=student,
                    name=names.get(student) if student is not None else None,
                )
            )
        out.append(
            AllocationGameOut(
                number=game.number, seats=seats, lifecycle=game.lifecycle if is_open else None
            )
        )
    return AllocationOut(
        registered_count=len(registered),
        missing_count=sum(1 for student in registered if student not in held),
        confirmed=draft["confirmed_at"] is not None,
        confirmed_at=draft["confirmed_at"],
        opened=is_open,
        method=method,
        draft=AllocationDraftOut(
            id=draft["id"], revision=draft["revision"], drawn_at=draft["drawn_at"], games=out
        ),
    )


async def _out_for(
    row: Mapping[str, Any],
    draft: Mapping[str, Any] | None,
    opened: list[games_service.ClassGame] | None = None,
) -> AllocationOut:
    """The block's state for the Class session `row`: with Student choice (Story 5.17) the Class
    games as their Seats hold them from the save on, else `_allocation_out`."""
    method: AllocationMethod = row["allocation_method"]
    if method == "student_choice" and draft is not None and not opened:
        async with get_sessionmaker().begin() as s:
            games = await games_service.class_games(s, row["id"])
        return await _opened_out(row["class_id"], draft, games, is_open=False, method=method)
    out = await _allocation_out(row["class_id"], draft, opened)
    out.method = method
    return out


async def allocation_of(user: authz.Principal, session_id: uuid.UUID) -> AllocationOut | None:
    """The «Fordeling» block as stored, for the Class's staff (Assistant lecturers too). Once the
    Class games are open (Story 5.12) it lists them as their Seats hold them, and once locked it
    names the registered Students without a Seat (Story 5.13). None when the User may not read
    the Class."""
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, session_id)
    if row is None or await _class_for(user, row["class_id"], "class_sessions.read") is None:
        return None
    opened: list[games_service.ClassGame] | None = None
    async with get_sessionmaker().begin() as s:
        draft = await repo.draft_of(s, session_id)
        if row["snapshot"] is not None:
            found = await games_service.class_games(s, session_id)
            if found and all(game.has_snapshot for game in found):
                opened = found
    out = await _out_for(row, draft, opened)
    if row["locked_at"] is not None:
        # Story 5.13: who no Class game could seat, named for the Lecturer.
        without = await students_without_seat(session_id)
        names = await classes.student_names(row["class_id"], without)
        # A Student removed between the two reads has no name now: no longer one to list.
        out.without_seat = [
            AllocationStudentOut(user_id=student, name=names[student])
            for student in without
            if student in names
        ]
    return out


async def draw_allocation(
    user: authz.Principal, session_id: uuid.UUID, *, now: datetime, again: bool
) -> AllocationOut | None:
    """Opening «Fordeling» (`again` False): the stored draft as it is, or, when none is stored, a
    draft drawn from the registered Students with a fresh seed, revision 1. «Kjør fordeling på
    nytt» (`again` True): a new seed and a new draft under a new id. With no registered Student
    nothing is stored (and a redraw removes the draft). A stored draft emits `session:<id>`; no
    Student is told and no Game or Seat exists (FR-20). Once the Start date has passed, opening a
    stored draft still returns it, and any draw raises `SessionLocked`. Raises `ClassArchived`;
    None when the User may not manage the Class."""
    row = await _managed_session(user, session_id)
    if row is None:
        return None
    students = await classes.registered_students(row["class_id"])
    async with get_sessionmaker().begin() as s:
        await _writable(s, row["class_id"])
        row = await repo.session_row(s, session_id, lock=True)
        if row is None:
            return None
        draft = await repo.draft_of(s, session_id)
        if is_locked(row, now=now) and (again or draft is None):
            # Opening a stored draft only reads it, so a page open past the Start date still
            # shows it; drawing is what the lock refuses.
            refused = SessionLocked({"allocation": "locked"})
            log.info(
                "allocation_refused",
                class_session_id=str(session_id),
                error_code=refused.code,
            )
            raise refused
        if draft is not None and draft["confirmed_at"] is not None and again:
            # Confirmed: only move and swap remain (Story 5.10).
            confirmed = AllocationConfirmed({"allocation": "confirmed"})
            log.info(
                "allocation_refused",
                class_session_id=str(session_id),
                error_code=confirmed.code,
            )
            raise confirmed
        if draft is not None and not again:
            pass  # The stored draft, never recomputed.
        elif not students:
            if draft is not None:
                await repo.delete_draft(s, session_id)
                await events.emit(s, "session", str(session_id))
            draft = None
        else:
            seed = allocation.draw_seed()
            seats = allocation.allocate(students, seed)
            draft_id = uuid.uuid7()
            await repo.replace_draft(
                s,
                session_id,
                id=draft_id,
                revision=1,
                seed=seed,
                assignments=[
                    {
                        "user_id": str(seat.user_id),
                        "game_number": seat.game_number,
                        "role": seat.role.value,
                    }
                    for seat in seats
                ],
                drawn_by=user.id,
                drawn_at=now,
            )
            await events.emit(s, "session", str(session_id))
            draft = await repo.draft_of(s, session_id)
            log.info(
                "allocation_drawn",
                class_session_id=str(session_id),
                draft_id=str(draft_id),
                again=again,
                students=len(students),
                games=seats[-1].game_number,
            )
    return await _out_for(row, draft)


# Confirming the allocation (Story 5.9, FR-20, FR-7, AD-2, AD-4, AD-9).

ALLOCATION_NOTICE = "allocation_confirmed"
"""The notice kind each allocated Student gets when the allocation is confirmed, `digest`
(Story 5.9, AD-9). Its mail names no game or Role: a Student sees those from the Start date."""


def _without(assignments: list[Mapping[str, Any]], kept: set[str]) -> list[dict[str, Any]]:
    """The assignments of the Students in `kept`, with the games left empty dropped and the rest
    numbered again from 1 in their order, so «Spill N» stays contiguous."""
    left = [dict(a) for a in assignments if a["user_id"] in kept]
    numbers = {n: i for i, n in enumerate(sorted({a["game_number"] for a in left}), start=1)}
    return [{**a, "game_number": numbers[a["game_number"]]} for a in left]


async def confirm_allocation(
    user: authz.Principal, session_id: uuid.UUID, wanted: AllocationConfirmIn, *, now: datetime
) -> AllocationOut | None:
    """«Bekreft fordeling»: commits the stored draft the Lecturer is looking at, and nothing else.

    Under the Class session's row lock, in one transaction: one Class game per group through
    `games.commands.create` (purpose `class`, the session id and game number, no settings) and
    one Seat per Student through `games.commands.assign_seat` (`student` with the id), the draft
    marked confirmed, one `ALLOCATION_NOTICE` per Student and `session:<id>`. Empty Seats stay
    free until the lock gives them AI players (Story 5.12).

    Raises `SessionLocked` once locked, and `AllocationChanged` when `wanted` is not the current
    draft id and revision (nothing committed) or when Students of the draft have left the Roster
    since: those Seats are freed in the draft (its revision raised, emptied games dropped, none
    left: no draft) and that is committed instead, for a new press. A second confirm of the
    confirmed draft changes nothing. Raises `ClassArchived`; None when the User may not manage
    the Class."""
    row = await _managed_session(user, session_id)
    if row is None:
        return None
    registered = {str(student) for student in await classes.registered_students(row["class_id"])}
    refused: AllocationChanged | None = None
    async with get_sessionmaker().begin() as s:
        await _writable(s, row["class_id"])
        row = await repo.session_row(s, session_id, lock=True)
        if row is None:
            return None
        draft = await repo.draft_of(s, session_id)
        if is_locked(row, now=now):
            refused_lock = SessionLocked({"allocation": "locked"})
            _confirm_refused(session_id, refused_lock.code)
            raise refused_lock
        if draft is None or (draft["id"], draft["revision"]) != (wanted.draft_id, wanted.revision):
            changed = AllocationChanged({"draft": "changed"})
            _confirm_refused(session_id, changed.code)
            raise changed
        assignments = draft["assignments"]
        kept = _without(assignments, registered)
        if draft["confirmed_at"] is not None:
            pass  # Confirmed already: the same answer, no second set of Games.
        elif len(kept) != len(assignments):
            if kept:
                await repo.update_draft(
                    s, session_id, assignments=kept, revision=draft["revision"] + 1
                )
            else:
                await repo.delete_draft(s, session_id)
            await events.emit(s, "session", str(session_id))
            refused = AllocationChanged({"draft": "students_removed"})
            log.info(
                "allocation_students_removed",
                class_session_id=str(session_id),
                removed=len(assignments) - len(kept),
            )
        else:
            await _commit_allocation(s, session_id, draft, user.id, now)
        draft = await repo.draft_of(s, session_id)
    if refused is not None:
        _confirm_refused(session_id, refused.code)
        raise refused
    return await _out_for(row, draft)


def _confirm_refused(session_id: uuid.UUID, code: str) -> None:
    log.info("allocation_confirm_refused", class_session_id=str(session_id), error_code=code)


async def _commit_allocation(
    s: AsyncSession,
    session_id: uuid.UUID,
    draft: Mapping[str, Any],
    confirmed_by: uuid.UUID | None,
    now: datetime,
) -> None:
    """The Games, Seats, mark, notices and event of a confirmation, in the caller's transaction;
    `confirmed_by` is None when the lock allocated (Story 5.12)."""
    by_game: dict[int, list[Mapping[str, Any]]] = {}
    for assignment in draft["assignments"]:
        by_game.setdefault(assignment["game_number"], []).append(assignment)
    for number in sorted(by_game):
        game_id = await games_commands.create(
            games_service.Purpose.CLASS,
            class_session_id=session_id,
            game_number=number,
            within=s,
        )
        for assignment in by_game[number]:
            await games_commands.assign_seat(
                game_id,
                assignment["role"],
                games_service.OccupantKind.STUDENT,
                user_id=assignment["user_id"],
                within=s,
            )
    await repo.update_draft(s, session_id, confirmed_at=now, confirmed_by=confirmed_by)
    await events.emit(s, "session", str(session_id))
    for assignment in draft["assignments"]:
        student = uuid.UUID(assignment["user_id"])
        await notify.enqueue(
            s,
            student,
            ALLOCATION_NOTICE,
            f"{ALLOCATION_NOTICE}:{draft['id']}:{student}",
            ref=session_id,
        )
    log.info(
        "allocation_confirmed",
        class_session_id=str(session_id),
        draft_id=str(draft["id"]),
        games=len(by_game),
        students=len(draft["assignments"]),
    )


# Moving and swapping Students (Story 5.10, FR-20, AD-2, AD-8, AD-9).


def _moved(
    assignments: list[Mapping[str, Any]], wanted: AllocationMoveIn
) -> tuple[list[dict[str, Any]], list[str]]:
    """The draft's assignments after the move or swap, and the Students who moved. Raises
    `InvalidMove` when the draft cannot take it."""
    numbers = {a["game_number"] for a in assignments}
    origin = (wanted.from_game, wanted.from_role.value)
    target = (wanted.to_game, wanted.to_role.value)
    if origin == target:
        raise InvalidMove({"to": "same"})
    for side, number in (("from", wanted.from_game), ("to", wanted.to_game)):
        if number not in numbers:
            raise InvalidMove({side: "unknown"})
    held = {(a["game_number"], a["role"]): a["user_id"] for a in assignments}
    moving = held.get(origin)
    if moving is None:
        raise InvalidMove({"from": "empty"})
    staying = held.get(target)
    if (
        staying is None
        and wanted.from_game != wanted.to_game
        and sum(1 for a in assignments if a["game_number"] == wanted.from_game) == 1
    ):
        raise InvalidMove({"from": "last_student"})
    edited: list[dict[str, Any]] = []
    for a in assignments:
        seat = (a["game_number"], a["role"])
        if seat == origin:
            if staying is not None:
                edited.append({**a, "user_id": staying})
        elif seat == target:
            edited.append({**a, "user_id": moving})
        else:
            edited.append(dict(a))
    if staying is None:
        edited.append({"user_id": moving, "game_number": target[0], "role": target[1]})
    edited.sort(key=lambda a: (a["game_number"], SEAT_ORDER.index(Role(a["role"]))))
    return edited, [moving, *([staying] if staying is not None else [])]


async def move_allocation(
    user: authz.Principal, session_id: uuid.UUID, wanted: AllocationMoveIn, *, now: datetime
) -> AllocationOut | None:
    """Move a Student to a free Seat, or swap two, in the draft the Lecturer is looking at.

    Under the Class session's row lock, in one transaction: the stored draft changes under the
    same id with its revision raised by one, and `session:<id>` is emitted. Once the allocation
    is confirmed the Class games change with it through `games.commands.move_seat`, and each
    Student who moved gets the allocation notice again (`ALLOCATION_NOTICE`, keyed by the new
    revision), so the draft is always what the Seats hold.

    Raises `SessionLocked` once locked, `AllocationChanged` (`{"draft": "changed"}`) when
    `wanted` is not the current draft id and revision, `InvalidMove` for a move the draft cannot
    take and `SeatCommandRefused` when the command refuses; nothing is committed then. Raises
    `ClassArchived`; None when the User may not manage the Class."""
    row = await _managed_session(user, session_id)
    if row is None:
        return None
    try:
        async with get_sessionmaker().begin() as s:
            await _writable(s, row["class_id"])
            row = await repo.session_row(s, session_id, lock=True)
            if row is None:
                return None
            draft = await repo.draft_of(s, session_id)
            if is_locked(row, now=now):
                raise SessionLocked({"allocation": "locked"})
            if row["allocation_method"] == "student_choice":
                # Story 5.17: the Students take and change their Seats themselves.
                raise AllocationConfirmed({"allocation": "student_choice"})
            if draft is None or (draft["id"], draft["revision"]) != (
                wanted.draft_id,
                wanted.revision,
            ):
                raise AllocationChanged({"draft": "changed"})
            edited, students = _moved(draft["assignments"], wanted)
            revision = draft["revision"] + 1
            await repo.update_draft(s, session_id, assignments=edited, revision=revision)
            await events.emit(s, "session", str(session_id))
            if draft["confirmed_at"] is not None:
                games = await games_service.class_game_ids(s, session_id)
                try:
                    await games_commands.move_seat(
                        games[wanted.from_game],
                        wanted.from_role,
                        games[wanted.to_game],
                        wanted.to_role,
                        within=s,
                    )
                except games_commands.CommandError as refused:
                    raise SeatCommandRefused(refused.code, refused.status) from None
                for student in students:
                    await notify.enqueue(
                        s,
                        uuid.UUID(student),
                        ALLOCATION_NOTICE,
                        f"{ALLOCATION_NOTICE}:{draft['id']}:{revision}:{student}",
                        ref=session_id,
                    )
            draft = await repo.draft_of(s, session_id)
    except (
        SessionLocked,
        AllocationChanged,
        AllocationConfirmed,
        InvalidMove,
        SeatCommandRefused,
    ) as refused:
        log.info(
            "allocation_move_refused", class_session_id=str(session_id), error_code=refused.code
        )
        raise
    log.info(
        "allocation_moved",
        class_session_id=str(session_id),
        revision=revision,
        swapped=len(students) == 2,
        confirmed=draft["confirmed_at"] is not None,
    )
    return await _out_for(row, draft)


async def allocation_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of an `ALLOCATION_NOTICE`, for `messaging` at send time (Story 5.9,
    AD-9): the Class's name. None, so the notice is left out, when the Class session is gone, its
    allocation is not confirmed or no longer holds the User, the Class is archived, or the User is
    no longer a registered Student of it."""
    if ref is None:
        return None
    row = await repo.session_row(session, ref)
    if row is None:
        return None
    draft = await repo.draft_of(session, ref)
    if draft is None or draft["confirmed_at"] is None:
        return None
    if str(user_id) not in {a["user_id"] for a in draft["assignments"]}:
        return None
    label = await classes.label_of_class(session, row["class_id"])
    if label is None or label.archived:
        return None
    if user_id not in await classes.registered_students(row["class_id"]):
        return None
    return {"class_name": label.name}


# The Start-date lock (Story 5.11, FR-12, FR-13, FR-15, FR-78, AD-4, AD-8, AD-9, AD-17, AD-23).

LOCK_REFUSED_NOTICE = "class_session_lock_refused"
"""The notice kind each owner of the Class and each Admin gets once when the lock is refused for
a missing provider key, `immediate` (Story 5.11, AD-17): the Start date has passed."""

PinProvider = Callable[[AsyncSession, Mapping[str, Any]], Awaitable[Any]]
"""`(session, class_session_row)` → the JSON value the lock pins under the provider's name."""

_pin_providers: dict[str, PinProvider] = {}


def register_pin_provider(name: str, provider: PinProvider) -> None:
    """Add a provider whose value every later lock stores in `SessionRuntime.pins[name]` (AD-23):
    Epic 6 the Starting task, Epic 9 the Debrief content, Epic 10 the Replay template, Epic 11 the
    question set. The lock's mechanism does not change with them. Registering the same provider
    again changes nothing; another one under a taken name is refused."""
    known = _pin_providers.get(name)
    if known is not None and known is not provider:
        raise ValueError(f"a pin provider named {name!r} is registered already")
    _pin_providers[name] = provider


# Story 6.3: every lock from now on pins the Starting task version (AD-23).
register_pin_provider(content.Kind.STARTING_TASK.value, content.starting_task_pin)
# Story 9.1: and the Detected pattern definitions the facts sets of its Games use (AD-23).
register_pin_provider(content.Kind.DETECTED_PATTERNS.value, content.detected_patterns_pin)
# Story 9.4: and the sentence templates its Debriefs render their text with (AD-23).
register_pin_provider(content.Kind.SENTENCE_TEMPLATES.value, content.sentence_templates_pin)
# Story 9.6: the reflection questions.
register_pin_provider(content.Kind.REFLECTION_QUESTIONS.value, content.reflection_questions_pin)
register_pin_provider(content.Kind.MOMENT_TEMPLATES.value, content.moment_templates_pin)


class ProviderKeyMissing(Exception):
    """LLM players, and the provider of the session's model config may not answer here (in
    production: its key is not set). The lock is refused and nothing is frozen (AD-17)."""

    code = "provider_key_missing"


async def build_snapshot(
    class_session: Mapping[str, Any], *, session: AsyncSession | None = None
) -> dict[str, Any]:
    """The frozen snapshot of a Class session row (AD-4), keyed like `games.SNAPSHOT_COLUMNS`:
    the `GameSettings` with `schema_version`, the demand series the engine materialises with its
    seed, the engine's `rules_version`, and the `SessionRuntime` (AI mode, Effort level,
    Inactivity limit, model config id and its prompt versions, and the pins of every registered
    provider). The one builder, so a Game that takes its snapshot at creation has the same
    shape."""
    if session is None:
        async with get_sessionmaker().begin() as s:
            return await build_snapshot(class_session, session=s)
    settings = GameSettings.model_validate(class_session["game_settings"])
    config_id: str | None = None
    level: str | None = None
    prompts: dict[str, int] | None = None
    if class_session["ai_mode"] == AiMode.llm.value:
        found = await config.get(class_session["model_config_id"], session=session)
        if found is None:
            raise config.ConfigNotFound(class_session["model_config_id"])
        config_id = str(found.id)
        level = class_session["effort_level"] or found.spec.effort_levels[0].name
        prompts = {str(purpose): version for purpose, version in found.spec.prompts.items()}
    pins = {
        name: await provider(session, class_session)
        for name, provider in sorted(_pin_providers.items())
    }
    runtime = games_commands.default_runtime(
        model_config_id=config_id,
        effort_level=level,
        inactivity_limit_hours=class_session["inactivity_limit_hours"],
        prompt_versions=prompts,
        pins=pins,
    )
    return {
        "settings": settings.model_dump(mode="json"),
        "demand_series": list(demand_series(settings)),
        "demand_seed": settings.demand_seed,
        "rules_version": RULES_VERSION,
        "session_runtime": runtime.model_dump(mode="json"),
    }


async def lock(
    class_session_id: uuid.UUID, *, now: datetime | None = None, due_only: bool = False
) -> bool:
    """Lock the Class session now, whatever its Start date (the sweep at the Start date, Epic 8
    when the Lecturer starts early): in one transaction under the session's row lock, set
    `locked_at`, store `build_snapshot`, mark the model config referenced (LLM players) and emit
    `session:<id>`. When no allocation is confirmed, the same transaction first allocates the
    registered Students at random and commits that as «Bekreft fordeling» would (Story 5.12,
    FR-20), unless the Class is archived. After it commits, `open_games` gives every Class game
    the snapshot, also when the session was locked already, so an open cut short is finished.

    True when this call locked it; False when it was locked already or does not exist. With LLM
    players whose provider may not answer here it raises `ProviderKeyMissing` and stores
    nothing; it never falls back to Rule-based players (AD-17).

    `due_only` (the sweep): the Start date is judged again under the row lock, so a Start date
    moved later, or cleared, after the finder listed the session is not locked at the old one
    (follow-up review of Story 5.11). Such a call locks nothing and opens nothing."""
    now = now or auth.utcnow()
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, class_session_id, lock=True)
        if row is None:
            return False
        locked_before = row["locked_at"] is not None
        if due_only and not locked_before and (row["start_at"] is None or row["start_at"] > now):
            return False
        if not locked_before:
            llm = row["ai_mode"] == AiMode.llm.value
            if llm:
                found = await config.get(row["model_config_id"], session=s)
                if found is None or not config.may_answer(found):
                    raise ProviderKeyMissing
            snapshot = await build_snapshot(row, session=s)
            if llm:
                await config.mark_referenced(row["model_config_id"], session=s)
            allocated = await _allocate_at_lock(s, row, now)
            await repo.set_locked(s, class_session_id, locked_at=now, snapshot=snapshot)
            await events.emit(s, "session", str(class_session_id))
    if not locked_before:
        log.info(
            "class_session_locked",
            class_session_id=str(class_session_id),
            ai_mode=row["ai_mode"],
            model_config_id=str(row["model_config_id"]) if llm else None,
            pins=sorted(snapshot["session_runtime"]["pins"] or {}),
            allocated=allocated,
        )
    await open_games(class_session_id)
    return not locked_before


async def _allocate_at_lock(s: AsyncSession, row: Mapping[str, Any], now: datetime) -> int:
    """With no confirmed allocation at the lock: the registered Students allocated at random with
    `allocation.allocate` and a fresh seed, stored as a new draft (drawn by nobody) and committed
    by `_commit_allocation` in the lock's transaction, notices included (Story 5.12, FR-20). An
    unconfirmed draft is replaced. Nothing for an archived Class or with no registered Student.
    Returns how many Students were seated. With Student choice the Students who chose no Seat are
    drawn into free Seats instead (`_draw_at_lock`, Story 5.17)."""
    if row["allocation_method"] == "student_choice":
        return await _draw_at_lock(s, row, now)
    draft = await repo.draft_of(s, row["id"])
    if draft is not None and draft["confirmed_at"] is not None:
        return 0
    if not await classes.is_writable(row["class_id"], session=s):
        return 0
    students = await classes.registered_students(row["class_id"])
    if not students:
        if draft is not None:  # a preview of Students who have all left: nothing to show
            await repo.delete_draft(s, row["id"])
        return 0
    seed = allocation.draw_seed()
    seats = allocation.allocate(students, seed)
    await repo.replace_draft(
        s,
        row["id"],
        id=uuid.uuid7(),
        revision=1,
        seed=seed,
        assignments=[
            {"user_id": str(seat.user_id), "game_number": seat.game_number, "role": seat.role.value}
            for seat in seats
        ],
        drawn_by=None,
        drawn_at=now,
    )
    draft = await repo.draft_of(s, row["id"])
    if draft is None:  # stored just above, in this transaction
        raise RuntimeError("the allocation drawn at the lock was not stored")
    await _commit_allocation(s, row["id"], draft, None, now)
    return len(seats)


async def open_games(class_session_id: uuid.UUID) -> int:
    """Give each Class game of a locked Class session that has no snapshot the session's frozen
    one through `games.commands.set_snapshot`, one Game per transaction, by game number (Story
    5.12, AD-2, AD-4). A Seat whose Student is no longer a registered Student of the Class gets
    an AI player too (FR-7). A Game that has its snapshot is never changed, so a call after one
    that stopped half way finishes the rest. A Game whose open fails is logged and left for the
    next sweep (`due_locks` returns its session), so it never fails the lock that committed before
    it. Returns how many Games were opened now."""
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, class_session_id)
        if row is None or row["snapshot"] is None:
            return 0
        waiting = [
            g for g in await games_service.class_games(s, class_session_id) if not g.has_snapshot
        ]
    if not waiting:
        return 0
    registered = await classes.registered_students(row["class_id"])
    opened = failed = 0
    for game in waiting:
        try:
            if await games_commands.set_snapshot(
                str(game.id), row["snapshot"], keep_students=registered
            ):
                opened += 1
        except Exception as exc:  # the type only: one Game's failure leaves the others to open
            failed += 1
            log.error(
                "class_game_open_failed",
                class_session_id=str(class_session_id),
                game_id=str(game.id),
                exc_type=type(exc).__name__,
            )
    log.info(
        "class_games_opened", class_session_id=str(class_session_id), games=opened, failed=failed
    )
    return opened


async def due_locks(now: datetime) -> list[uuid.UUID]:
    """The sweep's `sessions.lock` finder (AD-9): the Class sessions whose Start date has passed
    and that are not locked, and the locked ones with a Class game still waiting for its
    snapshot (an open cut short, Story 5.12), by id. A session whose lock was refused already is
    left out while its Class is archived: nobody is told of it, so retrying each minute would only
    log (GitHub issue 109); it is tried again if the Class is restored."""
    async with get_sessionmaker().begin() as s:
        due = []
        for row in await repo.due_locks(s, now):
            if row["lock_refused_at"] is not None and not await classes.is_writable(
                row["class_id"], session=s
            ):
                continue
            due.append(row["id"])
        waiting = await games_service.class_sessions_awaiting_snapshot(s)
        unfinished = await repo.locked_ids(s, waiting) if waiting else []
    return sorted({*due, *unfinished})


async def lock_due(class_session_id: object, now: datetime) -> bool:
    """The sweep's `sessions.lock` action, one Class session per transaction with its id only
    (AD-9): it locks the session and opens its Class games, or finishes opening them. A refusal
    for a missing provider key tells each owner of the Class and each Admin once, and the next
    minute's sweep tries again."""
    assert isinstance(class_session_id, uuid.UUID)
    try:
        return await lock(class_session_id, now=now, due_only=True)
    except ProviderKeyMissing:
        told = await _tell_lock_refused(class_session_id, now)
        log.warning(
            "class_session_lock_refused",
            class_session_id=str(class_session_id),
            error_code=ProviderKeyMissing.code,
            told=told,
        )
        return False


async def _tell_lock_refused(class_session_id: uuid.UUID, now: datetime) -> int:
    """Mark the session's lock refused (`lock_refused_at`, the first time only, so the Klasseøkt
    can say so), and one `LOCK_REFUSED_NOTICE` per owner of the Class and per active Admin, keyed
    by the session and the User, so each is told once. No notice for a Class that is archived.
    Returns how many notices were stored now."""
    told = 0
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, class_session_id)
        if row is None:
            return 0
        await repo.set_lock_refused(s, class_session_id, now)
        if not await classes.is_writable(row["class_id"], session=s):
            return 0
        recipients = set(await classes.owners_of(s, row["class_id"]))
        recipients |= set(await identity.active_admins(s))
        for user_id in sorted(recipients):
            key = f"{LOCK_REFUSED_NOTICE}:{class_session_id}:{user_id}"
            if await notify.enqueue(s, user_id, LOCK_REFUSED_NOTICE, key, ref=class_session_id):
                told += 1
    return told


async def lock_refused_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of a `LOCK_REFUSED_NOTICE`, for `messaging` at send time: the
    Class's name and the session's number. None, so no mail goes, once the session has locked,
    is gone or its Class is archived."""
    if ref is None:
        return None
    row = await repo.session_row(session, ref)
    if row is None or row["locked_at"] is not None:
        return None
    label = await classes.label_of_class(session, row["class_id"])
    if label is None or label.archived:
        return None
    return {
        "class_name": label.name,
        "session_number": await repo.number_of(session, ref, row["class_id"]),
    }


# Late registrants and removed Students (Story 5.13, FR-7, FR-20, AD-2, AD-5, AD-8, AD-9).

_rng = secrets.SystemRandom()
"""Where a late registrant is seated: a random game with a free Seat, a random Role in it."""

AI_KINDS = frozenset({games_service.OccupantKind.LLM, games_service.OccupantKind.RULE_BASED})


def _students_of(game: games_service.ClassGame) -> list[uuid.UUID]:
    return [
        seat.user_id
        for seat in game.seats
        if seat.occupant_kind == games_service.OccupantKind.STUDENT and seat.user_id is not None
    ]


def _seated(games: list[games_service.ClassGame]) -> set[uuid.UUID]:
    return {student for game in games for student in _students_of(game)}


def _open_seats(game: games_service.ClassGame, *, locked: bool) -> list[str]:
    """The Roles a late registrant may take in the Class game: before the lock its free Seats,
    after it the Seats an AI player holds in a game that has its snapshot. Only `not_started`."""
    if game.lifecycle != games_service.Lifecycle.NOT_STARTED:
        return []
    if not locked:
        return [seat.role for seat in game.seats if seat.occupant_kind is None]
    if not game.has_snapshot:
        return []
    return [seat.role for seat in game.seats if seat.occupant_kind in AI_KINDS]


async def students_without_seat(class_session_id: uuid.UUID) -> list[uuid.UUID]:
    """The registered Students of the Class session's Class who hold no Seat in its Class games,
    sorted (Story 5.13): after the lock, those no not-started game could seat, for the make-up of
    Epic 13. Before an allocation is confirmed that is every registered Student."""
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, class_session_id)
        if row is None:
            return []
        seated = _seated(await games_service.class_games(s, class_session_id))
    registered = await classes.registered_students(row["class_id"])
    return sorted(student for student in registered if student not in seated)


async def _seating_candidates(
    now: datetime,
) -> list[tuple[Mapping[str, Any], list[games_service.ClassGame], set[uuid.UUID]]]:
    """Each confirmed Class session of a Class that is not archived where a Seat may still change
    hands: not locked, or locked with an opened game that has not started. With its Class games
    and its registered Students now."""
    async with get_sessionmaker().begin() as s:
        sessions = await repo.confirmed_sessions(s)
        unstarted = set(await games_service.class_sessions_with_unstarted_games(s))
    sessions = [r for r in sessions if not is_locked(r, now=now) or r["id"] in unstarted]
    # A few reads for every session at once, not a few per session: the sweep runs this each
    # minute on the one `worker-batch` slot that also sends the mail.
    writable = await classes.writable_class_ids(list({r["class_id"] for r in sessions}))
    sessions = [r for r in sessions if r["class_id"] in writable]
    async with get_sessionmaker().begin() as s:
        games = await games_service.class_games_of(s, [r["id"] for r in sessions])
    registered = await classes.registered_students_of(list({r["class_id"] for r in sessions}))
    return [
        (row, games.get(row["id"], []), registered.get(row["class_id"], set())) for row in sessions
    ]


async def late_registrants(now: datetime) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """The sweep's `sessions.seat_late_registrant` finder (AD-9): `(class_session_id, user_id)` of
    each registered Student without a Seat in a confirmed Class session that can still seat them:
    before the lock always (a free Seat or a new Class game), after it only while an opened game
    that has not started has a Seat an AI player holds."""
    due: list[tuple[uuid.UUID, uuid.UUID]] = []
    for row, games, registered in await _seating_candidates(now):
        locked = is_locked(row, now=now)
        if not locked and row["allocation_method"] == "student_choice":
            continue  # Story 5.17: they choose a Seat themselves until the lock draws one.
        if locked and not any(_open_seats(game, locked=True) for game in games):
            continue
        seated = _seated(games)
        due.extend((row["id"], student) for student in sorted(registered - seated))
    return due


async def removed_students(now: datetime) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """The sweep's `sessions.replace_removed_student` finder (AD-9): `(class_session_id, user_id)`
    of each Student no longer registered who holds a Seat in an opened Class game that has not
    started, in a locked Class session. Before the lock the open does it (Story 5.12)."""
    due: list[tuple[uuid.UUID, uuid.UUID]] = []
    for row, games, registered in await _seating_candidates(now):
        if row["locked_at"] is None:
            continue
        held = {
            student
            for game in games
            if game.has_snapshot and game.lifecycle == games_service.Lifecycle.NOT_STARTED
            for student in _students_of(game)
        }
        due.extend((row["id"], student) for student in sorted(held - registered))
    return due


def _item(item: object) -> tuple[uuid.UUID, uuid.UUID]:
    if not isinstance(item, tuple) or len(item) != 2:
        raise TypeError("a late-seating item is (class_session_id, user_id)")
    class_session_id, user_id = item
    if not isinstance(class_session_id, uuid.UUID) or not isinstance(user_id, uuid.UUID):
        raise TypeError("a late-seating item holds two ids")
    return class_session_id, user_id


async def seat_late_registrant_due(item: object, now: datetime) -> bool:
    """The sweep's `sessions.seat_late_registrant` action: one Student per transaction, ids
    only."""
    class_session_id, user_id = _item(item)
    return await seat_late_registrant(class_session_id, user_id, now=now)


async def replace_removed_student_due(item: object, now: datetime) -> bool:
    """The sweep's `sessions.replace_removed_student` action: one Student per transaction, ids
    only."""
    class_session_id, user_id = _item(item)
    return await replace_removed_student(class_session_id, user_id)


async def _tell_users(s: AsyncSession, students: set[uuid.UUID]) -> None:
    for student in sorted(students):
        await events.emit(s, "user", str(student))


async def seat_late_registrant(
    class_session_id: uuid.UUID, user_id: uuid.UUID, *, now: datetime | None = None
) -> bool:
    """Seat a Student who registered after the allocation was confirmed (Story 5.13, FR-20), in
    one transaction under the Class session's row lock.

    Before the lock: a random free Role of a random Class game with a free Seat, through
    `games.commands.assign_seat`; when every Seat is taken a new Class game (the next number, no
    settings) through `games.commands.create`, whose other Seats get AI players at the lock. After
    the lock: a random Seat an AI player holds in a random opened Class game that has not started,
    through `assign_seat` with `replace` (the AI player's row stays, AD-5). A game that started
    meanwhile refuses under its row lock and the next one is tried; with none left the Student
    stays without a Seat (`students_without_seat`).

    The draft gains the Seat under a new revision, the Student gets the allocation notice, they and
    the game's other Students get `user:<id>` and the staff `session:<id>`. Nothing (False) for a
    Student who is seated or not registered, an allocation that is not confirmed or an archived
    Class: the sweep may call it again at any time."""
    now = now or auth.utcnow()
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, class_session_id, lock=True)
        if row is None or not await classes.is_writable(row["class_id"], session=s):
            return False
        draft = await repo.draft_of(s, class_session_id)
        if draft is None or draft["confirmed_at"] is None:
            return False
        if user_id not in await classes.registered_students(row["class_id"]):
            return False
        if await games_service.student_seated(s, class_session_id, user_id):
            return False
        locked = is_locked(row, now=now)
        choosing = row["allocation_method"] == "student_choice"
        if choosing and not locked:
            return False  # Story 5.17: the Student chooses until the lock draws a Seat.
        games = await games_service.class_games(s, class_session_id)
        candidates = [game for game in games if _open_seats(game, locked=locked)]
        _rng.shuffle(candidates)
        placed: tuple[games_service.ClassGame | None, int, str] | None = None
        for game in candidates:
            role = _rng.choice(_open_seats(game, locked=locked))
            try:
                await games_commands.assign_seat(
                    str(game.id),
                    role,
                    games_service.OccupantKind.STUDENT,
                    user_id=user_id,
                    replace=locked,
                    within=s,
                )
            except games_commands.CommandError as refused:
                if refused.code != "game_already_started":
                    raise
                continue  # it started since it was read: its Seats are never given away
            placed = (game, game.number, role)
            break
        if placed is None:
            if locked:
                log.info(
                    "late_registrant_without_seat",
                    class_session_id=str(class_session_id),
                    user_id=str(user_id),
                )
                return False
            number = max((game.number for game in games), default=0) + 1
            role = _rng.choice([r.value for r in ROLES])
            game_id = await games_commands.create(
                games_service.Purpose.CLASS,
                class_session_id=class_session_id,
                game_number=number,
                within=s,
            )
            await games_commands.assign_seat(
                game_id, role, games_service.OccupantKind.STUDENT, user_id=user_id, within=s
            )
            placed = (None, number, role)
        game, number, role = placed
        assignments = [dict(a) for a in draft["assignments"] if a["user_id"] != str(user_id)]
        assignments.append(
            {
                "user_id": str(user_id),
                "game_number": number,
                "role": role,
                # With Student choice a Seat the Student did not choose is a drawn one (5.17).
                **({"drawn": True} if choosing else {}),
            }
        )
        assignments.sort(key=lambda a: (a["game_number"], SEAT_ORDER.index(Role(a["role"]))))
        revision = draft["revision"] + 1
        await repo.update_draft(s, class_session_id, assignments=assignments, revision=revision)
        await notify.enqueue(
            s,
            user_id,
            ALLOCATION_NOTICE,
            f"{ALLOCATION_NOTICE}:{draft['id']}:{revision}:{user_id}",
            ref=class_session_id,
        )
        await _tell_users(s, {user_id, *(_students_of(game) if game is not None else [])})
        await events.emit(s, "session", str(class_session_id))
    log.info(
        "late_registrant_seated",
        class_session_id=str(class_session_id),
        game_number=number,
        new_game=game is None,
        replaced_ai=locked,
    )
    return True


async def replace_removed_student(class_session_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Give each Seat a Student removed from the Roster holds in an opened Class game that has not
    started the AI player the session's AI mode gives (Story 5.13, FR-7): `llm` with a model
    config in the snapshot, else `rule_based`, reason `initial`, through
    `games.commands.assign_seat` with `replace` (the Student's row stays, AD-5), in one
    transaction under the Class session's row lock. A game that has started is left as it is (the
    Lecturer's Takeover, Epic 8). The removed Student and the game's other Students get
    `user:<id>`, the staff `session:<id>`. Nothing (False) before the lock, for a registered
    Student or an archived Class."""
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, class_session_id, lock=True)
        if row is None or row["locked_at"] is None:
            return False
        if not await classes.is_writable(row["class_id"], session=s):
            return False
        if user_id in await classes.registered_students(row["class_id"]):
            return False
        runtime = games_service.SessionRuntime.model_validate(row["snapshot"]["session_runtime"])
        ai = (
            games_service.OccupantKind.LLM
            if runtime.model_config_id is not None
            else games_service.OccupantKind.RULE_BASED
        )
        told: set[uuid.UUID] = set()
        replaced = 0
        for game in await games_service.class_games(s, class_session_id):
            if not game.has_snapshot or game.lifecycle != games_service.Lifecycle.NOT_STARTED:
                continue
            for seat in game.seats:
                if (
                    seat.occupant_kind != games_service.OccupantKind.STUDENT
                    or seat.user_id != user_id
                ):
                    continue
                try:
                    await games_commands.assign_seat(
                        str(game.id), seat.role, ai, replace=True, within=s
                    )
                except games_commands.CommandError as refused:
                    if refused.code != "game_already_started":
                        raise
                    continue
                replaced += 1
                told |= set(_students_of(game))
        if not replaced:
            return False
        await _tell_users(s, told)
        await events.emit(s, "session", str(class_session_id))
    log.info(
        "removed_student_replaced",
        class_session_id=str(class_session_id),
        ai_player=ai.value,
        seats=replaced,
    )
    return True


# Deadline reminders (Story 5.14, FR-18, FR-17, FR-72, AD-9, AD-14, AD-19).

DEADLINE_REMINDER_NOTICE = "deadline_reminder"
"""The notice kind each Student gets 24 hours before a Play, Debrief or Test deadline, `digest`
(Story 5.14, AD-9). Its `ref` is the `deadline_reminders` row."""

REMINDER_AHEAD = timedelta(hours=24)
"""How long before a deadline its reminder is enqueued."""


async def reminder_recipients(
    class_session_id: uuid.UUID, deadline: DeadlineName
) -> list[uuid.UUID]:
    """Who is reminded of `deadline` (Story 5.14): for now every registered Student of the
    Class session's Class, sorted. The one place the recipients are chosen; Epic 11 leaves out a
    Student with an extension and Epic 13 one who has done the step (`progress.has_step`)."""
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, class_session_id)
    if row is None:
        return []
    return sorted(await classes.registered_students(row["class_id"]))


async def due_deadline_reminders(now: datetime) -> list[tuple[uuid.UUID, DeadlineName]]:
    """The sweep's `sessions.send_deadline_reminder` finder (AD-9): `(class_session_id,
    deadline)` of each deadline at most 24 hours ahead with no reminder at its current time, in
    a Class that is not archived."""
    async with get_sessionmaker().begin() as s:
        rows = await repo.due_deadlines(s, now, now + REMINDER_AHEAD)
    due: list[tuple[uuid.UUID, DeadlineName]] = []
    writable: dict[uuid.UUID, bool] = {}
    for row in rows:
        if row["class_id"] not in writable:
            writable[row["class_id"]] = await classes.is_writable(row["class_id"])
        if writable[row["class_id"]]:
            due.append((row["id"], row["deadline"]))
    return due


async def send_deadline_reminder_due(item: object, now: datetime) -> bool:
    """The sweep's `sessions.send_deadline_reminder` action: one deadline per transaction, with
    the session id and the deadline's name only."""
    if not isinstance(item, tuple) or len(item) != 2:
        raise TypeError("a reminder item is (class_session_id, deadline)")
    class_session_id, deadline = item
    if not isinstance(class_session_id, uuid.UUID) or deadline not in DEADLINE_NAMES:
        raise TypeError("a reminder item holds a session id and a deadline name")
    return await send_deadline_reminder(class_session_id, deadline, now=now)


async def send_deadline_reminder(
    class_session_id: uuid.UUID, deadline: DeadlineName, *, now: datetime
) -> bool:
    """Remind the Students of `deadline` once per deadline time (Story 5.14, FR-18): under the
    Class session's row lock, when the deadline is set, has not passed and is at most 24 hours
    away, record the reminder and enqueue one `DEADLINE_REMINDER_NOTICE` per Student of
    `reminder_recipients`, keyed by session, deadline kind, deadline time and User. Returns False,
    changing nothing, when there is nothing to remind of now or it was reminded before."""
    if deadline not in DEADLINE_NAMES:
        raise ValueError(f"not a deadline: {deadline!r}")
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, class_session_id, lock=True)
        if row is None:
            return False
        at = row[deadline]
        if at is None or not now < at <= now + REMINDER_AHEAD:
            return False
        if not await classes.is_writable(row["class_id"], session=s):
            return False
        reminder_id = await repo.insert_reminder(
            s, class_session_id=class_session_id, deadline=deadline, deadline_at=at, now=now
        )
        if reminder_id is None:
            return False
        # Read once the reminder is recorded, so a Student registered until now is among them.
        recipients = await reminder_recipients(class_session_id, deadline)
        kind = DATE_KINDS[deadline]
        for user_id in recipients:
            key = f"{DEADLINE_REMINDER_NOTICE}:{class_session_id}:{kind}:{at.isoformat()}:{user_id}"
            await notify.enqueue(s, user_id, DEADLINE_REMINDER_NOTICE, key, ref=reminder_id)
    log.info(
        "deadline_reminder_sent",
        class_session_id=str(class_session_id),
        deadline=kind,
        students=len(recipients),
    )
    return True


async def deadline_reminder_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of a `DEADLINE_REMINDER_NOTICE`, for `messaging` at send time
    (Story 5.14, AD-9): the Class's name, the deadline (`play`, `debrief`, `test`), its time in
    Europe/Oslo and whether the session is obligatory. None, so the notice is left out, when the
    reminder or session is gone, the deadline has moved from the reminded time or passed, the
    Class is archived, or the User is no longer a registered Student of it."""
    if ref is None:
        return None
    reminder = await repo.reminder_row(session, ref)
    if reminder is None:
        return None
    row = await repo.session_row(session, reminder["class_session_id"])
    if row is None:
        return None
    at = row[reminder["deadline"]]
    if at is None or at != reminder["deadline_at"] or at <= now:
        return None
    label = await classes.label_of_class(session, row["class_id"])
    if label is None or label.archived:
        return None
    if user_id not in await classes.registered_students(row["class_id"]):
        return None
    return {
        "class_name": label.name,
        "deadline": DATE_KINDS[reminder["deadline"]],
        "at": at.astimezone(OSLO),
        "obligatory": row["obligatory"],
    }


# Student choice (Story 5.17, FR-21, AD-2, AD-4, AD-8, AD-9, AD-17, UX-DR62).

STUDENT_CHOICE_NOTICE = "student_choice_open"
"""The notice kind each registered Student gets once when they may choose a Class game and a
Seat, `digest` (Story 5.17, AD-9). Its mail reads the session at send time
(`student_choice_mail_context`)."""


def student_choice_enabled() -> bool:
    """`FEATURE_STUDENT_CHOICE` (AD-17): whether the Klasseøkt offers Student choice and the
    Students' «Velg spill og sete» route answers."""
    return get_settings().feature_student_choice


def _choice_key(class_session_id: uuid.UUID, user_id: uuid.UUID) -> str:
    return f"{STUDENT_CHOICE_NOTICE}:{class_session_id}:{user_id}"


async def _judge_method(
    s: AsyncSession, row: Mapping[str, Any], method: AllocationMethod, *, locked: bool
) -> None:
    """A changed allocation method (Story 5.17): `FeatureDisabled` for Student choice while
    `FEATURE_STUDENT_CHOICE` is off, `SessionLocked` once locked, and `AllocationConfirmed` once
    an allocation is confirmed, Student choice's own included (it is final once saved)."""
    if method == "student_choice" and not student_choice_enabled():
        raise FeatureDisabled({"allocation_method": "feature_disabled"})
    if locked:
        raise SessionLocked({"allocation_method": "locked"})
    draft = await repo.draft_of(s, row["id"])
    if draft is not None and draft["confirmed_at"] is not None:
        raise AllocationConfirmed({"allocation_method": "confirmed"})


async def _ensure_games(
    s: AsyncSession,
    class_session_id: uuid.UUID,
    games: list[games_service.ClassGame],
    registered: list[uuid.UUID],
) -> int:
    """Create empty Class games (no settings; the snapshot comes at the lock) through
    `games.commands.create` until there are four Seats for every Student who holds a Seat or is
    registered. Returns how many were created."""
    need = len(_seated(games) | set(registered))
    count = len(games)
    number = max((game.number for game in games), default=0)
    added = 0
    while count * len(ROLES) < need:
        number += 1
        count += 1
        added += 1
        await games_commands.create(
            games_service.Purpose.CLASS,
            class_session_id=class_session_id,
            game_number=number,
            within=s,
        )
    return added


async def _open_student_choice(
    s: AsyncSession,
    class_session_id: uuid.UUID,
    by: uuid.UUID,
    students: list[uuid.UUID],
    now: datetime,
) -> None:
    """Saving Student choice, in the save's transaction: a confirmed draft with no Seat replaces
    any preview (so the Lærerhjem, the lock and Story 5.13 see a confirmed allocation), empty Class
    games for every registered Student, and one `STUDENT_CHOICE_NOTICE` per Student, which emits
    `user:<id>`."""
    await repo.replace_draft(
        s,
        class_session_id,
        id=uuid.uuid7(),
        revision=1,
        seed=allocation.draw_seed(),
        assignments=[],
        drawn_by=by,
        drawn_at=now,
        confirmed_at=now,
        confirmed_by=by,
    )
    games = await _ensure_games(s, class_session_id, [], students)
    for student in students:
        await notify.enqueue(
            s,
            student,
            STUDENT_CHOICE_NOTICE,
            _choice_key(class_session_id, student),
            ref=class_session_id,
        )
    log.info(
        "student_choice_opened",
        class_session_id=str(class_session_id),
        games=games,
        students=len(students),
    )


def _drawn_seat(draft: Mapping[str, Any] | None, user_id: uuid.UUID) -> SeatRef | None:
    """The Seat the draw gave `user_id` (an assignment marked `drawn`), or None."""
    if draft is None:
        return None
    for a in draft["assignments"]:
        if a["user_id"] == str(user_id) and a.get("drawn"):
            return SeatRef(game_number=a["game_number"], role=Role(a["role"]))
    return None


async def _draw_at_lock(s: AsyncSession, row: Mapping[str, Any], now: datetime) -> int:
    """The lock of a Class session with Student choice, in its transaction: each registered
    Student without a Seat takes a random free Seat of a Class game that has not started, or of
    a new Class game when none is free, through `games.commands.assign_seat`; the draft gains
    each Seat marked `drawn` under one new revision, and each such Student gets the allocation
    notice (FR-21). The open then gives every other free Seat its AI player. Nothing for an
    archived Class. Returns how many Students were drawn."""
    draft = await repo.draft_of(s, row["id"])
    if draft is None or not await classes.is_writable(row["class_id"], session=s):
        return 0
    registered = await classes.registered_students(row["class_id"])
    games = await games_service.class_games(s, row["id"])
    seated = _seated(games)
    waiting = [student for student in registered if student not in seated]
    if not waiting:
        return 0
    # A Seat a Student chose and then left the Class with is free to the draw too: the open would
    # give it an AI player anyway (follow-up review of Story 5.17). It is taken with `replace`.
    kept = set(registered)
    left = {
        (str(game.id), seat.role): seat.user_id
        for game in games
        if game.lifecycle == games_service.Lifecycle.NOT_STARTED
        for seat in game.seats
        if seat.occupant_kind == games_service.OccupantKind.STUDENT
        and seat.user_id is not None
        and seat.user_id not in kept
    }
    free = [
        (str(game.id), game.number, role)
        for game in games
        for role in _open_seats(game, locked=False)
    ] + [
        (game_id, next(g.number for g in games if str(g.id) == game_id), role)
        for game_id, role in left
    ]
    _rng.shuffle(free)
    number = max((game.number for game in games), default=0)
    _rng.shuffle(waiting)
    assignments = [dict(a) for a in draft["assignments"]]
    for student in waiting:
        if not free:
            number += 1
            game_id = await games_commands.create(
                games_service.Purpose.CLASS,
                class_session_id=row["id"],
                game_number=number,
                within=s,
            )
            roles = [role.value for role in ROLES]
            _rng.shuffle(roles)
            free = [(game_id, number, role) for role in roles]
        game_id, game_number, role = free.pop()
        gone = left.get((game_id, role))
        await games_commands.assign_seat(
            game_id,
            role,
            games_service.OccupantKind.STUDENT,
            user_id=student,
            replace=gone is not None,
            within=s,
        )
        if gone is not None:
            assignments = [
                a
                for a in assignments
                if not (a["user_id"] == str(gone) and a["game_number"] == game_number)
            ]
        assignments.append(
            {"user_id": str(student), "game_number": game_number, "role": role, "drawn": True}
        )
    assignments.sort(key=lambda a: (a["game_number"], SEAT_ORDER.index(Role(a["role"]))))
    revision = draft["revision"] + 1
    await repo.update_draft(s, row["id"], assignments=assignments, revision=revision)
    for student in waiting:
        await notify.enqueue(
            s,
            student,
            ALLOCATION_NOTICE,
            f"{ALLOCATION_NOTICE}:{draft['id']}:{revision}:{student}",
            ref=row["id"],
        )
    log.info("student_choice_drawn", class_session_id=str(row["id"]), students=len(waiting))
    return len(waiting)


async def _choice_session(user: authz.Principal, session_id: uuid.UUID) -> Mapping[str, Any] | None:
    """The Class session whose «Velg spill og sete» `user` may open: `FEATURE_STUDENT_CHOICE` on,
    the session uses Student choice and the User is a registered Student of its Class. None
    otherwise, which the route answers as not found."""
    if not student_choice_enabled():
        return None
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, session_id)
    if row is None or row["allocation_method"] != "student_choice":
        return None
    if user.id not in await classes.registered_students(row["class_id"]):
        return None
    return row


async def _seat_choice_out(
    user_id: uuid.UUID, row: Mapping[str, Any], *, now: datetime
) -> SeatChoiceOut:
    async with get_sessionmaker().begin() as s:
        games = await games_service.class_games(s, row["id"])
        draft = await repo.draft_of(s, row["id"])
        number = await repo.number_of(s, row["id"], row["class_id"])
        label = await classes.label_of_class(s, row["class_id"])
    names = await classes.student_names(row["class_id"], sorted(_seated(games)))
    mine: SeatRef | None = None
    out: list[SeatChoiceGameOut] = []
    for game in games:
        by_role = {seat.role: seat for seat in game.seats}
        seats: list[SeatChoiceSeatOut] = []
        for role in SEAT_ORDER:
            seat = by_role.get(role.value)
            kind = seat.occupant_kind if seat is not None else None
            student = (
                seat.user_id
                if seat is not None and kind == games_service.OccupantKind.STUDENT
                else None
            )
            if student is not None and student == user_id:
                mine = SeatRef(game_number=game.number, role=role)
            seats.append(
                SeatChoiceSeatOut(
                    role=role,
                    holder="free" if kind is None else "ai" if student is None else "student",
                    name=names.get(student) if student is not None else None,
                    mine=student is not None and student == user_id,
                )
            )
        out.append(SeatChoiceGameOut(number=game.number, seats=seats))
    drawn = _drawn_seat(draft, user_id)
    return SeatChoiceOut(
        class_session_id=row["id"],
        class_name=label.name if label is not None else "",
        number=number,
        start_at=row["start_at"],
        open=not is_locked(row, now=now),
        my_seat=mine,
        drawn=drawn is not None and drawn == mine,
        games=out,
    )


async def seat_choice(
    user: authz.Principal, session_id: uuid.UUID, *, now: datetime
) -> SeatChoiceOut | None:
    """«Velg spill og sete» (Story 5.17, UX-DR62): the Class session's Class games, each Seat
    free, a Student's (named now) or, after the lock, an AI player's, and the reader's own Seat.
    None (not found) unless `_choice_session` lets the User open it."""
    row = await _choice_session(user, session_id)
    if row is None:
        return None
    return await _seat_choice_out(user.id, row, now=now)


async def take_seat(
    user: authz.Principal, session_id: uuid.UUID, wanted: SeatChoiceIn, *, now: datetime
) -> SeatChoiceOut | None:
    """«Ta setet Grossist i Spill 17» (Story 5.17, FR-21): under the Class session's row lock, in
    one transaction, the Student takes the free Seat through `games.commands.assign_seat`, or,
    holding a Seat already, moves to it through `games.commands.move_seat`; a Student holds one
    Seat per Class session. The draft mirrors the Seats under a new revision, every registered
    Student (who can still choose) gets `user:<id>` and the staff `session:<id>`. Their own Seat
    again changes nothing.

    Raises `SessionLocked` once locked, `InvalidSeat` for a game or Role the session does not
    have and `SeatTaken` when another occupant holds the Seat (a second press of the same free
    Seat waits on the row lock and gets this); nothing is committed then. Raises `ClassArchived`;
    None (not found) unless `_choice_session` lets the User open it."""
    row = await _choice_session(user, session_id)
    if row is None:
        return None
    registered = await classes.registered_students(row["class_id"])
    held: tuple[games_service.ClassGame, games_service.ClassGameSeat] | None = None
    unchanged = False
    try:
        async with get_sessionmaker().begin() as s:
            await _writable(s, row["class_id"])
            locked_row = await repo.session_row(s, session_id, lock=True)
            if locked_row is None:
                return None
            row = locked_row
            if is_locked(row, now=now):
                raise SessionLocked({"seat": "locked"})
            games = await games_service.class_games(s, session_id)
            game = next((g for g in games if g.number == wanted.game_number), None)
            target = (
                next((seat for seat in game.seats if seat.role == wanted.role), None)
                if game is not None
                else None
            )
            if game is None or target is None:
                raise InvalidSeat({"seat": "unknown"})
            held = next(
                (
                    (g, seat)
                    for g in games
                    for seat in g.seats
                    if seat.occupant_kind == games_service.OccupantKind.STUDENT
                    and seat.user_id == user.id
                ),
                None,
            )
            if held is not None and (held[0].number, held[1].role) == (game.number, target.role):
                unchanged = True
            else:
                unchanged = False
                if target.occupant_kind is not None:
                    raise SeatTaken({"seat": "taken"})
                try:
                    if held is None:
                        await games_commands.assign_seat(
                            str(game.id),
                            target.role,
                            games_service.OccupantKind.STUDENT,
                            user_id=user.id,
                            within=s,
                        )
                    else:
                        await games_commands.move_seat(
                            str(held[0].id), held[1].role, str(game.id), target.role, within=s
                        )
                except games_commands.CommandError as refused:
                    if refused.code in {"seat_occupied", "student_already_seated"}:
                        raise SeatTaken({"seat": "taken"}) from None
                    raise
                draft = await repo.draft_of(s, session_id)
                if draft is not None:
                    assignments = [
                        dict(a) for a in draft["assignments"] if a["user_id"] != str(user.id)
                    ]
                    assignments.append(
                        {"user_id": str(user.id), "game_number": game.number, "role": target.role}
                    )
                    assignments.sort(
                        key=lambda a: (a["game_number"], SEAT_ORDER.index(Role(a["role"])))
                    )
                    await repo.update_draft(
                        s, session_id, assignments=assignments, revision=draft["revision"] + 1
                    )
                await _tell_users(s, {*registered, user.id})
                await events.emit(s, "session", str(session_id))
    except (SessionLocked, InvalidSeat, SeatTaken) as refused:
        log.info("seat_choice_refused", class_session_id=str(session_id), error_code=refused.code)
        raise
    if not unchanged:
        log.info(
            "seat_chosen",
            class_session_id=str(session_id),
            game_number=wanted.game_number,
            moved=held is not None,
        )
    return await _seat_choice_out(user.id, row, now=now)


async def student_choice_offers(now: datetime) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """The sweep's `sessions.offer_student_choice` finder (AD-9): `(class_session_id, user_id)` of
    each registered Student of a Class session with Student choice, not locked and of a Class
    that is not archived, who has not had the `STUDENT_CHOICE_NOTICE` (a Student who registered
    after the save). Nothing while `FEATURE_STUDENT_CHOICE` is off: the lock draws them a Seat."""
    if not student_choice_enabled():
        return []
    async with get_sessionmaker().begin() as s:
        sessions = await repo.open_student_choice_sessions(s)
    sessions = [row for row in sessions if not is_locked(row, now=now)]
    writable = await classes.writable_class_ids(list({r["class_id"] for r in sessions}))
    sessions = [row for row in sessions if row["class_id"] in writable]
    registered = await classes.registered_students_of(list({r["class_id"] for r in sessions}))
    keys = {
        _choice_key(row["id"], student): (row["id"], student)
        for row in sessions
        for student in sorted(registered.get(row["class_id"], ()))
    }
    async with get_sessionmaker().begin() as s:
        used = await notify.used_keys(s, list(keys))
    return [item for key, item in keys.items() if key not in used]


async def offer_student_choice_due(item: object, now: datetime) -> bool:
    """The sweep's `sessions.offer_student_choice` action: one Student per transaction, ids
    only."""
    class_session_id, user_id = _item(item)
    return await offer_student_choice(class_session_id, user_id, now=now)


async def offer_student_choice(
    class_session_id: uuid.UUID, user_id: uuid.UUID, *, now: datetime | None = None
) -> bool:
    """A Student who registered after Student choice was saved (Story 5.17): under the Class
    session's row lock, more empty Class games when the registered and seated Students outnumber
    the Seats, and the `STUDENT_CHOICE_NOTICE`, once. New games tell every registered Student
    (`user:<id>`) and the staff (`session:<id>`). False when nothing was done: not Student choice,
    locked, archived, the Student not registered or told already."""
    now = now or auth.utcnow()
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, class_session_id, lock=True)
        if row is None or row["allocation_method"] != "student_choice":
            return False
        if is_locked(row, now=now) or not await classes.is_writable(row["class_id"], session=s):
            return False
        registered = await classes.registered_students(row["class_id"])
        if user_id not in registered:
            return False
        games = await games_service.class_games(s, class_session_id)
        added = await _ensure_games(s, class_session_id, games, registered)
        told = await notify.enqueue(
            s,
            user_id,
            STUDENT_CHOICE_NOTICE,
            _choice_key(class_session_id, user_id),
            ref=class_session_id,
        )
        if added:
            await _tell_users(s, set(registered))
            await events.emit(s, "session", str(class_session_id))
    if added or told:
        log.info(
            "student_choice_offered",
            class_session_id=str(class_session_id),
            games_added=added,
            told=told,
        )
    return bool(added or told)


async def student_choice_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of a `STUDENT_CHOICE_NOTICE`, for `messaging` at send time (Story
    5.17, AD-9): the Class's name and the Start date in Europe/Oslo (None while unset). None, so
    the notice is left out, when `FEATURE_STUDENT_CHOICE` is off (the route answers not found),
    the session is gone, no longer uses Student choice, is locked, the Class is archived or the
    User is no longer a registered Student of it."""
    if ref is None or not student_choice_enabled():
        return None
    row = await repo.session_row(session, ref)
    if row is None or row["allocation_method"] != "student_choice" or is_locked(row, now=now):
        return None
    label = await classes.label_of_class(session, row["class_id"])
    if label is None or label.archived:
        return None
    if user_id not in await classes.registered_students(row["class_id"]):
        return None
    start = row["start_at"]
    return {"class_name": label.name, "start_at": start.astimezone(OSLO) if start else None}


# Rerun (Story 5.18, FR-66, FR-78, AD-4, AD-6, AD-12, AD-17).

RERUN_DISABLED = {"rerun": "feature_disabled"}


def lecturer_test_enabled() -> bool:
    """`FEATURE_LECTURER_TEST_GAME` (AD-17): whether a Lecturer may play a test Game (6.20)."""
    return get_settings().feature_lecturer_test_game


class TestGameRefused(Exception):
    """«Start testspill» refused (Story 6.20): 404 `not_found` while the flag is off; 409
    `session_locked` from the Start date, `test_game_running` while the Lecturer's last test Game
    here has not finished, `llm_unavailable` when its LLM players' provider may not answer; 422
    `unknown_role` for a Role the session's settings have no Seat for."""

    def __init__(self, code: str, status: int) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


async def start_test_game(
    user: authz.Principal, session_id: uuid.UUID, role: str
) -> uuid.UUID | None:
    """«Start testspill» (Story 6.20, FR-87, AD-4, AD-13): a `lecturer_test` Game on the Class
    session's current settings, snapshotted now by `build_snapshot` (so its demand series, seed,
    `rules_version` and `SessionRuntime` are the session's as they stand), with the Lecturer in
    the `role` Seat as a `student` occupant and AI players of the session's AI mode in the others;
    then started. Created and seated in one transaction under the session's row lock, so two
    presses make one Game, and started in the next; a test Game whose start failed after that
    commit is started by the next press instead of blocking it. The session row itself is never
    written, so its settings stay editable. None when the User may not manage the session (the
    route's 403). Returns the Game id."""
    if not lecturer_test_enabled():
        raise TestGameRefused("not_found", 404)
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, session_id)
    if row is None or await _class_for(user, row["class_id"], "class_sessions.manage") is None:
        return None
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, session_id, lock=True)
        if row is None:
            return None
        if is_locked(row):
            raise TestGameRefused("session_locked", 409)
        earlier = await games_service.staff_test_games(s, session_id, user.id)
        unstarted = (
            str(earlier[0].id)
            if earlier and earlier[0].lifecycle == games_service.Lifecycle.NOT_STARTED
            else None
        )
        if (
            earlier
            and unstarted is None
            and earlier[0].lifecycle != games_service.Lifecycle.FINISHED
        ):
            raise TestGameRefused("test_game_running", 409)
        # A test Game whose start failed after its commit is started now, never made twice.
        game_id = unstarted
        if game_id is None:
            if row["ai_mode"] == AiMode.llm.value:
                found = (
                    await config.get(row["model_config_id"], session=s)
                    if row["model_config_id"] is not None
                    else None
                )
                if found is None or not config.may_answer(found):
                    raise TestGameRefused("llm_unavailable", 409)
            snapshot = await build_snapshot(row, session=s)
            ai = (
                games_service.OccupantKind.LLM
                if snapshot["session_runtime"]["model_config_id"] is not None
                else games_service.OccupantKind.RULE_BASED
            )
            roles = GameSettings.model_validate(snapshot["settings"]).roles
            if role not in {seat_role.value for seat_role in roles}:
                raise TestGameRefused("unknown_role", 422)
            game_id = await games_commands.create(
                "lecturer_test", snapshot=snapshot, class_session_id=session_id, within=s
            )
            for seat_role in roles:
                if seat_role.value == role:
                    await games_commands.assign_seat(
                        game_id, seat_role, "student", user_id=user.id, within=s
                    )
                else:
                    await games_commands.assign_seat(game_id, seat_role, ai.value, within=s)
    try:
        await games_commands.start(game_id)
    except games_commands.CommandError as refused:
        # Two presses on a Game whose start failed: the other one started it.
        if refused.code != "game_already_started":
            raise
    log.info("test_game_started", game_id=game_id, class_session_id=str(session_id))
    return uuid.UUID(game_id)


def rerun_enabled() -> bool:
    """`FEATURE_RERUN` (AD-17): whether a Class session may be made from an earlier one."""
    return get_settings().feature_rerun


async def copy_sources(user: authz.Principal, class_id: uuid.UUID) -> CopySourceListOut | None:
    """The Class sessions `user` may copy into the Class: every session of every Class they are
    staff of (`authz.classes_visible_to`), archived Classes included, newest first. Raises
    `FeatureDisabled` while `FEATURE_RERUN` is off; None when the User may not manage the Class."""
    if not rerun_enabled():
        raise FeatureDisabled(dict(RERUN_DISABLED))
    if await _class_for(user, class_id, "class_sessions.manage") is None:
        return None
    visible = {item.id: item for item in (await classes.list_classes(user)).items}
    async with get_sessionmaker().begin() as s:
        rows = await repo.copy_sources(s, user, list(visible))
    return CopySourceListOut(
        items=[
            CopySourceOut(
                id=row["id"],
                class_id=row["class_id"],
                class_name=visible[row["class_id"]].name,
                number=row["number"],
                start_at=row["start_at"],
                archived=visible[row["class_id"]].archived,
            )
            for row in rows
        ]
    )


def _copied_settings(source: Mapping[str, Any], *, keep_seed: bool) -> GameSettings:
    """The source's editable `GameSettings` (never its locked snapshot, AD-4) with a fresh demand
    seed unless `keep_seed`; a capacity or a view whose flag is off now is left out. The engine
    judges the result again and `InvalidSettings` is raised when it refuses it (FR-12)."""
    stored = GameSettings.model_validate(source["game_settings"])
    update: dict[str, Any] = {}
    if not keep_seed:
        update["demand_seed"] = new_seed(secrets.token_bytes(16))
    if not capacity_enabled():
        update["capacity"] = None
    if not info_visibility_enabled():
        update["info_visibility"] = GameSettings().info_visibility
    copied = stored.model_copy(update=update)
    errors = validate(
        copied,
        capacity_enabled=capacity_enabled(),
        info_visibility_enabled=info_visibility_enabled(),
    )
    if errors:
        raise InvalidSettings(
            {e.field: _problem(e.code, e.field, e.minimum, e.maximum) for e in errors}
        )
    return copied


async def copy_from(
    user: authz.Principal,
    source_id: uuid.UUID,
    target_class_id: uuid.UUID,
    *,
    now: datetime,
    keep_seed: bool = False,
) -> ClassSessionOut | None:
    """A new Class session in `target_class_id` made from an earlier one (FR-66), in one
    transaction as «Lag Klasseøkt»: the source's Game settings (`_copied_settings`), AI mode,
    Debrief mode and Inactivity limit; the active default model config with its budget row, never
    the source's (AD-6). With LLM players the source's Effort level is kept when that config
    offers it, else the config's default is taken and the source's level is stored as
    `effort_level_replaced` (FR-78); with no active default the copy gets Rule-based players, as
    «Lag Klasseøkt» does. Dates, Lab hours, the Roster, the allocation and the obligatory mark
    with its share are not copied. Raises `FeatureDisabled` while `FEATURE_RERUN` is off,
    `InvalidSettings`, `ClassArchived`; None when the User may not manage the target Class or may
    not read the source. It copies the settings of Epic 5 only; the later stories that own more
    session settings (FR-66) add theirs here."""
    if not rerun_enabled():
        raise FeatureDisabled(dict(RERUN_DISABLED))
    if await _class_for(user, target_class_id, "class_sessions.manage") is None:
        return None
    async with get_sessionmaker().begin() as s:
        source = await repo.session_row(s, source_id)
    if source is None or await _class_for(user, source["class_id"], "class_sessions.read") is None:
        return None
    session_id = uuid.uuid7()
    replaced: str | None = None
    async with get_sessionmaker().begin() as s:
        await _writable(s, target_class_id)
        # Read again in this transaction, under a share lock: the copy is of the settings as they
        # stand now, and a source gone meanwhile gives the same answer as one never there.
        source = await repo.session_row(s, source_id, share=True)
        if source is None:
            return None
        try:
            settings = _copied_settings(source, keep_seed=keep_seed)
        except InvalidSettings as refused:
            log.info(
                "class_session_copy_refused",
                source_id=str(source_id),
                error_code=refused.code,
                fields=sorted(refused.problems),
            )
            raise
        default = await config.active_default(session=s)
        offered = await config.offered_effort_levels(default.id, session=s) if default else []
        llm = source["ai_mode"] == AiMode.llm.value and default is not None
        level: str | None = None
        if llm:
            wanted = source["effort_level"]
            if wanted is not None and wanted in {o.name for o in offered}:
                level = wanted
            else:
                # `active_default` only returns a config that offers a level.
                level = offered[0].name if offered else None
                replaced = wanted
        await repo.insert_session(
            s,
            id=session_id,
            class_id=target_class_id,
            game_settings=settings.model_dump(mode="json"),
            ai_mode=(AiMode.llm if llm else AiMode.rule_based).value,
            debrief_mode=source["debrief_mode"],
            inactivity_limit_hours=source["inactivity_limit_hours"],
            obligatory=DEFAULT_OBLIGATORY,
            required_share_percent=get_settings().completion_default_share_percent,
            model_config_id=default.id if default else None,
            effort_level=level,
            created_by=user.id,
            created_at=now,
            copied_from=source_id,
            effort_level_replaced=replaced,
        )
        if default is not None:
            await budget.set_budget(budget.BudgetScope.class_session(session_id), session=s)
        await events.emit(s, "session", str(session_id))
    log.info(
        "class_session_copied",
        class_session_id=str(session_id),
        source_id=str(source_id),
        class_id=str(target_class_id),
        model_config_id=str(default.id) if default else None,
        seed_kept=keep_seed,
        effort_level_replaced=replaced is not None,
    )
    return await get_session(user, session_id)


async def _copy_notes(
    user: authz.Principal, row: Mapping[str, Any]
) -> tuple[CopiedFromOut | None, ReplacedLevelOut | None]:
    """What the Klasseøkt says of a copy: its source, when the User may still read it, and the
    source's Effort level the new config did not offer, with the source config's label."""
    source_id = row["copied_from"]
    replaced_name = row["effort_level_replaced"]
    if source_id is None and replaced_name is None:
        return None, None
    source = None
    number = 0
    if source_id is not None:
        async with get_sessionmaker().begin() as s:
            source = await repo.session_row(s, source_id)
            if source is not None:
                number = await repo.number_of(s, source_id, source["class_id"])
    copied = None
    if source is not None:
        found = await _class_for(user, source["class_id"], "class_sessions.read")
        if found is not None:
            copied = CopiedFromOut(id=source_id, class_name=found.name, number=number)
    replaced = None
    if replaced_name is not None:
        label = None
        if source is not None and source["model_config_id"] is not None:
            old = await config.get(source["model_config_id"])
            spec = old.effort_level(replaced_name) if old else None
            label = spec.label if spec else None
        replaced = ReplacedLevelOut(name=replaced_name, label=label)
    return copied, replaced
