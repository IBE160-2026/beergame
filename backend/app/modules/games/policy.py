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
    snapshot: Literal["at_creation", "at_lock"]
    """When the Game takes its settings snapshot (AD-4): `at_creation`, from the settings
    `games.commands.create` is given; `at_lock`, from its Class session's lock (Story 5.12), so
    `create` takes no settings and `start` answers `game_not_ready` until the snapshot exists."""
    student_occupants: bool
    """Whether a Seat may be held by a Student (`student` occupant with a `user_id`, AD-5)."""
    class_session_game: bool
    """Whether the Game belongs to a Class session: created with its id and a game number."""


POLICIES: Mapping[Purpose, GamePolicy] = MappingProxyType(
    {
        Purpose.SIMULATION: GamePolicy(
            inactivity_takeover=False,
            pause=False,
            play_deadline_playout=False,
            lecturer_overview=False,
            guided_weeks="settings",
            scripted_occupants=True,
            snapshot="at_creation",
            student_occupants=False,
            class_session_game=False,
        ),
        # A Class game (Story 5.9): created when the allocation is confirmed, its snapshot taken
        # at the Class session's lock.
        Purpose.CLASS: GamePolicy(
            inactivity_takeover=True,
            pause=True,
            play_deadline_playout=True,
            lecturer_overview=True,
            guided_weeks="settings",
            scripted_occupants=False,
            snapshot="at_lock",
            student_occupants=True,
            class_session_game=True,
        ),
    }
)


def policy(purpose: Purpose | str) -> GamePolicy:
    """What applies to Games of `purpose`; raises PurposeNotSupportedError for any other."""
    try:
        return POLICIES[Purpose(purpose)]
    except KeyError, ValueError:
        raise PurposeNotSupportedError(f"no Game policy for purpose {purpose!r}") from None
