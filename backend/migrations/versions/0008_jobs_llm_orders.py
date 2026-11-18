"""Job platform and LLM Orders (Story 2.5): the procrastinate schema, `llm_call` ids on the
Decision log and the fallback types (AD-9, AD-15, AD-24, FR-32, FR-67).

The procrastinate schema is the SQL procrastinate 3.11.0 ships (its `schema.sql`, kept here
as `migrations/sql/procrastinate-3.11.0-schema.sql`, so this revision never changes with the
installed version); a later procrastinate upgrade adds its migration SQL in a revision of its
own.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-18
"""

from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PROCRASTINATE_SCHEMA = Path(__file__).parents[1] / "sql" / "procrastinate-3.11.0-schema.sql"

FALLBACKS = ("none", "timeout", "invalid_output", "budget_exhausted", "provider_error")


def _fallback_check(values: Sequence[str]) -> str:
    return f"fallback IN ({', '.join(repr(value) for value in values)})"


def _run_sql(statements: str) -> None:
    """Run SQL as it is: the driver reads `%` as a placeholder, so it is doubled, as
    procrastinate's own `apply_schema` does."""
    op.get_bind().exec_driver_sql(statements.replace("%", "%%"))


def upgrade() -> None:
    _run_sql(PROCRASTINATE_SCHEMA.read_text(encoding="utf-8"))
    op.add_column(
        "seat_weeks",
        sa.Column(
            "llm_call_ids",
            postgresql.ARRAY(sa.Uuid()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.drop_constraint("ck_seat_weeks_fallback", "seat_weeks", type_="check")
    op.create_check_constraint("ck_seat_weeks_fallback", "seat_weeks", _fallback_check(FALLBACKS))


def downgrade() -> None:
    # Rows marked with a fallback type break the narrower check: such a database cannot go
    # below 0008 (the Decision log is append-only).
    op.drop_constraint("ck_seat_weeks_fallback", "seat_weeks", type_="check")
    op.create_check_constraint("ck_seat_weeks_fallback", "seat_weeks", _fallback_check(["none"]))
    op.drop_column("seat_weeks", "llm_call_ids")
    _run_sql(
        """
        DO $$
        DECLARE item record;
        BEGIN
          FOR item IN SELECT tablename FROM pg_tables
                      WHERE schemaname = current_schema() AND tablename LIKE 'procrastinate%'
          LOOP
            EXECUTE format('DROP TABLE IF EXISTS %I CASCADE', item.tablename);
          END LOOP;
          FOR item IN SELECT p.oid::regprocedure AS signature FROM pg_proc p
                      JOIN pg_namespace n ON n.oid = p.pronamespace
                      WHERE n.nspname = current_schema() AND p.proname LIKE 'procrastinate%'
          LOOP
            EXECUTE format('DROP FUNCTION IF EXISTS %s CASCADE', item.signature);
          END LOOP;
          FOR item IN SELECT t.typname FROM pg_type t
                      JOIN pg_namespace n ON n.oid = t.typnamespace
                      WHERE n.nspname = current_schema() AND t.typname LIKE 'procrastinate%'
                        AND t.typtype IN ('e', 'c')
          LOOP
            EXECUTE format('DROP TYPE IF EXISTS %I CASCADE', item.typname);
          END LOOP;
        END $$;
        """
    )
