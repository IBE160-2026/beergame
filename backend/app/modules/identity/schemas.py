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


class UserOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    roles: list[AccountRole]


class SessionOut(BaseModel):
    user: UserOut


def normalise_email(email: str) -> str:
    return email.strip().lower()
