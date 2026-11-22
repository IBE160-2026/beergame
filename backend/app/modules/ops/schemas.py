"""The envelopes of «Pseudonymisert eksport» (Story 15.4, FR-71, AD-19)."""

import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field, SecretStr, StringConstraints

from app.modules.ops.models import AGREEMENT_TEXT_MAX

KEY_MIN = 32
KEY_MAX = 512
"""The pseudonym key's length in characters after trimming: long enough that its stored
fingerprint cannot be guessed back, short enough for a form."""
EXPORT_SESSIONS_MAX = 20
"""The most Class sessions one export takes."""

AgreementText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=AGREEMENT_TEXT_MAX),
]


class AgreementIn(BaseModel):
    """An Institution agreement for one Class session: who agreed, on which day, and who is
    controller for the evaluation (FR-71)."""

    agreed_by: AgreementText
    agreed_on: date
    controller: AgreementText


class AgreementOut(BaseModel):
    agreed_by: str
    agreed_on: date
    controller: str
    recorded_at: datetime


class EvaluationSessionOut(BaseModel):
    """A Class session as the export page lists it: how it is named, its Test deadline, the day
    its Student data is deleted (null while there is no Test deadline), and its agreement."""

    id: uuid.UUID
    number: int
    class_name: str
    course_code: str | None
    institution_name: str | None
    start_at: datetime | None
    test_deadline: datetime | None
    deletion_date: date | None
    agreement: AgreementOut | None


class EvaluationSessionListOut(BaseModel):
    items: list[EvaluationSessionOut]


class KeyIn(BaseModel):
    """The pseudonym key, typed by the key holder; never stored, logged or echoed."""

    key: SecretStr


class KeyStateOut(BaseModel):
    """The stored fingerprint of the pseudonym key, or nulls before the first export."""

    fingerprint: str | None
    set_at: datetime | None


class ExportIn(BaseModel):
    class_session_ids: Annotated[
        list[uuid.UUID], Field(min_length=1, max_length=EXPORT_SESSIONS_MAX)
    ]
    key: SecretStr


class ExportSessionOut(BaseModel):
    """A Class session of an export, with the day by which the exported data must be deleted;
    the name fields are null for a Class session that is gone."""

    id: uuid.UUID
    number: int | None
    class_name: str | None
    deletion_date: date | None


class ExportOut(BaseModel):
    """One export run or refusal, from its audit row."""

    id: uuid.UUID
    occurred_at: datetime
    actor_id: uuid.UUID | None
    actor_name: str | None
    outcome: str
    key_fingerprint: str | None
    class_sessions: list[ExportSessionOut]


class ExportListOut(BaseModel):
    items: list[ExportOut]
