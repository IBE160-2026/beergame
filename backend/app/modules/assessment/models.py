"""The tables owned by `modules/assessment` (Epic 12).

Story 12.1 (FR-61, AD-9): `assessment_switches` holds the «KI-vurdering» switch of a Class
session, one row per session that was ever saved with it or pinned; no row reads as on. The
Test-deadline lock pins it (`pinned_at`), and a trigger then refuses any update of the row, so
the value an assessment reads never moves. A delete is not refused: the Class session's cascade
removes the row with it."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Table, Uuid, func, true

from app.platform.db import metadata

assessment_switches = Table(
    "assessment_switches",
    metadata,
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("enabled", Boolean, nullable=False, server_default=true()),
    # Set once by `sessions.lock_test` at the original Test deadline; NULL until then.
    Column("pinned_at", DateTime(timezone=True), nullable=True),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
