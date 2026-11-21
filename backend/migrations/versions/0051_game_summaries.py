"""The Lecturer overview's read model (Story 7.1, AD-25): `game_summaries`, one row per Game.

`games.commands` rewrites a Game's row in the transaction of every change (`games.overview`); it
is the only source of a Game's status for lists and overviews. This revision creates the table
and stores a row for every existing Game. The backfill below mirrors `games.rules.game_status` and
`games.overview.recompute` in SQL (a revision imports no app code); a test runs `BACKFILL` over
played Games and compares the rows with `recompute`.

Revision ID: 0051
Revises: 0050
Create Date: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0051"
down_revision: str | None = "0050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BACKFILL = """
WITH latest_occupancy AS (
    SELECT DISTINCT ON (o.seat_id) o.seat_id, o.occupant_kind, o.user_id
    FROM seat_occupancy o
    ORDER BY o.seat_id, o.id DESC
),
occupants AS (
    SELECT s.game_id,
           jsonb_agg(
               jsonb_build_object(
                   'role', s.role, 'occupant_kind', l.occupant_kind, 'user_id', l.user_id
               )
               ORDER BY s.position
           ) AS occupants
    FROM seats s
    LEFT JOIN latest_occupancy l ON l.seat_id = s.id
    GROUP BY s.game_id
),
newest AS (
    SELECT DISTINCT ON (w.game_id) w.game_id, w.week, w.finished,
           (SELECT sum((e ->> 'total_cost')::numeric)
            FROM jsonb_array_elements(w.state -> 'seats') e) AS chain_cost
    FROM game_weeks w
    ORDER BY w.game_id, w.week DESC, w.finished DESC
),
student_turns AS (
    SELECT t.game_id, s.role, s.position, t.wait_started_at, f.user_id,
           t.ordered_at IS NOT NULL
           AND NOT (
               t.week <= (g.settings ->> 'guided_weeks')::int AND t.viewed_at IS NULL
           ) AS ordered
    FROM games g
    JOIN newest n ON n.game_id = g.id AND NOT n.finished
    JOIN seat_turns t ON t.game_id = g.id AND t.week = n.week
    JOIN seats s ON s.id = t.seat_id
    JOIN LATERAL (
        SELECT o.occupant_kind, o.user_id
        FROM seat_occupancy o
        WHERE o.seat_id = t.seat_id AND o.from_week <= t.week
        ORDER BY o.from_week DESC, o.id DESC
        LIMIT 1
    ) f ON f.occupant_kind = 'student'
    WHERE g.lifecycle IN ('running', 'playing_out')
),
waits AS (
    SELECT game_id,
           bool_or(ordered) AND NOT bool_and(ordered) AS waiting,
           coalesce(
               jsonb_agg(
                   jsonb_build_object('role', role, 'user_id', user_id, 'since', wait_started_at)
                   ORDER BY position
               ) FILTER (WHERE NOT ordered AND wait_started_at IS NOT NULL),
               '[]'::jsonb
           ) AS waiting_for,
           min(wait_started_at) FILTER (WHERE NOT ordered) AS wait_started_at
    FROM student_turns
    GROUP BY game_id
)
INSERT INTO game_summaries (
    game_id, class_session_id, game_number, purpose, status, week, wait_started_at,
    waiting_for, occupants, chain_cost, version
)
SELECT g.id, g.class_session_id, g.game_number, g.purpose,
       CASE
           WHEN g.lifecycle = 'not_started' THEN 'not_started'
           WHEN g.lifecycle = 'finished' THEN 'finished'
           WHEN coalesce(w.waiting, false) THEN 'waiting'
           ELSE 'running'
       END,
       CASE WHEN g.lifecycle = 'not_started' THEN NULL ELSE n.week END,
       CASE WHEN coalesce(w.waiting, false) THEN w.wait_started_at END,
       CASE WHEN coalesce(w.waiting, false) THEN w.waiting_for ELSE '[]'::jsonb END,
       coalesce(o.occupants, '[]'::jsonb),
       CASE WHEN g.lifecycle = 'not_started' THEN NULL ELSE n.chain_cost END,
       g.version
FROM games g
LEFT JOIN occupants o ON o.game_id = g.id
LEFT JOIN newest n ON n.game_id = g.id
LEFT JOIN waits w ON w.game_id = g.id
{where}
"""
"""The rows of every Game (`{where}` empty), or of the Games a test names."""


def upgrade() -> None:
    op.create_table(
        "game_summaries",
        sa.Column(
            "game_id",
            sa.Uuid(),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("class_session_id", sa.Uuid(), nullable=True),
        sa.Column("game_number", sa.Integer(), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("week", sa.Integer(), nullable=True),
        sa.Column("wait_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("waiting_for", postgresql.JSONB(), nullable=False),
        sa.Column("occupants", postgresql.JSONB(), nullable=False),
        sa.Column("chain_cost", sa.Numeric(14, 4), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "status IN ('not_started', 'running', 'waiting', 'finished')",
            name="ck_game_summaries_status",
        ),
    )
    op.create_index("ix_game_summaries_class_session_id", "game_summaries", ["class_session_id"])
    op.execute(BACKFILL.format(where=""))


def downgrade() -> None:
    op.drop_index("ix_game_summaries_class_session_id", table_name="game_summaries")
    op.drop_table("game_summaries")
