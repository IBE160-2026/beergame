# replay

The Student's Replay (Epic 10): one round alone after the Debrief quiz, in the Role of their own
game, against three AI players, under the Class session's Replay scenario.

- **Owns:** `replays` (one row per Student and Class session, unique; names the `replay` Game);
  `replay_narrations` and `replay_walkthroughs` (Story 10.7, each written once).
- **Writes no game table.** Games, Seats and Weeks only through `games.commands`.
- **Reads** other modules only through `games.service`, `sessions.service`, `progress.service`
  and `content.service`; words AI text only through `app.ai.text` (with `ai.budget`,
  `ai.gateway.Inputs`).
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
- **Story 10.6:** policy `closes_at_test_deadline` (the Replay only). The sweep's
  `games.close_at_test_deadline` calls `games.commands.close(game, test_deadline, due=now)` for
  each unfinished Replay once its Student's `effective_test_deadline` (read through a reader
  `sessions` registers with `games.service`) has passed: `finished` with `end_reason =
  test_deadline`, no last Week, no finish hook (so no `replay` step), never played out; the
  Orders stay. `place_order` (and `view_week`) answer 409 `test_deadline_passed` on it, and a
  Student's own Order on a Replay past the deadline before the sweep has closed it; an AI
  player's may still complete a Week the Student ordered in time. `ai-orders` jobs and the rescue
  loop end on that code. `end_reason` comes with the Game (`games.service`, the card, Hjem's Replay,
  Spillinnsikt); a closed Replay has no `/result`, facts set or finished-game check.
- **Story 10.7:** `walkthrough.py` and `GET /api/me/games/{game_id}/walkthrough`
  (`getMyReplayWalkthrough`), for the Replay's own Student only (403 `forbidden` for anyone else):
  the Replay Seat's and the own Class game Seat's Week rows (Decision log `state_seen`: Netto
  lager, Order, running cost) and Totalkostnad, from the stored facts sets
  (`games.service.fact_set`, `analysis.facts` unchanged); the game compared with only through
  `games.service.student_game`. Moments by `analysis.moments.render` with the pinned templates:
  the two ranked first (pattern, later cost, Uke), every one when the Class game Seat has fewer
  than 10 Student Orders (`mostly_ai`, no Class game in the answer). 409 `replay_closed` (Story
  10.6) and `replay_not_finished`. The first ready view stores `replay_walkthroughs` (both
  `fact_set_id`s, the line shown then), so the line never changes under the Student.
- The line: the finish hook `replay.walkthrough` defers `replay.narrate_walkthrough(game_id)` on
  `llm-batch` (queueing lock `replay-walkthrough:<game>`) when the session's pinned Debrief AI
  text is on. The job words it through `app.ai.text.worded("replay_walkthrough", <Class session
  scope on the pin's config>, …)` with `analysis.validate_ai_text` and the code renderer
  `walkthrough.code_text` (mock answer: the code's own choice), stores it once per Replay facts set
  in `replay_narrations` and emits `user:<id>`. Until stored, and within
  `replay_walkthrough_wait_seconds` (placeholder 45) of the finish on the database clock, the
  answer is `pending` with `retry_after_seconds`; after it the code line shows unmarked. No sweep
  re-enqueues a lost job: the wait limit covers it. Production setup of a model config:
  `python -m app.ai.cli config edit <id> --prompt replay_walkthrough=1`, then measure and pin.

## The questions after the walkthrough (Story 10.8)

- `GET`/`POST /api/me/games/{game_id}/another-round` (`replay.questions`): «Ville du spilt en runde
  til?», `{answer: bool | null}`, stored once per Student and Class session in
  `replay_another_round` (201; a second answer `409 already_answered`, the first stands). Only the
  Replay's own Student (403 `forbidden` for anyone else); `409 replay_closed` and
  `replay_not_finished` as the walkthrough. No event, no name, no staff reader (Epic 14 reports).
- The believability question beside it is stored by `games` (`games.service.rate_believability`,
  table `believability_ratings`) and served from `sessions/routes.py` (`GET`/`POST
  /api/me/games/{id}/believability`, own game through `_own_locked_game`): a finished Replay
  always asks it.
