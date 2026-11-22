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
    """A User's role in one Class (`class_staff.role`). Co-owners (4.9) are owners too: one role,
    so they have exactly the owner's rights. An Assistant lecturer (4.9) reads the Class."""

    owner = authz.OWNER
    assistant = authz.ASSISTANT_STAFF


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
    archived: bool
    """Archived (Story 4.10): the Lærerhjem lists it under its own heading."""


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
    can_manage: bool
    """Whether the User may change the Class: its Roster, Invitations and staff (an owner, Story
    4.9). The web app shows those actions only then; the api refuses them otherwise. An archived
    Class takes no change at all, whatever this says (Story 4.10)."""
    created_at: datetime
    archived: bool
    """Archived (Story 4.10): read-only, kept until the retention period ends."""
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
    or was voided unaccepted. `not_invited`: added by hand and sent no Invitation yet (Story
    4.8)."""

    registered = "registered"
    registered_manually = "registered_manually"
    renewal_requested = "renewal_requested"
    bounced = "bounced"
    invited = "invited"
    unregistered = "unregistered"
    not_invited = "not_invited"


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
    user_id: uuid.UUID | None = None
    """The Student's User id, only while the address is registered (Story 13.2: the Roster's link
    to the Studentside); None otherwise."""


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


# Single addresses and manual registration (Story 4.8, FR-7, FR-9).

EMAIL_MAX_LENGTH = 320
STUDENT_NAME_MAX_LENGTH = 200
"""As `identity`'s `NAME_MAX_LENGTH`: the longest name an account may have."""


class RosterEntryIn(BaseModel):
    """«Legg til adresse»: one address, checked as an upload's are. A refused one answers 422
    `invalid_request` with `fields.email`: an address problem (`missing_at`, …) or `on_roster`."""

    email: str = Field(max_length=EMAIL_MAX_LENGTH)


class UploadRow(BaseModel):
    """A row of the Class's staged upload: the invalid row a manual registration corrects."""

    upload_id: uuid.UUID
    row_number: int = Field(ge=1)


class ManualRegistrationIn(BaseModel):
    """«Registrer manuelt»: the address and the Student's name (used only when the address has
    no account yet). `roster_entry_id` is the Roster row the form was opened from: when the
    address typed is another one, that row is removed (a wrong address corrected).
    `upload_row` is the staged invalid row it was opened from, which is deleted. A refused
    address answers 422 `invalid_request` with `fields.email` (an address problem or
    `already_registered`), a refused name with `fields.name` (`name_empty`, `name_too_long`)."""

    email: str = Field(max_length=EMAIL_MAX_LENGTH)
    name: str = Field(max_length=4 * STUDENT_NAME_MAX_LENGTH)
    roster_entry_id: uuid.UUID | None = None
    upload_row: UploadRow | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value or any(not ch.isprintable() for ch in value):
            raise PydanticCustomError("name_empty", "A name is required.")
        if len(value) > STUDENT_NAME_MAX_LENGTH:
            raise PydanticCustomError("name_too_long", "A name has at most 200 characters.")
        return value


class InvalidRosterAddress(ValueError):
    """The address of a single-address command is refused: `reason` goes in `fields.email`."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


# The Class's staff (Story 4.9, FR-10, UX-DR56): «Faglærere og assistenter».


class StaffEmailIn(BaseModel):
    """«Legg til Faglærer» or «Inviter Assistent»: one address. A refused address answers 422
    `invalid_request` with `fields.email`: an address problem, `not_lecturer` (Faglærer: no
    active account with the Lecturer role, one reason for all) or `already_staff`."""

    email: str = Field(max_length=EMAIL_MAX_LENGTH)


class StaffStatus(StrEnum):
    active = "active"
    invited = "invited"
    expired = "expired"


class StaffLecturer(BaseModel):
    """A Faglærer of the Class: an owner (the creator or a co-owner), always active."""

    user_id: uuid.UUID
    name: str
    email: str


class StaffAssistant(BaseModel):
    """An Assistant of the Class: `active` (staff, `user_id` set), or an Invitation not yet
    accepted (`invitation_id` set): `invited` with its last valid day, or `expired`."""

    user_id: uuid.UUID | None = None
    invitation_id: uuid.UUID | None = None
    name: str | None = None
    email: str
    status: StaffStatus
    last_valid_day: date | None = None


class StaffOut(BaseModel):
    """«Faglærere og assistenter»: each group by name, then address."""

    lecturers: list[StaffLecturer]
    assistants: list[StaffAssistant]


class StaffRefused(ValueError):
    """A staff command is refused: `field` (or None for the whole command) and `reason`."""

    def __init__(self, reason: str, field: str | None = "email") -> None:
        super().__init__(reason)
        self.reason = reason
        self.field = field
