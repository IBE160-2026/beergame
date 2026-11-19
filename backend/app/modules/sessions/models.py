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
    # The `ai` model config the Class session uses; no foreign key into `ai` tables (AD-6).
    Column("model_config_id", Uuid, nullable=True),
    Column("created_by", Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    # Set by «Lagre Klasseøkt»; NULL while the Class session was created and never saved.
    Column("saved_at", DateTime(timezone=True), nullable=True),
    CheckConstraint("ai_mode IN ('llm', 'rule_based')", name="ck_class_sessions_ai_mode"),
    CheckConstraint("debrief_mode IN ('group', 'personal')", name="ck_class_sessions_debrief_mode"),
    CheckConstraint(
        f"inactivity_limit_hours >= {MIN_INACTIVITY_LIMIT_HOURS}",
        name="ck_class_sessions_inactivity_limit",
    ),
    CheckConstraint(
        "ai_mode <> 'llm' OR model_config_id IS NOT NULL",
        name="ck_class_sessions_llm_has_config",
    ),
)
"""One row per Class session. Times come from the api's clock."""
