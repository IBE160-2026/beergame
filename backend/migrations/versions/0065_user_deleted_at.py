"""When a User was erased on the Institution's instruction (Story 15.2, FR-76, AD-14).

`users.deleted_at` is set by `identity.erasure.erase_user` when it anonymises the row in place:
the id stays, so every Seat, occupancy row and Decision log row keeps pointing to it, but the
name, e-mail and password are gone. A User with `deleted_at` set is left out of the User list.

A Debrief summary is stored once (0107), but it copies the Student's reflection answers: the
trigger now lets one update through, the erasure's, which empties `reflection` and changes
nothing else, so the finished Debrief still counts.

Revision ID: 0065
Revises: 0209
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0065"
down_revision: str | None = "0209"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SUMMARY_ERASABLE = """
CREATE OR REPLACE FUNCTION debrief_summaries_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.reflection = '[]'::jsonb
        AND (NEW.user_id, NEW.class_session_id, NEW.game_id, NEW.fact_set_id, NEW.moment_ids,
             NEW.finished_at)
        IS NOT DISTINCT FROM
            (OLD.user_id, OLD.class_session_id, OLD.game_id, OLD.fact_set_id, OLD.moment_ids,
             OLD.finished_at)
    THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'a Debrief summary is stored once'
        USING ERRCODE = 'restrict_violation';
END $$
"""

SUMMARY_IMMUTABLE = """
CREATE OR REPLACE FUNCTION debrief_summaries_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'a Debrief summary is stored once'
        USING ERRCODE = 'restrict_violation';
END $$
"""


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(SUMMARY_ERASABLE)


def downgrade() -> None:
    op.execute(SUMMARY_IMMUTABLE)
    op.drop_column("users", "deleted_at")
