"""The tables owned by `modules/debrief` (Story 9.2, AD-21). Written by `debrief.commands` only."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    SmallInteger,
    Table,
    UniqueConstraint,
    Uuid,
)

from app.platform.db import metadata

STEPS = 5
"""The Debrief's five steps (EXPERIENCE.md → Debrief sequence): 1 «Skriv Forklaringen først» to
5 «Debrief-quiz»."""

debrief_sessions = Table(
    "debrief_sessions",
    metadata,
    Column("id", Uuid, primary_key=True),
    # One Debrief session per Game: its Students share it (the Group debrief, Story 9.11).
    Column("game_id", Uuid, ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    # The step pointer, 1 when opened.
    Column("step", SmallInteger, nullable=False, server_default="1"),
    Column("opened_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("game_id", name="uq_debrief_sessions_game"),
    CheckConstraint(f"step BETWEEN 1 AND {STEPS}", name="ck_debrief_sessions_step"),
)

debrief_releases = Table(
    "debrief_releases",
    metadata,
    # A held Class session whose Debriefs the sweep released, once (Story 9.2).
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("released_at", DateTime(timezone=True), nullable=False),
)
