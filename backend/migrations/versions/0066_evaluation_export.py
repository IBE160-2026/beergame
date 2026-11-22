"""The Institution agreement and the pseudonym key fingerprint of the evaluation export (Story
15.4, FR-71, AD-12, AD-14).

`evaluation_agreements` holds one agreement per Class session: who at the Institution agreed,
on which date, and who is controller for the evaluation. Only with a row here may the Admin
export the Class session (`platform/authz`, `export_pseudonymised`).

`pseudonym_key_fingerprints` holds at most one row: the fingerprint of the key the key holder
types at the first export. The key itself is never stored anywhere.

Revision ID: 0066
Revises: 0065
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0066"
down_revision: str | None = "0065"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evaluation_agreements",
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("agreed_by", sa.Text(), nullable=False),
        sa.Column("agreed_on", sa.Date(), nullable=False),
        sa.Column("controller", sa.Text(), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "btrim(agreed_by) <> '' AND btrim(controller) <> ''",
            name="ck_evaluation_agreements_text",
        ),
    )
    op.create_table(
        "pseudonym_key_fingerprints",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("set_by", sa.Uuid(), nullable=True),
        sa.Column("set_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_pseudonym_key_fingerprints_one_row"),
        sa.CheckConstraint(
            "fingerprint ~ '^[0-9a-f]{64}$'", name="ck_pseudonym_key_fingerprints_hex"
        ),
    )


def downgrade() -> None:
    op.drop_table("pseudonym_key_fingerprints")
    op.drop_table("evaluation_agreements")
