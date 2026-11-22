"""The FR-36 due times of a Seat's turn (Story 8.1, FR-35, FR-36, AD-15, AD-20, AD-25).

`seat_turns.takeover_due_at` and `insert_allowed_at` are set by `games.commands` only, from
`games.rules.turn_times`, on the Student-held turns that have not ordered when the first Student
orders (or views a Guided Week) in a Game whose policy has inactivity Takeover. Later stories of
Epic 8 recompute them (Pause, Tilrettelegging, in the room), so the `seat_turns` trigger does not
keep them once set.

`seat_weeks` copies the turn's wait start and both due times when the Order is placed (write-once,
AD-15). `game_summaries.takeover_due_at` holds the nearest due time of the Seats the Game waits
for: the overview's `next_change_at` comes from it.

A Class game already waiting when this revision runs has its wait start stored (0048) but no due
time, and `games.commands` sets due times only with the wait start. `BACKFILL` gives those open
Student-held turns the due times `games.rules.turn_times` would have given them (the wait start
plus the frozen Inactivity limit; no later story's input exists yet), then the summaries of
waiting games their nearest one, as `games.overview.recompute` reads it. Decision log rows already
written stay as they are (write-once, AD-15).

Revision ID: 0053
Revises: 0052
Create Date: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0053"
down_revision: str | None = "0119"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


BACKFILL = """
UPDATE seat_turns t
SET takeover_due_at = t.wait_started_at
        + make_interval(hours => (g.session_runtime->>'inactivity_limit_hours')::int),
    insert_allowed_at = t.wait_started_at
        + make_interval(hours => (g.session_runtime->>'inactivity_limit_hours')::int)
FROM games g
WHERE g.id = t.game_id
  AND g.purpose = 'class'
  AND g.lifecycle = 'running'
  AND g.session_runtime->>'inactivity_limit_hours' IS NOT NULL
  AND t.wait_started_at IS NOT NULL
  AND t.takeover_due_at IS NULL
  AND t.week = (SELECT max(w.week) FROM game_weeks w WHERE w.game_id = t.game_id)
  AND (
      SELECT o.occupant_kind FROM seat_occupancy o
      WHERE o.seat_id = t.seat_id AND o.from_week <= t.week
      ORDER BY o.id DESC LIMIT 1
  ) = 'student';

UPDATE game_summaries gs
SET takeover_due_at = (
    SELECT min(t.takeover_due_at)
    FROM seat_turns t
    JOIN seats s ON s.id = t.seat_id
    WHERE t.game_id = gs.game_id
      AND t.week = gs.week
      AND s.role IN (SELECT w->>'role' FROM jsonb_array_elements(gs.waiting_for) w)
)
WHERE gs.status = 'waiting' AND gs.takeover_due_at IS NULL;
"""
"""Due times for the waits that started before this revision (see the module docstring)."""


def upgrade() -> None:
    for column in ("takeover_due_at", "insert_allowed_at"):
        op.add_column("seat_turns", sa.Column(column, sa.DateTime(timezone=True)))
    for column in ("wait_started_at", "takeover_due_at", "insert_allowed_at"):
        op.add_column("seat_weeks", sa.Column(column, sa.DateTime(timezone=True)))
    op.add_column("game_summaries", sa.Column("takeover_due_at", sa.DateTime(timezone=True)))
    for statement in BACKFILL.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    op.drop_column("game_summaries", "takeover_due_at")
    for column in ("insert_allowed_at", "takeover_due_at", "wait_started_at"):
        op.drop_column("seat_weeks", column)
    for column in ("insert_allowed_at", "takeover_due_at"):
        op.drop_column("seat_turns", column)
