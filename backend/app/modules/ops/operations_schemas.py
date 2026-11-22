"""The envelopes of «Drift» (Story 15.8, NFR-8, AD-19): counts, shares, timings and amounts per
Class session, no Student data. Shares are decimal strings from 0 to 1 with four places, or null
when there is nothing to share; USD amounts are decimal strings with eight places."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class OperationsSessionOut(BaseModel):
    """A Class session as «Drift» lists it, with its errors of the last 24 hours."""

    id: uuid.UUID
    label: str
    """«class-of-1994 · Klasseøkt 2»."""
    institution_name: str | None
    errors_24h: int


class OperationsSessionListOut(BaseModel):
    read_at: datetime
    items: list[OperationsSessionOut]


class ErrorCountsOut(BaseModel):
    """Counted errors per source."""

    conservation_check: int
    job_failed: int
    api_error: int


class ErrorHourOut(ErrorCountsOut):
    hour: datetime
    """The hour's start (UTC); the hour runs to the next."""


class FallbackOut(BaseModel):
    kind: str
    """The fallback's mark: `fallback_timeout`, `fallback_invalid_output`,
    `fallback_budget_exhausted` or `fallback_provider_error`."""
    orders: int
    share: str | None
    """`orders` over `llm_orders`."""


class ResponseTimeOut(BaseModel):
    effort_level: str
    calls: int
    median_ms: int
    p95_ms: int


class OperationsOut(BaseModel):
    """One Class session's operations figures (Story 15.8, NFR-8, FR-79)."""

    class_session_id: uuid.UUID
    label: str
    institution_name: str | None
    read_at: datetime
    hours: list[ErrorHourOut]
    """The last 24 hours, oldest first, ending with the current hour."""
    totals: ErrorCountsOut
    """Every counted error of the Class session."""
    llm_orders: int
    fallbacks: list[FallbackOut]
    response_times: list[ResponseTimeOut]
    """Per Effort level of the LLM players' attempts."""
    llm_seats: int
    switched_seats: int
    switched_share: str | None
    cost_usd: str
    ai_calls: int
