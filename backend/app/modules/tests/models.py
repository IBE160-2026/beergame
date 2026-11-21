"""The table owned by `modules/tests` (Story 6.3, FR-85)."""

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
