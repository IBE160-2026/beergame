"""API shapes and data rules of `modules/classes` (Story 4.1)."""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

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


class InstitutionChoice(BaseModel):
    id: uuid.UUID
    name: str


class InstitutionChoicesOut(BaseModel):
    """The Institutions a new Class may belong to, by name («Lag Klasse»)."""

    items: list[InstitutionChoice]
