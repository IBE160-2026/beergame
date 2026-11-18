"""API shapes of `modules/identity`."""

import uuid
from enum import StrEnum

from pydantic import BaseModel, Field


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


class UserOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    roles: list[AccountRole]


class SessionOut(BaseModel):
    user: UserOut


def normalise_email(email: str) -> str:
    return email.strip().lower()
