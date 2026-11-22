# Epic 8 Context: Every game finishes: Pause, Takeover and deadlines

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

A missing Student must never block a Class game group, the Lecturer must be able to steer games, and every Class game must end by the Play deadline so all Students can reach the Debrief. The epic adds the game's own turn clock, automatic and manual Takeover by AI players, Reclaim, Pause, Lecturer controls (start, in-room, fill Seats, per-Student extra time), turn reminder mail and the Play deadline playout. Guided Weeks are covered too: opening a Week counts as ordering.

## Stories

- Story 8.1: Record when each Week opened and when each Seat ordered
- Story 8.2: An AI player takes over after the Inactivity limit
- Story 8.3: See on the Oversikt which Class game is closest to Takeover
- Story 8.4: Take the Seat back with «Ta tilbake setet»
- Story 8.5: Put an AI player in one Seat from Spillstyring
- Story 8.6: Pause the Class game with «Ta pause»
- Story 8.7: Pause a Class game with an agreed time as Lecturer
- Story 8.8: Put an AI player in an absent Seat as a Student
- Story 8.9: Give one Student more time with Tilrettelegging
- Story 8.10: Start one Class game or all of them as Lecturer
- Story 8.11: Mark a Class game as «I rommet» during a Lab hour
- Story 8.12: Fill every waited-for Seat in one action
- Story 8.13: Get an email when the game waits for your Order
- Story 8.14: Finish every unfinished Class game at the Play deadline

## Requirements & Constraints

- The system records per Seat when each Week opened and when the Student ordered.
- Automatic Takeover happens only when at least one other Student has ordered that Week and the absent Seat has waited the Inactivity limit. If nobody has ordered, nothing happens until the Play deadline; AI players never play a Class game on their own before then.
- Inactivity limit is set per Class session, default 24 hours, never below 20 hours. Shorter limits apply only to games the Lecturer marks as in the room during a Lab hour (default 10 min, range 2 to 120). A per-Student Tilrettelegging factor multiplies the limit and can only extend it.
- No automatic Takeover while paused. Pause does not move the Play deadline. Any Student or the Lecturer can pause; only the Lecturer sets an agreed time; any Student's Order ends a Pause. After the Seat's own time has run out (agreed time, else limit with adjustment), other Students may put an AI player in; no Student can shorten another's time.
- Lecturer or Assistant lecturer can trigger Takeover of any Seat; Lecturer can fill all waited-for Seats in one game or all games. A Reclaim is queued and takes effect when the next Week opens. AI-played Weeks stay marked as AI Weeks and never count as ordered by the Student.
- At the Play deadline every unfinished Class game (also never-started and paused ones) is played out with AI players; Students see it ended at the deadline and are led to the Debrief.
- Warnings and notices must never reveal the number of Weeks. Takeover notice mail is immediate; turn reminders are digest mail (max one per User per day, never 22:00 to 07:00 Europe/Oslo). Takeover must happen within one minute of the due time.
- Assistant lecturers may only insert an AI player per Seat and send Messages; other Spillstyring actions are Lecturer-only. Tilrettelegging stores no health data and no reason.
- Pages must reflow from 320 to 1440 px without horizontal scroll and pass axe. UI copy is Norwegian in `frontend/src/copy/nb.ts` and mail templates.

## Technical Decisions

- Only `games.commands` mutates games, Seats, occupancy, turns and Week states. Each command runs in one transaction with `SELECT … FOR UPDATE` on the Game row, increments `version` and emits events via `platform/events.emit` with a registry entry. Commands owned here: `takeover` (added in 8.2), `request_reclaim`, `pause`, `resume`, `set_agreed_time`, `mark_in_room`, `end_in_room`, `recompute_turn_times`, `playout`; `start` gains an `actor`. Every command calls `advance` after its own commit; a Week advances one at a time.
- Race outcomes are stable 409 codes (`seat_not_yours`, `takeover_exists`, `already_paused`, `not_paused`, `already_started`, `seat_not_student_held`, `insert_not_allowed_yet`, `game_not_ready`, `play_deadline_passed`). Decided in Story 8.5: a command that loses a race to a person or the system carries `fields.acted_by` (`kind` of `student`, `staff` or `system`, and `user_id`, null for the system) and `fields.acted_at`, ids only; the web app reads the name from the refreshed view, never from an error or log line. Later Spillstyring commands reuse this shape.
- One clock: `seat_turns` holds `opened_at`, `viewed_at`, `wait_started_at`, `takeover_due_at`, `insert_allowed_at`, `ai_deadline_at`, `ordered_at` (plus `reminder_due_at`); only `games.commands` writes them, and only the pure `games.rules.turn_times` computes them. `games.rules.can_take_over` is the only eligibility check (automatic, peer and staff; a Student actor must hold another Seat in the same Game and the target's `insert_allowed_at` must have passed, whether or not paused). `games.rules.waited_for(turn)` is the one waiting predicate shared with `game_status`. Views show stored times; nothing else derives them. In a Guided Week "has ordered" means `viewed_at` is set. On `place_order`, times are copied to the write-once `seat_week`.
- Game has `lifecycle` (`not_started`, `running`, `playing_out`, `finished`) separate from Pause columns (`paused_at`, `paused_by`, `resume_at`); only `pause`, `resume`, `place_order`, `playout` write them. A Student's `place_order` clears the Pause. Displayed status comes only from `games.rules.game_status`, stored in `game_summaries` and updated in the same transaction (new commands join the Story 7.1 recomputation test).
- Occupancy history is append-only with reasons `takeover_inactivity`, `takeover_staff`, `takeover_peer`, `reclaim`, `playout`, `guard_switch`, `cost_limit`. Decided in Story 8.2: the actor is a nullable `seat_occupancy.actor_user_id` (id only, names resolved at read time; migration 0054). A check constraint keeps it NULL for `initial`, `takeover_inactivity`, `guard_switch`, `cost_limit`, `playout` and `moved`; later stories set it to the staff member for `takeover_staff`, the pressing Student for `takeover_peer` and the Student for `reclaim`. `players.ensure_order` runs in the same transaction after any mid-Week Takeover. `takeover` takes a `staff` actor (reason `takeover_staff`, `actor_user_id` set, audit row `seat.taken_over`; Story 8.5); a Seat that has already ordered is taken from the next Week by a future-dated occupancy row, as `switch_to_rule_based` does. The new occupant is `llm` or `rule_based` per the session's AI mode, and `rule_based` if the Play guard switched the Seat or the cost-limit state is set. Playout LLM Orders go to `llm-batch` with no `ai_deadline_at`; a typed failure gives the Rule-based Order.
- `ops.sweep` (every minute, one item per transaction, idempotent) gains due actions for Takeover (`games.takeover`, added in 8.2), in-room end, reminders and playout. When time crosses a boundary it emits events; views carry `server_now` and `next_change_at` and the browser clock never decides. `game_summaries` also gains nearest `takeover_due_at`, pause state and in-room mark.
- Decided in Story 8.11: «I rommet» is stored on the Game (`in_room_minutes`, `in_room_until`, `in_room_lab_hour_id`, `in_room_by`, `in_room_marked_at`) and mirrored as `game_summaries.in_room_until`. `end_in_room` is the single way a mark ends: by a Lecturer («Ikke i rommet lenger», audited), by the `games.end_in_room` due action once `in_room_until` has passed (no actor), or via `games.service.lab_hour_changed` when its Lab hour is removed or moved so it is no longer on (no actor). A Lab hour moved but still on moves `in_room_until` through `mark_in_room` with no actor. Ending recomputes the open Week's due times from the stored wait starts. Whether a Lab hour is on is judged on the api clock; Lab hours are stored on.
- Still to be decided by Story 8.12 (recorded against the spine's Deferred item): batch Takeover as a loop of per-Seat `takeover` commands returning real counts.
- `games.policy(purpose)` decides whether Takeover, Pause and playout apply (Replay, lecturer-test and simulation Games are excluded); never branch on purpose elsewhere.
- Notifications go through `platform/notify.enqueue` (ids only, dedupe key); kinds `takeover_notice` (immediate) and `turn_reminder` (digest). Person-triggered Takeover, Pause and start are recorded through `platform/audit.record`. Authorization only through `platform/authz` policies. Per-Student adjustments live in `student_adjustments` owned by `modules/sessions`, read only via `sessions` `service.py`.
- Batch actions (start all, fill all Seats) loop one command per Game/Seat in separate transactions, skip and report failures, and are repeat-safe.
- Finishing a game by playout runs the same replay check as a normal finish and records the `class_game` step for every Student ever assigned to a Seat.

## UX & Interaction Patterns

- Student play screen and Hjem: Setestatus rows («Fabrikk  KI-spiller  bestiller for Jonas»), «Ta pause» with in-place Pausevalg, «Ta tilbake setet», polite-announced lines for Pause, Takeover, in-room and playout. Seats taken by AI keep the label «KI-spiller»; a Seat switched to a rule-based player by the Play guard says so on the same row.
- Lecturer: Spillinnsikt gets a «Spillstyring» block of in-place forms with consequence text directly above each secondary button; the Varselbånd shows the game closest to Takeover with countdown and actions; header Lenker lead to batch pages («Start spill», «Sett inn KI-spiller i alle seter»). Studentside with «Tilrettelegging» for Lecturers only.
- Keep one primary button per screen; only one in-place form open at a time. Focus moves to the first field or primary button when a form opens, «Avbryt» returns focus to the opener, and a result line replaces the form and takes focus (`tabindex="-1"`). Inline action errors keep the button active. Tap targets at least 44 px; actions full width below 1024 px. Students never see why a Seat's time differs or who has Tilrettelegging.

## Cross-Story Dependencies

- Builds on `seat_turns` and reference Orders (Stories 1.8, 2.6, 2.9), `wait_started_at` (6.14), `viewed_at` and Guided Week placement (6.10), start/finish checks (6.5, 6.18), the Oversikt, Varselbånd, Spillinnsikt and `game_summaries` (Epic 7, 7.7 and 7.11), the `ops.sweep` and notify delivery table (3.5), and `sessions.service.required_share` (5.7).
- Story 8.1 (clock, `turn_times`) underpins 8.2 to 8.14; 8.2 adds `takeover`, `can_take_over`, `actor_user_id` and the notices that 8.4, 8.5, 8.8 and 8.12 reuse; 8.5 adds the staff actor on `takeover` and the `acted_by` conflict shape that 8.6 to 8.12 reuse; 8.3 replaces Story 7.11's longest-wait choice; 8.6 adds Pause columns used by 8.7, 8.8 and 8.14; 8.9 extends `turn_times` and is read by 8.11; 8.11 adds the in-room columns, `mark_in_room`/`end_in_room` and the `games.service.lab_hour_changed` hook that Lab hour changes call; 8.14 clears Pause, in-room and Reclaim state.
- Epic 13 reuses the Studentside page (8.9) and the stored share of Weeks; Epic 11 reads the time factor; Epic 6 Debrief entry follows playout.
