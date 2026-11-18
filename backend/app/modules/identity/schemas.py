"""API shapes of `modules/identity`."""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError


class AccountRole(StrEnum):
    admin = "admin"
    lecturer = "lecturer"


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

    email: str
    role: AccountRole
    valid_days: int
    """Whole days left, rounded up."""
    has_account: bool
    """Whether the address already has an account: the page then asks for its password."""


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
    roles: list[AccountRole]


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


def email_is_valid(email: str) -> bool:
    """The web app's check of an address (`validate-login.ts`), on the normalised value: no
    whitespace or control character (Postgres refuses NUL), exactly one `@`, a name before it
    and a domain of two or more labels after it."""
    if (
        not email
        or any(ch.isspace() or not ch.isprintable() for ch in email)
        or email.count("@") != 1
    ):
        return False
    local, domain = email.split("@")
    labels = domain.split(".")
    return bool(local) and len(labels) >= 2 and all(labels)


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


class RosterUploadOut(BaseModel):
    """A staged Roster upload as the Class page shows it."""

    file_name: str
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
    preview: list[RosterPreviewRow]


class RosterStagingOut(BaseModel):
    upload: RosterUploadOut | None


class RosterColumnIn(BaseModel):
    column: int = Field(ge=0, le=10_000)


class InvalidRosterColumn(Exception):
    """The chosen column is not one of the staged upload's (`column_unknown`)."""
