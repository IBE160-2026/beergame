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
        "games.advance": frozenset({"game"}),
        "games.switch_to_rule_based": frozenset({"game"}),
        # A notice to a User (Story 3.5, AD-9); a notice addressed by reference emits nothing.
        "notify.enqueue": frozenset({"user"}),
        # A role the Admin grants or revokes (Story 3.9): the User's open pages reload it.
        "identity.grant_role": frozenset({"user"}),
        "identity.revoke_role": frozenset({"user"}),
    }
)
"""`<module>.<command>` -> topics. Commands on a Game the Lecturer overview lists will add
`session` (AD-13); simulation Games never do. `games.finish` runs inside the transaction of the
command that completes the last Week and shares its one event, as an Order that
`players.ensure_order` places shares the event of the command that opened its Week."""
