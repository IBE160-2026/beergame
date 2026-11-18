"""Staged Roster uploads (Story 4.2, FR-7, AD-14), owned by `identity`.

A Lecturer's uploaded student list is parsed in memory; only its cell values are kept here, one
upload per Class, until `expires_at` (`ROSTER_STAGING_TTL_HOURS`). The file is never stored.

Revision ID: 0024
Revises: 0023
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "roster_uploads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "class_id",
            sa.Uuid(),
            sa.ForeignKey("classes.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "uploaded_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("headers", JSONB(), nullable=False),
        sa.Column("has_header", sa.Boolean(), nullable=False),
        sa.Column("column_count", sa.Integer(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("chosen_column", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.CheckConstraint(
            "chosen_column IS NULL OR (chosen_column >= 0 AND chosen_column < column_count)",
            name="ck_roster_uploads_chosen_column",
        ),
    )
    op.create_table(
        "roster_upload_rows",
        sa.Column(
            "upload_id",
            sa.Uuid(),
            sa.ForeignKey("roster_uploads.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("row_number", sa.Integer(), primary_key=True),
        sa.Column("cells", JSONB(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("roster_upload_rows")
    op.drop_table("roster_uploads")
