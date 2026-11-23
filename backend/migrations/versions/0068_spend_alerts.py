"""The daily AI spend alert (Story 15.7, FR-69, AD-6, AD-9).

`ai_spend_alerts` holds one row per Europe/Oslo day on which the AI spend passed
`AI_DAILY_ALERT_USD`: the alert amount and the spend when the sweep found it, and when. The Admins'
notices name the row by its id, so the mail knows its day. Amounts and times only. An index on
`llm_call.started_at` serves the sum of one day, which the sweep reads every minute.

Revision ID: 0068
Revises: 0067
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0068"
down_revision: str | None = "0067"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_spend_alerts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("alert_usd", sa.Numeric(18, 8), nullable=False),
        sa.Column("spent_usd", sa.Numeric(18, 8), nullable=False),
        sa.Column("alerted_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "alert_usd >= 0 AND spent_usd > alert_usd", name="ck_ai_spend_alerts_money"
        ),
        sa.UniqueConstraint("day", name="uq_ai_spend_alerts_day"),
    )
    op.create_index("ix_llm_call_started_at", "llm_call", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_llm_call_started_at", table_name="llm_call")
    op.drop_table("ai_spend_alerts")
