"""Game settings: one versioned model whose defaults are the Classic game (FR-11).

Only basic type and sign constraints live here. Ranges and warnings are Story 1.3.
"""

from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Role(StrEnum):
    RETAILER = "retailer"
    WHOLESALER = "wholesaler"
    DISTRIBUTOR = "distributor"
    FACTORY = "factory"


ROLES: tuple[Role, ...] = (Role.RETAILER, Role.WHOLESALER, Role.DISTRIBUTOR, Role.FACTORY)
"""The Classic chain, downstream first: the first Role serves the customer, the last produces."""

Units = Annotated[int, Field(strict=True, ge=0)]
Delay = Annotated[int, Field(strict=True, ge=1)]
Week = Annotated[int, Field(strict=True, ge=1)]
Rate = Annotated[Decimal, Field(ge=0)]

FROZEN = ConfigDict(frozen=True, extra="forbid")


class DemandStep(BaseModel):
    """Customer demand `start` until `change_week`, then `new_level` from that Week on."""

    model_config = FROZEN

    kind: Literal["step"]
    start: Units
    new_level: Units
    change_week: Week

    def demand_for(self, week: int) -> int:
        return self.new_level if week >= self.change_week else self.start


class GameSettings(BaseModel):
    """Everything that defines a Game's arithmetic. `GameSettings()` is the Classic game."""

    model_config = FROZEN

    schema_version: Literal[1] = 1
    roles: tuple[Role, ...] = ROLES
    starting_inventory: Units = 12
    supply_line: Units = 4
    """Units (or Orders) in every pipeline slot when the Game opens."""
    order_delay: Delay = 2
    shipping_delay: Delay = 2
    production_delay: Delay = 2
    demand: DemandStep = DemandStep(kind="step", start=4, new_level=8, change_week=5)
    holding_cost: Rate = Decimal("0.50")
    backorder_cost: Rate = Decimal("1.00")
    weeks: Week = 36
    guided_weeks: Units = 4
    max_order: Units = 999
    """A stated placeholder: large enough that it does not bind in normal play."""

    @field_validator("roles")
    @classmethod
    def _roles_form_a_chain(cls, roles: tuple[Role, ...]) -> tuple[Role, ...]:
        if not roles:
            raise ValueError("a chain needs at least one Role")
        if len(set(roles)) != len(roles):
            raise ValueError("each Role appears once in the chain")
        return roles
