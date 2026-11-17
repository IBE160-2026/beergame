"""Tables owned by `modules/games`. Only `games.commands` writes them (AD-2)."""

from enum import StrEnum

from sqlalchemy import (
    BigInteger,
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
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.modules.games.schemas import Lifecycle, OccupancyReason, OccupantKind, Purpose
from app.platform.db import metadata


def _in(column: str, values: type[StrEnum]) -> str:
    return f"{column} IN ({', '.join(repr(value.value) for value in values)})"


games = Table(
    "games",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("purpose", Text, nullable=False),
    Column("lifecycle", Text, nullable=False),
    Column("version", Integer, nullable=False),
    Column("settings", JSONB, nullable=False),
    Column("demand_series", JSONB, nullable=False),
    Column("demand_seed", BigInteger, nullable=False),
    Column("rules_version", Integer, nullable=False),
    Column("session_runtime", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(_in("purpose", Purpose), name="ck_games_purpose"),
    CheckConstraint(_in("lifecycle", Lifecycle), name="ck_games_lifecycle"),
    CheckConstraint("version >= 0", name="ck_games_version"),
)

seats = Table(
    "seats",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("game_id", Uuid, ForeignKey("games.id"), nullable=False),
    Column("role", Text, nullable=False),
    # Place in the chain: 0 is the Role that serves the customer.
    Column("position", SmallInteger, nullable=False),
    UniqueConstraint("game_id", "role", name="uq_seats_game_role"),
    UniqueConstraint("game_id", "position", name="uq_seats_game_position"),
)

seat_occupancy = Table(
    "seat_occupancy",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("seat_id", Uuid, ForeignKey("seats.id"), nullable=False, index=True),
    Column("from_week", Integer, nullable=False),
    Column("occupant_kind", Text, nullable=False),
    Column("policy_id", Text, nullable=True),
    Column("reason", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("from_week >= 1", name="ck_seat_occupancy_from_week"),
    CheckConstraint(_in("occupant_kind", OccupantKind), name="ck_seat_occupancy_kind"),
    CheckConstraint(_in("reason", OccupancyReason), name="ck_seat_occupancy_reason"),
)
"""Append-only (AD-5): a trigger refuses UPDATE and DELETE. The latest row by `id` (UUIDv7) is
the current occupant."""

game_weeks = Table(
    "game_weeks",
    metadata,
    Column("game_id", Uuid, ForeignKey("games.id"), primary_key=True),
    Column("week", Integer, primary_key=True),
    # The engine's `WeekState` of the opened Week, stored before anyone can read it (FR-26).
    Column("state", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("week >= 1", name="ck_game_weeks_week"),
)

seat_turns = Table(
    "seat_turns",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("game_id", Uuid, ForeignKey("games.id"), nullable=False),
    Column("seat_id", Uuid, ForeignKey("seats.id"), nullable=False),
    Column("week", Integer, nullable=False),
    Column("opened_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("ordered_at", DateTime(timezone=True), nullable=True),
    Column("rule_based_reference_order", Integer, nullable=False),
    CheckConstraint("week >= 1", name="ck_seat_turns_week"),
    CheckConstraint("rule_based_reference_order >= 0", name="ck_seat_turns_reference_order"),
    UniqueConstraint("game_id", "week", "seat_id", name="uq_seat_turns_game_week_seat"),
)
"""One row per Seat per opened Week (AD-20). A trigger refuses DELETE and any UPDATE of the
Week, the Seat, `opened_at` or the Rule-based reference Order, which is computed once when the
Week opens (AD-5)."""
