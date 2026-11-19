"""API shapes and data rules of `modules/classes` (Story 4.1)."""

import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

from app.platform import authz

CLASS_NAME_MAX_LENGTH = 200
COURSE_CODE_MAX_LENGTH = 50


class StaffRole(StrEnum):
    """A User's role in one Class (`class_staff.role`). Co-owners (4.9) are owners too."""

    owner = authz.OWNER


class InvalidClass(ValueError):
    """The fields a new Class is refused for: field name → reason code, every one at once."""

    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__(", ".join(f"{k}={v}" for k, v in fields.items()))
        self.fields = fields


def _collapse(value: str) -> str:
    return " ".join(value.split())


def class_name(value: str) -> tuple[str, str | None]:
    """The stored form of a Class name (trimmed, inner whitespace collapsed) and the reason it is
    refused, or None: `name_empty`, `name_too_long` (over 200 characters) or `name_invalid` (a
    control character). The web app checks the same before sending (`modules/classes/classes.ts`);
    this one decides."""
    value = _collapse(value)
    if not value:
        return value, "name_empty"
    if len(value) > CLASS_NAME_MAX_LENGTH:
        return value, "name_too_long"
    if any(not ch.isprintable() for ch in value):
        return value, "name_invalid"
    return value, None


def course_code(value: str | None) -> tuple[str | None, str | None]:
    """The stored course code (trimmed, collapsed; None when blank) and the reason it is refused,
    or None: `course_code_too_long` (over 50 characters) or `course_code_invalid`."""
    value = _collapse(value or "")
    if not value:
        return None, None
    if len(value) > COURSE_CODE_MAX_LENGTH:
        return value, "course_code_too_long"
    if any(not ch.isprintable() for ch in value):
        return value, "course_code_invalid"
    return value, None


class ClassIn(BaseModel):
    """A new Class (Story 4.1). The service checks the fields and answers every refused one in
    `fields`: `name`, `institution_id` (`institution_missing`, `institution_unknown`) and
    `course_code`."""

    name: str = Field(default="", max_length=4 * CLASS_NAME_MAX_LENGTH)
    institution_id: uuid.UUID | None = None
    course_code: str | None = Field(default=None, max_length=4 * COURSE_CODE_MAX_LENGTH)


class ClassListItem(BaseModel):
    """One Class on the Lærerhjem: «Klassene dine»."""

    id: uuid.UUID
    name: str
    course_code: str | None
    roster_count: int
    """Addresses on the Class's Roster (Story 4.4, UX-DR56)."""


class ClassListOut(BaseModel):
    """The Classes the User is staff of, by name. No paging: a Lecturer has a handful."""

    items: list[ClassListItem]


class ClassOut(BaseModel):
    """One Class with its Institution's name and the User's staff role in it."""

    id: uuid.UUID
    name: str
    course_code: str | None
    institution_id: uuid.UUID
    institution_name: str | None
    staff_role: StaffRole
    created_at: datetime
    archived: bool
    roster_count: int
    """Addresses on the Class's Roster (Story 4.4)."""


class EnrolledClassOut(BaseModel):
    """A Class the User is a Student in (Story 4.5): what Hjem names."""

    id: uuid.UUID
    name: str
    course_code: str | None


class EnrolledClassListOut(BaseModel):
    """The Classes the User is a Student in, by name. No paging: a Student has a handful."""

    items: list[EnrolledClassOut]


class InstitutionChoice(BaseModel):
    id: uuid.UUID
    name: str


class InstitutionChoicesOut(BaseModel):
    """The Institutions a new Class may belong to, by name («Lag Klasse»)."""

    items: list[InstitutionChoice]


# Sending Invitations to the Roster (Story 4.4, FR-8).

INVITATION_VALID_DAYS_DEFAULT = 14
INVITATION_VALID_DAYS_MIN = 1
INVITATION_VALID_DAYS_MAX = 60
"""The range of whole days a Student Invitation may be valid for, per sending ([ASSUMPTION]:
FR-8 asks for a stated range; 60 days covers a semester's start with room)."""


class RosterSendIn(BaseModel):
    """«Send N Invitasjoner»: the staged upload the page shows, and the validity in whole days.
    A validity outside the range answers 422 `invalid_request` with
    `fields.valid_days = valid_days_out_of_range`."""

    upload_id: uuid.UUID
    # Strict: `true`, "14" or 14.0 are refused, not read as a number of days.
    valid_days: int = Field(default=INVITATION_VALID_DAYS_DEFAULT, strict=True)

    @field_validator("valid_days")
    @classmethod
    def _range(cls, value: int) -> int:
        return valid_days_in_range(value)


def valid_days_in_range(value: int) -> int:
    """A validity outside the range is refused as `valid_days_out_of_range`."""
    if not INVITATION_VALID_DAYS_MIN <= value <= INVITATION_VALID_DAYS_MAX:
        raise PydanticCustomError(
            "valid_days_out_of_range", "The validity is outside the allowed range."
        )
    return value


class RosterSendOut(BaseModel):
    """What the result line states: how many Invitations went out, and until when they work."""

    sent: int
    valid_days: int
    last_valid_day: date
    """The last day (Europe/Oslo) the links work."""
    expires_at: datetime


# What became of the Invitations (Story 4.6, FR-8, NFR-10).


class BounceClass(StrEnum):
    """Why a mail did not reach its address: `hard` the provider calls permanent (the address
    does not exist or refuses mail), `soft` every other bounce (a full mailbox, a server down)."""

    hard = "hard"
    soft = "soft"


class BouncedRegistration(StrEnum):
    """The registration status of an address whose Invitation bounced; Story 4.7 lists it with
    the other statuses."""

    bounced = "bounced"


class InvitationBounce(BaseModel):
    """A Roster address whose newest Invitation bounced, not registered and not removed."""

    email: str
    registration: BouncedRegistration
    bounce_class: BounceClass


class InvitationSummaryOut(BaseModel):
    """The counts of the Class's Student Invitations, computed by the api at read time, and the
    addresses the mail did not reach, by address. `sent`: handed to the mail provider; `bounced`:
    of those, reported bounced; `accepted`: accepted (Story 4.5); `expired`: neither accepted nor
    voided, and past their last valid day now. Each counts Invitations, not addresses."""

    sent: int
    bounced: int
    accepted: int
    expired: int
    bounces: list[InvitationBounce]


# Registration status and reminders (Story 4.7, FR-9, NFR-10, UX-DR47).


class RegistrationStatus(StrEnum):
    """Where a Roster address stands, read at request time; the first that applies wins.
    `registered` / `registered_manually`: a Student in the Class (stored). `renewal_requested`:
    the Student asked for a new Invitation from a link that no longer works. `bounced`: the mail
    of its newest Invitation did not arrive (with `bounce_class`). `invited`: its newest
    Invitation still works (with `last_valid_day`). `unregistered`: its newest Invitation expired
    unaccepted (or it has none)."""

    registered = "registered"
    registered_manually = "registered_manually"
    renewal_requested = "renewal_requested"
    bounced = "bounced"
    invited = "invited"
    unregistered = "unregistered"


class RegistrationOut(BaseModel):
    """One address on the Roster with its status. `id` names the Roster entry for a reminder to
    it alone; `remindable` is whether a reminder would go to it (not registered, not a hard
    bounce)."""

    id: uuid.UUID
    email: str
    status: RegistrationStatus
    last_valid_day: date | None = None
    bounce_class: BounceClass | None = None
    remindable: bool


class RegistrationTotals(BaseModel):
    """«Registrert 238», «Manuelt 2», «Uregistrert 10»: every address not removed, once."""

    registered: int
    registered_manually: int
    unregistered: int


class RegistrationsOut(BaseModel):
    """«Status etter utsending»: the totals, how many addresses have not registered («Send
    påminnelse til N»), and every address by address."""

    totals: RegistrationTotals
    reminder_count: int
    items: list[RegistrationOut]


class ReminderIn(BaseModel):
    """«Send påminnelse»: to every address that has not registered, or with `roster_entry_id` to
    that one alone, valid for `valid_days` (1–60, as a Roster send)."""

    roster_entry_id: uuid.UUID | None = None
    valid_days: int = Field(default=INVITATION_VALID_DAYS_DEFAULT, strict=True)

    @field_validator("valid_days")
    @classmethod
    def _range(cls, value: int) -> int:
        return valid_days_in_range(value)


class ReminderOut(BaseModel):
    """What the result line states: how many reminders went out, until when they work, and the
    addresses left out because their last mail bounced hard (to correct or register by hand)."""

    sent: int
    valid_days: int
    last_valid_day: date
    expires_at: datetime
    left_out: list[str]
