---
title: 'Story 6.5: Start the Class game'
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: 'b4a0687df12249c5035b020d756d02e49eebf5be'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Student who has read the rules and done the Starting task has no way to start their Class game: the Starting task's done screen sends them to Hjem, Hjem offers nothing to start, `games.commands.start` emits only `game:`/`session:`, and there is no play route.

**Approach:** The api tells the web app each own game's play status (`not_ready | ready | running | finished`, plus the open Week while running) and gains `POST /api/me/games/{id}/start`, which runs `games.commands.start` (now also emitting `user:<id>` per Student in the Game). Hjem, the Starting task's done screen and a new play route `/spill/{id}` share one "next action" block: «Les reglene» → consequence line + «Start spillet» → «Gå til Uke n». The play route shows «Uke n», «Grossist, Spill 17» and the four Seats.

## Boundaries & Constraints

**Always:**
- `games.commands.start` stays the only start path (one transaction, Game row lock, version bump). After opening Week 1 it emits `user:<id>` for each Seat held by a Student (`occupant_kind == student` with a `user_id`); `session:` keeps coming from `_commit_change` for Lecturer-overview Games. Registry: `"games.start": {"game","session","user"}`. Simulation Games still emit only `game`.
- `StudentGameOut` gains `status` (`not_ready`: `not_started` without snapshot; `ready`: `not_started` with snapshot; `running`: `running` or `playing_out`; `finished`) and `week: int | None` (the open Week, only when `running`). Computed in `games.service.play_status(session, game_id)`; never the number of Weeks.
- `POST /api/me/games/{game_id}/start` (`sessions` routes, policy `games.start_own` = ANY_USER): same `_own_locked_game` checks as `GET /api/me/games/{id}` (else 403 `forbidden`, identical body); 409 `starting_task_required` without `progress` `starting_task`; 409 `game_not_ready` when `start` refuses so; `game_already_started` is treated as done; answers 200 with the fresh `StudentGameOut`.
- Web: one component decides the game's next action from `briefing_first` and `status`: briefing first → «Les reglene» (link to briefing); `ready` → «Spillet starter for alle fire. Reglene for ventetid gjelder fra nå.» above primary «Start spillet» (no dialog); `running` → primary link «Gå til Uke n» to `/spill/{id}`; `not_ready` → line «Spillet er ikke klart til å starte ennå.» [ASSUMPTION]. Hjem keeps one primary: the first listed game with an action; later ones render as Lenke / secondary button.
- On a successful start (or already started) the web app stores the answer under `myGameKey`, invalidates `enrolledSessionsKey`, and navigates to `/spill/{id}`. Errors through `useAction` messages: `game_not_ready` → the not-ready line, `starting_task_required` → «Gjør Startoppgaven først.» [ASSUMPTION], fallback «Spillet ble ikke startet. Prøv igjen.» [ASSUMPTION].
- The Starting task done screen keeps «Ferdig. Gå til Uke 1.» (focus target) and shows the same action block under it; «Til Hjem» as the primary only when `not_ready`. Copy `startsFromHome` is removed.
- Play route `frontend/src/app/(app)/spill/[gameId]/page.tsx` → `modules/games/play-page.tsx`: running → h1 «Uke n», line «Grossist, Spill 17» (`ink-secondary`), «Til Hjem» Lenke, «Setene» list (same holder words as Hjem, «KI-spiller»). Not running → h1 «Spill 17 · Du er Grossist» with the action block (finished: «Spillet er ferdig.» [ASSUMPTION]). Forbidden → the permission-denied page. Live: existing `game:`/`user:` topic map already invalidates `["games","mine",id]` and Hjem; `topics.ts` unchanged.
- Copy in `nb.ts` (`nb.games.start`, `nb.games.play`), drafts marked [ASSUMPTION]; no «Beer Game», no exclamation marks.

**Never:** No `started_by`/`started_at` columns or `actor` argument (Story 8.10); no `games.policy` columns (6.18); no Kjedebånd, week table, Ordrefelt, Totalkostnad or Setestatus status line (6.6+); no confirmation dialog; no change to `sprint-status.yaml` or «class-of-1994»; no dev/test backdoor route.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Start | own game `ready`, task done | 200, `status: running`, `week: 1`; events `game`, `session`, `user` × each Student | — |
| Already started | another started it first | 200 with the running card | none shown |
| Not ready | locked by date, no snapshot | 409 `game_not_ready`; card `status: not_ready`, no button | not-ready line |
| Task not done | no `starting_task` step | 409 `starting_task_required` | message line |
| Not own | other's game / unknown id / not uuid / before Start date | 403 `forbidden`, same body | access denied |
| Simulation start | `commands.start` on simulation | only `game:` | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/commands.py:937` `start` -- add `user:` emits after `_open_week`; `_commit_change` (:227) already emits `session:`; `seats_with_occupant` rows carry `occupant_kind`, `user_id`.
- `backend/app/platform/events/registry.py:11` -- `games.start` topics + comment.
- `backend/tests/games/test_registry.py` -- `_run_start` becomes a Class game with snapshot and a Student (setup emits 7 events: create 2, assign 2, set_snapshot 3); simulation runners use a separate `_started_simulation`.
- `backend/tests/games/test_start.py` -- add a Class-game start test for the user events.
- `backend/app/modules/games/repo.py:85` `get_game`, `:365` `open_week` -- for `play_status`; `games/service.py` `__all__` + new `PlayStatus` dataclass / `play_status`.
- `backend/app/modules/sessions/service.py:1219` `_game_out`, `:1241` `_own_locked_game`, `:1264` `student_game_of` -- add status/week; new `start_own_game`, `StartRefused`.
- `backend/app/modules/sessions/schemas.py:380` `StudentGameOut` -- `status`, `week`.
- `backend/app/modules/sessions/routes.py:574` -- new POST route next to `get_my_game`.
- `backend/app/platform/authz.py:105` -- `games.start_own`.
- `backend/tests/sessions/test_student_home.py` -- helpers `confirmed`, `sweep.run(START + MINUTE)`, `email(i)`, `call`; `progress.record_step(user, sid, "starting_task", NOW)`; monkeypatch `auth.utcnow` past START without sweep for `not_ready`; `tests/games/helpers.listening`.
- `frontend/src/modules/games/{api.ts,home.ts,student-hjem.tsx,starting-task-page.tsx}` -- `startGame`, action decision, Hjem wiring, Done block.
- `frontend/src/modules/identity/homes.ts:48` `gamePath` -- play route path.
- `frontend/src/lib/api/topics.ts` -- read-only; `user` → `enrolledSessionsKey`, `["games","mine"]`; `game` → `["games","mine",id]`.
- `frontend/e2e/starting-task.spec.ts`, `briefing.spec.ts`, `student-home.spec.ts` -- stand-in fixtures (`myGame`, `withHjem`) need `status`/`week`; `live-updates.spec.ts` `studentPage`, `untilLive`, `saveDates` patterns.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/games/commands.py`, `platform/events/registry.py` -- user events on start; registry entry.
- `backend/app/modules/games/service.py` -- `play_status`.
- `backend/app/modules/sessions/{schemas,service,routes}.py`, `platform/authz.py` -- status/week, `start_own_game`, route, policy.
- `backend/tests/games/test_registry.py`, `test_start.py`, `backend/tests/sessions/test_start_game.py` (new) -- matrix rows over the real api.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerate.
- `frontend/src/copy/nb.ts` -- `games.start`, `games.play`; drop `startingTask.startsFromHome`.
- `frontend/src/modules/games/home.ts` (+ `home.test.ts`) -- `nextAction(game)` and `weekLink` text.
- `frontend/src/modules/games/game-action.tsx` (new) -- the shared action block with the start mutation.
- `frontend/src/modules/games/student-hjem.tsx`, `starting-task-page.tsx` -- use it.
- `frontend/src/modules/games/play-page.tsx`, `frontend/src/app/(app)/spill/[gameId]/page.tsx` (new) -- play route.
- `frontend/e2e/game-start.spec.ts` (new) + fixture updates -- flows below with stand-ins for game state (a locked game needs the Start date, as in 6.3) and the real event stream.

**Acceptance Criteria:**
- Given a Student on Hjem whose own game is `ready` and Starting task done, when Hjem shows, then the one primary button is «Start spillet» with the consequence line above it, and pressing it posts the start once and lands on `/spill/{id}` showing «Uke 1», «Grossist, Spill 17» and the four Seats (axe clean at 320, 360, 1440 px).
- Given the Starting task just finished on a `ready` game, when the done screen shows, then «Ferdig. Gå til Uke 1.» has focus and «Start spillet» with its consequence line is under it.
- Given a game whose start answers `game_already_started`-as-done (200 running), when pressed, then the Student lands on the play route with no error.
- Given two Students on Hjem (`student7@`, `student8@` on a fresh Class, removed afterwards), when one starts the game and a real `user:` event reaches the other's stream, then the other sees «Gå til Uke 1» within 2 s without reload and focus has not moved.
- Given a `not_ready` game, when Hjem shows, then no «Start spillet» is offered and the not-ready line is shown.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 37 findings — high 0, medium 4, low 25, false 8, maybe-false 0
- findings:
  - `[false]` `[reject]` blind: a running game with no open Week links «Gå til Uke 1» to itself. A running or playing-out Game always has an opened, unfinished Week: `finish` runs in the transaction that completes the last Week and sets `finished`.
  - `[low]` `[patch]` blind: any unknown lifecycle reads as running. `play_status` now maps `running`/`playing_out` explicitly and raises on anything else.
  - `[low]` `[reject]` blind: other `start` refusals (`rules_version_unsupported`, `snapshot_mismatch`, `parameter_set_changed`) surface as 500. They are system faults, not Student states; a 500 is the honest answer.
  - `[low]` `[reject]` blind: an already running game still answers `starting_task_required` to a Student without the task. The web app never offers the start then (it shows «Les reglene»); the gate is the intended answer.
  - `[medium]` `[patch]` blind: the play route skipped the briefing gate for a running game. The play route now shows the game's next action («Les reglene») until `briefing_first` is false; new e2e case.
  - `[low]` `[reject]` blind: Hjem does not say the game started without the Student. An enhancement beyond the story; «Les reglene» leads them in.
  - `[low]` `[reject]` blind: «Ferdig. Gå til Uke 1.» can sit above a not-ready line. It is the spine's fixed done line (EXPERIENCE.md → Startoppgave Done).
  - `[low]` `[patch]` blind: the done screen showed «Til Hjem» while the game loaded, then swapped. It now renders nothing until the game read settles.
  - `[low]` `[patch]` blind: a refused start kept the stale «Start spillet». A refusal now re-reads the game and Hjem.
  - `[low]` `[reject]` blind: the two-Student e2e does not run the real start. Each link is pinned: the start's `user:` emits (`test_start.py`, `test_start_game.py`), `user` → Hjem key (`topics.test.ts`), refetch within 2 s with focus kept (e2e); joining them needs a test-only lock route the spec rules out.
  - `[low]` `[patch]` blind: "a simulation Game emits `game` alone" untested. True by policy (`student_occupants` off; `assign_seat` refuses Students); the registry comment now says why.
  - `[low]` `[patch]` blind: no record of who pressed «Start spillet». The log line now carries `user_id`; `started_by` is Story 8.10's column.
  - `[low]` `[reject]` blind: the checks and the start run in two transactions. Progress steps only accumulate and a Seat move needs a not-started Game; the window is negligible.
  - `[low]` `[reject]` blind: hard-coded setup event counts in the registry test. A changed count fails loudly at that test.
  - `[low]` `[patch]` blind: the not-ready string defined twice. One `NOT_READY` constant in `nb.ts`.
  - `[low]` `[patch]` edge: simulation Games with a Student Seat would emit `user:`. As blind 11.
  - `[false]` `[reject]` edge: running with `open_week` None. As blind 1.
  - `[false]` `[reject]` edge: self-link on the play route. As blind 1.
  - `[medium]` `[patch]` edge: the play route bypasses the briefing gate. As blind 5.
  - `[low]` `[patch]` edge: the done screen of a finished game had no primary control. It now shows «Til Hjem» as the primary whenever the game has no next action or cannot be read; e2e case.
  - `[false]` `[reject]` edge: `game_not_found` between check and start gives 500. No command deletes a Game.
  - `[low]` `[reject]` edge: access lost between start and re-read answers 403. Needs a Roster removal within the same request; the game is still correctly started.
  - `[low]` `[reject]` edge: the check and the start are not atomic. As blind 13.
  - `[low]` `[reject]` edge: undocumented 404/500 statuses on the route. 404 is unreachable (blind 6 / edge 6); 500 is never documented in this api.
  - `[low]` `[reject]` edge: the live e2e does not exercise the start event. As blind 10.
  - `[low]` `[patch]` edge: the registry comment claim about simulation Games. As blind 11.
  - `[low]` `[reject]` intent: the live-update AC is proven in pieces, not end to end. As blind 10.
  - `[low]` `[reject]` intent: "started first" is tested only at the api, never for the Lecturer. No Lecturer start exists until Story 8.10; the web app's landing on 200 is the same path as a fresh start.
  - `[low]` `[reject]` intent: browser tests run on stand-in game states. A locked game needs its Start date and the sweep (as in 6.2/6.3); the api's shapes are pinned by `test_start_game.py`.
  - `[low]` `[reject]` intent: a refused lock is not tested. A refused lock leaves the Game without its snapshot, the state `test_a_game_without_its_snapshot_is_not_ready` covers.
  - `[false]` `[reject]` intent: the registry "exactly" holds only on the Class path. A simulation Game cannot hold a Student or emit `session`, so the listed set is exact for the Games that take this route.
  - `[false]` `[reject]` intent: `starting_task_required` is stricter than the story. The story's precondition is "a Student who has done the Starting task"; the api enforcing it is the reading recorded in Design Notes.
  - `[false]` `[reject]` intent: «Ferdig. Gå til Uke 1.» is not a navigating button. EXPERIENCE.md lists it as the Startoppgave's Done state text; the screen showing it offers «Start spillet» directly.
  - `[medium]` `[patch]` verification-gap: `finished` and `playing_out` statuses untested. Added `test_a_game_that_plays_out_reads_running_and_a_finished_one_finished` (also: a start on a finished game counts as done).
  - `[medium]` `[patch]` verification-gap: the done screen's not-ready, finished and stale-briefing branches untested. Added «the done screen leads on from where the game stands» to `starting-task.spec.ts`.
  - `[false]` `[reject]` verification-gap (other): running with `week` null. As blind 1.
  - `[low]` `[reject]` verification-gap (other): the live e2e uses a different `user:` event. As blind 10.

All four reviewers finished; their reports were read from their transcripts. The orchestrator runs the visual check (visible screens changed: Hjem, Startoppgave done screen, new play route).

## Design Notes

Founder-level decisions: the api refuses a start before the Starting task (`starting_task_required`) rather than trusting the web app; the gate is asked for Class games only because this route only serves them (6.18 moves it to `games.policy`); a game started by someone else still shows «Les reglene» first until the Student has done the Starting task; `playing_out` reads as `running`; the play route for a finished game shows only «Spillet er ferdig.» until 6.18. E2E: a real locked game needs the Start date to pass and the sweep, so game state is a stand-in (as Stories 6.2/6.3) while the live refresh rides a real `user:` event on the real stream; the start's own emits are pinned by backend tests.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/games/test_registry.py tests/games/test_start.py tests/sessions/test_start_game.py tests/sessions/test_student_home.py -q` -- pass
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run build && npx playwright test --workers=2` -- pass

## Auto Run Result

Status: done

**Summary.** A Student can now start their Class game. `games.commands.start` additionally emits `user:<id>` for every Student holding a Seat (registry `games.start` = `game`, `session`, `user`). `StudentGameOut` (Hjem and `GET /api/me/games/{id}`) gains `status` (`not_ready | ready | running | finished`, from `games.service.play_status`) and `week` (the open Week while running). New `POST /api/me/games/{id}/start` (policy `games.start_own`) starts the own locked Class game through `games.commands.start`: 403 `forbidden` for any other game alike, 409 `starting_task_required` before the Starting task, 409 `game_not_ready` without a snapshot, and an already started game counts as done. In the web app one `GameAction` block decides the next step from `briefing_first` and `status` («Les reglene» → «Spillet starter for alle fire. Reglene for ventetid gjelder fra nå.» over «Start spillet» → «Gå til Uke n»; not-ready line otherwise), used on Hjem (one primary per page), on the Startoppgave done screen under «Ferdig. Gå til Uke 1.», and on the new play route `/spill/{id}`, which shows «Uke n», «Grossist, Spill 17», «Til Hjem» and «Setene». A press stores the answer, re-reads Hjem and lands on the play route; the existing `user:`/`game:` topic map refreshes other Students' Hjem live.

**Files.**
- `backend/app/modules/games/commands.py` -- `start` emits `user:` per seated Student.
- `backend/app/platform/events/registry.py` -- `games.start` topics.
- `backend/app/modules/games/service.py` -- `PlayStatus`, `play_status`.
- `backend/app/modules/sessions/{schemas,service,routes}.py`, `backend/app/platform/authz.py` -- `status`/`week`, `start_own_game`, `StartRefused`, the route, `games.start_own`.
- `backend/tests/games/test_registry.py`, `test_start.py`, `backend/tests/sessions/test_start_game.py` (new) -- registry on a Class game; start events; every matrix row over the real api.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerated (`startMyGame`).
- `frontend/src/copy/nb.ts` -- `games.start`, `games.play` (drafts [ASSUMPTION]); `startsFromHome` removed.
- `frontend/src/modules/games/{home.ts,home.test.ts,api.ts,game-action.tsx,play-page.tsx,student-hjem.tsx,starting-task-page.tsx}`, `frontend/src/app/(app)/spill/[gameId]/page.tsx` -- next action, start, play route.
- `frontend/e2e/game-start.spec.ts` (new); `starting-task.spec.ts`, `briefing.spec.ts`, `student-home.spec.ts`, `student-choice.spec.ts` -- fixtures gain `status`/`week`; done-screen branches.

**Review.** One pass, 37 findings (high 0, medium 4, low 25, false 8). Patched: 4 medium entries' worth (play-route briefing gate; finished/playing-out status test; done-screen branch tests) and 7 low (explicit lifecycle mapping, done screen waits for the game read and falls back to «Til Hjem», refused start re-reads, registry comment, `user_id` in the start log, one `NOT_READY` string). Deferred: none. Rejections with reasons in the triage log.

**Follow-up review:** true. Two or more medium entries were patched (play-route gate, done-screen fallback) and verified only by the suites, not reviewed again. Named risk: the play route's gate for a running game the Student has not been briefed on, and the done screen's loading/fallback logic.

**Founder-level decisions taken (no human in the loop).** The api enforces the pre-play gate on start (`409 starting_task_required`), for Class games through this route only (6.18 moves it to `games.policy`); a game started by another still shows «Les reglene» first on Hjem and on the play route until the Student has done the Starting task; `playing_out` reads as `running`; a finished game shows «Spillet er ferdig.» on the play route until 6.18; Hjem keeps one primary per page (first listed game with an action), others become a Lenke or secondary button; the done screen keeps «Ferdig. Gå til Uke 1.» as its text with the action under it; draft copy «Spillet er ikke klart til å starte ennå.», «Gjør Startoppgaven først.», «Spillet ble ikke startet. Prøv igjen.», «Spillet er ferdig.» and «Grossist, Spill 17» layout; e2e uses stand-in game states and a real `user:` event (Lecturer date save) for the live flow, since a real locked game needs the Start date and the sweep; demo `student7@` is registered on a fresh Class for that test and removed afterwards. The implementation ran in the orchestrating agent's own context (caller's runbook), not a separate implementation subagent.

**Verification.**
- Backend: 2659 passed (62 s); ruff check and format clean. New tests: `test_a_student_starts_the_game_and_everyone_in_it_hears_of_it` takes about 1.3 s (two Students, lock sweep and start), the others under 1 s.
- Frontend: typecheck, Vitest 495 passed, `check:copy`, build; compose rebuilt; full Playwright `--workers=2`: 319 passed (5.4 min). A first full run before the review patches had one failure in `admin-status.spec.ts` (deactivate/reactivate), untouched by this story; it passed on rerun and in the final run. New e2e tests: 0.3–1.6 s each, no fixed sleeps.
- No migration.

**Residual risks.** Draft copy awaits the founder (#31). The start → other Student's Hjem chain is verified in linked pieces, not in one real end-to-end run. `Spillet starter for alle fire` is shown even when fewer than four Students hold Seats (spine copy).

