"""Free Seats before the start (Story 5.10, FR-20, AD-2, AD-5).

`games.commands.move_seat` moves a Student to another Seat of the Class session before its Games
start. Occupancy is append-only, so the Seat left behind gets a row of its own: no occupant kind,
reason `moved`. `seat_occupancy.occupant_kind` becomes nullable, `ck_seat_occupancy_free` ties a
NULL kind to the reason `moved` (and no policy id or user id), and both reason checks take `moved`.

Revision ID: 0039
Revises: 0038
Create Date: 2026-11-20
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0039"
down_revision: str | None = "0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REASONS = (
    "initial",
    "takeover_inactivity",
    "takeover_staff",
    "takeover_peer",
    "reclaim",
    "guard_switch",
    "cost_limit",
    "playout",
)
FREE_SEAT_ROW = (
    "(occupant_kind IS NULL) = (reason = 'moved') "
    "AND (occupant_kind IS NOT NULL OR (policy_id IS NULL AND user_id IS NULL))"
)


def _reasons(*extra: str) -> str:
    return f"reason IN ({', '.join(repr(r) for r in (*REASONS, *extra))})"


def _replace_reason_checks(*extra: str) -> None:
    for table in ("seat_occupancy", "seat_weeks"):
        op.drop_constraint(f"ck_{table}_reason", table, type_="check")
        op.create_check_constraint(f"ck_{table}_reason", table, _reasons(*extra))


def upgrade() -> None:
    _replace_reason_checks("moved")
    op.alter_column("seat_occupancy", "occupant_kind", nullable=True)
    op.create_check_constraint("ck_seat_occupancy_free", "seat_occupancy", FREE_SEAT_ROW)


def downgrade() -> None:
    # A free-Seat row makes the checks below fail: occupancy is append-only, so the downgrade
    # does not delete it.
    op.drop_constraint("ck_seat_occupancy_free", "seat_occupancy", type_="check")
    op.alter_column("seat_occupancy", "occupant_kind", nullable=False)
    _replace_reason_checks()
