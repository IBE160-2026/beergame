"""The tables owned by `modules/debrief` (Stories 9.2, 9.3, 9.6 to 9.8, AD-21). Written by
`debrief.commands` only."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB

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

EXPLANATION_MAX = 5000
"""The longest Explanation, in characters (Story 9.3)."""

debrief_explanations = Table(
    "debrief_explanations",
    metadata,
    # One Explanation per Student per Class session (FR-41, AD-14), stored once as typed and never
    # changed (a trigger refuses updates).
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("game_id", Uuid, ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
    Column("text", Text, nullable=False),
    # Characters, as typed.
    Column("length", Integer, nullable=False),
    Column("saved_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        f"length = char_length(text) AND length BETWEEN 1 AND {EXPLANATION_MAX}",
        name="ck_debrief_explanations_length",
    ),
)

ANSWER_MAX = 2000
"""The longest reflection answer, in characters (Story 9.6)."""

debrief_reflection_answers = Table(
    "debrief_reflection_answers",
    metadata,
    # A Student's answer to one reflection question in a Class session (FR-45, AD-14), stored once
    # as typed and never changed (a trigger refuses updates).
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    # The question's id in the pinned content version.
    Column("question_id", Text, primary_key=True),
    Column("game_id", Uuid, ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
    Column("questions_version", Integer, nullable=False),
    Column("text", Text, nullable=False),
    Column("length", Integer, nullable=False),
    Column("saved_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        f"length = char_length(text) AND length BETWEEN 1 AND {ANSWER_MAX}",
        name="ck_debrief_reflection_answers_length",
    ),
)

debrief_fact_sets = Table(
    "debrief_fact_sets",
    metadata,
    # The facts set a Student's own moments are rendered from, in a Class session (Story 9.7,
    # AD-7): stored at their first view of step 4 and never changed (a trigger refuses updates),
    # so every later read cites the same set.
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("game_id", Uuid, ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
    Column("fact_set_id", Uuid, ForeignKey("fact_sets.id", ondelete="CASCADE"), nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
)

debrief_summaries = Table(
    "debrief_summaries",
    metadata,
    # A Student's finished Debrief in a Class session (Story 9.8, FR-47, AD-7, AD-16): the key
    # moments by fact id, the reflection answers and the facts set they cite, with the database
    # time it was finished; stored once and never changed (a trigger refuses updates).
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("game_id", Uuid, ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
    Column("fact_set_id", Uuid, ForeignKey("fact_sets.id", ondelete="CASCADE"), nullable=False),
    # The ids of the Seat's own moments (`moment:<role>:<week>`), by Week; empty when the game
    # was played mostly by AI players.
    Column("moment_ids", JSONB, nullable=False),
    # `[{question_id, questions_version, text}]`, in the order asked.
    Column("reflection", JSONB, nullable=False),
    Column("finished_at", DateTime(timezone=True), nullable=False),
)
