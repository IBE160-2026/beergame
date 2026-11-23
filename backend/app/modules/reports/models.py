"""The tables owned by `modules/reports` (Stories 13.4, 13.7 and 14.3, FR-17, FR-20, FR-57, FR-65).

`makeup_games` names each Student's one Oppfølgingsspill in a Class session: the `makeup` Game a
Lecturer gave them, who gave it and when. The Game itself, its Seats and its Weeks are `games`
tables, written only by `games.commands`."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    PrimaryKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.platform.db import metadata

makeup_games = Table(
    "makeup_games",
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
    Column("game_id", Uuid, ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
    Column("given_by", Uuid, ForeignKey("users.id", ondelete="SET NULL")),
    Column("given_at", DateTime(timezone=True), nullable=False),
    # One Oppfølgingsspill per Student and Class session: two presses at once make one Game.
    UniqueConstraint("user_id", "class_session_id", name="uq_makeup_games_student"),
    UniqueConstraint("game_id", name="uq_makeup_games_game"),
)


# The Student report (Story 13.7, FR-57, AD-9, AD-14, AD-18).

REPORT_STATUSES = ("pending", "ready", "failed")
REPORT_VARIANTS = ("standard", "ai", "ai_letter", "staff", "staff_ai")
"""Story 13.11: `standard` holds no AI data; `ai` adds the AI assessment section, `ai_letter` the
section with the Indicative letter. Story 13.12: `staff` and `staff_ai` are the staff's downloads
(the latter with the section, never the letter). Each is its own request and its own stored PDF."""

report_requests = Table(
    "report_requests",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    # The Student the report is about.
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("requested_by", Uuid, ForeignKey("users.id", ondelete="SET NULL")),
    Column("variant", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("requested_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True)),
    # The PDF's object path in the `reports` bucket once ready; never a name.
    Column("object_path", Text),
    # A failure's code only (`render_failed`, `stale`), never a message.
    Column("failure", Text),
    CheckConstraint("status IN ('pending', 'ready', 'failed')", name="ck_report_requests_status"),
    CheckConstraint(
        "variant IN ('standard', 'ai', 'ai_letter', 'staff', 'staff_ai')",
        name="ck_report_requests_variant",
    ),
    Index("ix_report_requests_student", "class_session_id", "user_id", "requested_at"),
    # One render at a time per Student, Class session and variant: a second press answers it.
    Index(
        "uq_report_requests_pending",
        "class_session_id",
        "user_id",
        "variant",
        unique=True,
        postgresql_where=text("status = 'pending'"),
    ),
)
"""Each press of «Lag Studentrapport»: who asked, for whom, and how the render ended."""

report_snapshots = Table(
    "report_snapshots",
    metadata,
    Column("id", Uuid, primary_key=True),
    # The single report's request, or (Story 13.13) the ZIP's: exactly one of the two.
    Column(
        "request_id",
        Uuid,
        ForeignKey("report_requests.id", ondelete="CASCADE"),
        index=True,
    ),
    Column("zip_id", Uuid, ForeignKey("report_zips.id", ondelete="CASCADE"), index=True),
    # SHA-256 of the render token; the token itself is never stored.
    Column("token_hash", LargeBinary, nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("used_at", DateTime(timezone=True)),
    # `reports.build_report_data`'s output: the Student's name and their work. Deleted when the
    # render ends, so no copy stays outside the bucket (AD-14).
    Column("data", JSONB, nullable=False),
    CheckConstraint("(request_id IS NULL) <> (zip_id IS NULL)", name="ck_report_snapshots_owner"),
)
"""The report content between the assembler and the print route, for one render only."""

report_zips = Table(
    "report_zips",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("requested_by", Uuid, ForeignKey("users.id", ondelete="SET NULL")),
    Column("status", Text, nullable=False),
    Column("requested_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True)),
    # The ZIP's object path in the `reports` bucket once ready; never a name.
    Column("object_path", Text),
    # A failure's code only (`render_failed`, `stale`), never a message.
    Column("failure", Text),
    # How many Student reports the ready ZIP holds.
    Column("students", Integer),
    CheckConstraint("status IN ('pending', 'ready', 'failed')", name="ck_report_zips_status"),
    Index("ix_report_zips_session", "class_session_id", "requested_at"),
    # One ZIP at a time per Class session: a second press answers it.
    Index(
        "uq_report_zips_pending",
        "class_session_id",
        unique=True,
        postgresql_where=text("status = 'pending'"),
    ),
)
"""Story 13.13: each press of «Last ned alle Studentrapporter (ZIP)»: who asked, for which Class
session, and how its job ended."""


# The aggregates of Cross-class statistics (Story 14.3, FR-65, AD-14).

class_aggregates = Table(
    "class_aggregates",
    metadata,
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    # When `reports.write_aggregate` last wrote the rows (the host clock, as the assessments').
    Column("written_at", DateTime(timezone=True), nullable=False),
    # Group sizes: the reporting Students, those who held a Seat in a finished Class game, and
    # the finished Class games. Counts only.
    Column("students", Integer, nullable=False),
    Column("game_students", Integer, nullable=False),
    Column("games_finished", Integer, nullable=False),
    # What a comparison must hold equal (Game settings, AI mode, model config, prompt versions,
    # Effort level, question set, Item weights, Scoring guide): settings and ids, no text.
    Column("keys", JSONB, nullable=False),
    CheckConstraint(
        "students >= 0 AND game_students >= 0 AND games_finished >= 0",
        name="ck_class_aggregates_counts",
    ),
)
"""One anonymised aggregate per Class session: the header of its measure rows. No `user_id`,
`seat_id`, Game id, name or free text; it survives the deletion of the Student data."""

class_aggregate_measures = Table(
    "class_aggregate_measures",
    metadata,
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_aggregates.class_session_id", ondelete="CASCADE"),
        nullable=False,
    ),
    # A measure code (`chain.median`, `cost.factory.median`, `question.<item id>.percent`, ...).
    Column("measure", Text, nullable=False),
    # How many Students the measure is over; under 10 it is withheld.
    Column("group_size", Integer, nullable=False),
    Column("value", Numeric, nullable=True),
    Column("withheld", Boolean, nullable=False),
    PrimaryKeyConstraint("class_session_id", "measure", name="pk_class_aggregate_measures"),
    CheckConstraint("group_size >= 0", name="ck_class_aggregate_measures_group"),
    CheckConstraint("NOT withheld OR value IS NULL", name="ck_class_aggregate_measures_withheld"),
)
"""One figure of a Class session's aggregate, or the mark that its group was too small."""
