"""The LLM player's request: prompt values from the `SeatState` alone (FR-31, AD-3, C-1).

`build_inputs` turns what a Student in the Seat sees into the values the `player_order` prompt
is rendered from, and reads nothing else: no query, no table status, no settings, no demand
series and no Week count. Time is told relative to the open Week ("2 weeks ago", "in 3 weeks"):
no Week number is printed, though the Seat's own history (all earlier Weeks, as a Student sees
it) shows how many Weeks have passed; nothing says how many are left. The Seat is named by its
Role only. Customer wording goes to the Retailer and production wording to the Factory (or any
Seat with goods in production): the Classic chain, the only one Epic 2 plays.

`request_inputs` adds the caller reference (Game, Seat, Week: ids, stored on every call
row, never rendered) and the mock answer (the stored Rule-based reference Order, read by the
mock provider only). `order_schema` is the JSON schema the answer must match: one whole-number
Order in the Seat's Order range. Story 2.5's job calls `ai.run` with these.

This module loads pydantic-ai through `app.ai.gateway`; `players.service` does not import it.
"""

import uuid
from functools import cache

from pydantic import BaseModel, ConfigDict, Field, create_model

from app.ai import gateway
from app.modules.games import service as games_service

__all__ = [
    "PURPOSE",
    "PROBE_PURPOSE",
    "ProbeAnswer",
    "build_inputs",
    "order_schema",
    "request_inputs",
    "without_answer_format",
]

PURPOSE = "player_order"
PROBE_PURPOSE = "recognition_probe"

ANSWER_FORMAT = "\n\nAnswer with JSON only"
"""Starts the last paragraph of the `player_order` prompt, which asks for the Order as JSON."""


def without_answer_format(prompt: str) -> str:
    """The player prompt without its answer-format paragraph, so the recognition probe asks for
    one JSON answer only (its own)."""
    head, found, _ = prompt.rpartition(ANSWER_FORMAT)
    return head if found else prompt


CUSTOMER_FACING = "retailer"
"""The Role whose incoming order is customer demand (FR-31: only it sees customer demand)."""
PRODUCING = "factory"


class ProbeAnswer(BaseModel):
    """The answer to the recognition probe (`python -m app.sim probe`, issue #19)."""

    model_config = ConfigDict(extra="forbid")

    recognised: bool
    name: str
    explanation: str


def _weeks(count: int) -> str:
    return f"{count} week" if count == 1 else f"{count} weeks"


def _producing(state: games_service.SeatState) -> bool:
    """The last Role of the chain produces its units; its goods are `in_production`."""
    return state.role == PRODUCING or any(
        slot.stage == "in_production" for slot in state.supply_line_slots
    )


def _supply_line(state: games_service.SeatState, producing: bool) -> str:
    lines = []
    for slot in state.supply_line_slots:
        when = f"in {_weeks(slot.arrival_week - state.week)}"
        if slot.stage == "in_transit":
            lines.append(f"  - {slot.quantity} units in transit to you, arriving {when}")
        elif slot.stage == "in_production":
            lines.append(f"  - {slot.quantity} units in production, ready {when}")
        elif producing:
            lines.append(f"  - {slot.quantity} units ordered for production, ready {when}")
        else:
            lines.append(
                f"  - {slot.quantity} units ordered and not yet received by your supplier, "
                f"arriving {when} if your supplier ships them in full"
            )
    return "\n".join(lines) if lines else "  - nothing"


def _history(state: games_service.SeatState, incoming: str) -> str:
    if not state.history:
        return "(no earlier weeks)"
    header = (
        f"weeks ago | {incoming} | received | shipped | inventory | backlog | your order | cost"
    )
    rows = [
        " | ".join(
            str(value)
            for value in (
                state.week - row.week,
                row.incoming_order,
                row.incoming_delivery,
                row.shipped,
                row.inventory,
                row.backlog,
                row.order,
                row.cost,
            )
        )
        for row in state.history
    ]
    return "\n".join([header, *rows])


def build_inputs(seat_state: games_service.SeatState) -> dict[str, gateway.Scalar]:
    """The values the `player_order` prompt is rendered from, built from `seat_state` alone."""
    state = seat_state
    role = str(state.role)
    producing = _producing(state)
    rates = {line.kind: line.rate for line in state.cost_lines}
    lead_time = state.preview.order_arrival_week - state.week
    if role == CUSTOMER_FACING:
        customers = "end customers, who buy from your store"
        incoming_label = "Customer demand this week"
        incoming_column = "customer demand"
    else:
        customers = "businesses that order from you"
        incoming_label = "Orders received from your customers this week"
        incoming_column = "orders received"
    if producing:
        source = "You produce the units yourself."
        supplier = "production"
        delay_rule = (
            f"Units you order for production now reach your inventory in {_weeks(lead_time)}."
        )
    else:
        source = "You buy the units from your supplier."
        supplier = "your supplier"
        delay_rule = (
            f"An order you place now reaches your inventory in {_weeks(lead_time)} at the "
            "earliest: your supplier first has to receive it and then ship it, and it can "
            "only ship what it has in stock."
        )
    if producing:
        overdue_line = f"Units ordered for production and held up: {state.overdue}"
    else:
        overdue_line = (
            "Units your supplier has received an order for but not yet shipped to you: "
            f"{state.overdue}"
        )
    return {
        "role": role,
        "customers": customers,
        "source": source,
        "supplier": supplier,
        "delay_rule": delay_rule,
        "holding_rate": str(rates["holding"]),
        "backorder_rate": str(rates["backorder"]),
        "incoming_label": incoming_label,
        "incoming_order": state.incoming_order,
        "incoming_delivery": state.incoming_delivery,
        "shipped": state.shipped,
        "inventory": state.inventory,
        "backlog": state.backlog,
        "supply_line": _supply_line(state, producing),
        "overdue_line": overdue_line,
        "position": state.position,
        "week_cost": str(state.week_cost),
        "total_cost": str(state.total_cost),
        "history": _history(state, incoming_column),
        "min_order": state.min_order,
        "max_order": state.max_order,
    }


@cache
def order_schema(min_order: int, max_order: int) -> type[BaseModel]:
    """The answer schema: one whole-number Order from `min_order` to `max_order`. A missing,
    fractional, string, negative or too large Order does not match (FR-32)."""
    return create_model(
        "OrderDecision",
        __config__=ConfigDict(extra="forbid"),
        order=(
            int,
            Field(
                strict=True,
                ge=min_order,
                le=max_order,
                description="Units to order this week, a whole number.",
            ),
        ),
    )


def request_inputs(
    game_id: str | uuid.UUID,
    seat_id: str | uuid.UUID,
    week: int,
    seat_state: games_service.SeatState,
    reference_order: int,
) -> gateway.Inputs:
    """The gateway inputs for one Order: the prompt values, the caller reference (ids only) and
    the Rule-based reference Order as the mock answer."""
    return gateway.Inputs(
        values=build_inputs(seat_state),
        caller={"game": str(game_id), "seat": str(seat_id), "week": week},
        mock_answer={"order": reference_order},
    )
