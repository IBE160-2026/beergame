"""`games.policy(purpose)`: the one table of behaviour per Game purpose (AD-13).

Commands, sweeps and views ask this table and never compare a purpose themselves. A purpose
gets its row in the story that first creates such Games; until then asking for it fails.
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.modules.games.schemas import Purpose


class PurposeNotSupportedError(LookupError):
    """No behaviour is defined for this purpose yet."""


class GamePolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    inactivity_takeover: bool
    pause: bool
    play_deadline_playout: bool
    lecturer_overview: bool
    """Listed in the Lecturer overview, so its commands also emit `session:<id>` (AD-8)."""
    guided_weeks: Literal["settings"]
    """`settings`: Guided Weeks are the Game settings' `guided_weeks`."""
    scripted_occupants: bool
    """Whether a Seat may be held by a scripted policy (AD-22)."""


POLICIES: Mapping[Purpose, GamePolicy] = MappingProxyType(
    {
        Purpose.SIMULATION: GamePolicy(
            inactivity_takeover=False,
            pause=False,
            play_deadline_playout=False,
            lecturer_overview=False,
            guided_weeks="settings",
            scripted_occupants=True,
        ),
    }
)


def policy(purpose: Purpose | str) -> GamePolicy:
    """What applies to Games of `purpose`; raises PurposeNotSupportedError for any other."""
    try:
        return POLICIES[Purpose(purpose)]
    except KeyError, ValueError:
        raise PurposeNotSupportedError(f"no Game policy for purpose {purpose!r}") from None
