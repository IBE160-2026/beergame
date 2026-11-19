"""Classes and their staff (Story 4.1, FR-6), owned by `classes`.

A Class has a name, an Institution and an optional course code. `class_staff` holds who works in a
Class and as what; the Lecturer who creates a Class is its `owner`. `archived_at` is set by the
archive (Story 4.10); an archived Class no longer keeps its owner's Lecturer role from a revoke.
Times come from the api's clock.

Revision ID: 0023
Revises: 0022
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "classes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("course_code", sa.Text(), nullable=True),
        sa.Column(
            "institution_id",
            sa.Uuid(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("name <> ''", name="ck_classes_name_not_empty"),
        sa.CheckConstraint(
            "course_code IS NULL OR course_code <> ''", name="ck_classes_course_code_not_empty"
        ),
    )
    op.create_table(
        "class_staff",
        sa.Column(
            "class_id",
            sa.Uuid(),
            sa.ForeignKey("classes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            index=True,
        ),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('owner')", name="ck_class_staff_role"),
    )


def downgrade() -> None:
    op.drop_table("class_staff")
    op.drop_table("classes")
