"""The tables owned by `modules/tests` (Story 6.3, FR-85; Story 11.1, FR-52; Story 11.2, FR-81;
Story 11.3, FR-51; Story 11.8, FR-53)."""

from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from app.platform.db import metadata

PLAYED_BEFORE = "played_before"
"""The `item_id` of the final question's row; content item ids hold no underscore."""


class Choice(StrEnum):
    """The answers to «Har du spilt et spill som ligner dette før?»; `skipped` is «Hopp over»."""

    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"
    SKIPPED = "skipped"


starting_task_answers = Table(
    "starting_task_answers",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("content_version", Integer, nullable=False),
    Column("item_id", Text, nullable=False),
    Column("answer", Integer, nullable=True),
    Column("correct", Boolean, nullable=True),
    Column("choice", Text, nullable=True),
    Column("answered_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        f"(item_id = '{PLAYED_BEFORE}' AND answer IS NULL AND correct IS NULL "
        "AND choice IN (" + ", ".join(f"'{c.value}'" for c in Choice) + ")) OR "
        f"(item_id <> '{PLAYED_BEFORE}' AND answer IS NOT NULL AND correct IS NOT NULL "
        "AND choice IS NULL)",
        name="ck_starting_task_answers_kind",
    ),
    UniqueConstraint(
        "user_id", "class_session_id", "item_id", name="uq_starting_task_answers_item"
    ),
)
"""One row per Student, Class session and item, stored once; the final question's row has
`item_id = 'played_before'` and a `choice`."""


test_selections = Table(
    "test_selections",
    metadata,
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("question_set_version", Integer, nullable=False),
    Column("excluded", ARRAY(Text), nullable=False, server_default="{}"),
    Column("weights", JSONB, nullable=False),
    Column("adapted_weight", Integer, nullable=False),
    Column("updated_by", Uuid, ForeignKey("users.id", ondelete="SET NULL")),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("question_set_version >= 1", name="ck_test_selections_version"),
    CheckConstraint("adapted_weight BETWEEN 0 AND 100", name="ck_test_selections_adapted_weight"),
)
"""A Class session's selection of the question set (Story 11.1, FR-52, FR-53): the version it was
made on, the items taken out, each Core item's weight and the Adapted total weight, saved with
«Lagre vekter» before the Start date. No row reads as the latest version's defaults; the lock pins
the selection in force (`selection.question_set_pin`)."""


test_scoring_guides = Table(
    "test_scoring_guides",
    metadata,
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "scoring_guide_id",
        Uuid,
        ForeignKey("content_records.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("base_id", Uuid, ForeignKey("content_records.id", ondelete="CASCADE"), nullable=False),
    Column("pinned_at", DateTime(timezone=True), nullable=True),
    Column("updated_by", Uuid, ForeignKey("users.id", ondelete="SET NULL")),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
"""The Scoring guide version in force for a Class session (Story 11.2, FR-81, AD-23): a version
a Lecturer's save made for it (or one a copy carried over, FR-66), the default it derives from
(`base_id`: a question whose text differs from it is «Endret»), and when the Test-deadline lock
pinned it. No row reads as the latest default. A trigger (migration 0122) refuses any change of a
pinned row."""


class AttemptStatus(StrEnum):
    """An Individual test attempt's status (Story 11.3, AD-9): `open` until the Student submits
    (`submitted`, Story 11.10) or the Test deadline or the sitting's end submits it
    (`auto_submitted`, Stories 11.11 and 11.12)."""

    OPEN = "open"
    SUBMITTED = "submitted"
    AUTO_SUBMITTED = "auto_submitted"


test_attempts = Table(
    "test_attempts",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("question_set_version", Integer, nullable=False),
    Column("selection", JSONB, nullable=False),
    Column("items", JSONB, nullable=False),
    Column("statement_accepted_at", DateTime(timezone=True), nullable=False),
    Column("effective_deadline", DateTime(timezone=True), nullable=True),
    Column("status", Text, nullable=False, server_default=AttemptStatus.OPEN.value),
    Column("submitted_at", DateTime(timezone=True), nullable=True),
    Column("sitting_ends_at", DateTime(timezone=True), nullable=True),
    CheckConstraint("question_set_version >= 1", name="ck_test_attempts_version"),
    CheckConstraint(
        "status IN (" + ", ".join(f"'{s.value}'" for s in AttemptStatus) + ")",
        name="ck_test_attempts_status",
    ),
    CheckConstraint(
        "(status = 'open') = (submitted_at IS NULL)", name="ck_test_attempts_submitted"
    ),
    UniqueConstraint("user_id", "class_session_id", name="uq_test_attempts_user_session"),
)
"""A Student's Individual test in a Class session (Story 11.3, FR-51, AD-9, AD-23), made once when
they accept the own-work statement (`statement_accepted_at`): the question set version and
selection it was opened on, the frozen ordered item list (`[{id, type, weight}]`), the Student's
effective Test deadline and its status. Written only by `tests.commands`."""


test_answers = Table(
    "test_answers",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column(
        "attempt_id",
        Uuid,
        ForeignKey("test_attempts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("item_id", Text, nullable=False),
    Column("value", JSONB, nullable=False),
    Column("revision", Integer, nullable=False),
    Column("saved_at", DateTime(timezone=True), nullable=False),
    Column("score", JSONB, nullable=True),
    Column("scored_version", Integer, nullable=True),
    CheckConstraint("revision >= 1", name="ck_test_answers_revision"),
    CheckConstraint(
        "score IS NULL OR scored_version IS NOT NULL", name="ck_test_answers_scored_version"
    ),
    UniqueConstraint("attempt_id", "item_id", name="uq_test_answers_item"),
)
"""One saved answer per attempt and item with its revision, the highest kept (Story 11.4 on), and
from the hand-in its computed score with the question set version it was computed with (Story
11.10; null for an answer no computed rule scores). Written only by `tests.commands`; holds text a
Student wrote (personal data)."""


test_prepared_items = Table(
    "test_prepared_items",
    metadata,
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("question_set_version", Integer, nullable=False),
    Column("adapted_weight", Integer, nullable=False),
    Column("items", JSONB, nullable=False),
    Column("prepared_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    PrimaryKeyConstraint("user_id", "class_session_id", name="pk_test_prepared_items"),
    CheckConstraint("question_set_version >= 1", name="ck_test_prepared_items_version"),
    CheckConstraint(
        "adapted_weight BETWEEN 0 AND 100", name="ck_test_prepared_items_adapted_weight"
    ),
)
"""A Student's prepared Adapted items in a Class session (Story 11.8, AD-9): the Adapted (or
replacement) items the `tests.prepare_adapted` job built before the Student opened the test, with
any LLM wording already validated, for the question set version and Adapted total weight they were
built for. Stored once by `tests.prepare`, never updated; `tests.commands.open_attempt` freezes
them. Holds the Student's id and text rendered from their own game's facts (personal data)."""
