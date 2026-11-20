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
        # A User the Admin deactivates or reactivates (Story 3.10): their open pages reload.
        "identity.deactivate_user": frozenset({"user"}),
        "identity.reactivate_user": frozenset({"user"}),
        # A Class session created or saved (Story 5.1): its Class's staff read it again. A save
        # that changes a date also tells each registered Student of the Class (Story 5.2), and
        # one that marks it obligatory enqueues a notice per Student, which emits `user` (5.7).
        "sessions.create": frozenset({"session"}),
        "sessions.save": frozenset({"session", "user"}),
        # A Lab hour added, changed or removed (Story 5.6): the staff read the session again, and
        # each registered Student's notice emits `user:<id>`.
        "sessions.add_lab_hour": frozenset({"session", "user"}),
        "sessions.change_lab_hour": frozenset({"session", "user"}),
        "sessions.remove_lab_hour": frozenset({"session", "user"}),
        # An allocation draft drawn or drawn again (Story 5.8): the staff read the session again;
        # no Student is told before the confirmation.
        "sessions.draw_allocation": frozenset({"session"}),
        # The allocation confirmed (Story 5.9): its Class games are created and seated through
        # `games.commands` in the same transaction (`game:<id>`), the staff read the session
        # again, and each Student's allocation notice emits `user:<id>`. A confirm that only
        # takes removed Students out of the draft emits `session` alone.
        "sessions.confirm_allocation": frozenset({"game", "session", "user"}),
    }
)
"""`<module>.<command>` -> topics. Commands on a Game the Lecturer overview lists will add
`session` (AD-13); simulation Games never do. `games.finish` runs inside the transaction of the
command that completes the last Week and shares its one event, as an Order that
`players.ensure_order` places shares the event of the command that opened its Week."""
