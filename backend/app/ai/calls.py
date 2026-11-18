"""Reading `llm_call` rows (FR-67): what one call's attempts cost and took, for reports such as
`python -m app.sim endpoint`. Only `app/ai` reads the table (AD-6)."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select

from app.ai.db import transaction
from app.ai.models import llm_calls


@dataclass(frozen=True)
class Attempt:
    id: uuid.UUID
    attempt: int
    outcome: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    served_model: str | None
    served_by: str | None
    error: str | None


async def get(ids: Sequence[uuid.UUID]) -> list[Attempt]:
    """The rows with these ids, in attempt order."""
    if not ids:
        return []
    columns = [getattr(llm_calls.c, name) for name in Attempt.__dataclass_fields__]
    async with transaction(None) as session:
        rows = (
            await session.execute(
                select(*columns)
                .where(llm_calls.c.id.in_(list(ids)))
                .order_by(llm_calls.c.started_at, llm_calls.c.attempt)
            )
        ).all()
    return [Attempt(*row) for row in rows]
