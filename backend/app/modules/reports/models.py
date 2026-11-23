"""The tables owned by `modules/reports` (Stories 13.4 and 13.7, FR-17, FR-20, FR-57).

`makeup_games` names each Student's one Oppfølgingsspill in a Class session: the `makeup` Game a
Lecturer gave them, who gave it and when. The Game itself, its Seats and its Weeks are `games`
tables, written only by `games.commands`."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
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
REPORT_VARIANTS = ("standard", "ai", "ai_letter")
"""Story 13.11: `standard` holds no AI data; `ai` adds the AI assessment section, `ai_letter` the
section with the Indicative letter. Each is its own request and its own stored PDF."""

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
        "variant IN ('standard', 'ai', 'ai_letter')", name="ck_report_requests_variant"
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
    Column(
        "request_id",
        Uuid,
        ForeignKey("report_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    # SHA-256 of the render token; the token itself is never stored.
    Column("token_hash", LargeBinary, nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("used_at", DateTime(timezone=True)),
    # `reports.build_report_data`'s output: the Student's name and their work. Deleted when the
    # render ends, so no copy stays outside the bucket (AD-14).
    Column("data", JSONB, nullable=False),
)
"""The report content between the assembler and the print route, for one render only."""
