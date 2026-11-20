"""Tables owned by `modules/sessions` (Story 5.1, FR-11, AD-4)."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Table,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.platform.db import metadata

MIN_INACTIVITY_LIMIT_HOURS = 20
"""The floor of the Inactivity limit (EXPERIENCE.md: whole hours, never under 20)."""

MIN_REQUIRED_SHARE_PERCENT = 1
MAX_REQUIRED_SHARE_PERCENT = 100
"""The range of «Andel uker som kreves», a whole percent (Story 5.7, FR-17)."""

DATE_NAMES = ("start_at", "play_deadline", "debrief_deadline", "test_deadline")
"""The four dates of a Class session in their order (Story 5.2, FR-18): Startdato, Spillfrist,
Debrieffrist, Testfrist. Every pair that is set keeps this order."""

class_sessions = Table(
    "class_sessions",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column(
        "class_id", Uuid, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
    ),
    # The engine's `GameSettings` as JSON, with its `schema_version` (AD-4).
    Column("game_settings", JSONB, nullable=False),
    Column("ai_mode", Text, nullable=False),
    Column("debrief_mode", Text, nullable=False),
    Column("inactivity_limit_hours", Integer, nullable=False),
    Column("obligatory", Boolean, nullable=False),
    # The share of Weeks a Student must order in, in percent (Story 5.7); read through
    # `service.required_share` only.
    Column("required_share_percent", Integer, nullable=False),
    # The `ai` model config the Class session uses; no foreign key into `ai` tables (AD-6).
    Column("model_config_id", Uuid, nullable=True),
    # The Effort level in force (Story 5.5): a level name of that config; NULL for Rule-based.
    Column("effort_level", Text, nullable=True),
    Column("created_by", Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    # Set by «Lagre Klasseøkt»; NULL while the Class session was created and never saved.
    Column("saved_at", DateTime(timezone=True), nullable=True),
    # The four dates (Story 5.2), UTC, NULL until the Lecturer sets them.
    *(Column(name, DateTime(timezone=True), nullable=True) for name in DATE_NAMES),
    CheckConstraint("ai_mode IN ('llm', 'rule_based')", name="ck_class_sessions_ai_mode"),
    CheckConstraint("debrief_mode IN ('group', 'personal')", name="ck_class_sessions_debrief_mode"),
    CheckConstraint(
        f"inactivity_limit_hours >= {MIN_INACTIVITY_LIMIT_HOURS}",
        name="ck_class_sessions_inactivity_limit",
    ),
    CheckConstraint(
        f"required_share_percent BETWEEN {MIN_REQUIRED_SHARE_PERCENT} "
        f"AND {MAX_REQUIRED_SHARE_PERCENT}",
        name="ck_class_sessions_required_share",
    ),
    CheckConstraint(
        "ai_mode <> 'llm' OR model_config_id IS NOT NULL",
        name="ck_class_sessions_llm_has_config",
    ),
    CheckConstraint(
        "ai_mode = 'llm' OR effort_level IS NULL",
        name="ck_class_sessions_effort_level_llm_only",
    ),
    CheckConstraint(
        " AND ".join(
            f"({a} IS NULL OR {b} IS NULL OR {a} < {b})"
            for i, a in enumerate(DATE_NAMES)
            for b in DATE_NAMES[i + 1 :]
        ),
        name="ck_class_sessions_date_order",
    ),
)
"""One row per Class session. Times come from the api's clock."""

PLACE_MAX_LENGTH = 120
"""The longest place of a Lab hour, in characters (Story 5.6)."""

lab_hours = Table(
    "lab_hours",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("starts_at", DateTime(timezone=True), nullable=False),
    Column("ends_at", DateTime(timezone=True), nullable=False),
    Column("place", Text, nullable=False),
    # Raised by each change, so each change has its own notice key.
    Column("revision", Integer, nullable=False, server_default="1"),
    # Set when the Lecturer removes it; the row stays so its cancellation mail can name it.
    Column("cancelled_at", DateTime(timezone=True), nullable=True),
    Column("created_by", Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("ends_at > starts_at", name="ck_lab_hours_order"),
    CheckConstraint(
        f"char_length(place) BETWEEN 1 AND {PLACE_MAX_LENGTH}", name="ck_lab_hours_place"
    ),
)
"""The Lab hours of a Class session (Story 5.6, FR-19), UTC. Only `sessions` reads it; other
modules ask `service.current_lab_hour`."""
