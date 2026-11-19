"""What the mail provider reports about a sent mail (Story 4.6, AD-14, NFR-10): `mail_deliveries`
gains the delivery state, the bounce class and the id of the last stored webhook event, and an
index on the provider's message id, by which the webhook finds its row.

Expand-only.

Revision ID: 0028
Revises: 0027
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("mail_deliveries", sa.Column("delivery_state", sa.Text(), nullable=True))
    op.add_column("mail_deliveries", sa.Column("bounce_class", sa.Text(), nullable=True))
    op.add_column("mail_deliveries", sa.Column("last_event_id", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_mail_deliveries_delivery_state",
        "mail_deliveries",
        "delivery_state IN ('delayed', 'delivered', 'bounced')",
    )
    op.create_check_constraint(
        "ck_mail_deliveries_bounce_class",
        "mail_deliveries",
        "bounce_class IN ('hard', 'soft')",
    )
    op.create_check_constraint(
        "ck_mail_deliveries_bounce_fields",
        "mail_deliveries",
        "(delivery_state IS NOT DISTINCT FROM 'bounced') = (bounce_class IS NOT NULL)",
    )
    op.create_index(
        "ix_mail_deliveries_provider_message_id", "mail_deliveries", ["provider_message_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_mail_deliveries_provider_message_id", table_name="mail_deliveries")
    op.drop_constraint("ck_mail_deliveries_bounce_fields", "mail_deliveries", type_="check")
    op.drop_constraint("ck_mail_deliveries_bounce_class", "mail_deliveries", type_="check")
    op.drop_constraint("ck_mail_deliveries_delivery_state", "mail_deliveries", type_="check")
    op.drop_column("mail_deliveries", "last_event_id")
    op.drop_column("mail_deliveries", "bounce_class")
    op.drop_column("mail_deliveries", "delivery_state")
