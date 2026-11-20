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

Every mutation passes one guard, `_writable`, which asks `classes.service.is_writable` inside the
mutation's transaction and raises `classes.service.ClassArchived` (409 `class_archived`) for an
archived Class. Who may do what is `platform/authz`'s: `class_sessions.read`,
`class_sessions.manage` (held to the User's staff role in the Class) and
`class_sessions.read_enrolled` (held to `authz.classes_enrolled_by`).
"""

import secrets
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import structlog
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import budget, config
from app.engine import GameSettings
from app.engine.demand import DemandFixed, DemandRandom, DemandStep, DemandStepNoise, new_seed
from app.engine.settings import (
    DEMAND_RANGES,
    RANGES,
    Range,
    demand_series,
    validate,
    warnings,
)
from app.modules.classes import service as classes
from app.modules.players import service as players
from app.modules.sessions import repo
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
    """The one predicate of the Start-date lock points (FR-18): true once the Start date has
    passed. Settings then answer `session_locked`; deadlines that have not passed still move.
    Story 5.11 adds `locked_at` here."""
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
    staff of and that are not archived: per Class the sessions that still lack a date, and the
    next date across all of them. Empty when there is no Class session."""
    active = [item for item in (await classes.list_classes(user)).items if not item.archived]
    if not active:
        return LecturerOverviewOut(waiting=[], next_date=None)
    names = {item.id: item.name for item in active}
    async with get_sessionmaker().begin() as s:
        rows = await repo.staff_sessions(s, user, list(names))
    now = auth.utcnow()
    waiting: dict[uuid.UUID, list[SessionRef]] = {}
    upcoming: list[tuple[datetime, int, Mapping[str, Any]]] = []
    for row in rows:
        if any(row[name] is None for name in DATE_NAMES):
            waiting.setdefault(row["class_id"], []).append(
                SessionRef(id=row["id"], number=row["number"])
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
