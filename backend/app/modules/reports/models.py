"""The tables owned by `modules/reports` (Story 13.4, FR-17, FR-20).

`makeup_games` names each Student's one Oppfølgingsspill in a Class session: the `makeup` Game a
Lecturer gave them, who gave it and when. The Game itself, its Seats and its Weeks are `games`
tables, written only by `games.commands`."""

from sqlalchemy import Column, DateTime, ForeignKey, Table, UniqueConstraint, Uuid

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
