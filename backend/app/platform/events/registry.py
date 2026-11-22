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
        # An Order placed (Story 6.12): a Class game's session hears of it, the Student who
        # ordered reads Hjem again, and when the Order completed the Week every Student of the
        # Game does. An Order with no actor that completes no Week, in a Game no Lecturer overview
        # lists (simulations), emits `game` alone.
        "games.place_order": frozenset({"game", "session", "user"}),
        # The end of a Game (Story 6.18). A Class game also records `class_game` for every
        # Student it ever seated, whose `progress.record_step` emits `user` and `session` in the
        # transaction of the command that completed the last Week.
        "games.finish": frozenset({"game"}),
        # An advance by the rescue loop or a settle (follow-up review of Story 6.13): a Class
        # game's session hears of it, and every Student of the Game waits on a new Week, so each
        # reads Hjem again. A simulation emits `game` alone.
        "games.advance": frozenset({"game", "session", "user"}),
        "games.switch_to_rule_based": frozenset({"game"}),
        # An AI player took a Student's Seat over (Story 8.2): only Class games take over, so
        # their Class session hears of it, and every Student of the Game and the one whose Seat
        # it was read it again, each through a `takeover_notice` too.
        "games.takeover": frozenset({"game", "session", "user"}),
        # A Student asked for their Seat back (Story 8.4): only Class games take over, so their
        # Class session hears of it, and the Student's pages read the queued request. The Week
        # opening that hands the Seat back emits under its own command (place_order, advance).
        "games.request_reclaim": frozenset({"game", "session", "user"}),
        # A Student paused the Class game (Story 8.6): its Class session hears of it, and every
        # Student of the Game reads the pause line. The Order that ends it emits as place_order.
        "games.pause": frozenset({"game", "session", "user"}),
        # The Lecturer's agreed Pause time and «Avslutt pausen» (Story 8.7), and the sweep crossing
        # the agreed time: the Class session hears of each, and every seated Student reads it.
        "games.set_agreed_time": frozenset({"game", "session", "user"}),
        "games.resume": frozenset({"game", "session", "user"}),
        "games.reach_agreed_time": frozenset({"game", "session", "user"}),
        # The sweep crossed a Seat's insert time (Story 8.8): every Student of the Game reads
        # «Sett inn KI-spiller for …» without a reload, and the Class session hears of it.
        "games.announce_insert_time": frozenset({"game", "session", "user"}),
        # A turn reminder queued (Story 8.13): nothing a game view shows changes, so only the
        # reminded Student's `user` topic, which `platform/notify.enqueue` emits.
        "games.queue_turn_reminder": frozenset({"user"}),
        # A Student's Tilrettelegging moved the open Week's due times (Story 8.9): the Varselbånd
        # and every Student of the Game read the new times.
        "games.recompute_turn_times": frozenset({"game", "session", "user"}),
        # «I rommet» marked or ended (Story 8.11): the wall's row label, Spillstyring and every
        # Student's line above Setestatus read it again with the new due times.
        "games.mark_in_room": frozenset({"game", "session", "user"}),
        "games.end_in_room": frozenset({"game", "session", "user"}),
        # The Play deadline playout took a Class game over (Story 8.14): its Class session hears
        # of it, and every Student who ever held a Seat reads Spill and Hjem again. The Weeks it
        # then plays emit as `advance` and `place_order` do.
        "games.playout": frozenset({"game", "session", "user"}),
        # A lost LLM job of a Game playing out deferred again (Story 8.14): only a job row is
        # written, so nothing a view shows changes; the Order's own command emits.
        "games.ensure_playout_order": frozenset(),
        # An unfinished Replay closed at its Student's Test deadline (Story 10.6, AD-9 sweep): the
        # Student's Hjem and play screen read it again. No Lecturer overview lists a purpose this
        # closes, so no `session`.
        "games.close": frozenset({"game", "user"}),
        # A Student opened a Guided Week (Story 6.10): only Class games take Students, so their
        # Class session hears of it; the viewer's waiting status changes, and when the view
        # completes the Week every Student of the Game sees the next one.
        "games.view_week": frozenset({"game", "session", "user"}),
        # A Student moved or two swapped before the start (Story 5.10): only Class games take
        # Students, so their Class session hears of it, and each moved Student's pages reload.
        "games.move_seat": frozenset({"game", "session", "user"}),
        # A Class game gets its Class session's snapshot and AI players at the lock (Story 5.12):
        # the Class session hears of it, and each Student who held a Seat reads it again.
        "games.set_snapshot": frozenset({"game", "session", "user"}),
        # The scheduling aid (Story 6.19, FR-22): a Student proposes a time to play, which the
        # Class session hears of and each other seated Student's `time_proposed` notice emits as
        # `user`; an acceptance tells every seated Student, so all see who accepted.
        "games.propose_time": frozenset({"game", "session", "user"}),
        "games.accept_time": frozenset({"game", "session", "user"}),
        # A due Takeover the sweep found but `takeover` refused (Story 8.3, AD-8): the time has
        # passed with no command, so the Game and its Class session are announced again.
        "ops.takeover_skipped": frozenset({"game", "session"}),
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
        # The Test-deadline lock (Story 12.1, the seam of Epic 11's `lock_test`, AD-9): it pins
        # the «KI-vurdering» switch, so the staff read the Klasseøkt again. A second run emits
        # nothing.
        "sessions.lock_test": frozenset({"session"}),
        # A late registrant seated, or a removed Student's Seat given to an AI player (Story
        # 5.13): the Seat changes through `games.assign_seat` (`game`), the staff read the
        # session again, and the Students of that game (and the one seated, with the allocation
        # notice) reload their pages.
        "sessions.seat_late_registrant": frozenset({"game", "session", "user"}),
        "sessions.replace_removed_student": frozenset({"game", "session", "user"}),
        # A deadline reminder (Story 5.14): one notice per Student, which emits `user`.
        "sessions.send_deadline_reminder": frozenset({"user"}),
        # One Student's reminder of their own Debrief or Test deadline (Story 11.13), likewise.
        "sessions.send_own_deadline_reminder": frozenset({"user"}),
        # The Play deadline playout of one Class game (Story 8.14), through `games.playout`.
        "sessions.playout": frozenset({"game", "session", "user"}),
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
        # A Lecturer corrected a step of a Student's Completion status (Story 13.3, AD-16): the
        # open Studentside and the Student's Hjem read it again. It records no step event.
        "reports.correct_completion": frozenset({"session", "user"}),
        # A Debrief session opened (Story 9.2, AD-21): created at step 1, its row locked;
        # opening one that exists emits nothing. A Group debrief's first open (Story 9.11) tells
        # the game's other Students, each `group_debrief_opened` notice emitting `user`.
        "debrief.open": frozenset({"debrief", "user"}),
        # A Student joined a Group debrief (Story 9.11, FR-43): the row locked; a second join
        # emits nothing.
        "debrief.join": frozenset({"debrief"}),
        # The opener moved a Group debrief's shared step pointer on (Story 9.11, FR-43).
        "debrief.move_on": frozenset({"debrief"}),
        # A Student went on alone from a Group debrief, by leaving or by the sweep's dropout
        # (Story 9.12, FR-43): the row locked; one alone already emits nothing.
        "debrief.leave": frozenset({"debrief"}),
        # Presence on each SSE heartbeat (Story 9.12): no Debrief row lock and no event.
        "debrief.touch": frozenset(),
        # The sweep's 48-hour fallback to a Personal debrief (Story 9.12, FR-43, AD-9): the row
        # locked; each Student told by a `debrief_fallback` notice, which emits `user`.
        "debrief.open_personal_fallback": frozenset({"debrief", "user"}),
        # A held Class session's Debriefs released by the sweep (Story 9.2, AD-9): each seated
        # Student's `debrief_released` notice emits `user`, so Hjem updates without reload.
        "debrief.release": frozenset({"user"}),
        # An Explanation sent (Story 9.3, FR-41, AD-16): the Debrief row locked; the
        # `explanation` step recorded in the same transaction emits `user` and `session`.
        "debrief.save_explanation": frozenset({"debrief", "session", "user"}),
        # A reflection answer stored (Story 9.6, FR-45), or a joined Student's «finished» on a
        # Group debrief's shared step, which may move the pointer (Story 9.11): the Debrief row
        # locked; an answer or mark stored already emits nothing.
        "debrief.complete_step": frozenset({"debrief"}),
        # The facts set of a Student's own moments recorded at their first view of step 4
        # (Story 9.7, AD-7): the Debrief row locked; one recorded already emits nothing.
        "debrief.record_facts": frozenset({"debrief"}),
        # A facts set's narration or quiz line stored by the `llm-batch` job (Story 9.14): no
        # event, since the text a Student reads is fixed at their first view.
        "debrief.store_ai_text": frozenset(),
        # A Student's answered or declined follow-up question stored (Story 9.15, FR-45): no event,
        # the asking page has the answer and no other reader sees it.
        "debrief.store_follow_up": frozenset(),
        # A Student's follow-up closed when their Individual test opens (Story 9.15, Epic 11's
        # call): `user`, so an open Debrief page replaces the field. Closed already emits nothing.
        "debrief.close_follow_up": frozenset({"user"}),
        # A Debrief finished (Story 9.8, FR-47, AD-16): the Debrief row locked; the `debrief`
        # step recorded in the same transaction emits `user` and `session`. A summary stored
        # already emits nothing.
        "debrief.finish": frozenset({"debrief", "session", "user"}),
        # A Debrief quiz attempt stored (Story 9.9, FR-46, AD-16): the Debrief row locked; a
        # passing one records `quiz_passed` in the same transaction, which emits `user` and
        # `session`.
        "debrief.submit_quiz": frozenset({"debrief", "session", "user"}),
        # The Debrief quiz exclusions of a Class session changed (Story 9.10, FR-46, AD-23): the
        # Class session row locked; its staff read the block again (`session`), and each Student
        # whose last attempt it now covers gets a `quiz_changed` notice, which emits `user`.
        "debrief.set_quiz_exclusions": frozenset({"session", "user"}),
        # A Class session's question set selection saved, «Lagre vekter» (Story 11.1, FR-52): its
        # staff read the block again.
        "tests.save_question_set": frozenset({"session"}),
        # A Class session's Scoring guide edited, «Lagre sensorveiledning» (Story 11.2, FR-81):
        # its staff read the block again.
        "tests.save_scoring_guide": frozenset({"session"}),
        # A Student accepted the own-work statement and opened their Individual test (Story 11.3,
        # FR-51): their other devices read the test again (`user`); the Debrief follow-up closed in
        # the same transaction emits `user` as well. Opening the one they have emits nothing.
        "tests.open_attempt": frozenset({"user"}),
        # A Student's answer autosaved (Story 11.4, AD-10): no event, the saving page has it and
        # another device reads it when it reads the test again; a save per click would refetch
        # the whole test on the saving device.
        "tests.save_answer": frozenset(),
        # A Student handed in their Individual test, «Lever testen» (Story 11.10, FR-51): the
        # `test_submitted` step recorded in the same transaction emits `user` (their Hjem and
        # other devices) and `session` (the Class session's overview). A repeat emits nothing.
        "tests.submit": frozenset({"session", "user"}),
        # An Individual test attempt closed at its Test deadline by the sweep (Story 11.11,
        # FR-51): an open one is auto-submitted and its `test_submitted` step emits `user` and
        # `session`, as at a hand-in; closing one handed in earlier emits nothing.
        "tests.close_attempt": frozenset({"session", "user"}),
        # A timed sitting ended before the Test deadline (Story 11.12, FR-51): the sweep hands the
        # attempt in, and its `test_submitted` step emits `user` and `session`, as at a hand-in.
        "tests.end_sitting": frozenset({"session", "user"}),
        # A Student's own Test deadline saved, «Lagre frist» (Story 11.13, FR-18): the Student's
        # Hjem and test read their own date (`user`), the Studentside reads its block (`session`).
        "tests.extend_deadline": frozenset({"session", "user"}),
        # A Student's Replay made and started (Story 10.3, FR-48): its Game is created, seated and
        # started through `games.commands` (`game`), and the Student's Hjem reads it again
        # (`user`). No Lecturer overview lists a Replay, so no `session`.
        "replay.start": frozenset({"game", "user"}),
        # A finished Replay's walkthrough line stored by the `llm-batch` job (Story 10.7): the
        # Student's waiting walkthrough page reads again (`user`).
        "replay.store_narration": frozenset({"user"}),
        # A Student's walkthrough stored at their first ready view (Story 10.7): no event, the
        # viewing page has it and no other reader sees it.
        "replay.record_walkthrough": frozenset(),
        # A Student's answer after their Replay-gjennomgang (Story 10.8, FR-50): whether they would
        # have played another round. No event: the page that sent it has it, and no other reader
        # may see it. (The believability answer is no `games.commands` command and emits none.)
        "replay.answer_another_round": frozenset(),
    }
)
"""`<module>.<command>` -> topics. Commands on a Game the Lecturer overview lists will add
`session` (AD-13); simulation Games never do. `games.finish` runs inside the transaction of the
command that completes the last Week and shares its one event, as an Order that
`players.ensure_order` places shares the event of the command that opened its Week."""
