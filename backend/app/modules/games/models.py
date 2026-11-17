"""Tables owned by `modules/games`. Only `games.commands` writes them (AD-2)."""

from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
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
    false,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.modules.games.schemas import (
    DecidedBy,
    Fallback,
    Lifecycle,
    OccupancyReason,
    OccupantKind,
    Purpose,
)
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
    # False: the opened Week. True: the finished state after the last Week, same Week number.
    Column("finished", Boolean, primary_key=True, server_default=false()),
    # The engine's `WeekState`, stored before anyone can read it (FR-26).
    Column("state", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("week >= 1", name="ck_game_weeks_week"),
)
"""Append-only: a trigger refuses UPDATE and DELETE."""

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
Week, the Seat, `opened_at`, an `ordered_at` already set, or the Rule-based reference Order,
which is computed once when the Week opens (AD-5)."""

seat_weeks = Table(
    "seat_weeks",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("game_id", Uuid, ForeignKey("games.id"), nullable=False),
    Column("seat_id", Uuid, ForeignKey("seats.id"), nullable=False),
    Column("week", Integer, nullable=False),
    # The `SeatState` the Seat saw when it ordered (AD-3, FR-67).
    Column("state_seen", JSONB, nullable=False),
    Column("order", Integer, nullable=False),
    Column("decided_by", Text, nullable=False),
    Column("fallback", Text, nullable=False),
    # The occupancy row in force when the Order was placed.
    Column("occupant_kind", Text, nullable=False),
    Column("reason", Text, nullable=False),
    Column("opened_at", DateTime(timezone=True), nullable=False),
    Column("ordered_at", DateTime(timezone=True), nullable=False),
    Column("rule_based_reference_order", Integer, nullable=False),
    CheckConstraint("week >= 1", name="ck_seat_weeks_week"),
    CheckConstraint('"order" >= 0', name="ck_seat_weeks_order"),
    CheckConstraint("rule_based_reference_order >= 0", name="ck_seat_weeks_reference_order"),
    CheckConstraint(_in("decided_by", DecidedBy), name="ck_seat_weeks_decided_by"),
    CheckConstraint(_in("fallback", Fallback), name="ck_seat_weeks_fallback"),
    CheckConstraint(_in("occupant_kind", OccupantKind), name="ck_seat_weeks_occupant_kind"),
    CheckConstraint(_in("reason", OccupancyReason), name="ck_seat_weeks_reason"),
    UniqueConstraint("game_id", "week", "seat_id", name="uq_seat_weeks_game_week_seat"),
)
"""The Decision log (AD-15): one row per Seat per Week, written once by `place_order`. A
trigger refuses UPDATE and DELETE."""

game_checks = Table(
    "game_checks",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("game_id", Uuid, ForeignKey("games.id"), nullable=False),
    # The rules version the Game was replayed at: its stored `rules_version`.
    Column("rules_version", Integer, nullable=False),
    Column("ok", Boolean, nullable=False),
    # The `engine.Violation`s found, as JSON; empty when `ok`.
    Column("violations", JSONB, nullable=False),
    Column("checked_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("ok = (jsonb_array_length(violations) = 0)", name="ck_game_checks_ok"),
    UniqueConstraint("game_id", name="uq_game_checks_game"),
)
"""The finished-game check (AD-9, FR-29): one row per finished Game, written once by
`games.service.verify_finished`. A trigger refuses UPDATE and DELETE."""
