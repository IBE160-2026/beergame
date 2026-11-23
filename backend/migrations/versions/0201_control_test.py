"""The Control test (Story 12.7, FR-82, AD-27).

- `institutions.operator_owned` (owned by `modules/identity`): the operator's own Institution,
  where Control tests are set up. A partial unique index keeps it on one Institution at most.
- `class_sessions.kind` (owned by `modules/sessions`): `course` (every existing row) or
  `control_test`. A trigger refuses changing the kind, and changing the model config of a
  `control_test` row: a Control test is pinned to the model config under test when it is created.

Revision ID: 0201
Revises: 0130
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0201"
down_revision: str | None = "0130"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "institutions",
        sa.Column("operator_owned", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "uq_institutions_operator_owned",
        "institutions",
        ["operator_owned"],
        unique=True,
        postgresql_where=sa.text("operator_owned"),
    )
    op.add_column(
        "class_sessions",
        sa.Column("kind", sa.Text(), nullable=False, server_default="course"),
    )
    op.create_check_constraint(
        "ck_class_sessions_kind", "class_sessions", "kind IN ('course', 'control_test')"
    )
    op.execute(
        """
        CREATE FUNCTION class_sessions_kind_fixed() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.kind IS DISTINCT FROM OLD.kind THEN
                RAISE EXCEPTION 'the kind of a Class session does not change'
                    USING ERRCODE = 'restrict_violation';
            END IF;
            IF OLD.kind = 'control_test'
                AND NEW.model_config_id IS DISTINCT FROM OLD.model_config_id THEN
                RAISE EXCEPTION 'the model config of a Control test does not change'
                    USING ERRCODE = 'restrict_violation';
            END IF;
            RETURN NEW;
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_class_sessions_kind_fixed BEFORE UPDATE ON class_sessions "
        "FOR EACH ROW EXECUTE FUNCTION class_sessions_kind_fixed()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_class_sessions_kind_fixed ON class_sessions")
    op.execute("DROP FUNCTION class_sessions_kind_fixed()")
    op.drop_constraint("ck_class_sessions_kind", "class_sessions", type_="check")
    op.drop_column("class_sessions", "kind")
    op.drop_index("uq_institutions_operator_owned", table_name="institutions")
    op.drop_column("institutions", "operator_owned")
