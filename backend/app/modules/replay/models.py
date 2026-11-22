"""The table owned by `modules/replay` (Story 10.3, FR-48).

`replays` names each Student's one Replay in a Class session: the `replay` Game made for them.
The Game itself, its Seats and its Weeks are `games` tables, written only by `games.commands`."""

from sqlalchemy import Column, DateTime, ForeignKey, Table, UniqueConstraint, Uuid, func

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
