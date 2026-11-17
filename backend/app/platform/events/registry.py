"""The topics each command emits (AD-8). A command is added here when it is added to its module;
a test runs every command and checks it emits exactly these topics."""

from collections.abc import Mapping
from types import MappingProxyType

COMMAND_TOPICS: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "games.create": frozenset({"game"}),
        "games.assign_seat": frozenset({"game"}),
        "games.start": frozenset({"game"}),
        "games.place_order": frozenset({"game"}),
        "games.finish": frozenset({"game"}),
    }
)
"""`<module>.<command>` -> topics. Commands on a Game the Lecturer overview lists will add
`session` (AD-13); simulation Games never do. `games.finish` runs inside the transaction of the
command that completes the last Week and shares its one event."""
