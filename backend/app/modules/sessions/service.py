"""Class sessions (Stories 5.1 to 5.4, FR-11, FR-12, FR-13, FR-15, FR-18, AD-4, AD-6). Other
modules import only this file.

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
from typing import Any

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
from app.modules.sessions import repo
from app.modules.sessions.models import DATE_NAMES
from app.modules.sessions.schemas import (
    AiMode,
    ClassSessionListItem,
    ClassSessionListOut,
    ClassSessionOut,
    DateKind,
    DateName,
    DatesIn,
    DebriefMode,
    DemandSeriesOut,
    EnrolledSessionListOut,
    EnrolledSessionOut,
    LecturerOverviewOut,
    LlmUnavailable,
    NextDate,
    NextDeadline,
    SessionRef,
    SettingProblem,
    SettingsCheckOut,
    SettingWarning,
    WaitingClass,
)
from app.platform import auth, authz, events
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

log = structlog.get_logger(__name__)

DEFAULT_DEBRIEF_MODE = DebriefMode.group
DEFAULT_INACTIVITY_LIMIT_HOURS = 24
DEFAULT_OBLIGATORY = False
NO_DEFAULT_MODEL: LlmUnavailable = "no_default_model"

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


class InvalidDates(_FieldsError):
    """The dates break a rule (422 `invalid_dates`): `fields` maps each date in question to
    `past`, `order` (not after an earlier date), `before` (not before a later date that did not
    change) or `required`."""

    code = "invalid_dates"


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
        await repo.insert_session(
            s,
            id=session_id,
            class_id=class_id,
            game_settings=settings.model_dump(mode="json"),
            ai_mode=(AiMode.llm if default else AiMode.rule_based).value,
            debrief_mode=DEFAULT_DEBRIEF_MODE.value,
            inactivity_limit_hours=DEFAULT_INACTIVITY_LIMIT_HOURS,
            obligatory=DEFAULT_OBLIGATORY,
            model_config_id=default.id if default else None,
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


async def get_session(user: authz.Principal, session_id: uuid.UUID) -> ClassSessionOut | None:
    """The Class session, or None when the User may not read its Class (or it does not exist)."""
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, session_id)
        number = await repo.number_of(s, session_id, row["class_id"]) if row else 0
    if row is None:
        return None
    found = await _class_for(user, row["class_id"], "class_sessions.read")
    if found is None:
        return None
    unavailable = None
    if row["model_config_id"] is None and await config.active_default() is None:
        unavailable = NO_DEFAULT_MODEL
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
        llm_unavailable=unavailable,
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
    dates: DatesIn | None = None,
    game_settings: Mapping[str, Any] | None = None,
) -> ClassSessionOut | None:
    """«Lagre Klasseøkt»: saves the Class session as it stands and emits `session:<id>`. LLM
    players on a Class session with no model config take the active default and its budget row
    in the same transaction, or raise `LlmUnavailableError` and change nothing. With
    `game_settings` the draft is judged by `judge_settings` and stored, or `InvalidSettings` is
    raised. With `dates` the four dates are replaced under the rules of `judge_dates`; a change
    emits `user:<id>` once per registered Student of the Class. Once locked, a changed AI mode or
    changed Game settings raise `SessionLocked`. None when the User may not manage the Class;
    raises `ClassArchived`."""
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, session_id)
    if row is None or await _class_for(user, row["class_id"], "class_sessions.manage") is None:
        return None
    students = await classes.registered_students(row["class_id"]) if dates is not None else []
    async with get_sessionmaker().begin() as s:
        await _writable(s, row["class_id"])
        row = await repo.session_row(s, session_id, lock=True)
        if row is None:
            return None
        locked = is_locked(row, now=now)
        changed: dict[str, datetime | None] = {}
        new_settings: GameSettings | None = None
        try:
            if locked and ai_mode.value != row["ai_mode"]:
                raise SessionLocked({"ai_mode": "locked"})
            if game_settings is not None:
                new_settings = _settings_to_store(row, game_settings, locked=locked)
            if dates is not None:
                changed = judge_dates(row, dates, now=now, locked=locked)
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
        config_id = row["model_config_id"]
        if ai_mode is AiMode.llm and config_id is None:
            default = await config.active_default(session=s)
            if default is None:
                log.info(
                    "class_session_refused",
                    class_session_id=str(session_id),
                    error_code="llm_unavailable",
                )
                raise LlmUnavailableError
            config_id = default.id
            await budget.set_budget(budget.BudgetScope.class_session(session_id), session=s)
        await repo.save(
            s,
            session_id,
            now=now,
            ai_mode=ai_mode.value,
            model_config_id=config_id,
            dates=changed,
            game_settings=new_settings.model_dump(mode="json") if new_settings else None,
        )
        await events.emit(s, "session", str(session_id))
        if changed:
            for student in students:
                await events.emit(s, "user", str(student))
    log.info(
        "class_session_saved",
        class_session_id=str(session_id),
        dates=sorted(changed),
        settings_changed=new_settings is not None,
    )
    if changed and locked:
        # After the start a moved deadline holds for the whole Class session (FR-18).
        log.info(
            "class_session_dates_moved", class_session_id=str(session_id), dates=sorted(changed)
        )
    return await get_session(user, session_id)


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
    """The Class sessions of the Classes `user` is a Student in (FR-18, AD-3, AD-12): the dates,
    the User's own deadlines and the next one that applies. Never the Game settings, the number
    of Weeks or the demand. What Epic 6's Hjem shows as «Neste frist»."""
    names = {item.id: item.name for item in (await classes.enrolled_classes(user)).items}
    async with get_sessionmaker().begin() as s:
        rows = await repo.enrolled_sessions(s, user)
    now = auth.utcnow()
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
