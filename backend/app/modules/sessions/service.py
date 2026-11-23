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

At the Play deadline the sweep's `sessions.playout` (Story 8.14) hands each unfinished Game of
the Class session to `games.commands.playout`, one Game per transaction, which reads the Play
deadline again (`_play_deadline_of`) so an extension made before it holds.

Every mutation passes one guard, `_writable`, which asks `classes.service.is_writable` inside the
mutation's transaction and raises `classes.service.ClassArchived` (409 `class_archived`) for an
archived Class. Who may do what is `platform/authz`'s: `class_sessions.read`,
`class_sessions.manage` (held to the User's staff role in the Class) and
`class_sessions.read_enrolled` (held to `authz.classes_enrolled_by`).
"""

import secrets
import uuid
from collections.abc import Awaitable, Callable, Collection, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import structlog
from pydantic import ValidationError
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import budget, calls, config
from app.analysis.completion import CompletionStatus
from app.analysis.letter import judge_thresholds
from app.engine import (
    RULES_VERSION,
    GameSettings,
    ReplayFixed,
    ReplayRandom,
    ReplayStep,
    ReplayTemplate,
    default_replay_template,
    validate_template,
)
from app.engine.demand import DemandFixed, DemandRandom, DemandStep, DemandStepNoise, new_seed
from app.engine.scenario import RANGED_FIELDS, Ranged
from app.engine.settings import (
    CAPACITY_RANGE,
    DEMAND_RANGES,
    RANGES,
    ROLES,
    InfoVisibility,
    Range,
    Role,
    demand_series,
    validate,
    warnings,
)
from app.modules.assessment import service as assessment
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
    AdjustmentOut,
    AiAssessmentOut,
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
    InRoomOut,
    LabHourIn,
    LabHourOut,
    LecturerOverviewOut,
    LetterSettingOut,
    LetterThresholdsOut,
    LlmUnavailable,
    NextDate,
    NextDeadline,
    OfferedEffortLevelOut,
    OwnAdjustmentOut,
    PauseOut,
    PlayOut,
    PlayTurnOut,
    ProposalPersonOut,
    ReplacedLevelOut,
    ReplayGameOut,
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
    StudentDeadlinesOut,
    StudentGameOut,
    StudentReplayOut,
    TableSeatOut,
    TableStatusOut,
    TestGameRefOut,
    TestSittingIn,
    TestSittingOut,
    TimeProposalOut,
    WaitingClass,
    WaitingReason,
)
from app.platform import audit, auth, authz, events, notify, retention
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker, reading

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


class ConsentMissing(_FieldsError):
    """A Control test's allocation while registered test students have not consented (409
    `consent_missing`, Story 12.8): `{"allocation": "consent_missing", "missing": "<N>"}`, or
    `{"seat": "consent_missing", "missing": "1"}` for the Student's own «Ta setet»."""

    code = "consent_missing"


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


class AiAssessmentPinned(_FieldsError):
    """The «KI-vurdering» switch was changed once the original Test deadline has passed or the
    Test-deadline lock has pinned it (409 `ai_assessment_pinned`, `{"ai_assessment": "pinned"}`,
    Story 12.1)."""

    code = "ai_assessment_pinned"


class LetterUnavailable(_FieldsError):
    """Story 12.6 (FR-56): the Institution forbids the Indicative letter, so only `unavailable`
    can be chosen (409 `letter_unavailable`, `{"letter_setting": "institution"}`)."""

    code = "letter_unavailable"


class LetterThresholdsLocked(_FieldsError):
    """Story 12.6 (FR-56): the letter bounds changed once a Test attempt of the Class session has
    been opened (409 `letter_thresholds_locked`, `{"letter_thresholds": "locked"}`)."""

    code = "letter_thresholds_locked"


class ScoringGuideLocked(_FieldsError):
    """The Scoring guide was edited once the original Test deadline has passed or the
    Test-deadline lock has pinned it (409 `scoring_guide_locked`, `{"scoring_guide": "locked"}`,
    Story 11.2, FR-18)."""

    code = "scoring_guide_locked"


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


class InvalidReplayScenario(Exception):
    """An own Replay scenario breaks the engine's rules (422 `invalid_replay_scenario`, Story
    10.2): one problem per setting, keyed as the Game settings' (`weeks`, `demand.start`), with
    the range that applies; `replay_template` `required` for `own` with no template at all."""

    code = "invalid_replay_scenario"

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


@dataclass(frozen=True)
class CompletionTerms:
    """What a Class session says about its requirement (Story 13.1, FR-17): its Class, whether it
    is obligatory and its required share of Weeks (`required_share`)."""

    class_id: uuid.UUID
    obligatory: bool
    required_share: int


async def completion_terms(
    session: AsyncSession, class_session_id: uuid.UUID
) -> CompletionTerms | None:
    """The `CompletionTerms` of the Class session, read in the caller's transaction; None for no
    such session. For `reports.service.completion_status`."""
    row = await repo.session_row(session, class_session_id)
    if row is None:
        return None
    return CompletionTerms(
        class_id=row["class_id"], obligatory=row["obligatory"], required_share=required_share(row)
    )


@dataclass(frozen=True)
class Adjustment:
    """A Student's Tilrettelegging in one Class session (Story 8.9, FR-17): the factor on the
    Inactivity limit (1, 1.5, 2 or 3; it only ever extends) and the share of Weeks required of
    them (None: the Class session's own, `required_share`). Personal data: never logged."""

    time_factor: Decimal
    share_percent: int | None


def _adjustment(row: Mapping[str, Any] | None) -> Adjustment | None:
    """A stored row as read: a share no lower than the Class session's own (the class lowered its
    share since the save) is the class's own, so an adjustment never raises the requirement."""
    if row is None:
        return None
    share = row["share_percent"]
    if share is not None and share >= row["class_share"]:
        share = None
    return Adjustment(time_factor=Decimal(row["time_factor"]), share_percent=share)


async def get_adjustment(
    session: AsyncSession, class_session_id: uuid.UUID, user_id: uuid.UUID
) -> Adjustment | None:
    """The one way another module reads a Student's Tilrettelegging (Story 8.9, AD-14): `games`
    for the turn times, Epic 11 for a timed sitting, Epic 13 for the share of Weeks. None without
    one. Read in the caller's transaction."""
    return _adjustment(await repo.adjustment_row(session, class_session_id, user_id))


async def time_factors(
    session: AsyncSession, class_session_id: uuid.UUID, user_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, float]:
    """`get_adjustment`'s factor for many Students of one Class session in one read (Story 8.9):
    only those whose factor is above 1; anyone else's limit is the Class session's. For
    `games.commands`, which multiplies the Inactivity limit by it (`rules.turn_times`)."""
    rows = await repo.adjustment_rows(session, class_session_id, sorted(set(user_ids), key=str))
    return {row["user_id"]: float(row["time_factor"]) for row in rows if row["time_factor"] > 1}


def own_adjustment(adjustment: Adjustment | None) -> OwnAdjustmentOut | None:
    """The Student's own Tilrettelegging as Hjem says it (Story 8.9, UX-DR53): the factor when
    above 1 and the share when it is below the Class session's; None when neither applies."""
    if adjustment is None:
        return None
    factor = float(adjustment.time_factor) if adjustment.time_factor > 1 else None
    if factor is None and adjustment.share_percent is None:
        return None
    return OwnAdjustmentOut(time_factor=factor, share_percent=adjustment.share_percent)


def adjustment_out(adjustment: Adjustment | None) -> AdjustmentOut | None:
    """The Tilrettelegging as the Lecturer's Studentside reads it; None when there is none."""
    if adjustment is None or (adjustment.time_factor <= 1 and adjustment.share_percent is None):
        return None
    return AdjustmentOut(
        time_factor=float(adjustment.time_factor), share_percent=adjustment.share_percent
    )


OWN_DEADLINE_KEYS = {
    "debrief_deadline": "own_debrief_deadline",
    "test_deadline": "own_test_deadline",
}
"""Story 11.13: the keys a per-Student row carries the Student's own deadlines under
(`_with_own_deadlines`), None where they have no extension."""


def _with_own_deadlines(row: Mapping[str, Any], extension: Mapping[str, Any] | None) -> dict:
    """The Class session row with the Student's own Debrief and Test deadlines (Story 11.13), as
    every per-Student reader passes it to `effective_debrief_deadline`/`effective_test_deadline`."""
    return dict(row) | {
        own: None if extension is None else extension[name]
        for name, own in OWN_DEADLINE_KEYS.items()
    }


async def _student_row(
    s: AsyncSession, row: Mapping[str, Any], user_id: uuid.UUID
) -> dict[str, Any]:
    """`row` with the Student's own deadlines, read in `s`."""
    return _with_own_deadlines(row, await repo.extension_row(s, row["id"], user_id))


def _effective(class_session: ClassSessionLike, name: str) -> datetime | None:
    """The Student's deadline `name` (Story 11.13, FR-18): the Class session's, or the Student's
    own where it is later; None while the Class session has none. A row must come through a
    per-Student reader (`_with_own_deadlines`), so no Student path reads the Class date silently;
    a `ClassSessionOut` has no Student and reads the Class session's."""
    if isinstance(class_session, ClassSessionOut):
        return getattr(class_session, name)
    own_key = OWN_DEADLINE_KEYS[name]
    if own_key not in class_session:
        raise KeyError(f"{own_key}: read the Class session through a per-Student reader")
    at: datetime | None = class_session[name]
    own: datetime | None = class_session[own_key]
    if at is None or own is None:
        return at
    return max(at, own)


def effective_debrief_deadline(
    user: authz.Principal | uuid.UUID, class_session: ClassSessionLike
) -> datetime | None:
    """The Student's Debrief deadline, the only way another module reads it: the Class session's,
    or the one their Test deadline extension moved (Story 11.13) where that is later."""
    return _effective(class_session, "debrief_deadline")


def effective_test_deadline(
    user: authz.Principal | uuid.UUID, class_session: ClassSessionLike
) -> datetime | None:
    """The Student's Test deadline, the only way another module reads it: the Class session's, or
    their own extension (Story 11.13) where that is later."""
    return _effective(class_session, "test_deadline")


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


def _refuse_control_test(found: classes.ClassOut) -> None:
    """A Control test Class holds its one Class session (Story 12.7, AD-27): no other is made in
    it, and none is copied into or out of it. Raises `classes.ControlTestClass`."""
    if found.control_test:
        log.info("class_session_refused", class_id=str(found.id), error_code="control_test_class")
        raise classes.ControlTestClass


CONTROL_TEST = "control_test"
COURSE = "course"
"""The kinds of a Class session (Story 12.7, AD-27): `course`, or a Control test."""


async def kind_of(
    class_session_id: uuid.UUID, *, session: AsyncSession | None = None
) -> str | None:
    """The kind of a Class session, `course` or `control_test` (Story 12.7, FR-82, AD-13); None
    for no such session. In the caller's `session` when given. What other modules ask to leave a
    Control test out (Epic 13's `reports.scope`)."""
    async with reading(session) as s:
        row = await repo.session_row(s, class_session_id)
    return None if row is None else row["kind"]


def control_test_session_ids() -> Select[tuple[uuid.UUID]]:
    """The ids of every Control test Class session, as a subquery for `NOT IN (...)` (Story 12.7,
    AD-13): what reports, statistics and exports leave out."""
    return repo.control_test_ids()


@dataclass(frozen=True)
class ControlTestFacts:
    """A Control test as its scorers see it (Story 12.9): the Class's name and the Class
    session's Test deadline, after which its answers are scored; and (Story 12.10) the model
    config under test, pinned at creation."""

    id: uuid.UUID
    name: str
    test_deadline: datetime | None  # None until the Admin sets the dates
    model_config_id: uuid.UUID | None = None

    def is_open(self, now: datetime) -> bool:
        """Whether the answers are open for scoring: the Test deadline is set and has passed."""
        return self.test_deadline is not None and now >= self.test_deadline


async def control_test_facts(
    s: AsyncSession, class_session_ids: list[uuid.UUID]
) -> dict[uuid.UUID, ControlTestFacts]:
    """These Class sessions by id when they are Control tests (Story 12.9, FR-82): with no User's
    scope; the caller judges access (`authz.control_tests_scored_by`, `control_tests.manage`).
    Any other id is left out."""
    found: dict[uuid.UUID, ControlTestFacts] = {}
    rows = [await repo.session_row(s, each) for each in dict.fromkeys(class_session_ids)]
    kept = [row for row in rows if row is not None and row["kind"] == CONTROL_TEST]
    names = await classes.class_facts(s, [row["class_id"] for row in kept])
    for row in kept:
        fact = names.get(row["class_id"])
        if fact is not None:
            found[row["id"]] = ControlTestFacts(
                row["id"], fact.name, row["test_deadline"], row["model_config_id"]
            )
    return found


ControlTestGuidePinner = Callable[[AsyncSession, uuid.UUID, uuid.UUID, datetime], Awaitable[Any]]
"""`(session, class_session_id, scoring_guide_id, now)`: pins the Scoring guide version under test
for a new Control test, in its creation's transaction (Story 12.7). `tests` registers it; it
raises `LookupError` (`content.ContentNotFound`) for an id that is no Scoring guide version."""
ControlTestGuideReader = Callable[[AsyncSession, uuid.UUID], Awaitable[Any]]
"""`(session, class_session_id)`: the Scoring guide record in force
(`content.ScoringGuideRecord`)."""


@dataclass(frozen=True)
class ControlTestGuide:
    """What `tests` lends `sessions` for a Control test's Scoring guide (Story 12.7)."""

    pin: ControlTestGuidePinner
    read: ControlTestGuideReader


_control_test_guide: list[ControlTestGuide] = []


def register_control_test_guide(pin: ControlTestGuidePinner, read: ControlTestGuideReader) -> None:
    """Called at import by `tests.guide`, which `sessions` may not import; once."""
    if not _control_test_guide:
        _control_test_guide.append(ControlTestGuide(pin, read))


def control_test_guide() -> ControlTestGuide:
    """The registered Scoring guide hooks; `RuntimeError` when `tests` was never imported."""
    if not _control_test_guide:  # pragma: no cover - the app and the tests import `tests.guide`
        raise RuntimeError("no Control test guide registered")
    return _control_test_guide[0]


@dataclass(frozen=True)
class StaffedSession:
    """A Class session as a module acting for its staff sees it (Story 7.9): its Class and its
    number within the Class."""

    id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    archived: bool
    number: int


async def staffed_session(
    user: authz.Principal, session_id: uuid.UUID, action: str
) -> StaffedSession | None:
    """The Class session when `user` may do the Class action `action` on it, else None: one answer
    for a Class session that does not exist, one of another Class and a role that may not
    (FR-5, AD-12)."""
    async with get_sessionmaker()() as s:
        row = await repo.session_row(s, session_id)
    if row is None:
        return None
    found = await _class_for(user, row["class_id"], action)
    if found is None:
        return None
    async with get_sessionmaker()() as s:
        number = await repo.number_of(s, session_id, row["class_id"])
    return StaffedSession(
        id=session_id,
        class_id=found.id,
        class_name=found.name,
        archived=found.archived,
        number=number,
    )


async def class_id_of(session: AsyncSession, session_id: uuid.UUID) -> uuid.UUID | None:
    """The Class of a Class session, read in the caller's transaction; None for no such session."""
    row = await repo.session_row(session, session_id)
    return None if row is None else row["class_id"]


async def class_ids_of(
    session: AsyncSession, session_ids: list[uuid.UUID]
) -> dict[uuid.UUID, uuid.UUID]:
    """The Class of each of these Class sessions in one read, by session id (Story 7.10: a
    Student's Messages name their Class); an unknown id is left out."""
    return await repo.class_ids_of(session, list(dict.fromkeys(session_ids)))


async def create_session(
    user: authz.Principal, class_id: uuid.UUID, *, now: datetime
) -> ClassSessionOut | None:
    """«Lag Klasseøkt»: one transaction stores the Class session with its defaults, its model
    config and budget row when a default is active, and emits `session:<id>`. None when the User
    may not manage the Class; raises `ClassArchived`."""
    found = await _class_for(user, class_id, "class_sessions.manage")
    if found is None:
        return None
    _refuse_control_test(found)
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
        switch = await assessment.switch_of(s, session_id) if row else assessment.DEFAULT_SWITCH
        sitting = await _sitting_minutes(s, session_id) if row else None
        attempts = await _attempts_opened(s, session_id) if row else False
        cost_state = (
            await budget.state(budget.BudgetScope.class_session(session_id), session=s)
            if row
            else None
        )
    if row is None:
        return None
    found = await _class_for(user, row["class_id"], "class_sessions.read")
    if found is None:
        return None
    forbids = await identity.institution_forbids_letter(found.institution_id)
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
    in_force = replay_template(row)
    now = auth.utcnow()
    copied_from, effort_level_replaced = await _copy_notes(user, row)
    return ClassSessionOut(
        id=row["id"],
        class_id=row["class_id"],
        class_name=found.name,
        number=number,
        kind=row["kind"],
        game_settings=settings,
        is_classic=is_classic(settings),
        ai_mode=AiMode(row["ai_mode"]),
        debrief_mode=DebriefMode(row["debrief_mode"]),
        debrief_release=DebriefRelease(row["debrief_release"]),
        debrief_ai_text=row["debrief_ai_text"],
        replay_scenario=row["replay_scenario"],
        replay_template=in_force,
        replay_default=default_replay_template(settings),
        replay_warnings=(
            replay_warnings(in_force, settings, info_visibility_enabled=info_visibility_enabled())
            if row["replay_scenario"] == "own"
            else []
        ),
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
        lock_refused_reason=(
            row["lock_refused_reason"]
            if row["locked_at"] is None and row["lock_refused_at"] is not None
            else None
        ),
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
        ai_assessment=_ai_assessment_out(
            user, found, row, switch, now, forbids=forbids, attempts=attempts
        ),
        cost_limit_reached_at=cost_state.players_exhausted_at if cost_state else None,
        test_sitting=TestSittingOut(
            minutes=sitting,
            min_minutes=get_settings().test_sitting_min_minutes,
            max_minutes=get_settings().test_sitting_max_minutes,
            can_change=authz.can(user, "class_sessions.manage", found)
            and not found.archived
            and not is_locked(row, now=now),
        ),
    )


def _ai_assessment_open(row: Mapping[str, Any], switch: assessment.Switch, now: datetime) -> bool:
    """Whether the «KI-vurdering» switch can still change (Story 12.1): not pinned, and the
    original Test deadline has not passed, also before the sweep has run `lock_test`."""
    deadline = row["test_deadline"]
    return not switch.pinned and (deadline is None or deadline > now)


def _ai_assessment_out(
    user: authz.Principal,
    found: classes.ClassOut,
    row: Mapping[str, Any],
    switch: assessment.Switch,
    now: datetime,
    *,
    forbids: bool,
    attempts: bool,
) -> AiAssessmentOut:
    is_open = _ai_assessment_open(row, switch, now)
    can_change = is_open and not found.archived and authz.can(user, "ai_assessment.change", found)
    rules = assessment.letter_rules(switch, institution_forbids=forbids)
    return AiAssessmentOut(
        enabled=switch.enabled,
        pinned_at=switch.pinned_at,
        open=is_open,
        can_change=can_change,
        letter=LetterSettingOut(
            setting=rules.setting,
            stored=switch.letter_setting,
            forced=rules.forced,
            thresholds=LetterThresholdsOut.model_validate(rules.thresholds),
            thresholds_open=can_change and not attempts,
            can_change=can_change,
        ),
    )


AttemptsOpened = Callable[[AsyncSession, uuid.UUID], Awaitable[bool]]
"""`(session, class_session_id)`: whether any Test attempt of the Class session has been opened
(Story 12.6: the letter bounds are read-only from then on). `tests` registers it."""

_attempts_readers: list[AttemptsOpened] = []


def register_attempts_opened(reader: AttemptsOpened) -> None:
    """Story 12.6: `tests` registers the reader of whether a Test attempt exists, for `sessions`
    may not import it. The same one again changes nothing."""
    if reader not in _attempts_readers:
        _attempts_readers.append(reader)


async def _attempts_opened(s: AsyncSession, class_session_id: uuid.UUID) -> bool:
    for reader in _attempts_readers:
        if await reader(s, class_session_id):
            return True
    return False


async def letter_rules(
    s: AsyncSession, class_session_id: uuid.UUID
) -> assessment.LetterRules | None:
    """Story 12.6 (FR-56): the Indicative letter rules in force for the Class session, read in
    `s`: the switch row's setting and bounds, and `unavailable` when the Class's Institution
    forbids the letter (`identity.service`). None for an unknown Class session. For `tests`,
    whose views hand the letter out through `assessment.letter_for`."""
    row = await repo.session_row(s, class_session_id)
    if row is None:
        return None
    facts = (await classes.class_facts(s, [row["class_id"]])).get(row["class_id"])
    forbids = facts is not None and await identity.institution_forbids_letter(
        facts.institution_id, session=s
    )
    switch = await assessment.switch_of(s, class_session_id)
    return assessment.letter_rules(switch, institution_forbids=forbids)


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
    debrief_ai_text: bool | None = None,
    dates: DatesIn | None = None,
    game_settings: Mapping[str, Any] | None = None,
    obligatory: bool | None = None,
    required_share_percent: int | None = None,
    inactivity_limit_hours: int | None = None,
    allocation_method: AllocationMethod | None = None,
    replay_scenario: str | None = None,
    replay_template: Mapping[str, Any] | None = None,
    ai_assessment: bool | None = None,
    test_sitting: TestSittingIn | None = None,
    letter_setting: assessment.LetterSetting | None = None,
    letter_thresholds: Mapping[str, int] | None = None,
) -> ClassSessionOut | None:
    """«Lagre Klasseøkt»: saves the Class session as it stands and emits `session:<id>`. LLM
    players on a Class session with no model config take the active default and its budget row
    in the same transaction, or raise `LlmUnavailableError` and change nothing. With LLM players
    the Effort level is `effort_level`, else the one in force, else the config's default; a
    changed level the config does not offer raises `InvalidEffortLevel`. With Rule-based players
    no level is in force. `debrief_mode` and `debrief_release` (Story 9.2) and `debrief_ai_text`
    (Story 9.14), None, keep the stored ones. With `game_settings` the
    draft is judged by `judge_settings` and stored, or `InvalidSettings` is raised. With `dates`
    the four dates are replaced under the rules of `judge_dates`; a change emits `user:<id>`
    once per registered Student of the Class. `obligatory`, `required_share_percent` and
    `inactivity_limit_hours` (Story 5.7), None, keep their values; a changed share outside 1 to
    100 or limit under 20 raises `InvalidSessionValues`, and switching the mark on enqueues one
    `OBLIGATORY_NOTICE` per registered Student. Once locked, a changed AI mode, Effort level,
    Debrief mode, Debrief release, Debrief AI text, Game settings, obligatory mark, share or
    Inactivity limit raise `SessionLocked`. `allocation_method` (Story 5.17), None, keeps the
    method; a change to `student_choice` is judged by `_judge_method` and opens the choice
    (`_open_student_choice`). `replay_scenario` (Story 10.2), None, keeps the Replay scenario;
    `own` with `replay_template` stores the own template judged by `judge_replay_template` for
    the Game settings as saved, or raises `InvalidReplayScenario` (`_replay_to_store`).
    `ai_assessment` (Story 12.1), None, keeps the «KI-vurdering» switch; a change is stored
    through `assessment.set_switch` in the same transaction, also after the Start date, and
    raises `AiAssessmentPinned` once the original Test deadline has passed or the switch is
    pinned. `test_sitting` (Story 11.12), None, keeps the Individual test's one timed sitting; a
    changed limit is judged by `_judge_sitting` and stored through the registered `tests` writer
    in the same transaction, and raises `SessionLocked` once locked. `letter_setting` and
    `letter_thresholds` (Story 12.6), None, keep the Indicative letter's setting and bounds; a
    change is stored through `assessment.set_letter` in the same transaction while the switch can
    change (`AiAssessmentPinned` after), only by the switch's owners; a setting other than
    `unavailable` raises `LetterUnavailable` while the Institution forbids the letter, bounds
    that break `analysis.letter.judge_thresholds` raise `InvalidSessionValues`, and changed bounds
    raise `LetterThresholdsLocked` once a Test attempt exists. None when the User may not
    manage the Class (or change the switch or the letter); raises `ClassArchived`."""
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, session_id)
    found = (
        await _class_for(user, row["class_id"], "class_sessions.manage")
        if row is not None
        else None
    )
    if row is None or found is None:
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
        ai_text = row["debrief_ai_text"] if debrief_ai_text is None else debrief_ai_text
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
        stored_sitting = await _sitting_minutes(s, session_id)
        sitting = stored_sitting if test_sitting is None else test_sitting.minutes
        timing = sitting != stored_sitting
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
                        ("debrief_ai_text", ai_text != row["debrief_ai_text"]),
                        ("obligatory", marked != row["obligatory"]),
                        ("required_share_percent", share != row["required_share_percent"]),
                        ("inactivity_limit_hours", limit != row["inactivity_limit_hours"]),
                        ("test_sitting", timing),
                    )
                    if differs
                }
                if refused:
                    raise SessionLocked(refused)
            switch = await assessment.switch_of(s, session_id)
            switching_assessment = ai_assessment is not None and ai_assessment != switch.enabled
            if switching_assessment:
                if not authz.can(user, "ai_assessment.change", found):
                    return None
                if not _ai_assessment_open(row, switch, now):
                    raise AiAssessmentPinned({"ai_assessment": "pinned"})
            letter = await _judge_letter(
                s,
                user,
                found,
                row,
                switch,
                now,
                setting=letter_setting,
                thresholds=letter_thresholds,
            )
            if letter is None:
                return None
            _judge_values(row, share, limit)
            if timing:
                _judge_sitting(sitting)
            if game_settings is not None:
                new_settings = _settings_to_store(row, game_settings, locked=locked)
            # An own template follows changed Game settings even when the scenario is not sent.
            if replay_scenario is None and new_settings and row["replay_scenario"] == "own":
                replay_scenario = "own"
            replay = (
                _replay_to_store(
                    row,
                    new_settings or GameSettings.model_validate(row["game_settings"]),
                    replay_scenario,
                    replay_template,
                    locked=locked,
                )
                if replay_scenario is not None
                else None
            )
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
        except (InvalidSettings, InvalidReplayScenario) as refused:
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
            debrief_ai_text=ai_text,
            dates=changed,
            game_settings=new_settings.model_dump(mode="json") if new_settings else None,
            obligatory=marked,
            required_share_percent=share,
            inactivity_limit_hours=limit,
            allocation_method=method if switching else None,
            replay=replay,
        )
        if "test_deadline" in changed:
            # Story 11.3: open Individual test attempts keep their stored deadline in step.
            for mover in _test_deadline_movers:
                await mover(s, session_id, changed["test_deadline"])
        if changed:
            # Story 13.9: the deletion date follows, in this transaction; without a Test deadline
            # it counts from the latest other date (`retention.deletion_base`).
            dated = await repo.session_row(s, session_id)
            assert dated is not None
            await _store_deletion_date(s, session_id, dated["test_deadline"])
        if timing and _test_sitting:
            await _test_sitting[0][1](s, session_id, sitting, user.id, now)
        if switching_assessment:
            assert ai_assessment is not None
            # The Class session's row lock, held since the read, keeps `lock_test` out meanwhile.
            await assessment.set_switch(s, session_id, ai_assessment, now=now)
        if letter.changed:
            await assessment.set_letter(
                s, session_id, setting=letter.setting, thresholds=letter.thresholds, now=now
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
        replay_scenario=replay[0] if replay else None,
        obligatory_switched_on=switched_on,
        students_told=len(students) if switched_on else 0,
        student_choice_opened=switching,
        ai_assessment=ai_assessment if switching_assessment else None,
        letter_setting=letter.setting,
        letter_thresholds_changed=letter.thresholds is not None,
        test_sitting_changed=timing,
    )
    if changed and locked:
        # After the start a moved deadline holds for the whole Class session (FR-18).
        log.info(
            "class_session_dates_moved", class_session_id=str(session_id), dates=sorted(changed)
        )
    return await get_session(user, session_id)


@dataclass(frozen=True)
class _LetterChange:
    """What a save changes of the Indicative letter (Story 12.6): the new setting and bounds, each
    None when unchanged."""

    setting: assessment.LetterSetting | None = None
    thresholds: dict[str, int] | None = None

    @property
    def changed(self) -> bool:
        return self.setting is not None or self.thresholds is not None


async def _judge_letter(
    s: AsyncSession,
    user: authz.Principal,
    found: classes.ClassOut,
    row: Mapping[str, Any],
    switch: assessment.Switch,
    now: datetime,
    *,
    setting: assessment.LetterSetting | None,
    thresholds: Mapping[str, int] | None,
) -> _LetterChange | None:
    """Judge a save's letter setting and bounds under the Class session's row lock (Story 12.6,
    FR-56). A value equal to the one in force is no change. None when the User may not change it
    (403); raises `AiAssessmentPinned`, `LetterUnavailable`, `InvalidSessionValues` or
    `LetterThresholdsLocked`."""
    new_setting = setting if setting is not None and setting != switch.letter_setting else None
    in_force = switch.letter_thresholds or assessment.default_thresholds()
    new_bounds = (
        dict(thresholds) if thresholds is not None and dict(thresholds) != in_force else None
    )
    if new_setting is None and new_bounds is None:
        # The Institution may forbid the letter after the Lecturer chose one: sending that choice
        # again is no change, but choosing it is refused below.
        return _LetterChange()
    if not authz.can(user, "ai_assessment.change", found):
        return None
    if not _ai_assessment_open(row, switch, now):
        pinned = {"letter_setting": "pinned"} if new_setting else {}
        raise AiAssessmentPinned(pinned | ({"letter_thresholds": "pinned"} if new_bounds else {}))
    if new_setting is not None and new_setting != "unavailable":
        if await identity.institution_forbids_letter(found.institution_id, session=s):
            raise LetterUnavailable({"letter_setting": "institution"})
    if new_bounds is not None:
        reason = judge_thresholds(new_bounds)
        if reason is not None:
            raise InvalidSessionValues({"letter_thresholds": reason})
        if await _attempts_opened(s, row["id"]):
            raise LetterThresholdsLocked({"letter_thresholds": "locked"})
    return _LetterChange(setting=new_setting, thresholds=new_bounds)


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
        found = await repo.enrolled_sessions(s, user)
        extensions = await repo.extensions_of_user(s, user.id, [row["id"] for row in found])
        rows = [_with_own_deadlines(row, extensions.get(row["id"])) for row in found]
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
        adjustments = {
            row["class_session_id"]: _adjustment(row)
            for row in await repo.adjustments_of_user(s, user.id, [row["id"] for row in rows])
        }
        cards = {
            row["id"]: await _student_card(s, user.id, row, done.get(row["id"], set()))
            for row in locked
        }
        changed = {
            row["id"]: await _quiz_changed_of(s, user.id, row["id"], done.get(row["id"], set()))
            for row in locked
        }
        grouped = {
            row["id"]: await _group_open_of(s, user.id, row["id"], done.get(row["id"], set()))
            for row in locked
            if cards.get(row["id"]) is not None and cards[row["id"]].debrief == "open"
        }
        replays = {
            row["id"]: await _replay_out(s, user, row, now)
            for row in locked
            if cards.get(row["id"]) is not None
            and progress.Step.QUIZ_PASSED in done.get(row["id"], set())
        }
        # Story 13.4: the Oppfølgingsspill a Lecturer gave the Student, as a game card; once it
        # finished and became their game (Story 13.5) it is `game` instead, not shown twice.
        makeups = {
            row["id"]: card
            for row in locked
            if (card := await _makeup_card(s, user.id, row, done.get(row["id"], set()))) is not None
            and (cards.get(row["id"]) is None or cards[row["id"]].id != card.id)
        }
    # Story 13.1 (FR-17): in an Obligatory class session where the Student has a game, which steps
    # count and whether the requirement is met, from the one assembler.
    completions = {
        row["id"]: await _completion_of(user.id, row["id"])
        for row in locked
        if row["obligatory"] and cards.get(row["id"]) is not None
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
                steps=_with_counts(
                    stegene(
                        cards.get(row["id"]) is not None
                        or _after_makeup(None, makeups.get(row["id"])),
                        done.get(row["id"], set()),
                        # Story 13.5: a Student with no Class game plays the Oppfølgingsspill
                        # that opens their Debrief.
                        after_makeup=_after_makeup(cards.get(row["id"]), makeups.get(row["id"])),
                        held=_held(cards.get(row["id"])),
                        quiz_changed=changed.get(row["id"], False),
                        group_open=grouped.get(row["id"], False),
                        replay_closed=_replay_closed(replays.get(row["id"]), user, row, now),
                        test_closed=test_deadline_passed(user, row, now),
                        # Story 13.7: «Rapport» opens at the Student's Test deadline.
                        report_open=test_deadline_passed(user, row, now),
                    ),
                    completions.get(row["id"]),
                ),
                requirement_met=_requirement_met(completions.get(row["id"])),
                adjustment=own_adjustment(adjustments.get(row["id"])),
                replay=replays.get(row["id"]),
                makeup=makeups.get(row["id"]),
                deletion_date=row["deletion_date"],
            )
            for row in rows
            if row["class_id"] in names
        ]
    )


def _after_makeup(game: StudentGameOut | None, makeup: StudentGameOut | None) -> bool:
    """Story 13.5: the Student has no Class game, and their Debrief opens when the
    Oppfølgingsspill they were given finishes (not one closed at the Test deadline)."""
    return game is None and makeup is not None and makeup.status != "finished"


STEGENE: tuple[tuple[str, progress.Step], ...] = (
    ("class_game", progress.Step.CLASS_GAME),
    ("debrief", progress.Step.DEBRIEF),
    ("quiz", progress.Step.QUIZ_PASSED),
    ("replay", progress.Step.REPLAY),
    ("test", progress.Step.TEST_SUBMITTED),
    ("report", progress.Step.ASSESSMENT_READY),
)
"""Stegene's six steps in order (UX-DR29) and the `progress` step that marks each done."""


def stegene(
    has_game: bool,
    done: set[progress.Step],
    *,
    held: bool = False,
    quiz_changed: bool = False,
    group_open: bool = False,
    replay_closed: bool = False,
    test_closed: bool = False,
    after_makeup: bool = False,
    report_open: bool = False,
) -> list[StepOut]:
    """The state of each of Stegene's steps (Story 6.1, AD-10): a done step is `done`; with a
    game the first step not done is `current` and the later ones `locked`; with no game (before
    the Start date, or no Seat yet) every step not done is `locked`. `held` (Story 9.2): the
    Lecturer holds the Debriefs until every Class game has finished, so a Debrief step that would
    be current is `locked` and says so, and no step is current until the release.
    `quiz_changed` (Story 9.10): a current Quiz step says the Lecturer has changed the quiz.
    `group_open` (Story 9.11): a current Debrief step says a Group debrief the Student can join is
    under way. `replay_closed` (Story 10.3): a current Replay step says the Test deadline has
    passed with no Replay started; it stays not done. `test_closed` (Story 11.11): a current
    Individual test step (not handed in) says the Student's Test deadline has passed; it stays
    not done, and turns done when the sweep hands a saved attempt in. `after_makeup` (Story
    13.5): a locked Debrief step says it opens when the Oppfølgingsspill is finished.
    `report_open` (Story 13.7, UX-DR29): «Rapport» opens at the Student's effective Test deadline,
    whatever the earlier steps (a step not done is marked so in the report); until then it is
    `locked` and says what opens it."""
    steps: list[StepOut] = []
    current_given = not has_game
    for name, step in STEGENE:
        if name == "report" and step not in done:
            steps.append(StepOut(step=name, state="current" if report_open else "locked"))
            continue
        if step in done:
            state = "done"
        elif not current_given:
            state, current_given = "current", True
            if name == "debrief" and held:
                steps.append(StepOut(step=name, state="locked", held=True))
                continue
            if name == "quiz" and quiz_changed:
                steps.append(StepOut(step=name, state=state, quiz_changed=True))
                continue
            if name == "debrief" and group_open:
                steps.append(StepOut(step=name, state=state, group_open=True))
                continue
            if (name == "replay" and replay_closed) or (name == "test" and test_closed):
                steps.append(StepOut(step=name, state=state, closed=True))
                continue
        else:
            state = "locked"
            if name == "debrief" and after_makeup:
                steps.append(StepOut(step=name, state=state, after_makeup=True))
                continue
        steps.append(StepOut(step=name, state=state))
    return steps


STEGENE_COMPLETION: dict[str, str] = {
    "class_game": "class_game",
    "debrief": "debrief",
    "quiz": "quiz_passed",
    "replay": "replay",
    "test": "test_submitted",
}
"""Stegene's steps that are steps of the requirement (FR-17), by Completion's step name; the
«Rapport» step is not one."""


def _with_counts(steps: list[StepOut], status: CompletionStatus | None) -> list[StepOut]:
    """Story 13.1: each step of the requirement says whether it counts, from the Completion
    status; without one (not obligatory, no game yet) `counts` stays None. Story 13.3: and
    whether a Lecturer's correction decided it."""
    if status is None:
        return steps
    found = []
    for step in steps:
        if step.step in STEGENE_COMPLETION:
            judged = status.step(STEGENE_COMPLETION[step.step])
            step = step.model_copy(update={"counts": judged.done, "corrected": judged.corrected})
        found.append(step)
    return found


def _requirement_met(status: CompletionStatus | None) -> bool | None:
    return None if status is None else status.requirement_met


# Story 13.1: a Student's Completion status and the Oversikt's funnel come from `reports`, which
# imports `sessions`; it registers its assembler and its funnel here (AD-16, AD-25).

CompletionProvider = Callable[[uuid.UUID, uuid.UUID], Awaitable[CompletionStatus | None]]
"""`(user_id, class_session_id)` → the Student's Completion status, None outside the reporting
scope (`reports.service.completion_status`)."""
FunnelProvider = Callable[[AsyncSession, uuid.UUID], Awaitable[progress.Funnel]]
"""`(session, class_session_id)` → the Trakt over the reporting Students
(`reports.service.funnel`)."""

_completion: list[CompletionProvider] = []
_funnel: list[FunnelProvider] = []


def register_completion(provider: CompletionProvider, funnel: FunnelProvider) -> None:
    """`reports.service` registers its assembler and its funnel at import. The same ones again
    change nothing; others are refused, so every reader judges Completion alike."""
    if (_completion and _completion[0] is not provider) or (_funnel and _funnel[0] is not funnel):
        raise ValueError("a Completion provider is registered already")
    _completion[:] = [provider]
    _funnel[:] = [funnel]


async def _completion_of(
    user_id: uuid.UUID, class_session_id: uuid.UUID
) -> CompletionStatus | None:
    if not _completion:
        raise RuntimeError("no Completion provider: import app.modules.reports.service")
    return await _completion[0](user_id, class_session_id)


async def funnel_of(session: AsyncSession, class_session_id: uuid.UUID) -> progress.Funnel:
    """The Oversikt's Trakt (Story 7.6) through `reports.service.funnel` (Story 13.1)."""
    if not _funnel:
        raise RuntimeError("no funnel provider: import app.modules.reports.service")
    return await _funnel[0](session, class_session_id)


ReportingStudents = Callable[[AsyncSession, uuid.UUID], Awaitable[list[uuid.UUID]]]
"""`(session, class_session_id)` → the Students reports count (`scope.reporting_students`)."""
_reporting_students: list[ReportingStudents] = []


def register_reporting_students(read: ReportingStudents) -> None:
    """`reports.service` registers `scope.reporting_students` at import, so a module `reports`
    reads (Story 12.5's list of AI assessments) can count the same Students without importing it."""
    _reporting_students[:] = [read]


async def reporting_students_of(
    session: AsyncSession, class_session_id: uuid.UUID
) -> list[uuid.UUID]:
    """The Students reports count in the Class session (Story 13.1): never a test student,
    nobody in a Control test."""
    if not _reporting_students:
        raise RuntimeError("no reporting scope: import app.modules.reports.service")
    return await _reporting_students[0](session, class_session_id)


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


# Story 9.10: whether the Lecturer has taken out every question the Student's last quiz attempt
# got wrong, as `debrief.rules` judges it; registered by `debrief`, as the Debrief state above.

QuizChangedProvider = Callable[[AsyncSession, uuid.UUID, uuid.UUID], Awaitable[bool]]
"""`(session, user_id, class_session_id)` → whether Hjem says the quiz has changed."""

_quiz_changed: list[QuizChangedProvider] = []


def register_quiz_changed(provider: QuizChangedProvider) -> None:
    """`debrief.rules` registers its one rule at import; another is refused."""
    if _quiz_changed and _quiz_changed[0] is not provider:
        raise ValueError("a quiz-changed provider is registered already")
    _quiz_changed[:] = [provider]


async def _quiz_changed_of(
    s: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID, done: set[progress.Step]
) -> bool:
    """Whether Stegene's current Quiz step says the quiz has changed: only while the Debrief is
    done and the quiz not passed, and never before `debrief` has registered its rule."""
    if not _quiz_changed or progress.Step.DEBRIEF not in done:
        return False
    if progress.Step.QUIZ_PASSED in done:
        return False
    return await _quiz_changed[0](s, user_id, class_session_id)


# Story 9.11: whether a Group debrief of the Student's game is under way that they have not joined,
# as `debrief.rules` judges it; registered by `debrief`, as the Debrief state above.

GroupOpenProvider = Callable[[AsyncSession, uuid.UUID, uuid.UUID], Awaitable[bool]]
"""`(session, user_id, class_session_id)` → whether Hjem offers the Student to join."""

_group_open: list[GroupOpenProvider] = []


def register_group_open(provider: GroupOpenProvider) -> None:
    """`debrief.rules` registers its one rule at import; another is refused."""
    if _group_open and _group_open[0] is not provider:
        raise ValueError("a group-open provider is registered already")
    _group_open[:] = [provider]


async def _group_open_of(
    s: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID, done: set[progress.Step]
) -> bool:
    """Whether Stegene's current Debrief step offers to join a Group debrief: never once the
    Debrief is done, nor before `debrief` has registered its rule."""
    if not _group_open or progress.Step.DEBRIEF in done:
        return False
    return await _group_open[0](s, user_id, class_session_id)


# Story 10.3: the Student's Replay in a Class session, as `replay` stores it. `replay` imports
# `sessions`, so it registers its lookup here instead of `sessions` importing it (AD-25).

ReplayGameProvider = Callable[[AsyncSession, uuid.UUID, uuid.UUID], Awaitable[uuid.UUID | None]]
"""`(session, user_id, class_session_id)` → the id of the Student's Replay Game, or None."""

_replay_game: list[ReplayGameProvider] = []


def register_replay_game(provider: ReplayGameProvider) -> None:
    """`replay.service` registers its one lookup at import; another is refused."""
    if _replay_game and _replay_game[0] is not provider:
        raise ValueError("a Replay game provider is registered already")
    _replay_game[:] = [provider]


def test_deadline_passed(
    user: authz.Principal | uuid.UUID, row: Mapping[str, Any], now: datetime
) -> bool:
    """Whether the Student's own Test deadline (`effective_test_deadline`) has passed at `now`
    (Story 10.3): no Replay starts after it (FR-18)."""
    deadline = effective_test_deadline(user, row)
    return deadline is not None and deadline <= now


async def _test_deadline_of(
    s: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> datetime | None:
    """The Student's `effective_test_deadline` in the Class session, read in `s`; None for no such
    session. What `games` judges a Replay's close and its Orders by (Story 10.6, FR-18)."""
    row = await repo.session_row(s, class_session_id)
    if row is None:
        return None
    return effective_test_deadline(user_id, await _student_row(s, row, user_id))


games_service.register_test_deadline(_test_deadline_of)


async def _replay_out(
    s: AsyncSession, user: authz.Principal, row: Mapping[str, Any], now: datetime
) -> StudentReplayOut:
    """The Replay on Hjem for a Student who has passed the Debrief quiz (Story 10.3): the started
    Replay with its Seats as `table_status` names them (every AI player `ai`), or whether «Start
    Replay» shows. Before `replay` has registered its lookup, no Replay is known."""
    game_id = await _replay_game[0](s, user.id, row["id"]) if _replay_game else None
    if game_id is None:
        return StudentReplayOut(can_start=not test_deadline_passed(user, row, now), game=None)
    table = await games_service.table_status(s, game_id, user.id, _names_in(row, s))
    play = await games_service.play_status(s, game_id)
    seats = _seats_out(table)
    role = next(seat.role for seat in seats if seat.mine)
    return StudentReplayOut(
        # A Replay stored but not started (its start failed after the commit) starts on the
        # next press, which `replay.start` allows.
        can_start=play.status == "ready" and not test_deadline_passed(user, row, now),
        game=ReplayGameOut(
            id=game_id,
            role=role,
            status=play.status,
            end_reason=play.end_reason,
            week=play.week,
            seats=seats,
            server_now=await games_service.database_now(s),
        ),
    )


def _replay_closed(
    replay: StudentReplayOut | None, user: authz.Principal, row: Mapping[str, Any], now: datetime
) -> bool:
    """Stegene's Replay step says the Test deadline has passed (Story 10.3): the quiz is passed,
    the deadline is behind, and no Replay was started or the started one was closed there
    unfinished (Story 10.6). A Replay still running in the minute before the sweep closes it reads
    as running, as Hjem's Replay block does."""
    if replay is None or not test_deadline_passed(user, row, now):
        return False
    return replay.game is None or replay.game.end_reason is not None


# Story 13.4: the Student's Oppfølgingsspill in a Class session, as `reports` stores it. `reports`
# imports `sessions`, so it registers its lookup here instead of `sessions` importing it (AD-25).

MakeupGameProvider = Callable[[AsyncSession, uuid.UUID, uuid.UUID], Awaitable[uuid.UUID | None]]
"""`(session, user_id, class_session_id)` → the id of the Student's Oppfølgingsspill, or None."""

_makeup_game: list[MakeupGameProvider] = []


def register_makeup_game(provider: MakeupGameProvider) -> None:
    """`reports.makeup` registers its one lookup at import; another is refused."""
    if _makeup_game and _makeup_game[0] is not provider:
        raise ValueError("an Oppfølgingsspill provider is registered already")
    _makeup_game[:] = [provider]


async def _makeup_card(
    s: AsyncSession, user_id: uuid.UUID, row: Mapping[str, Any], done: set[progress.Step]
) -> StudentGameOut | None:
    """The Student's Oppfølgingsspill on Hjem (Story 13.4) as a game card, while they hold its
    Seat (`games.service.own_game`); None without one, or before `reports` has registered its
    lookup."""
    game_id = await _makeup_game[0](s, user_id, row["id"]) if _makeup_game else None
    if game_id is None:
        return None
    found = await games_service.own_game(s, user_id, game_id)
    if found is None or not found.makeup:
        return None
    return await _game_out(s, user_id, found, row, done)


async def makeup_given_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of a `makeup_given` notice (Story 13.4, AD-9), for `messaging` at
    send time: the Class's name and the Student's Test deadline in Europe/Oslo, until which the
    Oppfølgingsspill is open. None, so the notice is left out, when the Class session or the
    Oppfølgingsspill is gone or has ended, the deadline has passed, the Class is archived, or the
    User is no longer a registered Student of it."""
    if ref is None or not _makeup_game:
        return None
    row = await repo.session_row(session, ref)
    if row is None:
        return None
    game_id = await _makeup_game[0](session, user_id, ref)
    if game_id is None or (await games_service.play_status(session, game_id)).status == "finished":
        return None
    deadline = effective_test_deadline(user_id, await _student_row(session, row, user_id))
    if deadline is None or deadline <= now:
        return None
    label = await classes.label_of_class(session, row["class_id"])
    if label is None or label.archived:
        return None
    if user_id not in await classes.registered_students(row["class_id"]):
        return None
    return {"class_name": label.name, "at": deadline.astimezone(OSLO)}


async def group_debrief_opened_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of a `group_debrief_opened` notice (Story 9.11): the Class's name,
    under the same rules as `debrief_released_mail_context`. None, so the mail is left out, once
    the Student has joined (or the Group debrief is no longer one they can join)."""
    if ref is None or not _group_open or not await _group_open[0](session, user_id, ref):
        return None
    return await debrief_released_mail_context(session, user_id, ref, now)


async def debrief_fallback_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of a `debrief_fallback` notice (Story 9.12): the Class's name,
    under the same rules as `debrief_released_mail_context`. None, so the mail is left out, once
    the Student has finished the Debrief."""
    if ref is None:
        return None
    done = await progress.steps_of(session, user_id, [ref])
    if progress.Step.DEBRIEF in done.get(ref, set()):
        return None
    return await debrief_released_mail_context(session, user_id, ref, now)


async def assessment_ready_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of an `assessment_ready` notice (Story 12.4, FR-55): the Class's
    name only (never a score, a letter or feedback), under the same rules as
    `debrief_released_mail_context`."""
    return await debrief_released_mail_context(session, user_id, ref, now)


async def assessment_failed_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of an `assessment_failed` notice (Story 12.4, NFR-8): the Class's
    name and the Class session's number. None, so the mail is left out, when the Class session or
    its Class is gone, or the User is no longer an active Admin."""
    if ref is None:
        return None
    row = await repo.session_row(session, ref)
    if row is None or user_id not in await identity.active_admins(session):
        return None
    label = await classes.label_of_class(session, row["class_id"])
    if label is None:
        return None
    number = await repo.number_of(session, ref, row["class_id"])
    return {"class_name": label.name, "session_number": number}


# Story 12.4: the assessment tells each Admin about a failed assessment; it may not import
# `identity`, so the Admins are read through this registration.
assessment.register_admin_reader(identity.active_admins)


async def student_names(
    class_session_id: uuid.UUID, user_ids: list[uuid.UUID]
) -> dict[uuid.UUID, str]:
    """The Roster names now of those of `user_ids` who are Students of the Class session's Class
    (Story 9.11), read at request time and never stored (AD-14). The caller has judged that the
    asking User may see them (the joined Students of one Group debrief)."""
    async with get_sessionmaker()() as s:
        row = await repo.session_row(s, class_session_id)
        if row is None:
            return {}
        return await session_student_names(row, user_ids, session=s)


def _held(card: StudentGameOut | None) -> bool:
    return card is not None and card.debrief == "held"


@dataclass(frozen=True)
class DebriefSession:
    """A locked Class session as the Debrief reads it (Story 9.2): its id, Class and whether the
    Lecturer holds the Debriefs until all Class games have finished."""

    id: uuid.UUID
    class_id: uuid.UUID
    hold: bool
    group: bool = False
    """Story 9.11: the Class session's Debrief mode is Group debrief."""


async def enrolled_locked_row(
    s: AsyncSession, user: authz.Principal, class_session_id: uuid.UUID
) -> Mapping[str, Any] | None:
    """The Class session row, read in `s`, when it is one of the User's own as a Student
    (`authz.classes_enrolled_by`), in a Class Hjem lists, and locked; None for every other case
    alike (FR-5). The Debrief (Story 9.2) and the Replay (Story 10.3) are reached only so."""
    listed = {item.id for item in (await classes.enrolled_classes(user, session=s)).items}
    rows = {row["id"]: row for row in await repo.enrolled_sessions(s, user)}
    row = rows.get(class_session_id)
    if row is None or row["class_id"] not in listed or not is_locked(row):
        return None
    return row


async def replay_session_of(
    s: AsyncSession, user: authz.Principal, class_session_id: uuid.UUID
) -> Mapping[str, Any] | None:
    """The whole Class session row for the Student's Replay (Story 10.3), read in `s` and
    share-locked, so its snapshot and Test deadline hold while the Replay is made; under
    `enrolled_locked_row`'s checks (None for every other case alike, FR-5). The caller reads it
    only through `replay_template`, `test_deadline_passed` and its frozen `snapshot`."""
    if await enrolled_locked_row(s, user, class_session_id) is None:
        return None
    row = await repo.session_row(s, class_session_id, share=True)
    return None if row is None else await _student_row(s, row, user.id)


@dataclass(frozen=True)
class IndividualTestSession:
    """A Class session as the Student's Individual test reads it (Story 11.3): its row, share-
    locked in the caller's transaction, and the pins its lock stored."""

    row: Mapping[str, Any]
    pins: Any


async def individual_test_session_of(
    s: AsyncSession, user: authz.Principal, class_session_id: uuid.UUID
) -> IndividualTestSession | None:
    """The Class session for the Student's Individual test (Story 11.3), read in `s` and share-
    locked, so its Test deadline and pins hold while an attempt is opened; under
    `enrolled_locked_row`'s checks (None for every other case alike, FR-5). The caller reads the
    deadline only through `effective_test_deadline`."""
    if await enrolled_locked_row(s, user, class_session_id) is None:
        return None
    row = await repo.session_row(s, class_session_id, share=True)
    if row is None:
        return None
    return IndividualTestSession(
        row=await _student_row(s, row, user.id), pins=await repo.session_pins(s, class_session_id)
    )


async def test_locked_session(
    s: AsyncSession, class_session_id: uuid.UUID
) -> IndividualTestSession | None:
    """The Class session for `tests.close_attempt` (Story 11.11, AD-9), read in `s` and share-
    locked, with its pins; None unless the Test-deadline lock (`lock_test`) has run for it, so
    nothing is closed before the Scoring guide and the «KI-vurdering» switch are pinned. A
    running `lock_test` holds the row `FOR UPDATE`, so this waits for it."""
    row = await repo.session_row(s, class_session_id, share=True)
    if row is None or row["test_locked_at"] is None:
        return None
    return IndividualTestSession(row=row, pins=await repo.session_pins(s, class_session_id))


def test_locked_ids() -> Select[tuple[uuid.UUID]]:
    """The ids of the Class sessions `lock_test` has run for, as a query (Story 11.11): the sweep's
    `tests.close_attempt` finder lists only their attempts."""
    return repo.test_locked_ids()


async def locked_pins(s: AsyncSession, class_session_id: uuid.UUID) -> Any:
    """The pins the Class session's lock stored (`SessionRuntime.pins`), read in `s`; None before
    the lock. For a job that has only ids (Story 11.8: the Adapted item wording)."""
    return await repo.session_pins(s, class_session_id)


TestDeadlineMover = Callable[[AsyncSession, uuid.UUID, datetime | None], Awaitable[None]]
"""`(session, class_session_id, new_test_deadline)`: run in the transaction of a save that
changes the Class session's Test deadline, under its row lock."""

_test_deadline_movers: list[TestDeadlineMover] = []


def register_test_deadline_mover(mover: TestDeadlineMover) -> None:
    """Add a mover a Test-deadline change runs (Story 11.3: `tests` moves the stored deadline of
    open attempts), for a module `sessions` may not import. The same one again changes nothing."""
    if mover not in _test_deadline_movers:
        _test_deadline_movers.append(mover)


async def test_session(
    s: AsyncSession, class_session_id: uuid.UUID, *, lock: bool = False
) -> IndividualTestSession | None:
    """The Class session for `tests.end_sitting` (Story 11.12, AD-9), read in `s` and share-locked
    with its pins, as `individual_test_session_of` holds it for a Student's own commands; None when
    it is gone. The sweep has only ids. With `lock` the row is locked for update instead: an
    extension writes the deletion date on it (Story 13.9), and two share locks waiting to update
    the same row would deadlock."""
    row = await repo.session_row(s, class_session_id, share=not lock, lock=lock)
    if row is None:
        return None
    return IndividualTestSession(row=row, pins=await repo.session_pins(s, class_session_id))


TestSittingReader = Callable[[AsyncSession, uuid.UUID], Awaitable[int | None]]
"""`(session, class_session_id)`: the Class session's time limit in whole minutes for one timed
sitting of the Individual test (Story 11.12), or None when it has none."""

TestSittingWriter = Callable[
    [AsyncSession, uuid.UUID, int | None, uuid.UUID, datetime], Awaitable[None]
]
"""`(session, class_session_id, minutes or None, user_id, now)`: stores the time limit (None
switches the timed sitting off), in the transaction of «Lagre Klasseøkt» under the row lock."""

_test_sitting: list[tuple[TestSittingReader, TestSittingWriter]] = []


def register_test_sitting(read: TestSittingReader, write: TestSittingWriter) -> None:
    """Register where the Individual test's one timed sitting is kept (Story 11.12: `tests`
    stores it), for a module `sessions` may not import. One pair; registering again replaces it."""
    _test_sitting[:] = [(read, write)]


async def _sitting_minutes(s: AsyncSession, class_session_id: uuid.UUID) -> int | None:
    """The Class session's time limit through the registered reader; None without one."""
    return await _test_sitting[0][0](s, class_session_id) if _test_sitting else None


def _judge_sitting(minutes: int | None) -> None:
    """Raises `InvalidSessionValues` for a time limit outside the configured range (Story 11.12;
    `test_sitting_minutes` `out_of_range`). None (switched off) is always allowed."""
    settings = get_settings()
    if minutes is not None and not (
        settings.test_sitting_min_minutes <= minutes <= settings.test_sitting_max_minutes
    ):
        raise InvalidSessionValues({"test_sitting_minutes": "out_of_range"})


async def debrief_session_of(
    s: AsyncSession, user: authz.Principal, class_session_id: uuid.UUID
) -> DebriefSession | None:
    """The Class session for the User's Debrief, read in `s`: one of their own
    (`authz.classes_enrolled_by`), in a Class Hjem lists, and locked; None for every other case
    alike (FR-5), as `_own_locked_game` judges a game."""
    row = await enrolled_locked_row(s, user, class_session_id)
    if row is None:
        return None
    return DebriefSession(
        id=row["id"],
        class_id=row["class_id"],
        hold=row["debrief_release"] == DebriefRelease.hold.value,
        group=row["debrief_mode"] == DebriefMode.group.value,
    )


async def makeup_session_row(
    s: AsyncSession, class_session_id: uuid.UUID, user_id: uuid.UUID, *, share: bool = False
) -> Mapping[str, Any] | None:
    """The whole Class session row with the Student's own deadlines, read in `s` (share-locked
    with `share`, so its snapshot and Test deadline hold while an Oppfølgingsspill is made, Story
    13.4); None for no such session. The caller has reached the Student through `student_target`
    and reads the row only through `effective_test_deadline` and its frozen `snapshot`."""
    row = await repo.session_row(s, class_session_id, share=share)
    return None if row is None else await _student_row(s, row, user_id)


async def own_report_session(
    s: AsyncSession, user: authz.Principal, class_session_id: uuid.UUID
) -> Mapping[str, Any] | None:
    """The Class session row with the Student's own deadlines for their own Student report (Story
    13.7), read in `s`; under `enrolled_locked_row`'s checks, None for every other case alike
    (FR-5). The caller reads the deadline only through `report_opens_at`."""
    if await enrolled_locked_row(s, user, class_session_id) is None:
        return None
    row = await repo.session_row(s, class_session_id)
    return None if row is None else await _student_row(s, row, user.id)


def report_opens_at(user: authz.Principal | uuid.UUID, row: Mapping[str, Any]) -> datetime | None:
    """When the Student's report opens to them (Story 13.7, FR-57, UX-DR29): their effective
    Test deadline; None while the Class session has none. Staff may download it at any time
    (Story 13.12)."""
    return effective_test_deadline(user, row)


def data_deleted(row: Mapping[str, Any], now: datetime) -> bool:
    """Whether the Class session's Student data counts as deleted (Story 13.12, FR-57, FR-77):
    its deletion date (Story 13.9) has come, on the Oslo calendar. The staff's report action says
    so and builds nothing."""
    if row.get("data_deleted_at") is not None:  # retention ran (Story 15.3): for good
        return True
    deletion = row.get("deletion_date")
    return deletion is not None and now.astimezone(OSLO).date() >= deletion


async def session_student_names(
    row: Mapping[str, Any], user_ids: list[uuid.UUID], session: AsyncSession | None = None
) -> dict[uuid.UUID, str]:
    """`classes.student_names` for the Class session `row`'s Class, or none once its Student data
    counts as deleted (Story 15.3, FR-77): a Student who keeps the account (a later Class session
    of the same Class) is then named nowhere in this Class session's views or mails, which show
    each Seat by Role, as the staff game views of `overview` do."""
    if not user_ids or data_deleted(row, auth.utcnow()):
        return {}
    return await classes.student_names(row["class_id"], user_ids, session=session)


@dataclass(frozen=True)
class ReportHeading:
    """What the Student report's header says of the Class session (Story 13.7, FR-58): the Class,
    its number, whether it is obligatory, and the dates, the Student's own Debrief and Test
    deadlines."""

    class_id: uuid.UUID
    class_name: str
    number: int
    obligatory: bool
    start_at: datetime | None
    play_deadline: datetime | None
    debrief_deadline: datetime | None
    test_deadline: datetime | None


async def report_heading(
    s: AsyncSession, class_session_id: uuid.UUID, user_id: uuid.UUID
) -> ReportHeading | None:
    """The report header's Class session part for `user_id`, read in `s`; None for no such
    session or Class. The caller (`reports.build_report_data`) runs after the policy allowed the
    request."""
    row = await repo.session_row(s, class_session_id)
    if row is None:
        return None
    label = await classes.label_of_class(s, row["class_id"])
    if label is None:
        return None
    own = await _student_row(s, row, user_id)
    return ReportHeading(
        class_id=row["class_id"],
        class_name=label.name,
        number=await repo.number_of(s, class_session_id, row["class_id"]),
        obligatory=row["obligatory"],
        start_at=row["start_at"],
        play_deadline=row["play_deadline"],
        debrief_deadline=effective_debrief_deadline(user_id, own),
        test_deadline=effective_test_deadline(user_id, own),
    )


async def student_deadlines(
    user_id: uuid.UUID, class_session_id: uuid.UUID
) -> tuple[datetime | None, datetime | None]:
    """The Student's effective Debrief and Test deadlines in the Class session (Story 9.8): read
    through `effective_debrief_deadline` and `effective_test_deadline`, so another module never
    reads the dates itself. (None, None) for a session that does not exist."""
    async with get_sessionmaker()() as s:
        found = await repo.session_row(s, class_session_id)
        row = None if found is None else await _student_row(s, found, user_id)
    if row is None:
        return None, None
    return effective_debrief_deadline(user_id, row), effective_test_deadline(user_id, row)


# One Student's own Test deadline (Story 11.13, FR-18, AD-8, AD-9, AD-12, AD-15).

DEADLINE_EXTENSION_SAVED = "deadline_extension.saved"
"""The audit action of «Lagre frist»: target the Class session and the Student, change the new
Test and Debrief deadlines and the ones before (ids and times only, AD-15)."""


class InvalidExtension(Exception):
    """422 `invalid_extension`: `fields.test_deadline` says why the date is refused:
    `no_test_deadline` (the Class session has none to extend), `not_later` (not after the Class
    session's Test deadline: an extension only ever extends) or `passed` (not after now)."""

    code = "invalid_extension"

    def __init__(self, reason: str) -> None:
        super().__init__(self.code)
        self.fields = {"test_deadline": reason}


@dataclass(frozen=True)
class StudentTarget:
    """A Student of a Class session as their Studentside reaches them (Story 8.9): the Class
    session row, its Class and the Student's Roster name now."""

    row: Mapping[str, Any]
    class_id: uuid.UUID
    class_name: str
    name: str
    can_manage: bool
    """Story 12.5: whether `user` may also manage the Class's sessions (`class_sessions.manage`:
    an owner), so the Studentside shows «Tilrettelegging» and «Frister»."""


async def student_target(
    user: authz.Principal,
    class_session_id: uuid.UUID,
    user_id: uuid.UUID,
    action: str = "class_sessions.manage",
) -> StudentTarget | None:
    """The Student `user_id` of the Class session when `user` may do the Class action `action`
    on its Class's sessions (by default `class_sessions.manage`: a Lecturer of the Class, never an
    Assistant lecturer) and `user_id` is a Student of the Class now; None, one answer, for
    anything else (FR-5, AD-12). The Studentside and its record (Stories 8.9, 13.2;
    `student_pages.read` from Story 12.5), a deadline extension (Story 11.13) and the staff's AI
    assessment (Story 12.5, `ai_assessments.read`) are reached only so."""
    if action not in authz.CLASS_STAFF_ROLES:
        # A Class action only; an unknown one refuses (one answer) rather than raise.
        log.warning("student_target_unknown_action", action=action)
        return None
    async with get_sessionmaker()() as s:
        row = await repo.session_row(s, class_session_id)
    if row is None:
        return None
    found = await _class_for(user, row["class_id"], action)
    if found is None:
        return None
    names = await classes.student_names(row["class_id"], [user_id])
    if user_id not in names:
        return None
    return StudentTarget(
        row=row,
        class_id=found.id,
        class_name=found.name,
        name=names[user_id],
        can_manage=authz.can(user, "class_sessions.manage", found),
    )


async def session_students(class_session_id: uuid.UUID) -> dict[uuid.UUID, str]:
    """The Students of the Class session's Class now (registered, not removed) with their Roster
    names, read at request time (AD-14): the Klasseøkt's list of AI assessments (Story 12.5). The
    caller has judged that the asking User may read them. Empty for an unknown session."""
    async with get_sessionmaker()() as s:
        row = await repo.session_row(s, class_session_id)
    if row is None:
        return {}
    students = await classes.registered_students(row["class_id"])
    return await session_student_names(row, students)


async def deadlines_out(
    s: AsyncSession, row: Mapping[str, Any], user_id: uuid.UUID
) -> StudentDeadlinesOut:
    """The block «Frister» of the Student's Studentside (Story 11.13), read in `s`."""
    student = await _student_row(s, row, user_id)
    done = await progress.steps_of(s, user_id, [row["id"]])
    test = effective_test_deadline(user_id, student)
    return StudentDeadlinesOut(
        class_debrief_deadline=row["debrief_deadline"],
        class_test_deadline=row["test_deadline"],
        debrief_deadline=effective_debrief_deadline(user_id, student),
        test_deadline=test,
        # Extended while the own date is still the later one: a Class date moved past it since
        # makes the Student's date the Class's again.
        extended=test is not None and test != row["test_deadline"],
        submitted=progress.Step.TEST_SUBMITTED in done.get(row["id"], set()),
    )


async def save_extension(
    s: AsyncSession,
    actor: uuid.UUID,
    class_session_id: uuid.UUID,
    user_id: uuid.UUID,
    test_deadline: datetime,
    now: datetime,
) -> Mapping[str, Any]:
    """Store the Student's own Test deadline (Story 11.13, FR-18), for
    `tests.commands.extend_deadline` in its transaction: the Class session row locked, its
    Class writable (`ClassArchived`), the date judged (`InvalidExtension`), the Student's extension
    row locked, then upserted with the Debrief deadline moved by the same amount (NULL when the
    Class session has none), and the change recorded in the audit log. The caller has judged the
    target (`student_target`). Returns the Class session row with the Student's own deadlines, as
    `effective_test_deadline` reads it. The Class session's deletion date is stored again (Story
    13.9) under its row lock, taken here. Nothing is logged."""
    row = await repo.session_row(s, class_session_id, lock=True)
    if row is None:
        raise LookupError("no such Class session")
    await _writable(s, row["class_id"])
    class_test: datetime | None = row["test_deadline"]
    if class_test is None:
        raise InvalidExtension("no_test_deadline")
    if test_deadline <= class_test:
        raise InvalidExtension("not_later")
    if test_deadline <= now:
        raise InvalidExtension("passed")
    was = await repo.extension_row(s, class_session_id, user_id, lock=True)
    class_debrief: datetime | None = row["debrief_deadline"]
    debrief = None if class_debrief is None else class_debrief + (test_deadline - class_test)
    await repo.save_extension(
        s,
        class_session_id=class_session_id,
        user_id=user_id,
        test_deadline=test_deadline,
        debrief_deadline=debrief,
        updated_by=actor,
        updated_at=now,
    )
    # Story 13.9: an extension past the latest one moves the deletion date, in this transaction.
    await _store_deletion_date(s, class_session_id, class_test)
    await audit.record(
        s,
        actor,
        DEADLINE_EXTENSION_SAVED,
        {"class_session_id": class_session_id, "user_id": user_id},
        {
            "test_deadline": test_deadline.isoformat(),
            "debrief_deadline": None if debrief is None else debrief.isoformat(),
            "was": None
            if was is None
            else {
                "test_deadline": was["test_deadline"].isoformat(),
                "debrief_deadline": None
                if was["debrief_deadline"] is None
                else was["debrief_deadline"].isoformat(),
            },
        },
        now,
    )
    return await _student_row(s, row, user_id)


# The deletion date (Story 13.9, FR-77, FR-57, AD-9).


def retention_months() -> int:
    """The configured placeholder retention period in calendar months (`RETENTION_MONTHS`,
    FR-77): what applies while an Institution has set none (Story 15.3)."""
    return get_settings().retention_months


async def retention_months_of_class(s: AsyncSession, class_id: uuid.UUID) -> int:
    """The retention period of the Class's Institution (Story 15.3, FR-77, AD-27): its own, set by
    the Admin, or the placeholder. A Control test's Class belongs to the operator-owned
    Institution, so it follows that Institution's period, never a course Institution's."""
    facts = (await classes.class_facts(s, [class_id])).get(class_id)
    return await identity.retention_months_of(facts.institution_id if facts else None, s)


async def _store_deletion_date(
    s: AsyncSession, class_session_id: uuid.UUID, test_deadline: datetime | None
) -> date | None:
    """Store the Class session's deletion date (Story 13.9, FR-77): `platform.retention` over its
    latest effective Test deadline, `test_deadline` (the Class session's, as just saved) or the
    latest Student extension where that is later, plus its Institution's retention period (Story
    15.3), read in `s`. The one writer of the column; every Test deadline save, every extension
    and every change of the Institution's period calls it in its own transaction, under the
    Class session's row lock, so no Student's data can fall due before their own period has
    run. Returns the date stored."""
    row = await repo.session_row(s, class_session_id)
    if row is not None and data_deleted(row, auth.utcnow()):
        # Epic 15 close-out: once the date has come (or retention ran) it stays, so a date saved
        # later cannot bring the names back or stop a retention run half-way.
        return row["deletion_date"]
    latest = retention.latest_test_deadline(
        test_deadline, await repo.extension_test_deadlines(s, class_session_id)
    )
    if row is not None:
        # Without a Test deadline the latest other date counts (`retention.deletion_base`).
        latest = retention.deletion_base(
            latest, [row["debrief_deadline"], row["play_deadline"], row["start_at"]]
        )
    months = await retention_months_of_class(s, row["class_id"]) if row else retention_months()
    deletion = retention.deletion_date(latest, months)
    await repo.set_deletion_date(s, class_session_id, deletion)
    return deletion


async def _redate_institution(s: AsyncSession, institution_id: uuid.UUID, now: datetime) -> None:
    """Story 15.3 (FR-77): in the transaction that changed the Institution's retention period,
    recompute the deletion date of each of its Class sessions whose date has not come yet (or
    that has none), under each row's lock. A Class session whose date has come keeps it: its
    Student data counts as deleted already (`data_deleted`), and retention may be running."""
    today = now.astimezone(OSLO).date()
    class_ids = await classes.class_ids_of_institution(s, institution_id)
    for class_session_id in await repo.session_ids_of_classes(s, class_ids):
        row = await repo.session_row(s, class_session_id, lock=True)
        if row is None or row["data_deleted_at"] is not None:
            continue
        if row["deletion_date"] is not None and row["deletion_date"] <= today:
            continue
        await _store_deletion_date(s, class_session_id, row["test_deadline"])
        # Its Students' Hjem and the staff read the new date (Story 13.9's line).
        await events.emit(s, "session", str(class_session_id))
        for student in await classes.registered_students(row["class_id"]):
            await events.emit(s, "user", str(student))


identity.register_retention_listener("sessions", _redate_institution)


# Retention (Story 15.3, FR-77, AD-9, AD-14): what `ops.retention` reads and marks of a Class
# session. The deletion itself runs through `identity.erase_user`, the one shared routine.


@dataclass(frozen=True)
class RetentionTarget:
    """A Class session as retention reads it: its Class, its stored deletion date and when its
    Student data was deleted (None until retention finished)."""

    id: uuid.UUID
    class_id: uuid.UUID
    deletion_date: date | None
    data_deleted_at: datetime | None


async def due_retention(now: datetime) -> list[uuid.UUID]:
    """The Class sessions whose deletion date has come on the Oslo calendar and whose Student data
    retention has not finished deleting, the earliest date first."""
    async with get_sessionmaker()() as s:
        return await repo.due_retention(s, now.astimezone(OSLO).date())


async def retention_target(
    s: AsyncSession, class_session_id: uuid.UUID, *, lock: bool = False
) -> RetentionTarget | None:
    """The Class session for retention, or None; with `lock` its row is locked."""
    row = await repo.session_row(s, class_session_id, lock=lock)
    if row is None:
        return None
    return RetentionTarget(row["id"], row["class_id"], row["deletion_date"], row["data_deleted_at"])


async def retention_targets_of_classes(
    s: AsyncSession, class_ids: list[uuid.UUID]
) -> list[RetentionTarget]:
    """Every Class session of these Classes, as retention reads them."""
    return [
        RetentionTarget(row["id"], row["class_id"], row["deletion_date"], row["data_deleted_at"])
        for row in await repo.retention_rows_of_classes(s, class_ids)
    ]


async def mark_data_deleted(s: AsyncSession, class_session_id: uuid.UUID, now: datetime) -> None:
    """Retention finished deleting the Class session's Student data (set once)."""
    await repo.mark_data_deleted(s, class_session_id, now)
    await events.emit(s, "session", str(class_session_id))


async def refresh_deletion_date(s: AsyncSession, class_session_id: uuid.UUID) -> date | None:
    """`_store_deletion_date` from the stored Test deadline, for a path that moved it outside the
    Class session save (the local dev route of Story 13.7). The caller holds the row lock."""
    row = await repo.session_row(s, class_session_id)
    if row is None:
        return None
    return await _store_deletion_date(s, class_session_id, row["test_deadline"])


async def own_test_deadlines(
    s: AsyncSession, class_session_id: uuid.UUID
) -> dict[uuid.UUID, datetime]:
    """Each Student's own Test deadline in the Class session, by Student, read in `s` (Story
    11.13): what `tests.move_deadline` keeps when the Class session's Test deadline moves."""
    rows = await repo.extensions_of_session(s, class_session_id)
    return {user_id: row["test_deadline"] for user_id, row in rows.items()}


async def class_staff_may(user: authz.Principal, class_session_id: uuid.UUID, action: str) -> bool:
    """Whether `user` may do the Class action `action` on the Class of the Class session (its
    staff role there, `authz.can`): how another module asks without reading Classes itself
    (Story 9.3: `explanations.read`). False for a session that does not exist."""
    async with get_sessionmaker()() as s:
        row = await repo.session_row(s, class_session_id)
    if row is None:
        return False
    return await _class_for(user, row["class_id"], action) is not None


async def staff_session_row(
    user: authz.Principal, class_session_id: uuid.UUID, action: str
) -> Mapping[str, Any] | None:
    """The Class session's row when `user` may do the Class action `action` on its Class (Story
    13.13: the ZIP of all Student reports, `reports.download`); None, one answer, for anything
    else, a session that does not exist included (FR-5, AD-12)."""
    if action not in authz.CLASS_STAFF_ROLES:
        log.warning("staff_session_unknown_action", action=action)
        return None
    async with get_sessionmaker()() as s:
        row = await repo.session_row(s, class_session_id)
    if row is None or await _class_for(user, row["class_id"], action) is None:
        return None
    return row


async def session_row(
    session: AsyncSession, class_session_id: uuid.UUID
) -> Mapping[str, Any] | None:
    """The Class session's row in the caller's `session`, None for none: for a job that runs after
    the policy allowed its request (Story 13.13 reads the deletion date again)."""
    return await repo.session_row(session, class_session_id)


REPORTS_ZIP_READY_NOTICE = "reports_zip_ready"
"""The notice kind the staff member who asked for the ZIP of all Student reports gets once it is
ready, `immediate` (Story 13.13, FR-59, AD-9). Its `ref` is the Class session."""


async def reports_zip_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of a `reports_zip_ready` notice, for `messaging` at send time: the
    Class's name and the Class session's number. None, so the mail is left out, when the Class
    session or its Class is gone. The mail holds no Student data and no link to the file: the
    download asks the policy again (AD-12)."""
    if ref is None:
        return None
    row = await repo.session_row(session, ref)
    if row is None:
        return None
    label = await classes.label_of_class(session, row["class_id"])
    if label is None:
        return None
    return {
        "class_name": label.name,
        "session_number": await repo.number_of(session, ref, row["class_id"]),
    }


@dataclass(frozen=True)
class QuizSession:
    """A Class session as the Debrief quiz's staff block reads it (Story 9.10): the pins its lock
    stored (None before the lock), its Test deadline, and whether the User may take questions out
    (an owner of a Class that is not archived)."""

    id: uuid.UUID
    class_id: uuid.UUID
    pins: Any
    test_deadline: datetime | None
    can_exclude: bool


async def quiz_session(user: authz.Principal, class_session_id: uuid.UUID) -> QuizSession | None:
    """The Class session for its staff's Debrief quiz block (`debrief_quiz.read`); None for
    every other caller and for a session that does not exist alike (FR-5)."""
    async with get_sessionmaker()() as s:
        row = await repo.session_row(s, class_session_id)
        pins = await repo.session_pins(s, class_session_id) if row is not None else None
    if row is None:
        return None
    found = await _class_for(user, row["class_id"], "debrief_quiz.read")
    if found is None:
        return None
    return QuizSession(
        id=row["id"],
        class_id=row["class_id"],
        pins=pins,
        test_deadline=row["test_deadline"],
        can_exclude=authz.can(user, "debrief_quiz.exclude", found) and not found.archived,
    )


async def lock_for_quiz_exclusions(
    s: AsyncSession, class_session_id: uuid.UUID
) -> tuple[Any, datetime | None]:
    """In the caller's transaction (Story 9.10): locks the Class session row, refuses an archived
    Class (`classes.ClassArchived`, 409 `class_archived`) and answers the pins its lock stored
    (None before the lock) with its Test deadline. The caller has checked
    `debrief_quiz.exclude`."""
    row = await repo.session_row(s, class_session_id, lock=True)
    if row is None:
        raise LookupError(f"no Class session {class_session_id}")
    await _writable(s, row["class_id"])
    return await repo.session_pins(s, class_session_id), row["test_deadline"]


@dataclass(frozen=True)
class QuestionSetSession:
    """A Class session as the «Spørsmål og vekter» block reads it (Story 11.1): its row (the
    Start date, the lock), the pins its lock stored (None before) and whether the User may change
    the selection (an owner of a Class that is not archived)."""

    id: uuid.UUID
    row: Mapping[str, Any]
    pins: Any
    may_change: bool
    """An owner of the Class (`question_set.change`)."""
    can_change: bool
    """An owner, and the Class is not archived."""


async def question_set_session(
    user: authz.Principal,
    class_session_id: uuid.UUID,
    change_action: str = "question_set.change",
) -> QuestionSetSession | None:
    """The Class session for its staff's «Spørsmål og vekter» block (`class_sessions.read`); None
    for every other caller and for a session that does not exist alike (FR-5). `may_change` and
    `can_change` answer `change_action`: the «Sensorveiledning» block (Story 11.2) asks
    `scoring_guide.change`."""
    async with get_sessionmaker()() as s:
        row = await repo.session_row(s, class_session_id)
        pins = await repo.session_pins(s, class_session_id) if row is not None else None
    if row is None:
        return None
    found = await _class_for(user, row["class_id"], "class_sessions.read")
    if found is None:
        return None
    return QuestionSetSession(
        id=row["id"],
        row=row,
        pins=pins,
        may_change=authz.can(user, change_action, found),
        can_change=authz.can(user, change_action, found) and not found.archived,
    )


async def lock_for_question_set(
    s: AsyncSession, class_session_id: uuid.UUID, *, now: datetime
) -> Mapping[str, Any]:
    """In the caller's transaction (Story 11.1): locks the Class session row, refuses an archived
    Class (`classes.ClassArchived`, 409 `class_archived`) and a session past its Start-date lock
    point (`SessionLocked`, 409 `session_locked`, FR-18), and answers the row. The caller has
    checked `question_set.change`."""
    row = await repo.session_row(s, class_session_id, lock=True)
    if row is None:
        raise LookupError(f"no Class session {class_session_id}")
    await _writable(s, row["class_id"])
    if is_locked(row, now=now):
        raise SessionLocked({"question_set": "locked"})
    return row


def test_deadline_reached(row: Mapping[str, Any], now: datetime) -> bool:
    """Whether the Class session's original Test deadline has passed at `now`, or the
    Test-deadline lock has run (Story 11.2, FR-18): what hangs on that deadline no longer
    changes, also in the minute before the sweep runs `lock_test`. Never for a session without
    a Test deadline that has not been test-locked."""
    if row["test_locked_at"] is not None:
        return True
    deadline = row["test_deadline"]
    return deadline is not None and deadline <= now


async def lock_for_scoring_guide(
    s: AsyncSession, class_session_id: uuid.UUID, *, now: datetime
) -> Mapping[str, Any]:
    """In the caller's transaction (Story 11.2): locks the Class session row, refuses an archived
    Class (`classes.ClassArchived`, 409 `class_archived`) and a session whose original Test
    deadline has passed (`ScoringGuideLocked`, 409 `scoring_guide_locked`, FR-18), and answers
    the row. The row lock keeps `lock_test` out meanwhile. The caller has checked
    `scoring_guide.change` (through `question_set_session`'s `may_change`)."""
    row = await repo.session_row(s, class_session_id, lock=True)
    if row is None:
        raise LookupError(f"no Class session {class_session_id}")
    await _writable(s, row["class_id"])
    if test_deadline_reached(row, now):
        raise ScoringGuideLocked({"scoring_guide": "locked"})
    return row


async def student_name(class_session_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
    """The Student's name on the Roster of the Class session's Class now (Story 9.10), read at
    request time and never stored (AD-14); None when they are no longer a Student of it. The
    caller has checked that the User may read the Class's Students."""
    async with get_sessionmaker()() as s:
        row = await repo.session_row(s, class_session_id)
        if row is None:
            return None
        names = await session_student_names(row, [user_id], session=s)
    return names.get(user_id)


async def held_debrief_sessions(s: AsyncSession) -> list[uuid.UUID]:
    """The locked Class sessions that hold their Debriefs (Story 9.2), for the sweep's release."""
    return await repo.held_debrief_sessions(s)


def _names_in(
    row: Mapping[str, Any], s: AsyncSession
) -> Callable[[list[uuid.UUID]], Awaitable[dict[uuid.UUID, str]]]:
    """`session_student_names` for the Class session `row`: the names `table_status` shows, read
    now, in the caller's session `s` (one connection per request, `db.reading`); none once its
    Student data counts as deleted (Story 15.3)."""

    async def resolve(user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        return await session_student_names(row, user_ids, session=s)

    return resolve


async def _student_card(
    s: AsyncSession, user_id: uuid.UUID, row: Mapping[str, Any], done: set[progress.Step]
) -> StudentGameOut | None:
    """The Student's game in a locked Class session, through `games.service.student_game` and
    `table_status` (Story 6.1, AD-3): their Class game, or their finished Oppfølgingsspill (Story
    13.5); None with neither."""
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
    # Story 8.11: the reader's own Tilrettelegging factor gives their own «I rommet» minutes, the
    # line Hjem shows as Spill does (Epic 8 close-out).
    own_factor = (await time_factors(s, found.class_session_id, [user_id])).get(user_id)
    table = await games_service.table_status(
        s, found.game_id, user_id, _names_in(row, s), factor=own_factor
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
        replay=found.replay,
        makeup=found.makeup,
        class_session_id=found.class_session_id,
        seats=_seats_out(table),
        # Story 6.2: the briefing comes first until the Starting task is done (AD-16), where
        # `games.policy` says the pre-play gate applies (Story 6.18).
        briefing_first=found.pre_play_gate and progress.Step.STARTING_TASK not in done,
        rules=game_rules(row),
        status=play.status,
        end_reason=play.end_reason,
        week=play.week,
        server_now=await games_service.database_now(s),
        seat_state=state,
        turn=turn,
        time_proposal=await _time_proposal_out(s, user_id, found.game_id, row),
        # Story 8.2 (FR-17): a test Game counts toward no requirement.
        obligatory=bool(row.get("obligatory")) and not found.test_game,
        can_pause=table.can_pause,
        pause=_pause_out(table),
        in_room=_in_room_out(table),
        played_out=play.played_out,
        # Story 9.2: a Lecturer's test Game has no Debrief (Story 6.20), nor has a Replay (10.4);
        # an Oppfølgingsspill has the Student's once it is their game (Story 13.5).
        debrief=(
            await _debrief_of(s, user_id, row) if await _has_debrief(s, user_id, found) else None
        ),
    )


async def _has_debrief(
    s: AsyncSession, user_id: uuid.UUID, found: games_service.StudentGame
) -> bool:
    """Whether a game card states the Student's Debrief: their Class game, or their
    Oppfølgingsspill once it has become their game (`student_game`, Story 13.5); never a test
    Game or a Replay."""
    if found.test_game or found.replay:
        return False
    if not found.makeup:
        return True
    theirs = await games_service.student_game(s, user_id, found.class_session_id)
    return theirs is not None and theirs.game_id == found.game_id


async def _time_proposal_out(
    s: AsyncSession, user_id: uuid.UUID, game_id: uuid.UUID, row: Mapping[str, Any]
) -> TimeProposalOut | None:
    """The game's open proposal of a time to play as the reader sees it (Story 6.19, FR-22):
    the names read now, never stored (AD-14)."""
    proposal = await games_service.open_time_proposal(s, game_id)
    if proposal is None:
        return None
    names = await _names_in(row, s)([proposal.proposed_by, *proposal.accepted_by])

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


def _in_room_out(table: games_service.TableStatus) -> InRoomOut | None:
    """The «I rommet» line (Story 8.11) with the reader's own minutes; None while not marked."""
    if table.in_room is None:
        return None
    return InRoomOut(until=table.in_room.until, minutes=table.in_room.minutes)


def _pause_out(table: games_service.TableStatus) -> PauseOut | None:
    """The pause line (Story 8.6) as the reader sees it."""
    pause = table.pause
    if pause is None:
        return None
    return PauseOut(
        state=pause.state,
        name=pause.name,
        mine=pause.mine,
        staff=pause.staff,
        resume_at=pause.resume_at,
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
            taken_over=seat.taken_over,
            ordering_for=seat.ordering_for,
            guard_switched=seat.guard_switched,
            reclaim_queued=seat.reclaim_queued,
            insert_at=seat.insert_at,
            insert_agreed=seat.insert_agreed,
            can_insert=seat.can_insert,
            inserted_by=seat.inserted_by,
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
    if found.replay:
        # The Replay (Story 10.4) runs on its own drawn settings: its rules are the Game's own,
        # never the Class game's (`game_rules`). The read opens a session of its own, so `s`'s
        # connection goes back first (`db.reading`).
        await s.commit()
        game = await games_service.get_game(str(found.game_id))
        if game is None or game.settings is None:
            return None
        return found, {**row, "snapshot_settings": game.settings.model_dump(mode="json")}
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
        # Story 8.11: the reader's own Tilrettelegging factor gives their own «I rommet» minutes.
        own_factor = (await time_factors(s, found.class_session_id, [user.id])).get(user.id)
        table = await games_service.table_status(
            s, found.game_id, user.id, _names_in(row, s), factor=own_factor
        )
        state, turn = await _own_week(s, found, play.week)
        now = await games_service.database_now(s)
    return PlayOut(
        seat_state=state,
        turn=turn,
        table_status=TableStatusOut(
            seats=_seats_out(table),
            can_pause=table.can_pause,
            pause=_pause_out(table),
            in_room=_in_room_out(table),
        ),
        server_now=now,
        # Read again when an AI player's Order falls due (AD-8, AD-20); one already past is the
        # rescue loop's to place, and its event says so.
        next_change_at=next((due for due in table.due_times if due > now), None),
        # Story 10.4 (UX-DR19): the policy says whether the screen draws the projection.
        projection=found.projection,
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


BelievabilityRefused = games_service.BelievabilityRefused


async def _own_game_id(user: authz.Principal, game_id: str) -> uuid.UUID | None:
    async with get_sessionmaker()() as s:
        own = await _own_locked_game(s, user, game_id)
    return None if own is None else own[0].game_id


async def student_believability_of(
    user: authz.Principal, game_id: str
) -> games_service.Believability | None:
    """The believability question of the Student's own game (Story 10.8, FR-70), under
    `student_game_of`'s checks (None for every other id alike): whether they are asked and their
    own answer. Only ever the reader's own answer."""
    own = await _own_game_id(user, game_id)
    if own is None:
        return None
    return await games_service.believability(own, user.id)


async def rate_own_believability(
    user: authz.Principal, game_id: str, rating: int
) -> games_service.Believability | None:
    """Store the Student's believability answer for their own game once (Story 10.8, FR-70),
    under `student_game_of`'s checks (None for every other id alike). Raises
    `games_service.BelievabilityRefused` (`not_offered`, `already_answered`)."""
    own = await _own_game_id(user, game_id)
    if own is None:
        return None
    return await games_service.rate_believability(own, user.id, rating)


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


class ReclaimRefused(Exception):
    """A «Ta tilbake setet» the api refuses (Story 8.4), with the command's code: 409
    `seat_not_yours`, `game_finished` or `game_not_running`."""

    def __init__(self, code: str, status: int) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


async def reclaim_own_seat(user: authz.Principal, game_id: str, role: str) -> StudentGameOut | None:
    """«Ta tilbake setet» (Story 8.4, FR-37, AD-2): the Student asks for the Seat `role` of their
    own Class game back, under `student_game_of`'s checks (None for every other game alike, FR-5).
    Only `games.commands.request_reclaim` queues it, with the Student as actor, so the Seat of
    another Student, or one no AI player took over from this Student, is refused there
    (`seat_not_yours`); a repeat changes nothing. Returns the game as it now stands."""
    async with get_sessionmaker()() as s:
        own = await _own_locked_game(s, user, game_id)
    if own is None:
        return None
    found, _ = own
    try:
        await games_commands.request_reclaim(str(found.game_id), role, actor=user.id)
    except games_commands.CommandError as refused:
        if refused.status == 404:
            return None
        raise ReclaimRefused(refused.code, refused.status) from None
    return await student_game_of(user, game_id)


class InsertRefused(Exception):
    """A «Sett inn KI-spiller for …» the api refuses (Story 8.8), with the command's code, status
    and fields: 409 `takeover_exists` (with `acted_by` and `acted_at`), `insert_not_allowed_yet`,
    `seat_not_yours`, `order_exists`, `seat_not_student_held`, `game_not_running` or
    `takeover_not_allowed`."""

    def __init__(self, code: str, status: int, fields: dict[str, Any]) -> None:
        super().__init__(code)
        self.code = code
        self.status = status
        self.fields = fields


async def insert_ai_player(user: authz.Principal, game_id: str, role: str) -> StudentGameOut | None:
    """«Sett inn KI-spiller for Jonas» (Story 8.8, FR-89, FR-37, AD-2, AD-12, AD-20): the Student
    puts an AI player in the Seat `role` of their own Class game, under `student_game_of`'s checks
    (None for every other game alike, FR-5). Only `games.commands.takeover` decides, with the
    Student as `peer` actor: they must hold another Seat of the game and the Seat's insert time
    must have passed (`rules.can_take_over`). Nothing a Student sends sets or moves a time. A
    refusal's `fields` never carry a staff member's id. Returns the game as it now stands."""
    async with get_sessionmaker()() as s:
        own = await _own_locked_game(s, user, game_id)
    if own is None:
        return None
    found, _ = own
    try:
        await games_commands.takeover(str(found.game_id), role, actor="peer", actor_user_id=user.id)
    except games_commands.CommandError as refused:
        if refused.status == 404:
            return None
        raise InsertRefused(refused.code, refused.status, _student_fields(refused.fields)) from None
    return await student_game_of(user, game_id)


class PauseRefused(Exception):
    """A «Ta pause» the api refuses (Story 8.6), with the command's code, status and fields: 409
    `already_paused` (with `acted_by` and `acted_at`), `seat_not_yours`, `game_finished`,
    `game_not_running` or `pause_not_allowed`."""

    def __init__(self, code: str, status: int, fields: dict[str, Any]) -> None:
        super().__init__(code)
        self.code = code
        self.status = status
        self.fields = fields


async def pause_own_game(user: authz.Principal, game_id: str) -> StudentGameOut | None:
    """«Ta pause uten avtalt tid» (Story 8.6, FR-89, AD-2): the Student pauses their own Class
    game, under `student_game_of`'s checks (None for every other game alike, FR-5). Only
    `games.commands.pause` writes it, with the Student as actor, so a Student who holds no Seat of
    the game now is refused there (`seat_not_yours`), and a second Pause answers `already_paused`
    with who paused first, by id. A Student never sets a time. Returns the game as it now
    stands."""
    async with get_sessionmaker()() as s:
        own = await _own_locked_game(s, user, game_id)
    if own is None:
        return None
    found, _ = own
    try:
        await games_commands.pause(str(found.game_id), actor=user.id)
    except games_commands.CommandError as refused:
        if refused.status == 404:
            return None
        raise PauseRefused(refused.code, refused.status, _student_fields(refused.fields)) from None
    return await student_game_of(user, game_id)


def _student_fields(fields: Mapping[str, Any]) -> dict[str, Any]:
    """A refusal's `fields` as a Student may read them (Story 8.7): a Pause a staff member set
    names no one to the Students, so its `acted_by` keeps the kind and drops the staff id."""
    found = dict(fields)
    acted = found.get("acted_by")
    if isinstance(acted, Mapping) and acted.get("kind") == "staff":
        found["acted_by"] = {**acted, "user_id": None}
    return found


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
        # The Student is stored as the one who started it (Story 8.10).
        await games_commands.start(str(found.game_id), actor=user.id)
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
    # A test Game has no group to agree a time with (Story 6.20), nor has an own round.
    if own is None or own[0].test_game or own[0].replay or own[0].makeup:
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
    if own is None or own[0].test_game or own[0].replay or own[0].makeup:
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
    names = await session_student_names(row, [proposal.proposed_by])
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
        if own is None or own[0].test_game or own[0].replay:
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
    # Story 8.11: a Class game marked «I rommet» for it follows the new end, or ends its mark when
    # the Lab hour is no longer on.
    await games_service.lab_hour_changed(lab_hour_id, stored["starts_at"], stored["ends_at"], now)
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
    # Story 8.11: a Class game marked «I rommet» for it is no longer in the room.
    await games_service.lab_hour_changed(lab_hour_id, None, None, now)
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


async def takeover_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of a `takeover_notice`, for `messaging` at send time (Story 8.2,
    FR-36, FR-17, AD-9): the Class's name, the game number, the Seat's Role, whether the reader is
    the Student whose Seat it was (`own`), that Student's name for the others (None when no longer
    in the Class), and whether the Class session is obligatory. Never a number of Uker (FR-14).
    None, so the notice is left out, when the row is no Takeover, the Class is archived or the
    User is no longer a registered Student of it."""
    if ref is None:
        return None
    info = await games_service.takeover_of(session, ref)
    if info is None:
        return None
    row = await repo.session_row(session, info.class_session_id)
    if row is None:
        return None
    label = await classes.label_of_class(session, row["class_id"])
    if label is None or label.archived:
        return None
    if user_id not in await classes.registered_students(row["class_id"]):
        return None
    own = info.student == user_id
    names = (
        await session_student_names(row, [info.student])
        if info.student is not None and not own
        else {}
    )
    return {
        "class_name": label.name,
        "game_number": info.number,
        "role": info.role,
        "own": own,
        "student": names.get(info.student) if info.student is not None else None,
        "obligatory": bool(row["obligatory"]),
    }


async def turn_reminder_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of a `turn_reminder`, for `messaging` when the digest is built
    (Story 8.13, FR-27, FR-14, AD-9): the Class's name, the game number and the Seat's Role.
    Never a number of Uker, demand or another Seat's numbers. None, so the game is left out of
    the mail, when the game no longer waits for the User on that turn
    (`games.service.turn_reminder_of`: they ordered, the Seat was taken over, the Week moved on,
    the game no longer runs), the Class is archived or the User is no longer a registered
    Student of it."""
    if ref is None:
        return None
    info = await games_service.turn_reminder_of(session, ref, user_id)
    if info is None:
        return None
    row = await repo.session_row(session, info.class_session_id)
    if row is None:
        return None
    label = await classes.label_of_class(session, row["class_id"])
    if label is None or label.archived:
        return None
    if user_id not in await classes.registered_students(row["class_id"]):
        return None
    return {"class_name": label.name, "game_number": info.number, "role": info.role}


async def quiz_changed_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of a `quiz_changed` notice (Story 9.10): the Class's name, under
    the same rules as `debrief_released_mail_context`. None, so the notice is left out, once the
    quiz no longer counts as changed for the Student (they tried again, passed, or the exclusion
    was lifted before the digest left)."""
    if ref is None or not await _quiz_changed_now(session, user_id, ref):
        return None
    return await debrief_released_mail_context(session, user_id, ref, now)


async def _quiz_changed_now(
    s: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> bool:
    return bool(_quiz_changed) and await _quiz_changed[0](s, user_id, class_session_id)


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


async def _without_consent(
    row: Mapping[str, Any],
    students: list[uuid.UUID],
    session: AsyncSession | None = None,
) -> list[uuid.UUID]:
    """Those of `students` a Control test may not seat yet: no consent given on the current text
    (Story 12.8, FR-82, AD-27). None for a course."""
    if row["kind"] != authz.CONTROL_TEST_KIND or not students:
        return []
    async with reading(session) as s:
        given = await identity.consented_users(s, students)
    return [student for student in students if student not in given]


async def _seatable(
    row: Mapping[str, Any],
    students: list[uuid.UUID],
    session: AsyncSession | None = None,
) -> list[uuid.UUID]:
    """`students` less those a Control test may not seat yet, in their order (Story 12.8)."""
    missing = set(await _without_consent(row, students, session))
    return [student for student in students if student not in missing]


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
        out = await _opened_out(row["class_id"], draft, games, is_open=False, method=method)
    else:
        out = await _allocation_out(row["class_id"], draft, opened)
        out.method = method
    if out.draft is not None and data_deleted(row, auth.utcnow()):
        # Story 15.3: once the Student data counts as deleted each Seat shows by Role.
        for game in out.draft.games:
            for seat in game.seats:
                seat.name = None
    if row["kind"] == authz.CONTROL_TEST_KIND:  # Story 12.8
        registered = await classes.registered_students(row["class_id"])
        out.consent_missing = len(await _without_consent(row, registered))
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
        names = await session_student_names(row, without)
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
        # Story 12.8, after the lock and confirmed refusals: a Control test is drawn only once
        # every test student has consented.
        if (draft is None or again) and (missing := await _without_consent(row, students, s)):
            refused_consent = ConsentMissing(
                {"allocation": "consent_missing", "missing": str(len(missing))}
            )
            log.info(
                "allocation_refused",
                class_session_id=str(session_id),
                error_code=refused_consent.code,
                missing=len(missing),
            )
            raise refused_consent
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
        if draft["confirmed_at"] is None and (
            missing := await _without_consent(row, [uuid.UUID(r) for r in registered], s)
        ):
            refused_consent = ConsentMissing(
                {"allocation": "consent_missing", "missing": str(len(missing))}
            )
            _confirm_refused(session_id, refused_consent.code)
            raise refused_consent
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
# Story 9.9: the Debrief quiz.
register_pin_provider(content.Kind.DEBRIEF_QUIZ.value, content.debrief_quiz_pin)
# Story 9.14: the narration templates, and whether the Debrief shows AI text, with the model
# config and Effort level its calls use.
register_pin_provider(content.Kind.NARRATION_TEMPLATES.value, content.narration_templates_pin)
# Story 11.7: the Adapted item templates its Individual tests are built with.
register_pin_provider(content.Kind.ADAPTED_TEMPLATES.value, content.adapted_templates_pin)


DEBRIEF_AI_TEXT_PIN = "debrief_ai_text"
"""The pin of the Debrief's AI-text switch in `SessionRuntime.pins` (Story 9.14)."""

DEBRIEF_NARRATION = "debrief_narration"
"""The purpose a model config must name a prompt for before the Debrief uses it (Story 9.14)."""


async def debrief_ai_text_pin(session: AsyncSession, class_session: Mapping[str, Any]) -> Any:
    """The lock's pin provider (Story 9.14, FR-15, FR-44, AD-4): `{enabled, model_config_id,
    effort_level}`. On only when the Lecturer left the switch on and the Class session holds a
    model config whose `prompts` map names the Debrief's narration (a config made before Story
    9.14 does not: its Debrief stays code-only); that config is then marked referenced, so the
    prompts it names never change."""
    config_id = class_session.get("model_config_id")
    enabled = bool(class_session.get("debrief_ai_text", True)) and config_id is not None
    if enabled:
        found = await config.get(config_id, session=session)
        enabled = found is not None and DEBRIEF_NARRATION in found.spec.prompts
    if enabled:
        await config.mark_referenced(config_id, session=session)
    return {
        "enabled": enabled,
        "model_config_id": str(config_id) if enabled else None,
        "effort_level": class_session["effort_level"] if enabled else None,
    }


register_pin_provider(DEBRIEF_AI_TEXT_PIN, debrief_ai_text_pin)


REPLAY_TEMPLATE_PIN = "replay_template"
"""The pin of the Replay scenario template in `SessionRuntime.pins` (Story 10.1): the only template
a Replay of the Class session reads."""


def replay_template(class_session: Mapping[str, Any]) -> ReplayTemplate:
    """The Replay scenario template of a Class session row (Stories 10.1 and 10.2, FR-49, AD-4):
    once locked the one its lock pinned; otherwise, and for a session locked before Story 10.1,
    the own template when one is chosen, else the default derived from its Game settings, so an
    edit before the Start date never leaves a stale default."""
    snapshot = class_session.get("snapshot")
    pins = ((snapshot or {}).get("session_runtime") or {}).get("pins") or {}
    pinned = pins.get(REPLAY_TEMPLATE_PIN)
    if pinned is not None:
        return ReplayTemplate.model_validate(pinned)
    own = class_session.get("replay_template")
    if own is not None:
        return ReplayTemplate.model_validate(own)
    return default_replay_template(GameSettings.model_validate(class_session["game_settings"]))


async def replay_template_pin(session: AsyncSession, class_session: Mapping[str, Any]) -> Any:
    """The lock's pin provider (Stories 10.1 and 10.2, AD-4): the template in force as JSON, the
    own one where chosen and the default derived from the Game settings being frozen otherwise."""
    choice = class_session.get("replay_scenario", "default")
    if choice == "own":
        own = ReplayTemplate.model_validate(class_session["replay_template"])
        return own.model_dump(mode="json")
    if choice != "default":
        raise ValueError(f"unknown Replay scenario {choice!r}")
    settings = GameSettings.model_validate(class_session["game_settings"])
    return default_replay_template(settings).model_dump(mode="json")


REPLAY_EDITABLE = frozenset(
    {*RANGED_FIELDS, "demand", "holding_cost", "backorder_cost", "info_visibility"}
)
"""The template fields a Lecturer sets in an own Replay scenario (Story 10.2): every Game setting
the Klasseøkt edits, the seed aside (each Replay draws its own). The chain and capacity are the
Class session's. Information visibility is the Replay's own (Story 10.9), switched on only while
`FEATURE_INFO_VISIBILITY` is on."""


def class_game_template(settings: GameSettings) -> ReplayTemplate:
    """The Class game's exact settings as a template with no range (Story 10.2, FR-49): what an
    own scenario starts from, and what a draft that leaves a field out falls back to. A `step` or
    `step+noise` pattern is a template `step` with its spread (0 for `step`); a fixed series has
    no spread."""
    pattern = settings.demand
    demand: ReplayStep | ReplayRandom | ReplayFixed
    if isinstance(pattern, DemandStep | DemandStepNoise):
        demand = ReplayStep(
            kind="step",
            start=pattern.start,
            new_level=pattern.new_level,
            change_week=pattern.change_week,
            spread=getattr(pattern, "spread", 0),
        )
    elif isinstance(pattern, DemandRandom):
        demand = ReplayRandom(kind="random", mean=pattern.mean, spread=pattern.spread)
    else:
        demand = ReplayFixed(kind="fixed", values=pattern.values, spread=0)
    return default_replay_template(settings).model_copy(
        update={"demand": demand, "weeks": settings.weeks, "guided_weeks": settings.guided_weeks}
    )


def _low(value: Ranged) -> int:
    return value if isinstance(value, int) else value.minimum


def _high(value: Ranged) -> int:
    return value if isinstance(value, int) else value.maximum


def _peak(pattern: object) -> int:
    """The highest demand level of a Game's or a template's pattern, before any variation."""
    if isinstance(pattern, DemandStep | DemandStepNoise | ReplayStep):
        return max(pattern.start, pattern.new_level)
    if isinstance(pattern, DemandRandom | ReplayRandom):
        return pattern.mean
    assert isinstance(pattern, DemandFixed | ReplayFixed)
    return max(pattern.values)


def _spread(pattern: object) -> int:
    """The variation each Week: a Game's fixed series and `step` have none."""
    return 0 if isinstance(pattern, DemandFixed) else getattr(pattern, "spread", 0)


def _changes_level(pattern: object) -> bool:
    """Whether the demand level moves during the Game: a step to another level, a fixed series
    with more than one value. Random demand varies around one mean."""
    if isinstance(pattern, DemandStep | DemandStepNoise | ReplayStep):
        return pattern.start != pattern.new_level
    if isinstance(pattern, DemandFixed | ReplayFixed):
        return len(set(pattern.values)) > 1
    return False


def replay_warnings(
    template: ReplayTemplate, settings: GameSettings, *, info_visibility_enabled: bool = False
) -> list[SettingWarning]:
    """The changes of an own Replay scenario that probably make the Replay easier than the Class
    game with `settings` (Story 10.2, FR-49, UX-DR48), one warning per change. A ranged value
    counts by its easier end: a delay by its lowest, Guided Weeks and starting inventory by their
    highest. The rules: a higher starting inventory (`replay_inventory_higher`); a delay shorter
    than the Class game's (`replay_delay_shorter`, per delay); any Guided Weeks, which the
    default never has (`replay_guided_weeks`); a lower peak demand level (`replay_demand_lower`);
    less variation each Week (`replay_demand_less_variable`); no change of level where the Class
    game had one (`replay_demand_no_change`); and, only while `FEATURE_INFO_VISIBILITY` is on
    (`info_visibility_enabled`, Story 10.9), each neighbour's view the Replay shows and the Class
    games do not (`replay_neighbour_visible`, `values` `{"view": "upstream"|"downstream"}`). They
    never block a save."""
    found: list[SettingWarning] = []

    def warn(code: str, field: str, replay: int, class_game: int) -> None:
        values = {"replay": str(replay), "class_game": str(class_game)}
        found.append(SettingWarning(code=code, field=field, values=values))

    inventory = _high(template.starting_inventory)
    if inventory > settings.starting_inventory:
        warn(
            "replay_inventory_higher", "starting_inventory", inventory, settings.starting_inventory
        )
    for field in ("order_delay", "shipping_delay", "production_delay"):
        delay = _low(getattr(template, field))
        if delay < getattr(settings, field):
            warn("replay_delay_shorter", field, delay, getattr(settings, field))
    guided = _high(template.guided_weeks)
    if guided > 0:
        warn("replay_guided_weeks", "guided_weeks", guided, settings.guided_weeks)
    demand, pattern = template.demand, settings.demand
    if _peak(demand) < _peak(pattern):
        warn("replay_demand_lower", "demand", _peak(demand), _peak(pattern))
    if demand.spread < _spread(pattern):
        warn("replay_demand_less_variable", "demand", demand.spread, _spread(pattern))
    if _changes_level(pattern) and not _changes_level(demand):
        warn("replay_demand_no_change", "demand", _peak(demand), _peak(pattern))
    if info_visibility_enabled:
        replay_views, class_views = template.info_visibility, settings.info_visibility
        for side in VIEWS:
            if getattr(replay_views, side) and not getattr(class_views, side):
                found.append(
                    SettingWarning(
                        code="replay_neighbour_visible",
                        field="info_visibility",
                        values={"view": side},
                    )
                )
    return found


def judge_replay_template(
    settings: GameSettings,
    draft: Mapping[str, Any],
    *,
    kept_views: InfoVisibility | None = None,
) -> tuple[ReplayTemplate | None, dict[str, SettingProblem], list[SettingWarning]]:
    """An own Replay scenario `draft` judged for a Class session with `settings` (Story 10.2,
    FR-12, FR-49): the template (None when it does not parse or the engine refuses it), the
    errors keyed as the Game settings' with their range, and the warnings of `replay_warnings`
    on settings without an error. The draft is laid over the Class game's exact settings
    (`class_game_template`); a key outside `REPLAY_EDITABLE` is `not_editable`. The chain and
    the capacity are always the Class session's, which `judge_settings` judged under its flag.

    Information visibility (Story 10.9, FR-83) is the Replay's own: the draft's, else
    `kept_views` (a stored own template's), else the Class session's. While
    `FEATURE_INFO_VISIBILITY` is off a draft that switches on a view that is off there is
    `info_visibility` `feature_disabled` (as `judge_settings`); switching a view off, or sending
    it back as it was, is always allowed."""
    base = class_game_template(settings).model_dump(mode="json")
    if kept_views is not None:
        base["info_visibility"] = kept_views.model_dump(mode="json")
    problems: dict[str, SettingProblem] = {
        key: _problem("not_editable", key) for key in draft if key not in REPLAY_EDITABLE
    }
    views_flag = info_visibility_enabled()
    if not views_flag and _shows_a_new_neighbour(
        draft.get("info_visibility"), base["info_visibility"]
    ):
        problems["info_visibility"] = _problem("feature_disabled", "info_visibility")
    data = {
        **base,
        **{
            key: value
            for key, value in draft.items()
            if key in REPLAY_EDITABLE and key not in problems
        },
    }
    # Fields that do not parse are judged no further; the others are judged with them at the
    # Class game's values, so one mistyped field hides no error elsewhere (as `judge_settings`).
    unreadable: set[str] = set()
    try:
        template = ReplayTemplate.model_validate(data)
    except ValidationError as exc:
        for error in exc.errors():
            if error["loc"]:
                unreadable.add(str(error["loc"][0]))
            field, found = _parse_problem(error, data, settings)
            problems.setdefault(field, found)
        try:
            judged = ReplayTemplate.model_validate(
                {key: base[key] if key in unreadable else value for key, value in data.items()}
            )
        except ValidationError:
            return None, problems, []
    else:
        judged = template
    for error in validate_template(judged, capacity_enabled=True, info_visibility_enabled=True):
        if error.field.split(".")[0] not in unreadable:
            problems.setdefault(
                error.field, _problem(error.code, error.field, error.minimum, error.maximum)
            )
    if unreadable:
        return None, problems, []
    template = judged
    risky = [
        w
        for w in replay_warnings(template, settings, info_visibility_enabled=views_flag)
        if not any(key == w.field or key.startswith(f"{w.field}.") for key in problems)
    ]
    return (None if problems else template), problems, risky


def _replay_to_store(
    row: Mapping[str, Any],
    settings: GameSettings,
    choice: str,
    draft: Mapping[str, Any] | None,
    *,
    locked: bool,
) -> tuple[str, dict[str, Any] | None] | None:
    """The Replay scenario choice and own template to store (Story 10.2), or None when they do
    not change. `own` with no draft keeps the stored own template's fields, judged again for
    `settings` so its chain and capacity follow the Game settings; its Information visibility is
    its own and kept (Story 10.9). Raises
    `SessionLocked` for a change once locked and `InvalidReplayScenario` for a template the
    engine refuses; an unchanged scenario is never refused, so a locked session saves as it
    stands."""
    stored = row["replay_template"]
    stored_template = ReplayTemplate.model_validate(stored) if stored is not None else None
    if choice == "default":
        if row["replay_scenario"] == "default":
            return None
        if locked:
            raise SessionLocked({"replay_scenario": "locked"})
        return "default", None
    if draft is None:
        if stored_template is None:
            if locked:
                raise SessionLocked({"replay_scenario": "locked"})
            raise InvalidReplayScenario(
                {"replay_template": _problem("required", "replay_template")}
            )
        own = stored_template.model_dump(mode="json")
        draft = {key: value for key, value in own.items() if key in REPLAY_EDITABLE}
    kept = stored_template.info_visibility if stored_template is not None else None
    judged, problems, _ = judge_replay_template(settings, draft, kept_views=kept)
    if judged is None:
        if locked:
            raise SessionLocked({"replay_scenario": "locked"})
        raise InvalidReplayScenario(problems)
    template = judged
    if row["replay_scenario"] == "own" and template == stored_template:
        return None
    if locked:
        raise SessionLocked({"replay_scenario": "locked"})
    return "own", template.model_dump(mode="json")


async def check_replay_scenario(
    user: authz.Principal, session_id: uuid.UUID, draft: Mapping[str, Any], *, now: datetime
) -> SettingsCheckOut | None:
    """What the engine says of a draft of an own Replay scenario, as the Lecturer leaves a field
    (Story 10.2, FR-12, FR-49): errors, and warnings of changes that probably make the Replay
    easier; nothing stored. Raises `SessionLocked` once locked. None when the User may not
    manage the Class."""
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, session_id)
    if row is None or await _class_for(user, row["class_id"], "class_sessions.manage") is None:
        return None
    if is_locked(row, now=now):
        raise SessionLocked({"replay_scenario": "locked"})
    settings = GameSettings.model_validate(row["game_settings"])
    stored = row["replay_template"]
    kept = ReplayTemplate.model_validate(stored).info_visibility if stored is not None else None
    _, problems, risky = judge_replay_template(settings, draft, kept_views=kept)
    return SettingsCheckOut(errors=problems, warnings=risky)


def _copied_replay(
    source: Mapping[str, Any], settings: GameSettings, source_id: uuid.UUID
) -> tuple[str, dict[str, Any] | None]:
    """The source's Replay scenario for a copy (Stories 5.18 and 10.2, FR-66): the default as it
    is; an own template judged again for the copy's Game settings, whose chain and capacity it
    takes. Its Information visibility is copied while `FEATURE_INFO_VISIBILITY` is on and left
    out (both views off) while it is off, as `_copied_settings` (Story 10.9). A template the
    engine now refuses is not copied: the copy gets the default, and the refusal is logged."""
    if source["replay_scenario"] != "own":
        return "default", None
    own = ReplayTemplate.model_validate(source["replay_template"]).model_dump(mode="json")
    editable = {key: value for key, value in own.items() if key in REPLAY_EDITABLE}
    if not info_visibility_enabled():
        editable["info_visibility"] = InfoVisibility().model_dump(mode="json")
    template, problems, _ = judge_replay_template(settings, editable)
    if template is None:
        log.info(
            "class_session_copy_replay_default", source_id=str(source_id), fields=sorted(problems)
        )
        return "default", None
    return "own", template.model_dump(mode="json")


register_pin_provider(REPLAY_TEMPLATE_PIN, replay_template_pin)


class ProviderKeyMissing(Exception):
    """LLM players, and the provider of the session's model config may not answer here (in
    production: its key is not set). The lock is refused and nothing is frozen (AD-17)."""

    code = "provider_key_missing"


class PinRefused(Exception):
    """A pin provider refuses the lock with a stable code (Story 11.1: `question_set_draft`, a
    draft question set in production). Raised from `build_snapshot` inside the lock's
    transaction, so nothing is frozen; the sweep tells the owners as for `ProviderKeyMissing`."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


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
    students = await _seatable(row, await classes.registered_students(row["class_id"]), s)
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
    except (ProviderKeyMissing, PinRefused) as refused:
        told = await _tell_lock_refused(class_session_id, now, refused.code)
        log.warning(
            "class_session_lock_refused",
            class_session_id=str(class_session_id),
            error_code=refused.code,
            told=told,
        )
        return False


TestPinner = Callable[[AsyncSession, Mapping[str, Any], datetime], Awaitable[bool]]
"""`(session, class_session_row, at)` → whether this call pinned: pins what a module keeps that
hangs on the original Test deadline, in `lock_test`'s transaction, once and idempotently."""

_test_pinners: list[TestPinner] = []


def register_test_pinner(pinner: TestPinner) -> None:
    """Add a pinner `lock_test` runs (Story 11.2: `tests` pins the Scoring guide in force), for a
    module `sessions` may not import. Registering the same one again changes nothing."""
    if pinner not in _test_pinners:
        _test_pinners.append(pinner)


ASSESSMENT_PURPOSE = "assessment"
"""The purpose a model config must name a prompt for before the AI assessment uses it (12.2)."""


async def _assessment_config(
    s: AsyncSession, row: Mapping[str, Any]
) -> tuple[uuid.UUID, str | None] | None:
    """The model config (and Effort level) the Test-deadline lock pins for the AI assessment
    (Story 12.2, AD-23, AD-27), marked referenced; None while the switch is off or when no config
    names the `assessment` prompt. The Class session's own `model_config_id` (kept by Story 12.7's
    trigger for a Control test, and set for Rule-based players too) when its config names it;
    otherwise, for a course session made before the purpose existed, the active default when it
    names it. A Control test never falls back: it checks its own config."""
    if not (await assessment.switch_of(s, row["id"])).enabled:
        return None
    own = row["model_config_id"]
    found = await config.get(own, session=s) if own is not None else None
    level: str | None = row["effort_level"]
    if found is None or ASSESSMENT_PURPOSE not in found.spec.prompts:
        if row["kind"] != COURSE:
            return None
        found = await config.active_default(session=s)
        if found is None or ASSESSMENT_PURPOSE not in found.spec.prompts:
            return None
        level = None
    if level is not None and found.effort_level(level) is None:
        level = None
    await config.mark_referenced(found.id, session=s)
    return found.id, level


async def lock_test(class_session_id: uuid.UUID, *, now: datetime) -> bool:
    """The Test-deadline lock (Story 12.1; Epic 11's `lock_test`, AD-9, FR-18): under the Class
    session's row lock, in one transaction, it pins what hangs on the original Test deadline,
    once and idempotently: the «KI-vurdering» switch (`assessment.pin_switch`) and, through each
    pinner of `register_test_pinner`, the Scoring guide in force (Story 11.2). The sweep's
    `tests.close_attempt` due action comes right after it (Story 11.11), and `close_attempt`
    does nothing to an attempt of a Class session this lock has not run for. It sets
    `test_locked_at` and emits `session:<id>`; a second call changes and emits nothing. It does
    not judge the deadline: the sweep's finder does, and the local dev route calls it at once.
    True when this call locked it."""
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, class_session_id, lock=True)
        if row is None or row["test_locked_at"] is not None:
            return False
        # Pinned as of the Test deadline it hangs on, also when the sweep runs late (after an
        # outage, or for a session whose deadline passed before this lock existed); the dev route
        # runs it before the deadline, as of now.
        deadline = row["test_deadline"]
        at = now if deadline is None else min(now, deadline)
        chosen = await _assessment_config(s, row)
        pinned = await assessment.pin_switch(
            s,
            class_session_id,
            at=at,
            model_config_id=None if chosen is None else chosen[0],
            effort_level=None if chosen is None else chosen[1],
        )
        for pinner in _test_pinners:
            await pinner(s, row, at)
        await repo.set_test_locked(s, class_session_id, now)
        await events.emit(s, "session", str(class_session_id))
    log.info("class_session_test_locked", class_session_id=str(class_session_id), pinned=pinned)
    return True


async def due_test_locks(now: datetime) -> list[uuid.UUID]:
    """The sweep's `sessions.lock_test` finder (AD-9): the Class sessions whose original Test
    deadline has passed and that the Test-deadline lock has not run for, by id."""
    async with get_sessionmaker()() as s:
        return await repo.due_test_locks(s, now)


async def lock_test_due(class_session_id: object, now: datetime) -> bool:
    """The sweep's `sessions.lock_test` action, one Class session per transaction with its id
    only (AD-9)."""
    assert isinstance(class_session_id, uuid.UUID)
    return await lock_test(class_session_id, now=now)


async def _tell_lock_refused(
    class_session_id: uuid.UUID, now: datetime, reason: str = ProviderKeyMissing.code
) -> int:
    """Mark the session's lock refused (`lock_refused_at`, the first time only, so the Klasseøkt
    can say so, and `lock_refused_reason`, the latest reason), and one `LOCK_REFUSED_NOTICE` per
    owner of the Class and per active Admin, keyed by the session and the User, so each is told
    once. No notice for a Class that is archived.
    Returns how many notices were stored now."""
    told = 0
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, class_session_id)
        if row is None:
            return 0
        await repo.set_lock_refused(s, class_session_id, now, reason)
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
        "reason": row["lock_refused_reason"] or ProviderKeyMissing.code,
    }


# The cost-limit notice (Story 15.6, FR-69, AD-9): `ops.cost_limit` tells the Class's owners once
# that the LLM players switched to Rule-based players; these read who and what.


async def class_session_owners(
    session: AsyncSession, class_session_id: uuid.UUID
) -> list[uuid.UUID]:
    """The owners and co-owners of the Class session's Class, by id; none when the Class session
    is gone or its Class is archived (nothing there is told any more)."""
    row = await repo.session_row(session, class_session_id)
    if row is None or not await classes.is_writable(row["class_id"], session=session):
        return []
    return sorted(await classes.owners_of(session, row["class_id"]))


async def cost_limit_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of an `ai_cost_limit` notice, for `messaging` at send time: the
    Class's name, the session's number, when the limit was reached and the Klasseøkt's path. None,
    so no mail goes, when the session is gone, its Class archived, the recipient no longer an owner
    or the limit not reached."""
    if ref is None or user_id not in await class_session_owners(session, ref):
        return None
    state = await budget.state(budget.BudgetScope.class_session(ref), session=session)
    if state is None or state.players_exhausted_at is None:
        return None
    row = await repo.session_row(session, ref)
    label = await classes.label_of_class(session, row["class_id"]) if row else None
    if row is None or label is None:
        return None
    return {
        "class_name": label.name,
        "session_number": await repo.number_of(session, ref, row["class_id"]),
        "reached_at": state.players_exhausted_at.astimezone(calls.OSLO),
        "session_path": f"/klasseokter/{ref}",
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
        waiting = await _seatable(row, sorted(registered - seated))
        due.extend((row["id"], student) for student in waiting)
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
        if not await _seatable(row, [user_id], s):
            return False  # Story 12.8: a test student without consent gets no Seat.
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
    class_session_id: uuid.UUID, deadline: DeadlineName, user_id: uuid.UUID | None = None
) -> list[uuid.UUID]:
    """Who is reminded of `deadline` (Story 5.14): every registered Student of the Class
    session's Class, sorted; for the Test deadline, less those who have handed in their
    Individual test (`test_submitted`, Story 11.10, FR-18; read through `progress`, AD-16); for
    the Debrief and Test deadlines, less those with their own extension (Story 11.13), who are
    reminded of their own date instead. With `user_id`, the reminder of that Student's own
    deadline: them alone, when they are such a Student with an extension. The one place the
    recipients are chosen; Epic 13 leaves out one who has done the other steps."""
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, class_session_id)
        done: set[uuid.UUID] = set()
        extended: set[uuid.UUID] = set()
        if row is not None and deadline == "test_deadline":
            done = set(
                await progress.users_with_step(s, class_session_id, progress.Step.TEST_SUBMITTED)
            )
        if row is not None and deadline in OWN_DEADLINE_KEYS:
            extended = set(await repo.extensions_of_session(s, class_session_id))
    if row is None:
        return []
    students = set(await classes.registered_students(row["class_id"])) - done
    if user_id is not None:
        return [user_id] if user_id in students and user_id in extended else []
    return sorted(students - extended)


async def due_playouts(now: datetime) -> list[tuple[str, uuid.UUID]]:
    """The sweep's `sessions.playout` finder (Story 8.14, FR-38, AD-9, AD-13): `(game id, Class
    session id)` of every Game, where `games.policy` has the playout, that has neither finished
    nor begun its playout in a Class session whose Play deadline lies at or before `now`, oldest
    first. Also in an archived Class: every Class game ends."""
    async with get_sessionmaker()() as s:
        waiting = await games_service.sessions_with_playout_games(s)
        passed = await repo.passed_play_deadlines(s, now, waiting)
        return await games_service.playout_games(s, passed)


async def playout_due(item: object, now: datetime) -> bool:
    """The sweep's `sessions.playout` action, one Game per transaction with ids only (Story 8.14,
    AD-9): `games.commands.playout` reads the Class session's Play deadline again in its own
    transaction, so a deadline the Lecturer extended after the finder's read holds
    (`play_deadline_not_passed` is skipped quietly). A Game with no snapshot (the lock never
    succeeded) is logged as an error with its id and skipped, so the other Games play out."""
    if not isinstance(item, tuple) or len(item) != 2:
        raise TypeError("a playout item is (game_id, class_session_id)")
    game_id, class_session_id = item
    try:
        return await games_commands.playout(
            game_id, now=now, latest=_play_deadline_of(class_session_id)
        )
    except games_commands.CommandError as refused:
        if refused.code == "play_deadline_not_passed":
            log.info("playout_deadline_moved", game_id=game_id)
            return False
        # Any other refusal (no snapshot: the lock never succeeded; a snapshot this engine cannot
        # run) leaves the Game to the next minute, logged as an error once per Game and code in
        # this process, with its id, so the other Games play out.
        if (game_id, refused.code) not in _refused_playouts:
            _refused_playouts.add((game_id, refused.code))
            event = (
                "playout_game_not_ready" if refused.code == "game_not_ready" else "playout_refused"
            )
            log.error(event, game_id=game_id, code=refused.code)
        return False


_refused_playouts: set[tuple[str, str]] = set()
"""(Game id, refusal code) of the playouts refused and logged as an error in this process."""


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


async def due_own_deadline_reminders(
    now: datetime,
) -> list[tuple[uuid.UUID, uuid.UUID, DeadlineName]]:
    """The sweep's `sessions.send_own_deadline_reminder` finder (Story 11.13, AD-9): `(class
    session id, user id, deadline)` of each Student's own Debrief or Test deadline at most 24
    hours ahead with no reminder of theirs at that time, in a Class that is not archived."""
    async with get_sessionmaker().begin() as s:
        rows = await repo.due_own_deadlines(s, now, now + REMINDER_AHEAD)
    due: list[tuple[uuid.UUID, uuid.UUID, DeadlineName]] = []
    writable: dict[uuid.UUID, bool] = {}
    for row in rows:
        if row["class_id"] not in writable:
            writable[row["class_id"]] = await classes.is_writable(row["class_id"])
        if writable[row["class_id"]]:
            due.append((row["class_session_id"], row["user_id"], row["deadline"]))
    return due


async def send_own_deadline_reminder_due(item: object, now: datetime) -> bool:
    """The sweep's `sessions.send_own_deadline_reminder` action: one Student's deadline per
    transaction, with ids and the deadline's name only."""
    if not isinstance(item, tuple) or len(item) != 3:
        raise TypeError("an own reminder item is (class_session_id, user_id, deadline)")
    class_session_id, user_id, deadline = item
    if (
        not isinstance(class_session_id, uuid.UUID)
        or not isinstance(user_id, uuid.UUID)
        or deadline not in OWN_DEADLINE_KEYS
    ):
        raise TypeError("an own reminder item holds two ids and a Debrief or Test deadline")
    return await send_deadline_reminder(class_session_id, deadline, now=now, user_id=user_id)


async def send_deadline_reminder(
    class_session_id: uuid.UUID,
    deadline: DeadlineName,
    *,
    now: datetime,
    user_id: uuid.UUID | None = None,
) -> bool:
    """Remind the Students of `deadline` once per deadline time (Story 5.14, FR-18): under the
    Class session's row lock, when the deadline is set, has not passed and is at most 24 hours
    away, record the reminder and enqueue one `DEADLINE_REMINDER_NOTICE` per Student of
    `reminder_recipients`, keyed by session, deadline kind, deadline time and User. With
    `user_id` (Story 11.13), the case of that Student's own Debrief or Test deadline: the time is
    their `effective_*` deadline, the reminder row is theirs, and they alone are reminded, as the
    same `digest` kind with a key that holds their id, the deadline kind and their time. Returns
    False, changing nothing, when there is nothing to remind of now or it was reminded before."""
    if deadline not in DEADLINE_NAMES:
        raise ValueError(f"not a deadline: {deadline!r}")
    if user_id is not None and deadline not in OWN_DEADLINE_KEYS:
        raise ValueError(f"no Student has their own {deadline!r}")
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, class_session_id, lock=True)
        if row is None:
            return False
        at = (
            row[deadline]
            if user_id is None
            else _effective(await _student_row(s, row, user_id), deadline)
        )
        if at is None or not now < at <= now + REMINDER_AHEAD:
            return False
        if not await classes.is_writable(row["class_id"], session=s):
            return False
        reminder_id = await repo.insert_reminder(
            s,
            class_session_id=class_session_id,
            deadline=deadline,
            deadline_at=at,
            now=now,
            user_id=user_id,
        )
        if reminder_id is None:
            return False
        # Read once the reminder is recorded, so a Student registered until now is among them.
        recipients = await reminder_recipients(class_session_id, deadline, user_id)
        kind = DATE_KINDS[deadline]
        for recipient in recipients:
            key = (
                f"{DEADLINE_REMINDER_NOTICE}:{class_session_id}:{kind}:{at.isoformat()}:{recipient}"
            )
            await notify.enqueue(s, recipient, DEADLINE_REMINDER_NOTICE, key, ref=reminder_id)
    log.info(
        "deadline_reminder_sent",
        class_session_id=str(class_session_id),
        deadline=kind,
        students=len(recipients),
        own=user_id is not None,
    )
    return True


async def deadline_reminder_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of a `DEADLINE_REMINDER_NOTICE`, for `messaging` at send time
    (Story 5.14, AD-9): the Class's name, the deadline (`play`, `debrief`, `test`), its time in
    Europe/Oslo and whether the session is obligatory. None, so the notice is left out, when the
    reminder or session is gone, the deadline has moved from the reminded time or passed, the
    Class is archived, or the User is no longer a registered Student of it. Story 11.13: a
    Student's own reminder holds only for them at their own deadline; the Class session's Debrief
    or Test reminder is left out for a Student who has their own deadline by now."""
    if ref is None:
        return None
    reminder = await repo.reminder_row(session, ref)
    if reminder is None:
        return None
    if reminder["user_id"] is not None and reminder["user_id"] != user_id:
        return None
    row = await repo.session_row(session, reminder["class_session_id"])
    if row is None:
        return None
    name = reminder["deadline"]
    at = row[name]
    if name in OWN_DEADLINE_KEYS:
        student = await _student_row(session, row, user_id)
        own = student[OWN_DEADLINE_KEYS[name]] is not None
        if reminder["user_id"] is None and own:
            return None
        at = _effective(student, name)
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


# The deletion reminder (Story 13.9, FR-57, FR-77, AD-9).

DELETION_REMINDER_NOTICE = "deletion_reminder"
"""The notice kind each Student of a Class session gets once, `deletion_reminder_days` before its
deletion date, `digest` (Story 13.9, AD-9): download the Student report before the data is
deleted. Its `ref` is the Class session; the mail reads the date at send time."""


def _deletion_key(class_session_id: uuid.UUID, deletion: date, user_id: uuid.UUID) -> str:
    """Once per Student, Class session and date: a date that moves after the reminder (a later
    extension) is told again in its own window."""
    return f"{DELETION_REMINDER_NOTICE}:{class_session_id}:{deletion.isoformat()}:{user_id}"


def _reminder_ahead() -> timedelta:
    return timedelta(days=get_settings().deletion_reminder_days)


async def due_deletion_reminders(now: datetime) -> list[uuid.UUID]:
    """The sweep's `sessions.send_deletion_reminder` finder (Story 13.9, AD-9): the ids of the
    Class sessions whose deletion date is after today and at most `deletion_reminder_days` away
    on the Europe/Oslo calendar, whose Students were not reminded yet. An archived Class is
    included: its data is kept until this date."""
    async with get_sessionmaker()() as s:
        return await repo.due_deletion_reminders(s, now.astimezone(OSLO).date(), _reminder_ahead())


async def send_deletion_reminder_due(item: object, now: datetime) -> bool:
    """The sweep's `sessions.send_deletion_reminder` action: one Class session per transaction,
    with its id only."""
    if not isinstance(item, uuid.UUID):
        raise TypeError("a deletion reminder item is a Class session id")
    return await send_deletion_reminder(item, now=now)


async def send_deletion_reminder(class_session_id: uuid.UUID, *, now: datetime) -> bool:
    """Remind each registered Student of the Class session's Class, once, that their data is
    deleted on the deletion date (Story 13.9, FR-57): under the Class session's row lock, when the
    date is set, after today and at most `deletion_reminder_days` away, and the Students were not
    reminded, enqueue one `DELETION_REMINDER_NOTICE` per Student keyed by session and User, and
    record the reminder on the session. Returns False, changing nothing, otherwise. Idempotent:
    the key and the mark each keep a second run from telling anyone again."""
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, class_session_id, lock=True)
        if row is None or row["deletion_date"] is None or row["deletion_reminded_at"] is not None:
            return False
        today = now.astimezone(OSLO).date()
        deletion: date = row["deletion_date"]
        if not today < deletion <= today + _reminder_ahead():
            return False
        students = sorted(await classes.registered_students(row["class_id"]))
        for student in students:
            await notify.enqueue(
                s,
                student,
                DELETION_REMINDER_NOTICE,
                _deletion_key(class_session_id, deletion, student),
                ref=class_session_id,
            )
        await repo.mark_deletion_reminded(s, class_session_id, now)
    log.info(
        "deletion_reminder_sent",
        class_session_id=str(class_session_id),
        students=len(students),
    )
    return True


async def deletion_reminder_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of a `DELETION_REMINDER_NOTICE`, for `messaging` at send time (Story
    13.9, AD-9): the Class's name and the deletion date as it stands now. None, so the notice is
    left out, when the Class session or its date is gone, the date is today or has passed, the
    Class is gone, or the User is no longer a registered Student of it. An archived Class is
    still named: its data is kept until the date."""
    if ref is None:
        return None
    row = await repo.session_row(session, ref)
    if row is None or row["deletion_date"] is None:
        return None
    if row["deletion_date"] <= now.astimezone(OSLO).date():
        return None
    label = await classes.label_of_class(session, row["class_id"])
    if label is None:
        return None
    if user_id not in await classes.registered_students(row["class_id"]):
        return None
    return {"class_name": label.name, "deletion_date": row["deletion_date"]}


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
    waiting = await _seatable(row, [student for student in registered if student not in seated], s)
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
    names = await session_student_names(row, sorted(_seated(games)))
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
            if not await _seatable(row, [user.id], s):
                raise ConsentMissing({"seat": "consent_missing", "missing": "1"})
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
        # The Lecturer who pressed it is stored as its starter and audited (Story 8.10).
        await games_commands.start(game_id, actor=user.id)
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


Copier = Callable[[AsyncSession, Mapping[str, Any], uuid.UUID, datetime], Awaitable[None]]
"""`(session, source_row, new_session_id, now)`: copies what its module keeps of a Class session
into the copy, in `copy_from`'s transaction (FR-66)."""

_copiers: list[Copier] = []


def register_copier(copier: Copier) -> None:
    """Add a copier `copy_from` runs (Story 11.1: `tests` copies the question set selection), for
    a module `sessions` may not import. Registering the same one again changes nothing."""
    if copier not in _copiers:
        _copiers.append(copier)


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
    not read the source. It copies the settings of Epic 5, the Replay scenario
    (`_copied_replay`, Story 10.2), the «KI-vurdering» switch (Story 12.1) and, through each
    copier of `register_copier`, the question set selection (Story 11.1) and an edited Scoring
    guide (Story 11.2); the later stories that own more session settings (FR-66) add theirs
    here."""
    if not rerun_enabled():
        raise FeatureDisabled(dict(RERUN_DISABLED))
    target = await _class_for(user, target_class_id, "class_sessions.manage")
    if target is None:
        return None
    async with get_sessionmaker().begin() as s:
        source = await repo.session_row(s, source_id)
    found = (
        await _class_for(user, source["class_id"], "class_sessions.read")
        if source is not None
        else None
    )
    if source is None or found is None:
        return None
    _refuse_control_test(target)
    _refuse_control_test(found)
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
        replay_choice, own_template = _copied_replay(source, settings, source_id)
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
            replay_scenario=replay_choice,
            replay_template=own_template,
        )
        if default is not None:
            await budget.set_budget(budget.BudgetScope.class_session(session_id), session=s)
        # Story 12.1 (FR-66): the «KI-vurdering» switch's value, never its pin.
        await assessment.copy_switch(s, source_id, session_id, now=now)
        # Story 11.1 (FR-66): what the modules `sessions` may not import copy themselves.
        for copier in _copiers:
            await copier(s, source, session_id, now)
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


# Erasing a User (Story 15.2, FR-76, AD-2, AD-14): `sessions` joins the Class games, the
# Tilrettelegging it owns and the AI call bodies to the one erasure routine of `identity`.


async def _hand_over_seats(
    user_id: uuid.UUID, now: datetime, scope: uuid.UUID | None = None
) -> None:
    """Before the erasure's transaction: the User's running Seats go to AI players (with `scope`,
    Story 15.3, those in that Class session's Games only)."""
    await games_service.hand_over_seats_of(user_id, scope)


async def _erase_session_data(
    s: AsyncSession, user_id: uuid.UUID, scope: uuid.UUID | None = None
) -> None:
    """In the erasure's transaction: the Student's Tilrettelegging and own deadlines (Story 11.13),
    and the bodies of the AI calls made for them (a follow-up question quotes their own text);
    with `scope` (Story 15.3, retention), those of that Class session only."""
    await repo.delete_adjustments_of(s, user_id, scope)
    await repo.delete_extensions_of(s, user_id, scope)
    await calls.clear_bodies_of_user(s, user_id, scope)


identity.register_erasure_preparation("games", {"seat_reclaims"}, _hand_over_seats)
identity.register_erasure_step(
    "sessions",
    {"student_adjustments", "student_deadline_extensions", calls.CALL_TABLE},
    _erase_session_data,
)


@dataclass(frozen=True)
class EvaluationSession:
    """A Class session as the Admin's evaluation export lists it (Story 15.4, FR-71)."""

    id: uuid.UUID
    number: int
    class_name: str
    course_code: str | None
    institution_name: str | None
    start_at: datetime | None
    test_deadline: datetime | None
    deletion_date: date | None
    """The stored deletion date (Story 13.9, `_store_deletion_date`): the one rule, which
    retention (Story 15.3) deletes on."""


async def evaluation_sessions(
    session: AsyncSession, ids: list[uuid.UUID] | None = None
) -> list[EvaluationSession]:
    """Every saved Class session, newest first, or the ones with these ids (Story 15.4): how
    the Admin names them, with their dates and stored deletion date. No Student data."""
    rows = await repo.evaluation_rows(session, ids)
    facts = await classes.class_labels(session, list({row["class_id"] for row in rows}))
    found = []
    for row in rows:
        fact = facts.get(row["class_id"])
        if fact is None:  # pragma: no cover - a Class session always has its Class
            continue
        found.append(
            EvaluationSession(
                id=row["id"],
                number=row["number"],
                class_name=fact.name,
                course_code=fact.course_code,
                institution_name=fact.institution_name,
                start_at=row["start_at"],
                test_deadline=row["test_deadline"],
                deletion_date=row["deletion_date"],
            )
        )
    return found


@dataclass(frozen=True)
class ModelSetting:
    """A Class session as the Admin's «KI-kostnad» lists it (Story 15.5, FR-68): how the Admin
    names it, and its model setting. After the lock the frozen values come from the snapshot."""

    id: uuid.UUID
    number: int
    class_name: str
    institution_name: str | None
    start_at: datetime | None
    locked: bool
    ai_mode: str
    model_config_id: uuid.UUID | None
    effort_level: str | None
    frozen_model_config_id: uuid.UUID | None
    """The `SessionRuntime`'s config once locked (None before, and for Rule-based players)."""
    frozen_effort_level: str | None
    prompt_versions: dict[str, int] | None


async def model_settings(
    session: AsyncSession, ids: list[uuid.UUID] | None = None, *, now: datetime
) -> list[ModelSetting]:
    """Every saved Class session, newest first, or the ones with these ids, with its model
    setting (Story 15.5). No Student data."""
    rows = await repo.model_setting_rows(session, ids)
    facts = await classes.class_labels(session, list({row["class_id"] for row in rows}))
    found = []
    for row in rows:
        fact = facts.get(row["class_id"])
        if fact is None:  # pragma: no cover - a Class session always has its Class
            continue
        runtime = row["session_runtime"] or {}
        frozen = runtime.get("model_config_id")
        found.append(
            ModelSetting(
                id=row["id"],
                number=row["number"],
                class_name=fact.name,
                institution_name=fact.institution_name,
                start_at=row["start_at"],
                # A Control test keeps the config it checks (Story 12.7's trigger): never pinnable.
                locked=is_locked(row, now=now) or row["kind"] == CONTROL_TEST,
                ai_mode=row["ai_mode"],
                model_config_id=row["model_config_id"],
                effort_level=row["effort_level"],
                frozen_model_config_id=uuid.UUID(frozen) if frozen else None,
                frozen_effort_level=runtime.get("effort_level"),
                prompt_versions=runtime.get("prompt_versions"),
            )
        )
    return found


class ModelConfigFrozen(Exception):
    """The Class session is locked or its Start date has passed: its model config is frozen in
    `SessionRuntime` and can no longer change (AD-4, FR-68). A Control test's never changes
    (Story 12.7)."""

    code = "model_config_frozen"


@dataclass(frozen=True)
class PinOutcome:
    changed: bool
    """False when this config was pinned already: nothing was written."""
    previous: uuid.UUID | None


async def pin_model_config(
    s: AsyncSession, class_session_id: uuid.UUID, model_config_id: uuid.UUID, *, now: datetime
) -> PinOutcome | None:
    """The Admin pins a model config for a Class session before its Start date (Story 15.5,
    FR-68), in the caller's transaction under the session's row lock, so the lock cannot freeze
    the old config meanwhile. With LLM players the Effort level in force stays when the new config
    offers it, else the new config's first offered level (FR-78). The budget row is created when
    there is none, the config is marked referenced (an edit makes a new row) and `session:<id>`
    is emitted.

    None when the Class session does not exist. Raises `ModelConfigFrozen` once `is_locked`."""
    row = await repo.session_row(s, class_session_id, lock=True)
    if row is None:
        return None
    # A Control test's model config is the one its Scoring guide check names (Story 12.7, AD-27):
    # a trigger refuses any change, so it is as frozen as a locked Class session's.
    if is_locked(row, now=now) or row["kind"] == CONTROL_TEST:
        raise ModelConfigFrozen
    if row["model_config_id"] == model_config_id:
        return PinOutcome(False, model_config_id)
    level: str | None = None
    if row["ai_mode"] == AiMode.llm.value:
        # Offered here, else measured here (a config whose provider has no key yet offers
        # nothing): never a level without a measurement, which the lock would freeze (FR-78).
        offered = [o.name for o in await config.offered_effort_levels(model_config_id, session=s)]
        offered = offered or await config.measured_levels(model_config_id, session=s)
        level = row["effort_level"] if row["effort_level"] in offered else None
        level = level or (offered[0] if offered else None)
    scope = budget.BudgetScope.class_session(class_session_id)
    if await budget.state(scope, session=s) is None:
        await budget.set_budget(scope, session=s)
    await config.mark_referenced(model_config_id, session=s)
    await repo.set_model_config(
        s, class_session_id, model_config_id=model_config_id, effort_level=level
    )
    await events.emit(s, "session", str(class_session_id))
    log.info(
        "class_session_model_pinned",
        class_session_id=str(class_session_id),
        model_config_id=str(model_config_id),
    )
    return PinOutcome(True, row["model_config_id"])


# «Mine data» (Story 15.1, FR-75): the Student's own rows of this module, by their own id.
from app.modules.sessions.own_data import own_records  # noqa: E402, F401
