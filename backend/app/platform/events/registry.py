"""The topics each command emits (AD-8). A command is added here when it is added to its module;
a test runs every command and checks it emits exactly these topics."""

from collections.abc import Mapping
from types import MappingProxyType

COMMAND_TOPICS: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "games.create": frozenset({"game"}),
        "games.assign_seat": frozenset({"game"}),
        # A Game started (Story 6.5): a Class game's session hears of it, and each Student who
        # holds a Seat reads Hjem and the game again. A simulation Game takes no Student
        # (`games.policy`), so it emits `game` alone.
        "games.start": frozenset({"game", "session", "user"}),
        "games.place_order": frozenset({"game"}),
        "games.finish": frozenset({"game"}),
        "games.advance": frozenset({"game"}),
        "games.switch_to_rule_based": frozenset({"game"}),
        # A Student moved or two swapped before the start (Story 5.10): only Class games take
        # Students, so their Class session hears of it, and each moved Student's pages reload.
        "games.move_seat": frozenset({"game", "session", "user"}),
        # A Class game gets its Class session's snapshot and AI players at the lock (Story 5.12):
        # the Class session hears of it, and each Student who held a Seat reads it again.
        "games.set_snapshot": frozenset({"game", "session", "user"}),
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
        "sessions.copy_from": frozenset({"session"}),
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
        # A Student moved or two swapped in the allocation (Story 5.10): before the confirmation
        # only the draft changes (`session`); after it `games.move_seat` runs in the same
        # transaction (`game`, `session`, `user`) and each moved Student's notice emits `user`.
        "sessions.move_allocation": frozenset({"game", "session", "user"}),
        # The Start-date lock (Story 5.11): the staff read the session again; a lock refused for
        # a missing provider key tells each owner and Admin once, which emits `user`. With no
        # confirmed allocation the lock allocates and seats the Students (`game`, Story 5.12).
        "sessions.lock": frozenset({"game", "session", "user"}),
        # A late registrant seated, or a removed Student's Seat given to an AI player (Story
        # 5.13): the Seat changes through `games.assign_seat` (`game`), the staff read the
        # session again, and the Students of that game (and the one seated, with the allocation
        # notice) reload their pages.
        "sessions.seat_late_registrant": frozenset({"game", "session", "user"}),
        "sessions.replace_removed_student": frozenset({"game", "session", "user"}),
        # A deadline reminder (Story 5.14): one notice per Student, which emits `user`.
        "sessions.send_deadline_reminder": frozenset({"user"}),
        # Student choice (Story 5.17). A save that opens it creates the empty Class games
        # (`game`), the staff read the session again and each registered Student's notice emits
        # `user`. A Seat taken or changed (`games.assign_seat`/`move_seat`) tells every Student
        # who can still choose and the staff. A late registrant's offer tells them, and, when it
        # adds Class games, every registered Student and the staff.
        "sessions.open_student_choice": frozenset({"game", "session", "user"}),
        "sessions.choose_seat": frozenset({"game", "session", "user"}),
        "sessions.offer_student_choice": frozenset({"game", "session", "user"}),
        # A step a Student has done (Story 6.1, AD-16): their Hjem and Stegene read it again, and
        # so does the Class session's overview. A step already recorded emits nothing.
        "progress.record_step": frozenset({"session", "user"}),
    }
)
"""`<module>.<command>` -> topics. Commands on a Game the Lecturer overview lists will add
`session` (AD-13); simulation Games never do. `games.finish` runs inside the transaction of the
command that completes the last Week and shares its one event, as an Order that
`players.ensure_order` places shares the event of the command that opened its Week."""
