"""AI routing (Story 2.7): a model config's router preferences, and the model and upstream
provider a response reports on each `llm_call` row (AD-6, FR-68, C-1).

The provider check constraint goes: the provider names live in `app/ai/adapters.ADAPTERS`, so
adding a provider is one adapter and one config row, with no migration.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ai_model_configs", sa.Column("routing", JSONB(), nullable=True))
    op.add_column("llm_call", sa.Column("served_model", sa.Text(), nullable=True))
    op.add_column("llm_call", sa.Column("served_by", sa.Text(), nullable=True))
    op.drop_constraint("ck_ai_model_configs_provider", "ai_model_configs", type_="check")


def downgrade() -> None:
    op.create_check_constraint(
        "ck_ai_model_configs_provider",
        "ai_model_configs",
        "provider IN ('mock', 'openai_compatible')",
    )
    op.drop_column("llm_call", "served_by")
    op.drop_column("llm_call", "served_model")
    op.drop_column("ai_model_configs", "routing")
