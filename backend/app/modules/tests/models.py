"""The tables owned by `modules/tests` (Story 6.3, FR-85; Story 11.1, FR-52)."""

from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
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
