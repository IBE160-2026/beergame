"""The Institutions that Classes belong to (Story 3.11, FR-3), owned by `identity`.

A name is unique case-insensitively (`uq_institutions_name` on `lower(name)`). Times come from the
api's clock. There is no delete in v1.

Revision ID: 0021
Revises: 0020
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "institutions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("name <> ''", name="ck_institutions_name_not_empty"),
    )
    op.create_index("uq_institutions_name", "institutions", [sa.text("lower(name)")], unique=True)


def downgrade() -> None:
    op.drop_index("uq_institutions_name", table_name="institutions")
    op.drop_table("institutions")
