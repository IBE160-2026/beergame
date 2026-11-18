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
    name: str = Field(max_length=NAME_MAX_LENGTH)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value or any(not ch.isprintable() for ch in value):
            raise PydanticCustomError("name_empty", "A name is required.")
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
