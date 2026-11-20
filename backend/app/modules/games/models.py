"""Tables owned by `modules/games`. Only `games.commands` writes them (AD-2)."""

from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    false,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

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


SNAPSHOT_COLUMNS = ("settings", "demand_series", "demand_seed", "rules_version", "session_runtime")
SNAPSHOT_TOGETHER = f"num_nulls({', '.join(SNAPSHOT_COLUMNS)}) IN (0, {len(SNAPSHOT_COLUMNS)})"


simulation_batches = Table(
    "simulation_batches",
    metadata,
    Column("id", Uuid, primary_key=True),
    # The batch file as `python -m app.sim run` played it (its `model_config` filled in).
    Column("batch_file", JSONB, nullable=False),
    # The pass lines from the batch file (`{}` when it has none); never a code default (C-3).
    Column("pass_lines", JSONB, nullable=False),
    # The batch's LLM Seats were answered by the mock provider (AD-17).
    Column("mock", Boolean, nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
"""One row per simulation batch (Story 2.11, AD-22), written once by
`games.service.create_batch`. A trigger refuses UPDATE and DELETE, so its pass lines never
change after its first Game starts."""

games = Table(
    "games",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("purpose", Text, nullable=False),
    Column("lifecycle", Text, nullable=False),
    Column("version", Integer, nullable=False),
    # The frozen snapshot (AD-4): all five set together, or all NULL on a Game whose policy takes
    # it at the lock and that has not got it yet (Story 5.9).
    Column("settings", JSONB(none_as_null=True), nullable=True),
    Column("demand_series", JSONB(none_as_null=True), nullable=True),
    Column("demand_seed", BigInteger, nullable=True),
    Column("rules_version", Integer, nullable=True),
    Column("session_runtime", JSONB(none_as_null=True), nullable=True),
    # The Class session and its game number (Story 5.9), on Class games only. No foreign key:
    # `games` sits below `sessions`, which owns the Class session.
    Column("class_session_id", Uuid, nullable=True),
    Column("game_number", Integer, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    # The simulation batch the Game was played in (Story 2.11); None for every other Game.
    Column(
        "batch_id",
        Uuid,
        ForeignKey("simulation_batches.id"),
        nullable=True,
        index=True,
    ),
    CheckConstraint(_in("purpose", Purpose), name="ck_games_purpose"),
    CheckConstraint(_in("lifecycle", Lifecycle), name="ck_games_lifecycle"),
    CheckConstraint("version >= 0", name="ck_games_version"),
    CheckConstraint(SNAPSHOT_TOGETHER, name="ck_games_snapshot"),
    CheckConstraint(
        "(class_session_id IS NULL) = (game_number IS NULL)", name="ck_games_class_session"
    ),
    CheckConstraint("game_number >= 1", name="ck_games_game_number"),
    UniqueConstraint("class_session_id", "game_number", name="uq_games_class_session_number"),
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
    # The Student of a `student` occupant (Story 5.9): the id only, never a name (AD-14). No
    # foreign key: the rows are append-only, so a removed User could not be set NULL here.
    Column("user_id", Uuid, nullable=True),
    CheckConstraint("from_week >= 1", name="ck_seat_occupancy_from_week"),
    CheckConstraint(
        "occupant_kind = 'student' OR user_id IS NULL", name="ck_seat_occupancy_user_student"
    ),
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
    # When an LLM player's Order is due (AD-5, AD-20): set by `games.rules.turn_times`, NULL for
    # every other turn; the `worker-ai` rescue loop places the fallback Order after it.
    Column("ai_deadline_at", DateTime(timezone=True), nullable=True),
    # The near-optimal reference Order and the algorithm version that computed it (Story 2.9,
    # FR-67, FR-79); NULL only on turns opened before revision 0012.
    Column("near_optimal_reference_order", Integer, nullable=True),
    Column("near_optimal_algorithm_version", Text, nullable=True),
    CheckConstraint("week >= 1", name="ck_seat_turns_week"),
    CheckConstraint("rule_based_reference_order >= 0", name="ck_seat_turns_reference_order"),
    CheckConstraint("near_optimal_reference_order >= 0", name="ck_seat_turns_near_optimal_order"),
    CheckConstraint(
        "(near_optimal_reference_order IS NULL) = (near_optimal_algorithm_version IS NULL)",
        name="ck_seat_turns_near_optimal_pair",
    ),
    UniqueConstraint("game_id", "week", "seat_id", name="uq_seat_turns_game_week_seat"),
    Index(
        "ix_seat_turns_ai_deadline",
        "ai_deadline_at",
        postgresql_where=text("ordered_at IS NULL AND ai_deadline_at IS NOT NULL"),
    ),
)
"""One row per Seat per opened Week (AD-20). A trigger refuses DELETE and any UPDATE of the
Week, the Seat, `opened_at`, an `ordered_at` already set, an `ai_deadline_at` already set, the
Rule-based reference Order, or a near-optimal reference already set: both references are
computed once when the Week opens (AD-5)."""

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
    # The LLM call rows behind the Order (FR-67): its attempts, or the failed ones behind a
    # fallback Order.
    Column("llm_call_ids", ARRAY(Uuid), nullable=False, server_default=text("'{}'")),
    # The turn's AI deadline, copied like its other times (AD-15, AD-20).
    Column("ai_deadline_at", DateTime(timezone=True), nullable=True),
    # The turn's near-optimal reference and its algorithm version, copied (Story 2.9).
    Column("near_optimal_reference_order", Integer, nullable=True),
    Column("near_optimal_algorithm_version", Text, nullable=True),
    # The Effort level the Game froze, on rows an `llm` occupant ordered (Story 2.11, FR-78).
    Column("effort_level", Text, nullable=True),
    CheckConstraint("week >= 1", name="ck_seat_weeks_week"),
    CheckConstraint('"order" >= 0', name="ck_seat_weeks_order"),
    CheckConstraint("rule_based_reference_order >= 0", name="ck_seat_weeks_reference_order"),
    CheckConstraint("near_optimal_reference_order >= 0", name="ck_seat_weeks_near_optimal_order"),
    CheckConstraint(
        "(near_optimal_reference_order IS NULL) = (near_optimal_algorithm_version IS NULL)",
        name="ck_seat_weeks_near_optimal_pair",
    ),
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
