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
- **Story 10.4:** the Replay is played on the Class game's routes (`/api/me/games/{id}`, `/play`,
  `/weeks/{w}/order`), not here: `games.service.own_game` gives a Game without a number that no
  Lecturer plays to the Student while they hold its Seat (`replay`, `projection` from the policy),
  `sessions` states its own settings as its rules and no Debrief, refuses a time proposal and the
  Starting task, and puts `projection` in `PlayOut`. Orders only through `place_order`.
- **Story 10.5:** the finish hook `replay.step` (`games.service.on_game_finished`) records
  `progress` `replay` at database time in the finishing transaction for the Game a `replays` row
  names (once; `user:<id>` and `session:<id>`), which unlocks the Individual test. Every worker
  imports `replay.jobs` (`platform.jobs.TASK_MODULES`), so an AI player's last Order records it
  too. Spillinnsikt: policy `staff_insight` opens the Replay to its Class's staff (`replay: true`);
  `insight_links` adds a `replay` link on the Student's Seat of the Class game's Spillinnsikt. The
  finished-game check is the sweep's `games.verify_finished`, which takes every finished Game.
  Dev only: `POST /api/dev/class-sessions/{id}/quiz-passed` records the logged-in Student's steps
  up to `quiz_passed` (for the end-to-end test of a real Replay), never mounted in production.
