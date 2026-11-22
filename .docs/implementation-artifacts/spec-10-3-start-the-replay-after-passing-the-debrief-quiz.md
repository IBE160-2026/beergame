---
title: 'Story 10.3: Start the Replay after passing the Debrief quiz'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '3e81126c79c4844c09a13c1d32f377091f9225ec'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-10-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-10-2-set-the-replay-scenario-freely.md'
warnings: ['oversized']
deferred:
  - summary: >-
      `games.repo.finished_student_seats` (Story 9.14 narration sweep) filters Games only on a
      Class session id, so a finished Replay would get Debrief facts and narration.
    evidence: |-
      repo.py ~956 filters `games.class_session_id.is_not(None)`, not `_listed()`; its docstring
      says Class game. Unreachable in 10.3 (nothing finishes a Replay yet); Story 10.5, which
      finishes Replays, must filter it on the policy (verification-gap review, other finding 1).
    location: >-
      backend/app/modules/games/repo.py:956
    severity: medium
---

<intent-contract>

## Intent

**Problem:** A Student who passed the Debrief quiz has no way to start their Replay: there is no `replay` Game purpose row, no start command, nothing on Hjem, and `games.commands.assign_seat` refuses a Student who already holds a Class game Seat in the same Class session.

**Approach:** A new backend slice `modules/replay` whose `service.start(user, class_session_id)` checks `quiz_passed` and the Test deadline, resolves the session's pinned template with a fresh seed, creates a `purpose=replay` Game from the Class session's frozen snapshot with only settings, series and seed replaced, seats the Student in their own Role and AI players of the session's AI mode in the others, and starts it; a `replays` table (unique Student + Class session) makes it idempotent. Hjem gets a Replay block («Start Replay», then the Replay's Setene) under the Class game.

## Boundaries & Constraints

**Always:** `games.policy` gets a `replay` row (no Takeover, no Pause, no playout, Guided Weeks from settings, not on the overview, snapshot at creation, Student occupants, belongs to the Class session without a number, no `class_game` step, no pre-play gate) and a new `projection` column, on only for `replay`. `modules/replay` writes no game table and imports other modules only through `games.service`, `games.commands`, `sessions.service` and `progress.service`. Role only from `games.service.student_game`; gate only `progress.has_step`; deadline only `sessions.service.effective_test_deadline`; template only `sessions.service.replay_template(row)` (the pin once locked). AI kind follows the snapshot runtime (`llm` with a model config, else `rule_based`); `_assign`'s cost-limit rule stays the one place that makes it `rule_based`/`cost_limit`. UI copy only in `nb.ts`; Hjem keeps one primary button.

**Never:** no play-screen access to the Replay (Story 10.4: `own_game`, rules, projection, «Fortsett Replay, Uke 9.»); no finish/`replay` step (10.5); no close at the Test deadline (10.6); no Takeover/playout sweep code (Epic 8 adds it; its finders must filter on the policy columns); no change to Class game seating rules; no test that plays a Game per test.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| First start | quiz passed, before Test deadline | 201 `{game_id}`; Game `replay`, running, own Role `student`, three AI Seats; settings = `replay_settings(pin, seed)`, `demand_seed = seed`, runtime/rules_version = frozen snapshot's | — |
| Second start / two at once | Replay exists | 200 with the same `game_id`; one Game, one `replays` row | unique key; loser's transaction rolled back |
| Start failed after commit | Replay row, Game `not_started` | next request starts it, 200 | `game_already_started` counts as done |
| No quiz | `quiz_passed` missing | — | 403 `quiz_required` |
| Deadline passed | `effective_test_deadline <= now`, no Replay | — | 409 `test_deadline_passed`; Hjem: no start, step note says Testfrist passed, not done |
| Not theirs | unknown id, unlocked session, other Class | — | 403 `forbidden` (FR-5) |
| LLM mode at cost limit | session `llm`, scope over limit | AI Seats `rule_based`, reason `cost_limit` | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/policy.py` -- `GamePolicy`, `POLICIES`, `BoolColumn`; add `projection` + `replay` row.
- `backend/app/modules/games/commands.py:316 create` (takes `snapshot=` + `class_session_id=` already, Story 6.20), `:527 assign_seat`, `:567 _assign` (`student_already_seated` at ~600 must apply only to Games the overview lists), `:1001 start`; `test_commands_never_branch_on_purpose` forbids purpose literals there.
- `backend/app/modules/games/repo.py:140 student_seated` / `:261 student_seat_count` -- count listed Games only (`_listed()`).
- `backend/app/modules/games/service.py:280 student_game`, `table_status`, `play_status`, `database_now`, `OccupantKind`.
- `backend/app/modules/sessions/service.py` -- pattern `start_test_game` (~4468); `replay_template(row)` (~3045, reads `row["snapshot"]` pins); `build_snapshot` (~3316); `effective_test_deadline` (~592); `is_locked`; `debrief_session_of` (~1492, own+listed+locked check); `enrolled_sessions` (~1224), `stegene` (~1315), `_seats_out`, provider registration pattern `register_debrief_state` (~1365).
- `backend/app/modules/sessions/schemas.py:597-650` -- `StepOut`, `EnrolledSessionOut`, `TableSeatOut`, `GamePlayStatus`.
- `backend/app/engine/{scenario.py replay_settings, demand.py new_seed}`; `progress.service.has_step`; `platform/events/registry.py COMMAND_TOPICS`.
- `backend/app/main.py` -- include routers; `backend/migrations/env.py` -- import models; `tests/test_migrations.py` HEAD + table sets; `tests/test_imports.py` boundary tests.
- Tests: `tests/sessions/test_student_home.py` (`home`, `ALL_LOCKED`, `confirmed` + `sweep.run(START + MINUTE)`), `tests/sessions/test_test_game.py` (fixtures), `tests/games/test_registry.py`.
- Frontend: `modules/games/student-hjem.tsx` (`SessionBlock`, `wantsPrimary`), `modules/games/home.ts stepItems`, `modules/games/game-action.tsx StartAction` (useAction pattern), `modules/games/seat-status-view.tsx GameSeatStatus`, `modules/sessions/api.ts EnrolledSession`, `copy/nb.ts homes.student`; e2e `student-home.spec.ts` (route-stub pattern).

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/games/policy.py` -- `projection: bool` column (False everywhere, True for replay), `replay` row, `BoolColumn` entry.
- `backend/app/modules/games/commands.py` -- one-Seat-per-session check only when the target Game's policy has `lecturer_overview`.
- `backend/migrations/versions/0116_replays.py` + `backend/app/modules/replay/models.py` -- `replays(id uuid pk, user_id fk users cascade, class_session_id fk class_sessions cascade, game_id fk games cascade unique, created_at timestamptz)`, unique `(user_id, class_session_id)`; env.py import; `test_migrations.py` HEAD 0116 + `REPLAY_TABLES`.
- `backend/app/modules/replay/{__init__,repo,service,routes,README}.py/md` -- `start` (matrix), `replay_game_of(s, user_id, session_id)` registered with sessions; `POST /api/me/class-sessions/{session_id}/replay` (`startMyReplay`, `games.start_own`), `ReplayStartOut{game_id}`; registry `replay.start: {game, user}`.
- `backend/app/modules/sessions/{service,schemas}.py` -- `enrolled_locked_row`, `register_replay_game`, `EnrolledSessionOut.replay: StudentReplayOut | None` (`can_start`, `game: ReplayGameOut{id, role, status, week, seats, server_now}`), `StepOut.closed`; `main.py` router.
- `backend/tests/replay/test_start.py` (new) -- matrix rows over the api on one or two Class sessions; policy row + `purposes_with` excludes replay for takeover/playout and a sweep leaves a running Replay as it was; registry topics; import boundary in `test_imports.py`.
- `frontend/src/modules/replay/{api.ts,replay-block.tsx,replay.ts,replay.test.ts}` (new) + `student-hjem.tsx` + `home.ts` -- Replay block under the game: title «Replay · Du er Grossist» once started with `GameSeatStatus`; before, consequence line + «Start Replay» (primary when no game primary), errors inline; `closed` note.
- `frontend/src/copy/nb.ts` + `open-assumptions.md` -- draft copy; regenerate api client.
- `frontend/e2e/replay-start.spec.ts` (new) -- stubbed Hjem: start → Setene with three «KI-spiller», Stegene Replay «pågår»; refused start shows its line; closed note; axe 320/1440.

**Acceptance Criteria:**
- Given a Student without `quiz_passed`, when Hjem shows, then the Replay step reads «Replay, åpnes når du har bestått Debrief-quizen.», no start control shows, and a start request answers 403 `quiz_required`.
- Given a started Replay, when the Student opens Hjem, then the Replay step is current («pågår») and the Replay's Setene name every AI Seat «KI-spiller», with no AI kind in the payload.
- Given `games.policy`, then `replay` is the only purpose with `projection` and is not in `purposes_with("inactivity_takeover")`, `("play_deadline_playout")`, `("pause")`, `("lecturer_overview")`.
- Given Hjem at 320 and 1440 px with the Replay block, then axe passes and there is one primary button.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Four layers (sonnet; a new Game purpose and its access rules make this a risky story): blind hunter, edge-case hunter, verification gap, intent alignment. Every hand-back failed; findings were read from `review-{blind,edge,verification,intent}-10-3.md` in the scratchpad.
- verdicts: 39 findings — high 0, medium 2, low 18, false 19, maybe-false 0
- findings:
  - `[low]` `[patch]` (blind 1) mojibake «Â«Start ReplayÂ»» in the `start` docstring (a PowerShell rewrite) — fixed; no other file affected (searched).
  - `[false]` `[reject]` (blind 2) Hjem offers «Start Replay» to a Student with no game — `replays` on Hjem are built only where `cards` (from `student_game`) exist; the OUTSIDER Hjem assertion now pins it.
  - `[low]` `[reject]` (blind 3) `next(... if seat.mine)` can raise — the Student's Replay Seat is assigned in the creating transaction and no command replaces a Student Seat of a Game the overview does not list (no Takeover, no move); a guard would cover an undemonstrated state.
  - `[low]` `[reject]` (blind 4) Hjem reads grow per locked session — only sessions with `quiz_passed` read the Replay; one or two per Student.
  - `[low]` `[reject]` (blind 5) unregistered provider answers "no Replay" — the same registration pattern as the Debrief providers; the api process imports `replay` through `main.py`.
  - `[low]` `[patch]` (blind 6) quiz/deadline judged outside the creating transaction — the Test deadline is now judged inside it, under the row's share lock (the quiz step is never removed). The `build_snapshot` fallback for a locked session without a snapshot stays (Design Notes).
  - `[false]` `[reject]` (blind 7) `lecturer_test` now skips `student_already_seated` — a Lecturer holds no Class game Seat, so the check could never refuse there; Class games keep it (`test_class_games.py:138`).
  - `[low]` `[reject]` (blind 8) consequence copy incomplete, no play link — draft copy for review; the play link is Story 10.4 (recorded in `open-assumptions.md`).
  - `[false]` `[reject]` (blind 9) `closed` only after `quiz_passed` — before the quiz the step is `locked`, which is also "not done"; the AC is about a Student who tries to start, which needs the quiz.
  - `[low]` `[reject]` (blind 10) concurrency and constraints weakly tested — the stale-read test drives the `ON CONFLICT … uq_replays_student` path; `uq_replays_game` cannot conflict (a new Game id).
  - `[low]` `[patch]` (blind 11) `replay.start` registry entry unpinned — grouped with verification 2.
  - `[low]` `[reject]` (blind 12) one long test, fixture re-exports, README — the shared-setup style the runbook asks for (one session per scenario chain); the re-export pattern is the suite's; the README lists `games.commands` as the write path.
  - `[low]` `[patch]` (edge 1) a 409 refusal re-reads Hjem, the block unmounts and its line goes — Stegene then says «ikke gjort, Testfristen er ute»; the component comment now says so (no code change).
  - `[medium]` `[patch]` (edge 2) a Replay stored but not started could not be started from Hjem — `can_start` is now true while the stored Replay is `ready` (before the Testfrist) and the block shows its Seats above «Start Replay»; test asserts it.
  - `[low]` `[reject]` (edge 3) = blind 3.
  - `[low]` `[patch]` (edge 4) = blind 6.
  - `[low]` `[reject]` (edge 5) a stored, never-started Replay is started after the Testfrist — needs a failed start before the deadline and a retry after it; Story 10.6 closes Replays at the deadline.
  - `[false]` `[reject]` (edge 6) other `CommandError`s from `start` become 500 — `game_not_ready` cannot happen (snapshot at creation) and `game_not_found` neither (the Game was just made or is named by `replays`).
  - `[low]` `[reject]` (edge 7) = blind 5.
  - `[false]` `[reject]` (edge 8) re-registration on reload — the app never reloads modules; same as the Debrief providers.
  - `[false]` `[reject]` (edge 9) a Replay is charged to the Class session budget — intended: `scope_of` charges every Game of a Class session, and the cost-limit rule must apply to Replays (AC).
  - `[false]` `[reject]` (edge 10) `model_config_id` missing from the snapshot runtime — `SessionRuntime.model_dump` always writes the key.
  - `[low]` `[patch]` (edge 11) the "refusal stays under the button" claim — = edge 1, comment corrected.
  - `[low]` `[patch]` (verification 1) the sweep step overclaims Takeover/playout — comment now says those actions do not exist yet and the policy columns are pinned in `test_policy.py`.
  - `[low]` `[patch]` (verification 2) registry entry unpinned — the start's emitted topics now equal `COMMAND_TOPICS["replay.start"]`.
  - `[low]` `[patch]` (verification 3) Hjem for a Student with no game not asserted — `home(OUTSIDER)["replay"] is None` added.
  - `[medium]` `[defer]` (verification other 1) `finished_student_seats` would include a finished Replay — unreachable until Story 10.5; deferred in frontmatter.
  - `[false]` `[reject]` (verification other 2) = edge 9.
  - `[false]` `[reject]` (verification other 3) = blind 7.
  - `[false]` `[reject]` (intent 1) locked-step text not asserted by the new test — existing string, pinned by `home.test.ts` and `student-home.spec.ts`; descriptive.
  - `[false]` `[reject]` (intent 2) «pågår» is the generic current note — the AC asks for "in progress in Stegene"; descriptive.
  - `[false]` `[reject]` (intent 3) «KI-spiller» checked as `ai` in api and as text on a stub — the reused `GameSeatStatus` maps it; descriptive.
  - `[false]` `[reject]` (intent 4) `closed` is a new field and string — recorded decision; descriptive.
  - `[false]` `[reject]` (intent 5) the block disappears after the Testfrist — matches the AC (Stegene); descriptive.
  - `[false]` `[reject]` (intent 6) no game → 403 `forbidden` — recorded in `open-assumptions.md`; descriptive.
  - `[false]` `[reject]` (intent 7) an existing Replay answers 200 after the Testfrist — follows the idempotent-start AC; descriptive.
  - `[false]` `[reject]` (intent 8) start after the commit — recovery path tested; descriptive.
  - `[false]` `[reject]` (intent 9) `create` needed no extension (6.20 added it) — descriptive.
  - `[false]` `[reject]` (intent 10) nothing reads `projection`, no play link — Story 10.4; descriptive.

## Design Notes

Idempotency: the fast path reads `replays` first. Otherwise one transaction creates the Game (`within=s`), assigns its Seats and inserts the `replays` row `ON CONFLICT DO NOTHING`; a concurrent second start waits on the unique index, gets no row back and raises a private sentinel so its Game rolls back, then reads the winner's row. `start` runs after the commit; `game_already_started` counts as done.

Snapshot: `row["snapshot"]` (the lock's frozen `build_snapshot`, with pins) is the base; a locked session without one (start date passed before the sweep) uses `build_snapshot(row)`. Replaced: `settings`, `demand_series = demand_series(settings)`, `demand_seed = seed`.

## Auto Run Result

Status: done

**Summary.** A new backend slice `modules/replay` (table `replays`, migration 0116, unique on Student and Class session) makes a Student's one Replay: `service.start` checks the Student's own locked session and game, `quiz_passed` (403 `quiz_required`) and, inside the creating transaction under the row's share lock, the Test deadline (409 `test_deadline_passed`); it draws a fresh seed, resolves the pinned template with `engine.replay_settings`, and creates a `replay` Game from the Class session's frozen snapshot with only settings, series and seed replaced, seats the Student in their own Role (`student_game`) and AI players of the session's AI mode in the others (cost limit → `rule_based`/`cost_limit`), then starts it after the commit. `POST /api/me/class-sessions/{id}/replay` answers 201 (new) or 200 (existing, also for two starts at once: the loser's Game rolls back). `games.policy` has a `replay` row and a new `projection` column (on only for `replay`); `assign_seat`'s one-Seat-per-session rule now applies to Class games only. Hjem's `/api/me/class-sessions` carries `replay` (`can_start`, the started Replay's Role, status and Seats, AI as `ai`) and `StepOut.closed`; the Hjem block «Replay» / «Start Replay» (primary when no game action is) becomes «Replay · Du er Grossist» with its Setene.

**Files.** Backend: `modules/replay/{__init__,models,repo,service,routes}.py`, `README.md` (new); `migrations/versions/0116_replays.py` (new), `migrations/env.py`; `modules/games/{policy,commands}.py`; `modules/sessions/{service,schemas}.py` (`enrolled_locked_row`, `replay_session_of`, `register_replay_game`, `test_deadline_passed`, `_replay_out`, `stegene(replay_closed=)`); `platform/events/registry.py`; `main.py`. Tests: `tests/replay/test_start.py` (new), `games/{test_policy,test_create}.py`, `sessions/{test_student_home,test_dates}.py`, `debrief/{test_debrief,test_quiz_exclusions}.py`, `test_imports.py`, `test_migrations.py`. Frontend: `modules/replay/{api.ts,replay.ts,replay-block.tsx,replay.test.ts}` (new), `modules/games/{student-hjem.tsx,home.ts,home.test.ts}`, `copy/nb.ts`, regenerated `lib/api/{openapi.json,schema.ts}`, `e2e/replay-start.spec.ts` (new). Docs: `open-assumptions.md`, refreshed `epic-10-context.md` (planning docs were newer than it).

**Decisions the founder would otherwise take.** (1) A `replays` table owned by `modules/replay` holds the unique key, rather than a column on `games`. (2) The started Replay is shown on Hjem with its Setene, without a way to play it; Story 10.4 opens the play screen to it. (3) «Start Replay» stands on Hjem under the Class game with a consequence line, and is the primary button only when no game action is. (4) A Student with no game in the Class session gets 403 `forbidden` and no Replay block. (5) After the Testfrist with no Replay, the Replay step stays current with the note «ikke gjort, Testfristen er ute» (new `StepOut.closed`). (6) A Replay started before the Testfrist is still returned after it (Story 10.6 closes it). (7) A Replay stored but not started (start failed after the commit) is offered «Start Replay» again. (8) The base snapshot is the lock's stored snapshot; a locked session without one is snapshotted now with `build_snapshot`. (9) The start reuses the `games.start_own` permission. (10) Takeover and playout sweep actions do not exist on this branch; the test pins the policy filter and runs a sweep over a running Replay. (11) All copy is draft (`open-assumptions.md`). (12) Implementation done in this context (runbook), four review layers (new Game purpose).

**Review.** 39 findings (four sonnet layers): 11 rows patched (1 medium entry: a stored-but-not-started Replay can be started from Hjem; lows: docstring encoding, deadline judged in the creating transaction, comments, three test assertions), 1 deferred (medium, Story 10.5: `finished_student_seats`), the rest rejected with reasons in the triage log. `followup_review_recommended: false`: one medium entry patched, with its own test.

**Verification.** Full backend suite `--maxprocesses=8`: 3138 passed, 4 skipped (116.9 s), after the last fix; an earlier run found one stale key-set assertion (`test_dates.py`, now with `replay`). ruff check and format clean. Frontend typecheck, Vitest 910 passed, `check:copy`, `lint:colours`, and `next build` (in the image) passed. Stack rebuilt after the last change. Playwright `--workers=4` on replay-start, student-home, homes, test-game, briefing, debrief-*, game-*, order-*, week-*, graph-over-table, seat-status, chain-band, guided-week, cost-panel, time-proposal, live-updates: 246 passed, 2 failed once and passed on rerun (`homes.spec.ts` «320 px › admin opens the product and lands on their own home», `order-confirm.spec.ts` «a send that fails keeps the value…»), neither touching Hjem's Replay. axe at 320 and 1440 px in the new spec (360 and 200 % text in `student-home.spec.ts`). New tests over 1 s: `test_a_student_who_passed_the_quiz_starts_one_replay_in_their_own_role` (about 2.4 s, one session through nine scenarios) and `test_llm_players_take_the_other_seats_and_the_cost_limit_makes_them_rule_based` (about 1.4 s).

**Merge check.** The merge with main put revisions 0051 and 0052 (Epic 7) below 0101, so databases stamped at 0115 before the merge lack `game_summaries`, `messages` and `message_recipients`; `alembic upgrade` cannot see it. The lane's shared test databases (`olspillet_test*` on port 5433) are in that state: resetting them was refused by the permission system, so the backend suite ran on fresh test databases (`DATABASE_URL=…/olspillet_m`). The lane's dev database got the two revisions' `upgrade()` applied directly (additive). Other lanes and environments stamped past 0052 before the merge need the same.

**Residual risks.** The Replay cannot be played until Story 10.4. Hjem trusts the Student's Replay Seat to stay theirs (no guard if a future command replaced it).

## Verification

**Commands:**
- `uv run pytest tests/replay tests/games/test_registry.py tests/sessions/test_student_home.py tests/test_imports.py tests/test_migrations.py -q` -- pass
- `npm run typecheck && npx vitest run src/modules/replay` -- pass
- full gate per runbook before commit
