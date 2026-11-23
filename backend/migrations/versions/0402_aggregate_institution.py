"""The Institution of each stored aggregate (Story 14.7, FR-65, AD-14, AD-17).

`class_aggregates.institution_id`: the Institution whose Class the aggregate's Class session
belonged to when `reports.write_aggregate` wrote it, so the Admin's cross-Institution view groups
the aggregates without reading the live Class tables. Backfilled from `class_sessions` and
`classes` for the aggregates already written. An Institution id is no personal data.

Revision ID: 0402
Revises: 0401
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0402"
down_revision: str | None = "0401"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("class_aggregates", sa.Column("institution_id", sa.Uuid(), nullable=True))
    op.execute(
        "UPDATE class_aggregates AS a SET institution_id = c.institution_id "
        "FROM class_sessions AS s JOIN classes AS c ON c.id = s.class_id "
        "WHERE s.id = a.class_session_id"
    )
    op.alter_column("class_aggregates", "institution_id", nullable=False)
    op.create_foreign_key(
        "fk_class_aggregates_institution",
        "class_aggregates",
        "institutions",
        ["institution_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_class_aggregates_institution_id", "class_aggregates", ["institution_id"])


def downgrade() -> None:
    op.drop_index("ix_class_aggregates_institution_id", table_name="class_aggregates")
    op.drop_constraint("fk_class_aggregates_institution", "class_aggregates", type_="foreignkey")
    op.drop_column("class_aggregates", "institution_id")
