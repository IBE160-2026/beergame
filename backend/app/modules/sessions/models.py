"""Tables owned by `modules/sessions` (Story 5.1, FR-11, AD-4)."""

from sqlalchemy import (
    BigInteger,
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
    true,
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
    # The Start-date lock (Story 5.11, AD-4): when it froze the session, and what it froze
    # (`service.build_snapshot`). Both set together, by `service.lock` only.
    Column("locked_at", DateTime(timezone=True), nullable=True),
    Column("snapshot", JSONB(none_as_null=True), nullable=True),
    # When the sweep first refused the lock for a missing provider key (GitHub issue 109); NULL
    # otherwise. A refused lock shows on the Klasseøkt while `locked_at` is NULL.
    Column("lock_refused_at", DateTime(timezone=True), nullable=True),
    # How the Students get their Seats (Story 5.17, FR-21): `random` (Stories 5.8 to 5.13) or
    # `student_choice`, final once saved.
    Column("allocation_method", Text, nullable=False, server_default="random"),
    # The Class session this one was copied from (Story 5.18, FR-66); NULL otherwise, and once
    # that session is gone.
    Column(
        "copied_from",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="SET NULL", name="fk_class_sessions_copied_from"),
        nullable=True,
    ),
    # The source's Effort level when the new model config did not offer it (Story 5.18, FR-78).
    Column("effort_level_replaced", Text, nullable=True),
    # When the Debriefs open (Story 9.2, FR-42): `open`, each Student's once their own Class game
    # has finished, or `hold`, all of them once every Class game has. Frozen at the Start date.
    Column("debrief_release", Text, nullable=False, server_default="open"),
    # The Debrief's AI text (Story 9.14, FR-15, FR-44): on, or off for a code-only Debrief.
    # Frozen at the Start date and pinned at the lock (`debrief_ai_text`).
    Column("debrief_ai_text", Boolean, nullable=False, server_default=true()),
    CheckConstraint("(locked_at IS NULL) = (snapshot IS NULL)", name="ck_class_sessions_lock"),
    CheckConstraint(
        "allocation_method IN ('random', 'student_choice')",
        name="ck_class_sessions_allocation_method",
    ),
    CheckConstraint("ai_mode IN ('llm', 'rule_based')", name="ck_class_sessions_ai_mode"),
    CheckConstraint("debrief_mode IN ('group', 'personal')", name="ck_class_sessions_debrief_mode"),
    CheckConstraint(
        "debrief_release IN ('open', 'hold')", name="ck_class_sessions_debrief_release"
    ),
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

allocation_drafts = Table(
    "allocation_drafts",
    metadata,
    Column("id", Uuid, primary_key=True),
    # One current draft per Class session: a new draw replaces the row under a new id.
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    # 1 when drawn; Story 5.10's edits raise it, and Story 5.9's confirm checks it.
    Column("revision", Integer, nullable=False),
    Column("seed", BigInteger, nullable=False),
    # `[{"user_id", "game_number", "role"}]`: ids only, never names or emails (AD-14).
    Column("assignments", JSONB, nullable=False),
    Column("drawn_by", Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("drawn_at", DateTime(timezone=True), nullable=False),
    # Set when the Lecturer confirms this draft (Story 5.9); its Class games exist from then on.
    Column("confirmed_at", DateTime(timezone=True), nullable=True),
    Column(
        "confirmed_by",
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL", name="fk_allocation_drafts_confirmed_by"),
        nullable=True,
    ),
    CheckConstraint("revision >= 1", name="ck_allocation_drafts_revision"),
    UniqueConstraint("class_session_id", name="uq_allocation_drafts_class_session"),
)
"""The Class session's current allocation draft (Story 5.8, FR-20): what the preview shows and
what Story 5.9 confirms by id and revision. Never recomputed from the Roster."""

DEADLINE_NAMES = DATE_NAMES[1:]
"""The three deadlines a Student is reminded of (Story 5.14): Spillfrist, Debrieffrist and
Testfrist."""

deadline_reminders = Table(
    "deadline_reminders",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("deadline", Text, nullable=False),
    # The deadline's time when it was reminded: a moved deadline has a new time and a new row.
    Column("deadline_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "deadline IN ('play_deadline', 'debrief_deadline', 'test_deadline')",
        name="ck_deadline_reminders_deadline",
    ),
    UniqueConstraint(
        "class_session_id", "deadline", "deadline_at", name="uq_deadline_reminders_deadline"
    ),
)
"""One row per deadline time the Students were reminded of, 24 hours ahead (Story 5.14, FR-18):
what the sweep's `sessions.send_deadline_reminder` finder skips, and the `ref` of each
`deadline_reminder` notice. Ids and times only (AD-14)."""
