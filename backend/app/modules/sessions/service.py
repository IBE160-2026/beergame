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
owners and the Admins are told once, and the next sweep tries again.

Every mutation passes one guard, `_writable`, which asks `classes.service.is_writable` inside the
mutation's transaction and raises `classes.service.ClassArchived` (409 `class_archived`) for an
archived Class. Who may do what is `platform/authz`'s: `class_sessions.read`,
`class_sessions.manage` (held to the User's staff role in the Class) and
`class_sessions.read_enrolled` (held to `authz.classes_enrolled_by`).
"""

import secrets
import uuid
from collections.abc import Awaitable, Callable, Mapping
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
from app.modules.games import commands as games_commands
from app.modules.games import service as games_service
from app.modules.identity import service as identity
from app.modules.players import service as players
from app.modules.sessions import allocation, repo
from app.modules.sessions.models import (
    DATE_NAMES,
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
    AllocationMoveIn,
    AllocationOut,
    AllocationSeatOut,
    ClassSessionListItem,
    ClassSessionListOut,
    ClassSessionOut,
    DateKind,
    DateName,
    DatesIn,
    DebriefMode,
    DemandSeriesOut,
    EnrolledLabHourOut,
    EnrolledSessionListOut,
    EnrolledSessionOut,
    LabHourIn,
    LabHourOut,
    LecturerOverviewOut,
    LlmUnavailable,
    NextDate,
    NextDeadline,
    OfferedEffortLevelOut,
    SessionRef,
    SettingProblem,
    SettingsCheckOut,
    SettingWarning,
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
    if out_of_range:
        code = "out_of_range"
    else:
        code = "not_a_number" if range_of(field) is not None else "invalid"
    return field, _problem(code, field, ranged=True)


EDITABLE_SETTINGS = frozenset({*RANGES, "demand", "demand_seed"})
"""The Game settings a Lecturer changes through the Klasseøkt: those the engine gives a range
(Story 5.3), and the Demand pattern with its seed (Story 5.4). Story 5.15 adds capacity."""


def judge_settings(
    stored: GameSettings, draft: Mapping[str, Any]
) -> tuple[GameSettings | None, dict[str, SettingProblem], list[SettingWarning]]:
    """`draft` laid over `stored` and judged by the engine alone (FR-12, AD-1): the settings (None
    when they do not even parse), the errors by setting, and the warnings on settings without an
    error. A value of the wrong type is `not_a_number` and a negative one `out_of_range`, both
    with the setting's range, as the engine's own range errors. The other settings of a draft
    that does not parse are still judged, with the unreadable ones at their stored values, so
    one mistyped field hides no error or warning elsewhere. A key outside `EDITABLE_SETTINGS`
    (the chain, capacity until Story 5.15) is `not_editable` and never laid over."""
    base = stored.model_dump(mode="json")
    problems: dict[str, SettingProblem] = {
        key: _problem("not_editable", key) for key in draft if key not in EDITABLE_SETTINGS
    }
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
    for found in validate(judged, capacity_enabled=get_settings().feature_capacity):
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
    return ClassSessionOut(
        id=row["id"],
        class_id=row["class_id"],
        class_name=found.name,
        number=number,
        game_settings=settings,
        is_classic=is_classic(settings),
        ai_mode=AiMode(row["ai_mode"]),
        debrief_mode=DebriefMode(row["debrief_mode"]),
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
        passed_dates=_passed(row, now),
        play_time_warning=_play_time_warning(row, settings),
        settings_warnings=[
            SettingWarning(code=w.code, field=w.field, values=w.values) for w in warnings(settings)
        ],
        calibrated_settings=GameSettings(),
        lab_hours=[_lab_hour_out(lab, now) for lab in labs],
    )


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
        ]
    )


async def save_session(
    user: authz.Principal,
    session_id: uuid.UUID,
    ai_mode: AiMode,
    *,
    now: datetime,
    effort_level: str | None = None,
    debrief_mode: DebriefMode | None = None,
    dates: DatesIn | None = None,
    game_settings: Mapping[str, Any] | None = None,
    obligatory: bool | None = None,
    required_share_percent: int | None = None,
    inactivity_limit_hours: int | None = None,
) -> ClassSessionOut | None:
    """«Lagre Klasseøkt»: saves the Class session as it stands and emits `session:<id>`. LLM
    players on a Class session with no model config take the active default and its budget row
    in the same transaction, or raise `LlmUnavailableError` and change nothing. With LLM players
    the Effort level is `effort_level`, else the one in force, else the config's default; a
    changed level the config does not offer raises `InvalidEffortLevel`. With Rule-based players
    no level is in force. `debrief_mode` None keeps the stored one. With `game_settings` the
    draft is judged by `judge_settings` and stored, or `InvalidSettings` is raised. With `dates`
    the four dates are replaced under the rules of `judge_dates`; a change emits `user:<id>`
    once per registered Student of the Class. `obligatory`, `required_share_percent` and
    `inactivity_limit_hours` (Story 5.7), None, keep their values; a changed share outside 1 to
    100 or limit under 20 raises `InvalidSessionValues`, and switching the mark on enqueues one
    `OBLIGATORY_NOTICE` per registered Student. Once locked, a changed AI mode, Effort level,
    Debrief mode, Game settings, obligatory mark, share or Inactivity limit raise
    `SessionLocked`. None when the User may not manage the Class; raises `ClassArchived`."""
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, session_id)
    if row is None or await _class_for(user, row["class_id"], "class_sessions.manage") is None:
        return None
    needs_students = dates is not None or obligatory is True
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
        try:
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
            dates=changed,
            game_settings=new_settings.model_dump(mode="json") if new_settings else None,
            obligatory=marked,
            required_share_percent=share,
            inactivity_limit_hours=limit,
        )
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
    `SessionLocked` for a change once locked and `InvalidSettings` for a draft the engine
    refuses. An unchanged draft is never judged, so a locked session can be saved as it stands."""
    stored = GameSettings.model_validate(row["game_settings"])
    settings, problems, _ = judge_settings(stored, draft)
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
    shows as «Neste frist» and «Labtimer»."""
    names = {item.id: item.name for item in (await classes.enrolled_classes(user)).items}
    now = auth.utcnow()
    async with get_sessionmaker().begin() as s:
        rows = await repo.enrolled_sessions(s, user)
        labs = await repo.lab_hours_of(s, [row["id"] for row in rows], ending_after=now)
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
            )
            for row in rows
            if row["class_id"] in names
        ]
    )


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


# The allocation draft (Story 5.8, FR-20, AD-12, AD-14).

SEAT_ORDER: tuple[Role, ...] = tuple(reversed(ROLES))
"""The Seats of a Class game as the preview lists them: Fabrikk first, Detaljist last."""


async def _allocation_out(class_id: uuid.UUID, draft: Mapping[str, Any] | None) -> AllocationOut:
    """The block's state: the registered Students now, and the stored draft with its names."""
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


async def allocation_of(user: authz.Principal, session_id: uuid.UUID) -> AllocationOut | None:
    """The «Fordeling» block as stored, for the Class's staff (Assistant lecturers too). None
    when the User may not read the Class."""
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, session_id)
        draft = await repo.draft_of(s, session_id) if row else None
    if row is None or await _class_for(user, row["class_id"], "class_sessions.read") is None:
        return None
    return await _allocation_out(row["class_id"], draft)


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
    return await _allocation_out(row["class_id"], draft)


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
    return await _allocation_out(row["class_id"], draft)


def _confirm_refused(session_id: uuid.UUID, code: str) -> None:
    log.info("allocation_confirm_refused", class_session_id=str(session_id), error_code=code)


async def _commit_allocation(
    s: AsyncSession,
    session_id: uuid.UUID,
    draft: Mapping[str, Any],
    confirmed_by: uuid.UUID,
    now: datetime,
) -> None:
    """The Games, Seats, mark, notices and event of a confirmation, in the caller's transaction."""
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
    except (SessionLocked, AllocationChanged, InvalidMove, SeatCommandRefused) as refused:
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
    return await _allocation_out(row["class_id"], draft)


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


async def lock(class_session_id: uuid.UUID, *, now: datetime | None = None) -> bool:
    """Lock the Class session now, whatever its Start date (the sweep at the Start date, Epic 8
    when the Lecturer starts early): in one transaction under the session's row lock, set
    `locked_at`, store `build_snapshot`, mark the model config referenced (LLM players) and emit
    `session:<id>`. True when this call locked it; False when it was locked already or does not
    exist. With LLM players whose provider may not answer here it raises `ProviderKeyMissing`
    and stores nothing; it never falls back to Rule-based players (AD-17)."""
    now = now or auth.utcnow()
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, class_session_id, lock=True)
        if row is None or row["locked_at"] is not None:
            return False
        llm = row["ai_mode"] == AiMode.llm.value
        if llm:
            found = await config.get(row["model_config_id"], session=s)
            if found is None or not config.may_answer(found):
                raise ProviderKeyMissing
        snapshot = await build_snapshot(row, session=s)
        if llm:
            await config.mark_referenced(row["model_config_id"], session=s)
        await repo.set_locked(s, class_session_id, locked_at=now, snapshot=snapshot)
        await events.emit(s, "session", str(class_session_id))
    log.info(
        "class_session_locked",
        class_session_id=str(class_session_id),
        ai_mode=row["ai_mode"],
        model_config_id=str(row["model_config_id"]) if llm else None,
        pins=sorted(snapshot["session_runtime"]["pins"] or {}),
    )
    return True


async def due_locks(now: datetime) -> list[uuid.UUID]:
    """The sweep's `sessions.lock` finder (AD-9): the Class sessions whose Start date has passed
    and that are not locked, by id."""
    async with get_sessionmaker().begin() as s:
        return await repo.due_locks(s, now)


async def lock_due(class_session_id: object, now: datetime) -> bool:
    """The sweep's `sessions.lock` action, one Class session per transaction with its id only
    (AD-9). A refusal for a missing provider key tells each owner of the Class and each Admin
    once, and the next minute's sweep tries again."""
    assert isinstance(class_session_id, uuid.UUID)
    try:
        return await lock(class_session_id, now=now)
    except ProviderKeyMissing:
        told = await _tell_lock_refused(class_session_id)
        log.warning(
            "class_session_lock_refused",
            class_session_id=str(class_session_id),
            error_code=ProviderKeyMissing.code,
            told=told,
        )
        return False


async def _tell_lock_refused(class_session_id: uuid.UUID) -> int:
    """One `LOCK_REFUSED_NOTICE` per owner of the Class and per active Admin, keyed by the session
    and the User, so each is told once. None for a Class that is archived. Returns how many
    notices were stored now."""
    told = 0
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, class_session_id)
        if row is None or not await classes.is_writable(row["class_id"], session=s):
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
