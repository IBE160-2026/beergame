"""The table owned by `modules/content` (Story 6.3, Story 9.1, AD-23)."""

from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Integer,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.platform.db import metadata


class Kind(StrEnum):
    """The closed catalogue of content kinds. Later epics add theirs (quiz, question set …)."""

    STARTING_TASK = "starting_task"
    DETECTED_PATTERNS = "detected_patterns"


content_records = Table(
    "content_records",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("kind", Text, nullable=False),
    Column("version", Integer, nullable=False),
    Column("body", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        "kind IN (" + ", ".join(f"'{kind.value}'" for kind in Kind) + ")",
        name="ck_content_records_kind",
    ),
    CheckConstraint("version >= 1", name="ck_content_records_version"),
    UniqueConstraint("kind", "version", name="uq_content_records_kind_version"),
)
"""A trigger (migration 0046) refuses every UPDATE: a record never changes once stored."""
