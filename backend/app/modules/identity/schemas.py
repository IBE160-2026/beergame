"""API shapes of `modules/identity`."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError


class AccountRole(StrEnum):
    admin = "admin"
    lecturer = "lecturer"


class InvitationKind(StrEnum):
    """What an Invitation offers: an account role (Story 3.7), a place on a Class's Roster as a
    Student (Story 4.4), or a place in one Class's staff as Assistant lecturer (Story 4.9)."""

    role = "role"
    student = "student"
    assistant = "assistant"


class SessionRole(StrEnum):
    """The roles a session carries (`UserOut.roles`): the account roles, and `assistant` while the
    User is Assistant lecturer of at least one Class (Story 4.9). `assistant` is read from the
    Class staff on every request, never stored or granted by the Admin."""

    admin = "admin"
    lecturer = "lecturer"
    assistant = "assistant"


class RosterRegistration(StrEnum):
    """Where a Roster address stands, as stored (Story 4.4). Bounces, expiry and requests for a
    new Invitation are read from the Invitations, never stored here (Story 4.7)."""

    invited = "invited"
    registered = "registered"
    # Written by Story 4.8's manual registration; read by Story 4.7's status list.
    registered_manually = "registered_manually"


class LoginIn(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=1024)


PASSWORD_MIN_LENGTH = 8
"""The shortest password a User may choose (NIST SP 800-63B's floor); also for Story 3.8."""
PASSWORD_MAX_LENGTH = 1024


class PasswordResetIn(BaseModel):
    email: str = Field(max_length=320)


class ResetTokenIn(BaseModel):
    token: str = Field(max_length=128)


class NewPasswordIn(BaseModel):
    token: str = Field(max_length=128)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)


class ResetEmailOut(BaseModel):
    """The address a reset link belongs to, so «Logg inn» can be prefilled."""

    email: str


class ResetCheckOut(ResetEmailOut):
    """A usable reset link: its address, and whether the account has no password yet (a manually
    registered Student, Story 4.8), so «Nytt passord» words it as a first password."""

    first_password: bool = False


class InvitationIn(BaseModel):
    """An Invitation to an account role (Story 3.7)."""

    # Checked by `email_is_valid` in the service: a bad address answers
    # `fields.email = "invalid_email"`.
    email: str = Field(max_length=320)
    role: AccountRole
    access_request_id: uuid.UUID | None = None
    """The open request for lecturer access the Admin invites from (Story 3.13): sending closes
    it when the Invitation is to its address with the Lecturer role. Otherwise, or when the request
    is no longer open, it is ignored and the Invitation is sent as any other."""


class InvitationOut(BaseModel):
    id: uuid.UUID
    email: str
    role: AccountRole
    expires_at: datetime
    valid_days: int
    """Whole days the Invitation is valid, as the result line and the mail state it."""


NAME_MAX_LENGTH = 200


class InvitationTokenIn(BaseModel):
    """The token of an Invitation link, from the fragment of `/invitasjon#<token>` (Story 3.8)."""

    token: str = Field(max_length=128)


class InvitationCheckOut(BaseModel):
    """What «Du er invitert» shows for a usable link."""

    kind: InvitationKind
    """`role` (Story 3.8), `student`: a place on a Class's Roster (Story 4.5), or `assistant`: a
    place in a Class's staff (Story 4.9)."""
    email: str
    role: AccountRole | None
    """The account role a `role` Invitation grants; null for a Student Invitation."""
    valid_days: int
    """Whole days left: rounded up for a role Invitation; for a Student Invitation the days from
    today to its last valid day in Europe/Oslo, at least 1."""
    has_account: bool
    """Whether the address already has an account: the page then asks for its password."""
    class_name: str | None = None
    """The Class a Student or Assistant Invitation adds the address to."""
    course_code: str | None = None
    """The course code of that Class, when it has one."""
    invited_by: str | None = None
    """The name of the Lecturer who sent a Student or Assistant Invitation, while that User
    exists."""


class AcceptInvitationIn(BaseModel):
    """A new account from an Invitation."""

    token: str = Field(max_length=128)
    # Trimmed and collapsed first; the length limit applies to the result.
    name: str = Field(max_length=4 * NAME_MAX_LENGTH)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value or any(not ch.isprintable() for ch in value):
            raise PydanticCustomError("name_empty", "A name is required.")
        if len(value) > NAME_MAX_LENGTH:
            raise PydanticCustomError("name_too_long", "A name has at most 200 characters.")
        return value


class AcceptExistingIn(BaseModel):
    """An Invitation taken by the account its address already has: the account's password."""

    token: str = Field(max_length=128)
    password: str = Field(max_length=PASSWORD_MAX_LENGTH)


class UserOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    roles: list[SessionRole]


class SessionOut(BaseModel):
    user: UserOut


class UserListItem(BaseModel):
    """One User on «Brukere og roller» (Story 3.9)."""

    id: uuid.UUID
    name: str
    email: str
    roles: list[AccountRole]
    is_active: bool


class UserListOut(BaseModel):
    """A page of Users in the list envelope (AD-19 conventions): `next_cursor` is null on the
    last page."""

    items: list[UserListItem]
    next_cursor: str | None


SEARCH_MAX_LENGTH = 200
USER_PAGE_DEFAULT = 50
USER_PAGE_MAX = 100


class RoleIn(BaseModel):
    """The account role an Admin grants (Story 3.9)."""

    role: AccountRole


ROLES_KEEP_ONE_ACTIVE = frozenset({AccountRole.admin.value})
"""Roles at least one active User always holds: the product is never left without an Admin
(revoke, deactivation and erasure alike)."""

DELETE_REFERENCE_MAX_LENGTH = 200
"""The longest reference to an Institution's instruction (Story 15.2)."""


class InvalidDeleteReference(ValueError):
    """`code`: reference_empty | reference_too_long | reference_invalid."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def delete_reference(value: str) -> str:
    """The stored form of the reference to the Institution's instruction (Story 15.2, FR-76):
    trimmed, inner whitespace collapsed. Refuses an empty one, one over 200 characters, and one
    holding `@` or a control character: it lands in the audit row, which never holds an address
    (`platform/audit`). The service refuses one that holds the User's name."""
    value = " ".join(value.split())
    if not value:
        raise InvalidDeleteReference("reference_empty")
    if len(value) > DELETE_REFERENCE_MAX_LENGTH:
        raise InvalidDeleteReference("reference_too_long")
    if "@" in value or any(not ch.isprintable() for ch in value):
        raise InvalidDeleteReference("reference_invalid")
    return value


class UserDeleteIn(BaseModel):
    """The Admin's deletion of a User (Story 15.2): the reference to the Institution's
    instruction, checked by `delete_reference`; a bad one answers `fields.reference`."""

    reference: str = Field(max_length=4 * DELETE_REFERENCE_MAX_LENGTH)


class UserDeletedOut(BaseModel):
    """The erased User's id (Story 15.2): the row is gone from every list."""

    id: uuid.UUID


class InvitationStatus(StrEnum):
    """An Invitation as the Admin's list states it (Story 3.10). Expiry is read from `expires_at`
    against the api's clock; a voided Invitation that was never accepted reads as expired."""

    open = "open"
    accepted = "accepted"
    expired = "expired"


class InvitationListItem(BaseModel):
    """The newest Invitation to one address and role, on «Brukere og roller» (Story 3.10)."""

    id: uuid.UUID
    email: str
    role: AccountRole
    status: InvitationStatus
    expires_at: datetime
    """When the link stops working, or stopped: its expiry, or when it was voided if earlier."""
    accepted_at: datetime | None
    """When the Invitation was accepted; null while it is not."""
    account_deactivated: bool
    """Whether the address belongs to a deactivated User: such an Invitation is not sent again."""
    renewal_requested: bool
    """Whether the recipient asked for a new Invitation from a link that no longer works
    (Story 3.8) since the last one was sent."""


class InvitationListOut(BaseModel):
    """A page of Invitations in the list envelope: `next_cursor` is null on the last page."""

    items: list[InvitationListItem]
    next_cursor: str | None


INVITATION_PAGE_DEFAULT = 50
INVITATION_PAGE_MAX = 100

INSTITUTION_NAME_MAX_LENGTH = 200
INSTITUTION_PAGE_DEFAULT = 50
INSTITUTION_PAGE_MAX = 100


class InvalidInstitutionName(ValueError):
    """A name the Institution rule refuses; `code` is `name_empty`, `name_too_long` or
    `name_invalid`."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def institution_name(value: str) -> str:
    """The stored form of an Institution name: trimmed, inner whitespace collapsed. Refuses an
    empty name, one over 200 characters, and one holding a control character or `@` (an audit row
    holds the name, and `platform/audit` refuses anything that looks like an e-mail address). The
    web app checks it before sending (`modules/admin/institutions.ts`); this one decides."""
    value = " ".join(value.split())
    if not value:
        raise InvalidInstitutionName("name_empty")
    if len(value) > INSTITUTION_NAME_MAX_LENGTH:
        raise InvalidInstitutionName("name_too_long")
    if "@" in value or any(not ch.isprintable() for ch in value):
        raise InvalidInstitutionName("name_invalid")
    return value


class InstitutionIn(BaseModel):
    """The name of a new or renamed Institution (Story 3.11). Checked by `institution_name` in the
    service: a bad name answers `fields.name` with its code."""

    name: str = Field(max_length=4 * INSTITUTION_NAME_MAX_LENGTH)


class InstitutionOut(BaseModel):
    """One Institution (Story 3.11): what the Admin's list shows and what other modules read."""

    id: uuid.UUID
    name: str
    created_at: datetime


class InstitutionListOut(BaseModel):
    """A page of Institutions in the list envelope, newest first: `next_cursor` is null on the
    last page."""

    items: list[InstitutionOut]
    next_cursor: str | None


def normalise_email(email: str) -> str:
    return email.strip().lower()


class AddressProblem(StrEnum):
    """Why a value is not an address (Story 4.3, FR-7). The web app words each one."""

    empty = "empty"
    whitespace = "whitespace"
    """A space or control character inside it."""
    missing_at = "missing_at"
    two_at = "two_at"
    """More than one `@`."""
    missing_name = "missing_name"
    """Nothing before the `@`."""
    missing_domain = "missing_domain"
    """The part after the `@` is not two or more non-empty labels."""


def address_problem(email: str) -> AddressProblem | None:
    """The one check of an address, on the normalised value: what is wrong with it, or None when
    nothing is. It is the web app's check (`validate-login.ts`): no whitespace or control
    character (Postgres refuses NUL), exactly one `@`, a name before it and a domain of two or
    more labels after it. The Roster upload, paste and single-address add all use it."""
    if not email:
        return AddressProblem.empty
    if any(ch.isspace() or not ch.isprintable() for ch in email):
        return AddressProblem.whitespace
    ats = email.count("@")
    if ats == 0:
        return AddressProblem.missing_at
    if ats > 1:
        return AddressProblem.two_at
    local, domain = email.split("@")
    if not local:
        return AddressProblem.missing_name
    labels = domain.split(".")
    if len(labels) < 2 or not all(labels):
        return AddressProblem.missing_domain
    return None


def email_is_valid(email: str) -> bool:
    """Whether `address_problem` finds nothing wrong with the normalised address."""
    return address_problem(email) is None


ACCESS_REQUEST_PAGE_DEFAULT = 50
ACCESS_REQUEST_PAGE_MAX = 100


class AccessRequestIn(BaseModel):
    """A request for lecturer access from the public form «Be om lærertilgang» (Story 3.13).
    Each field answers its own code: `name_empty`/`name_too_long`, `invalid_email`, and the
    Institution name codes."""

    name: str = Field(max_length=4 * NAME_MAX_LENGTH)
    email: str = Field(max_length=320)
    institution: str = Field(max_length=4 * INSTITUTION_NAME_MAX_LENGTH)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value or any(not ch.isprintable() for ch in value):
            raise PydanticCustomError("name_empty", "A name is required.")
        if len(value) > NAME_MAX_LENGTH:
            raise PydanticCustomError("name_too_long", "A name has at most 200 characters.")
        return value

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        value = normalise_email(value)
        if not email_is_valid(value):
            raise PydanticCustomError("invalid_email", "The e-mail address is not valid.")
        return value

    @field_validator("institution")
    @classmethod
    def _institution(cls, value: str) -> str:
        try:
            return institution_name(value)
        except InvalidInstitutionName as error:
            raise PydanticCustomError(error.code, "The Institution name is not valid.") from None


class AccessRequestOut(BaseModel):
    """One open request on «Brukere og roller» (Story 3.13)."""

    id: uuid.UUID
    name: str
    email: str
    institution: str
    requested_at: datetime


class AccessRequestListOut(BaseModel):
    """A page of open requests in the list envelope, newest first: `next_cursor` is null on the
    last page."""

    items: list[AccessRequestOut]
    next_cursor: str | None


# Staged Roster uploads (Story 4.2, FR-7, AD-14).

ROSTER_PREVIEW_ROWS = 5
"""How many data rows the page shows under «Forhåndsvisning av fila»."""


class RosterColumn(BaseModel):
    index: int
    """0-based."""
    letter: str
    """As a spreadsheet names it: A, B, …, AA."""
    header: str
    """The header cell; "" when the file has no header row or the cell is empty."""


class RosterPreviewRow(BaseModel):
    row_number: int
    """The row's number in the file."""
    cells: list[str]


class RosterSource(StrEnum):
    file = "file"
    paste = "paste"


class RosterInvalidRow(BaseModel):
    """A staged row that gets no Invitation, and why (Story 4.3)."""

    row_number: int
    """The row's number in the file, or the address's place in the pasted text."""
    value: str
    """The cell in the chosen column, as staged."""
    reason: AddressProblem | Literal["duplicate", "on_roster"]
    """`on_roster`: the address is already on the Class's Roster (Story 4.4)."""
    first_row: int | None = None
    """For `duplicate`: the row where the address first occurs."""


class RosterUploadOut(BaseModel):
    """A staged Roster upload as the Class page shows it."""

    id: uuid.UUID
    """Sent back with «Send N Invitasjoner», so a replaced staging is never sent (Story 4.4)."""
    source: RosterSource
    file_name: str
    """"" for pasted addresses."""
    row_count: int
    """Data rows read, without the header row and empty rows."""
    has_header: bool
    columns: list[RosterColumn]
    suggested_column: int | None
    """The column with the most cells that look like addresses; None when none does."""
    suggested_count: int
    """How many rows look like addresses in the suggested column (0 with none)."""
    chosen_column: int | None
    chosen_count: int
    """How many rows look like addresses in the chosen column, evaluated from the staged cells."""
    valid_count: int
    """Rows of the chosen column that go on the Roster: valid, not a repeat of an earlier row
    and not already on the Roster (0 with no column chosen)."""
    restored_count: int = 0
    """Of `valid_count`, the rows whose address is a removed, registered Student of the Class: the
    send puts them back with access and no Invitation (Stories 4.4, 4.8), so «Send N
    Invitasjoner» counts `valid_count - restored_count`."""
    invalid_rows: list[RosterInvalidRow]
    """Every other row of the chosen column, by row number ([] with no column chosen)."""
    preview: list[RosterPreviewRow]


class RosterStagingOut(BaseModel):
    upload: RosterUploadOut | None


class RosterColumnIn(BaseModel):
    column: int = Field(ge=0, le=10_000)


ROSTER_PASTE_MAX_CHARS = 50 * 1024 * 1024
"""The schema's own outer cap on pasted text, the highest `ROSTER_MAX_FILE_MB` allows; the
service holds the text to the configured size and answers `roster_paste_too_long`."""


class RosterPasteIn(BaseModel):
    text: str = Field(max_length=ROSTER_PASTE_MAX_CHARS)


class RosterPasteTooLong(Exception):
    """Pasted text over the size cap, or with more addresses than `ROSTER_MAX_ROWS`."""


class InvalidRosterColumn(Exception):
    """The chosen column is not one of the staged upload's (`column_unknown`)."""
