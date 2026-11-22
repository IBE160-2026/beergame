# replay

The Student's Replay (Epic 10): one round alone after the Debrief quiz, in the Role of their own
game, against three AI players, under the Class session's Replay scenario.

- **Owns:** `replays` (one row per Student and Class session, unique; names the `replay` Game).
- **Writes no game table.** Games, Seats and Weeks only through `games.commands`.
- **Reads** other modules only through `games.service`, `sessions.service` and `progress.service`.
- **Story 10.3:** `service.start(user, class_session_id)` and
  `POST /api/me/class-sessions/{session_id}/replay` (`startMyReplay`): 403 `quiz_required`
  without `quiz_passed`, 409 `test_deadline_passed` after `sessions.effective_test_deadline`,
  201 with a new Replay, 200 with the one the Student has. The Game is the Class session's frozen
  snapshot with `engine.replay_settings(pinned template, fresh seed)`; its `SessionRuntime` and
  `rules_version` stay the session's (AD-4). `replay_game_of` is registered with `sessions`, so
  Hjem (`/api/me/class-sessions`) shows the Replay without `sessions` importing this module.
- `games.policy` row `replay`: no Takeover, Pause or playout, not on the overview, snapshot at
  creation, no `class_game` step or pre-play gate, `projection` on (Story 10.4 draws it).
