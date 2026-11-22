"""The tables owned by `modules/replay` (Stories 10.3, 10.7 and 10.8, FR-48, FR-50).

`replays` names each Student's one Replay in a Class session: the `replay` Game made for them.
The Game itself, its Seats and its Weeks are `games` tables, written only by `games.commands`.

Story 10.7: `replay_narrations` holds the line the `llm-batch` job worded for a Replay Seat's
facts set, and `replay_walkthroughs` a Student's walkthrough stored at their first ready view:
the two facts sets it cites and the line fixed then. Both are written once (a trigger refuses
updates)."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)

from app.platform.db import metadata

replays = Table(
    "replays",
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
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    # One Replay per Student and Class session: two starts at once make one Game (FR-48).
    UniqueConstraint("user_id", "class_session_id", name="uq_replays_student"),
    UniqueConstraint("game_id", name="uq_replays_game"),
)

replay_narrations = Table(
    "replay_narrations",
    metadata,
    # The walkthrough line of a Replay Seat's facts set (Story 10.7, AD-7), stored once by the
    # `llm-batch` job: the AI's, or the code text a rejected or failed call stores.
    Column("fact_set_id", Uuid, ForeignKey("fact_sets.id", ondelete="CASCADE"), primary_key=True),
    Column("text", Text, nullable=False),
    Column("ai_generated", Boolean, nullable=False),
    Column("llm_call_id", Uuid, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        "ai_generated = (llm_call_id IS NOT NULL)", name="ck_replay_narrations_marking"
    ),
)

replay_walkthroughs = Table(
    "replay_walkthroughs",
    metadata,
    # A Student's walkthrough of their Replay (Story 10.7, AD-7): the facts sets it cites and the
    # line fixed at their first ready view, so later views never change under them.
    Column("replay_game_id", Uuid, ForeignKey("games.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "replay_fact_set_id", Uuid, ForeignKey("fact_sets.id", ondelete="CASCADE"), nullable=False
    ),
    Column("compared_game_id", Uuid, ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
    Column(
        "compared_fact_set_id",
        Uuid,
        ForeignKey("fact_sets.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("narration_text", Text, nullable=True),
    Column("narration_ai_generated", Boolean, nullable=False),
    Column("narration_llm_call_id", Uuid, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        "narration_ai_generated = (narration_llm_call_id IS NOT NULL)",
        name="ck_replay_walkthroughs_marking",
    ),
)

replay_another_round = Table(
    "replay_another_round",
    metadata,
    # Story 10.8 (FR-50, SM-10): whether the Student would have wanted to play another round,
    # asked after their Replay-gjennomgang; one answer per Student and Class session, written once
    # (a trigger refuses updates). No name; only the Student who gave it reads it back.
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("answer", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
